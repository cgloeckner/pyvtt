#!/usr/bin/python3

from bottle import *

import os, json, random, time, sys, math, logging, tempfile, zipfile, pathlib, shutil

from pony import orm
from orm import db, db_session, Token, Game, engine

__author__ = "Christian Glöckner"



# setup database connection
db.bind('sqlite', str(engine.data_dir / 'data.db'), create_db=True)
db.generate_mapping(create_tables=True)


# setup db_session to all routes
app = default_app()
app.catchall = not engine.debug
app.install(db_session)

# setup engine with cli args and db session
engine.setup(sys.argv)


# --- GM routes ---------------------------------------------------------------

# decorator for GM-routes
def asGm(callback):
	def wrapper(*args, **kwargs):
		session = request.get_cookie('session')
		if session is None:
			# force login
			redirect('/vtt/register')
		return callback(*args, **kwargs)
	return wrapper


@get('/vtt/register')
@view('register')
def gm_login():
	return dict()

@post('/vtt/register')
def post_gm_login():
	name = engine.applyWhitelist(request.forms.gmname).lower()
	if name in engine.gm_blacklist or len(name) < 3:
		redirect('/vtt/register')
	
	ip  = request.environ.get('REMOTE_ADDR')
	sid = db.GM.genSession()
	
	# create new GM
	gm = db.GM(name=name, ip=ip, sid=sid)
	gm.postSetup()
	
	response.set_cookie('session', name, path='/', expires=gm.expire)
	response.set_cookie('session', sid, path='/', expires=gm.expire)

	db.commit()
	redirect('/')

@get('/', apply=[asGm])
@view('gm')
def get_game_list():
	gm = db.GM.loadFromSession(request)
	if gm is None:
		# GM not found on the server
		response.set_cookie('session', '', path='/', expires=0)
		redirect('/vtt/register')
	
	server = ''
	if engine.local_gm:
		server = 'http://{0}:{1}'.format(engine.getIp(), engine.port)
	
	# show GM's games
	return dict(gm=gm, server=server, dbScene=db.Scene)

@post('/vtt/create-game', apply=[asGm])
def post_create_game():
	gm = db.GM.loadFromSession(request)
	
	url = engine.applyWhitelist(request.forms.game_url).lower()
	print(request.forms.game_url, "\t", url)
	
	# test for URL collision with other games of this GM
	if len(db.Game.select(lambda g: g.admin == gm and g.url == url)) > 0:
		redirect('/')
	
	# create game
	game = db.Game(url=url, admin=gm)
	
	game.postSetup()
	db.commit()
	
	# may import game from zip
	if isinstance(request.files.archive, str):
		# create first scene
		scene = db.Scene(game=game)
		db.commit()
		
		game.active = scene.id
		
	else:
		# unzip uploaded file to temp dir
		archive   = request.files.archive
		temp_dir  = tempfile.TemporaryDirectory()
		temp_path = pathlib.Path(temp_dir.name)
		zip_path  = temp_path / archive.filename
		archive.save(str(zip_path))
		with zipfile.ZipFile(zip_path, 'r') as h:
			h.extractall(temp_dir.name)
		
		# copy images to game directory
		img_path = game.getImagePath()
		for fname in os.listdir(temp_path):
			if fname.endswith('.png'):
				shutil.copyfile(temp_path / fname, img_path / fname)
		
		# create all game data
		data = dict()
		with open(temp_path / 'game.json', 'r') as h:
			data = json.load(h)
		
		for sid, s in enumerate(data["scenes"]):
			# create scene
			scene = db.Scene(game=game)
			
			# create tokens for that scene
			for token_id in s["tokens"]:
				token_data = data["tokens"][token_id]
				# create token
				t = db.Token(
					scene=scene, url=game.getImageUrl(token_data['url']),
					posx=token_data['posx'], posy=token_data['posy'],
					zorder=token_data['zorder'], size=token_data['size'], 	
					rotate=token_data['rotate'], flipx=token_data['flipx'],
					locked=token_data['locked']
				)
				if s["backing"] == token_id:
					db.commit()
					scene.backing = t
		
			if data["active"] == sid:
				db.commit()
				game.active = scene.id
	
	
	db.commit()
	redirect('/')

@get('/vtt/modify-game/<url>', apply=[asGm])
@view('settings')
def modify_game(url):
	gm = db.GM.loadFromSession(request)
	
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	return dict(gm=gm, game=game)

@post('/vtt/modify-game/<url>', apply=[asGm])
def post_modify_game(url):
	gm = db.GM.loadFromSession(request)
	
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	game.d4  = request.forms.get('d4') == 'on'
	game.d6  = request.forms.get('d6')  == 'on'
	game.d8  = request.forms.get('d8')  == 'on'
	game.d10 = request.forms.get('d10') == 'on'
	game.d12 = request.forms.get('d12') == 'on'
	game.d20 = request.forms.get('d20') == 'on'
	
	game.multiselect = request.forms.get('multiselect') == 'on'
	
	db.commit()
	redirect('/')

@get('/vtt/export-game/<url>', apply=[asGm])
def export_game(url):
	gm = db.GM.loadFromSession(request)
	
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	# remove abandoned images
	game.removeAbandonedImages()
	
	# collect all tokens in this game
	tokens = list()
	id_translation = dict() # required because the current token ids will not persist
	game_tokens = db.Token.select(
		lambda t: t.scene is not None
			and t.scene.game is not None 
			and t.scene.game == game
	)
	for t in game_tokens:
		tokens.append({
			"url"    : t.url.split('/')[-1], # remove game url (will not persist!)
			"posx"   : t.posx,
			"posy"   : t.posy,
			"zorder" : t.zorder,
			"size"   : t.size,
			"rotate" : t.rotate,
			"locked" : t.locked
		})
		id_translation[t.id] = len(tokens) - 1
	
	# collect all scenes in this game
	scenes = list()
	active = 0
	for s in game.scenes:
		tkns = list()
		for t in s.tokens:
			# query new id from translation dict
			tkns.append(id_translation[t.id])
		scenes.append({
			"tokens"  : tkns,
			"backing" : id_translation[s.backing.id]
		})
		if game.active == s.id:
			active = len(scenes) - 1
	
	data = {
		"tokens" : tokens,
		"scenes" : scenes,
		"active" : active
	}
	
	# build zip file
	zip_path = game.getExportPath()
	zip_file = '{0}.zip'.format(game.url)
	
	with zipfile.ZipFile(zip_path / zip_file, "w") as h:
		# create temporary file and add it to the zip
		with tempfile.NamedTemporaryFile() as tmp:
			s = json.dumps(data, indent=4)
			tmp.write(s.encode('utf-8'))
			h.write(tmp.name, 'game.json')
		# add images to the zip, too
		p = game.getImagePath()
		for img in game.getAllImages():
			h.write(p / img, img)

	# offer file for downloading
	return static_file(zip_file, root=zip_path, download=zip_file, mimetype='application/zip')


@get('/vtt/delete-game/<url>', apply=[asGm])
def delete_game(url):
	gm = db.GM.loadFromSession(request)
	
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
		
	# delete everything for that game
	# @note: doing by hand to avoid some weird cycle stuff (workaround)
	for s in game.scenes:
		for t in s.tokens:
			t.delete()
		s.backing = None
		s.delete()
	game.active = None
	game.clear() # also delete images from disk!
	game.delete()
	
	db.commit()
	redirect('/')

"""
@get('/vtt/list-game/<url>', apply=[asGm])
@view('game_details')
def get_game_details(url):
	gm = db.GM.loadFromSession(request)
	
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	return dict(game=game, server='{0}:{1}'.format(engine.getIp(), engine.port))
"""

@post('/vtt/create-scene/<url>', apply=[asGm])
def post_create_scene(url):
	gm = db.GM.loadFromSession(request)
	
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	# create scene
	scene = db.Scene(game=game)
	db.commit()
	
	game.active = scene.id

@post('/vtt/activate-scene/<url>/<scene_id>', apply=[asGm])
def activate_scene(url, scene_id):
	gm = db.GM.loadFromSession(request)
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	game.active = scene_id

	db.commit()

@post('/vtt/delete-scene/<url>/<scene_id>', apply=[asGm])
def activate_scene(url, scene_id):
	gm = db.GM.loadFromSession(request)
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()

	# delete given scene
	scene = db.Scene.select(lambda s: s.id == scene_id).first()
	scene.backing = None
	scene.delete()
	
	# check if active scene is still valid
	active = db.Scene.select(lambda s: s.id == game.active).first()
	if active is None:
		# check for remaining scenes
		remain = db.Scene.select(lambda s: s.game == game).first()
		if remain is None:
			# create new scene
			remain = db.Scene(game=game)
			db.commit()
		# adjust active scene
		game.active = remain.id

	
@post('/vtt/clone-scene/<url>/<scene_id>', apply=[asGm])
def duplicate_scene(url, scene_id):
	gm = db.GM.loadFromSession(request)
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	# load required scene
	scene = db.Scene.select(lambda s: s.id == scene_id).first()
	
	# create copy of that scene
	clone = db.Scene(game=game)
	# copy tokens, too
	backing = None
	for t in scene.tokens:
		n = db.Token(
			scene=clone, url=t.url, posx=t.posx, posy=t.posy, zorder=t.zorder,
			size=t.size, rotate=t.rotate, flipx=t.flipx, locked=t.locked
		)
		if n.size == -1:
			n.back = clone
	
	assert(len(scene.tokens) == len(clone.tokens))
	
	db.commit()
	
	game.active = clone.id

# --- playing routes ----------------------------------------------------------

@get('/static/<fname>')
def static_files(fname):
	return static_file(fname, root='./static')

@get('/token/<gmname>/<url>/<fname>')
def static_token(gmname, url, fname):
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	path = game.getImagePath()
	
	return static_file(fname, root=path)

@get('/<gmname>/<url>/login')
@view('login')
def player_login(gmname, url):
	gm = db.GM.loadFromSession(request)

	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	
	playername = ''
	if gm is not None:
		playername = gm.name
	
	# pick color (either from cookie or random)
	playercolor = request.get_cookie('playercolor')
	if playercolor is None:
		colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff']
		playercolor = colors[random.randrange(len(colors))]
	
	return dict(game=game, color=playercolor, playername=playername)

@post('/<gmname>/<url>/login')
@view('redirect')
def set_player_name(gmname, url):
	playername  = engine.applyWhitelist(request.forms.get('playername'))[:15]
	playercolor = request.forms.get('playercolor')
	
	# make player color less bright
	parts       = [int(playercolor[1:3], 16), int(playercolor[3:5], 16), int(playercolor[5:7], 16)]
	playercolor = '#'
	for c in parts:
		c //= 2
		if c < 16:
			playercolor += '0'
		playercolor += hex(c)[2:]
	
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	
	# save playername in client cookie (expire after 30 days)
	expire = int(time.time() + 3600 * 24 * 30)
	response.set_cookie('playername', playername, path=game.getUrl(), expires=expire)
	response.set_cookie('playercolor', playercolor, path=game.getUrl(), expires=expire)
	
	return dict(game=game, playername=playername)

@get('/<gmname>/<url>')
@view('battlemap')
def get_player_battlemap(gmname, url):
	# load player name and color from cookie
	playername  = request.get_cookie('playername')
	playercolor = request.get_cookie('playercolor')
	
	gm = db.GM.loadFromSession(request)
	
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
		
	# redirect to login if player not found
	if playername is None:
		redirect('{0}/login'.format(game.getUrl()))
	else:		
		return dict(game=game, playername=playername, playercolor=playercolor, is_gm=gm is not None)

# on window open
@post('/<gmname>/<url>/join')
def join_game(gmname, url):
	# load player name from cookie
	playername = request.get_cookie('playername')
	playercolor = request.get_cookie('playercolor')
	
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	game_url = game.getUrl()
	
	# save this playername
	if game_url not in engine.players:
		engine.players[game_url] = set()
	engine.players[game_url].add(playername)
	
	# save this playercolor
	if game_url not in engine.colors:
		engine.colors[game_url] = dict()
	engine.colors[game_url][playername] = playercolor

# on window close
@post('/<gmname>/<url>/disconnect')
def quit_game(gmname, url):
	# load player name from cookie
	playername = request.get_cookie('playername')
	
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	game_url = game.getUrl()
	
	# remove player
	if game_url in engine.players and playername in engine.players[game_url]:
		engine.players[game_url].remove(playername)
	
	# note: color is kept


# on logout purpose
@get('/<gmname>/<url>/logout')
def quit_game(gmname, url):
	# load player name from cookie
	playername = request.get_cookie('playername')
	playercolor = request.get_cookie('playercolor')

	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	game_url = game.getUrl()
	
	# reset cookie
	response.set_cookie('playername', playername, path=game.getUrl(), expires=0)
	# note: color is kept in cookies
	
	# remove player
	if url in engine.players and playername in engine.players[game_url]:
		engine.players[game_url].remove(playername)
	# note: color is kept in cache
	
	if url in engine.selected:
		# reset selection
		engine.selected[game_url][playercolor] = list()
	
	# show login page
	redirect(game.getUrl())

@post('/<gmname>/<url>/update')
def post_player_update(gmname, url):
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	game_url = game.getUrl()
	# load active scene
	scene = db.Scene.select(lambda s: s.id == game.active).first()
	
	now = int(time.time())
	
	# fetch token updates from client
	timeid   = float(request.POST.get('timeid'))
	changes  = json.loads(request.POST.get('changes'))
	if game_url not in engine.selected:
		engine.selected[game_url] = dict()
	# mark all selected tokens in that color
	playercolor = request.get_cookie('playercolor')
	ids = request.POST.get('selected')
	engine.selected[game_url][playercolor] = ids
	
	# update token data
	for data in changes:
		token = scene.tokens.select(lambda s: s.id == data['id']).first()
		if token is not None:
			# check for set-as-background
			if data['size'] == -1:
				# delete previous background
				if scene.backing is not None:
					scene.backing.delete()
				scene.backing = token
			
			# update token
			token.update(
				timeid=int(timeid),
				pos=(int(data['posx']), int(data['posy'])),
				zorder=data['zorder'],
				size=data['size'],
				rotate=data['rotate'],
				flipx=data['flipx'],
				locked=data['locked']
			)

	# query token data for that scene
	tokens = list()
	for t in scene.tokens.select(lambda t: t.scene == scene):
		# consider token if it was updated after given timeid
		if t.timeid >= timeid:
			tokens.append(t.to_dict())
	
	# query rolls (within last 180 seconds)
	rolls = list()
	for r in db.Roll.select(lambda r: r.game == game and r.timeid >= now - 180).order_by(lambda r: -r.timeid)[:13]:
		# query color by player
		color = '#000000'
		if game_url in engine.colors and r.player in engine.colors[game_url]:
			color = engine.colors[game_url][r.player]
		# consider token if it was updated after given timeid
		rolls.append({
			'player' : r.player,
			'color'  : color,
			'sides'  : r.sides,
			'result' : r.result,
			'time'   : time.strftime('%H:%M:%S', time.localtime(r.timeid))
		})
	
	# query players alive
	playerlist = list()
	for playername in engine.players[game_url]:
		playercolor = '#000000'
		if game_url in engine.colors and playername in engine.colors[game_url]:
			playercolor = engine.colors[game_url][playername]
		playerlist.append('{0}:{1}'.format(playername, playercolor))
	
	# return tokens, rolls and timestamp
	data = {
		'active'   : game.active,
		'timeid'   : time.time(),
		'full'     : timeid == 0,
		'tokens'   : tokens,
		'rolls'    : rolls,
		'players'  : playerlist,
		'selected' : engine.selected[game_url]
	}
	return json.dumps(data)

@post('/<gmname>/<url>/roll/<sides:int>')
def post_roll_dice(gmname, url, sides):
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.id == game.active).first()
	scene.timeid = int(time.time())
	
	# load player name from cookie
	playername = request.get_cookie('playername')
	
	# add player roll
	result = random.randrange(1, sides+1)
	db.Roll(game=game, player=playername, sides=sides, result=result, timeid=int(time.time()))

@post('/<gmname>/<url>/upload/<posx:int>/<posy:int>')
def post_image_upload(gmname, url, posx, posy):
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.id == game.active).first()
	scene.timeid = int(time.time())
	
	# upload all files to the current game
	# and create a token each
	files = request.files.getall('file[]')
	
	tokens = list(db.Token.select(lambda t: t.scene == scene))
	if len(tokens) > 0:
		bottom = min(tokens, key=lambda t: t.zorder).zorder - 1
		if bottom == 0:
			bottom = -1
		top    = max(tokens, key=lambda t: t.zorder).zorder + 1
	else:
		bottom = -1
		top = 1
	
	# place tokens in circle around given position
	n = len(files)
	if n > 0:
		degree = 360 / n
		radius = 32 * n**0.5
		if n == 1:
			radius = 0
		for i, handle in enumerate(files):
			# move with radius-step towards y direction and rotate this position
			s = math.sin(i * degree * 3.14 / 180)
			c = math.cos(i * degree * 3.14 / 180)
			
			kwargs = {
				"scene"  : scene,
				"timeid" : scene.timeid,
				"url"    : game.upload(handle),
				"posx"   : int(posx - radius * s),
				"posy"   : int(posy + radius * c)
			}
			
			# determine file size to handle different image types
			size = game.getFileSize(kwargs["url"])
			if size < 250 * 1024:
				# files smaller 250kb as assumed to be tokens
				kwargs["zorder"] = top
				
			else:
				# files larger 250kb are handled as decoration (index cards) etc.)
				kwargs["size"]   = 300
				kwargs["zorder"] = bottom
				
			# create token
			db.Token(**kwargs)
		
	db.commit()

@post('/<gmname>/<url>/clone/<token_id:int>/<x:int>/<y:int>')
def ajax_post_clone(gmname, url, token_id, x, y):
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.id == game.active).first()
	# update position
	scene.timeid = int(time.time())
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# clone token
	db.Token(scene=token.scene, url=token.url, posx=x, posy=y,
		zorder=token.zorder, size=token.size, rotate=token.rotate,
		flipx=token.flipx, timeid=int(time.time()))

@post('/<gmname>/<url>/delete/<token_id:int>')
def ajax_post_delete(gmname, url, token_id):
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.id == game.active).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	if token is not None:
		# delete token
		token.delete()


# --- setup stuff -------------------------------------------------------------

app = default_app()

if engine.debug:
	run(host=engine.host, reloader=True, debug=True, port=engine.port)	
else:
	from paste import httpserver
	httpserver.serve(app, host=engine.host, port=engine.port)


