#!/usr/bin/python3

from gevent import monkey; monkey.patch_all()
from bottle import *

import os, json, time, sys, psutil, random

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
			redirect('/vtt/join')
		return callback(*args, **kwargs)
	return wrapper


@get('/vtt/join')
@view('join')
def gm_login():
	return dict(engine=engine)


@post('/vtt/join')
def post_gm_login():
	# escape gmname and test whether something was replaced
	if not engine.verifyUrlSection(request.forms.gmname):
		# contains invalid characters
		return {'gmname': ''}
	
	# load gmname with limit of characters, in lowercase and strip whitespaces
	name = request.forms.gmname[:20] .lower().strip()
	
	if name in engine.gm_blacklist:
		# blacklisted name
		return {'gmname': ''}
	
	ip  = engine.getClientIp(request)
	sid = db.GM.genSession()
	
	if len(db.GM.select(lambda g: g.name == name)) > 0:
		# collision
		return {'gmname': ''}
	
	# create new GM
	gm = db.GM(name=name, ip=ip, sid=sid)
	gm.postSetup()
	
	# set cookie (will never expire)
	response.set_cookie('session', name, path='/')
	response.set_cookie('session', sid, path='/')

	db.commit()
	return {'gmname': gm.name}

@get('/', apply=[asGm])
@view('gm')
def get_game_list():
	gm = db.GM.loadFromSession(request)
	if gm is None:
		redirect('/vtt/join')
	
	server = ''
	if engine.local_gm:
		server = 'http://{0}:{1}'.format(engine.getIp(), engine.port)
	
	# show GM's games
	return dict(engine=engine, gm=gm, server=server, dbScene=db.Scene)

@post('/vtt/import-game/<url>', apply=[asGm])
def post_import_game(url):  
	url_ok = False
	game   = None
	
	# trim url length, convert to lowercase and trim whitespaces
	url = url[:20].lower().strip()
	
	# check GM and url
	gm = db.GM.loadFromSession(request) 
	if gm is not None and engine.verifyUrlSection(url) and db.Game.isUniqueUrl(gm, url):
		url_ok = True
	
	# upload file
	files = request.files.getall('file')
	if url_ok and len(files) == 1:
		fname = files[0].filename
		if fname.endswith('zip'):
			game = db.Game.fromZip(gm, url, files[0])
		
		else:
			game = db.Game.fromImage(gm, url, files[0])
	
	# returning status
	return {
		'url' : url_ok,
		'file': game is not None
	}

@get('/vtt/export-game/<url>', apply=[asGm])
def export_game(url):
	gm = db.GM.loadFromSession(request)
	if gm is None:
		redirect('/')
	
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	# export game to zip-file
	zip_file, zip_path = game.toZip()
	
	# offer file for downloading
	return static_file(zip_file, root=zip_path, download=zip_file, mimetype='application/zip')

@post('/vtt/delete-game/<url>', apply=[asGm])
@view('games')
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
	game.clear()
	game.delete()
	
	server = ''
	if engine.local_gm:
		server = 'http://{0}:{1}'.format(engine.getIp(), engine.port)
	
	return dict(gm=gm, server=server)

@post('/vtt/create-scene/<url>', apply=[asGm])
@view('scenes')
def post_create_scene(url):
	gm = db.GM.loadFromSession(request)
	
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	# create scene
	scene = db.Scene(game=game)
	db.commit()
	
	game.active = scene.id
	
	return dict(engine=engine, game=game)

@post('/vtt/activate-scene/<url>/<scene_id>', apply=[asGm])
@view('scenes')
def activate_scene(url, scene_id):
	gm = db.GM.loadFromSession(request)
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	game.active = scene_id

	db.commit()  
	
	# broadcase scene switch to all players
	game_cache = engine.cache.get(game)
	game_cache.broadcastSceneSwitch(game)
	
	return dict(engine=engine, game=game)

@post('/vtt/delete-scene/<url>/<scene_id>', apply=[asGm]) 
@view('scenes')
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
		db.commit()
		
	# broadcase scene switch to all players
	game_cache = engine.cache.get(game)
	game_cache.broadcastSceneSwitch(game)
	
	return dict(engine=engine, game=game)
	
@post('/vtt/clone-scene/<url>/<scene_id>', apply=[asGm]) 
@view('scenes')
def duplicate_scene(url, scene_id):
	gm = db.GM.loadFromSession(request)
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	# load required scene
	scene = db.Scene.select(lambda s: s.id == scene_id).first()
	
	# create copy of that scene
	clone = db.Scene(game=game)
	# copy tokens (but ignore background)
	for t in scene.tokens:
		if t.size != -1:
			n = db.Token(
				scene=clone, url=t.url, posx=t.posx, posy=t.posy, zorder=t.zorder,
				size=t.size, rotate=t.rotate, flipx=t.flipx, locked=t.locked
			)
	
	db.commit()
	
	game.active = clone.id 
	
	# broadcase scene switch to all players
	game_cache = engine.cache.get(game)
	game_cache.broadcastSceneSwitch(game)
	
	return dict(engine=engine, game=game)

# --- playing routes ----------------------------------------------------------

@get('/static/<fname>')
def static_files(fname):
	root = engine.data_dir / 'static'
	if not os.path.isdir(root) or not os.path.exists(root / fname):
		root = './static'
	
	return static_file(fname, root=root)

@get('/token/<gmname>/<url>/<fname>')
def static_token(gmname, url, fname):
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	path = game.getImagePath()
	
	return static_file(fname, root=path)

@get('/websocket')
def accept_websocket():
	socket = request.environ.get('wsgi.websocket')
	if socket is not None:
		engine.cache.accept(socket)
	
	# sleep until socket is closed
	while not socket.closed:
		time.sleep(10)

@post('/<gmname>/<url>/login')
def set_player_name(gmname, url):
	result = {'playername': '', 'playercolor': ''}
	
	playername  = template('{{value}}', value=format(request.forms.playername))
	playercolor = request.forms.get('playercolor')
	
	if playername is None:
		return result
	
	# limit length, trim whitespaces
	playername = playername[:30].strip()
	
	# make player color less bright
	parts       = [int(playercolor[1:3], 16), int(playercolor[3:5], 16), int(playercolor[5:7], 16)]
	playercolor = '#'
	for c in parts:
		if c > 200:
			c = 200
		if c < 16:
			playercolor += '0'
		playercolor += hex(c)[2:]
	 
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	
	# check for player name collision
	try:
		game_cache = engine.cache.get(game)
		game_cache.insert(playername, playercolor)
	except KeyError:
		# name collision
		return result
	
	# save playername in client cookie
	expire = int(time.time() + engine.expire)
	response.set_cookie('playername', playername, path=game.getUrl(), expires=expire)
	response.set_cookie('playercolor', playercolor, path=game.getUrl(), expires=expire)
	
	return {'playername': playername, 'playercolor': playercolor}


@get('/<gmname>/<url>')
@view('battlemap')
def get_player_battlemap(gmname, url):
	# try to load playername from cookie (or from GM name)
	playername = request.get_cookie('playername')
	gm         = db.GM.loadFromSession(request)
	if playername is None:
		if gm is not None:
			playername = gm.name
		else:
			playername = ''
	
	# try to load playercolor from cookieplayercolor = request.get_cookie('playercolor')
	playercolor = request.get_cookie('playercolor')
	if playercolor is None:   
		colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff']
		playercolor = colors[random.randrange(len(colors))]
	
	# load game
	game = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	
	if game is None:
		abort(404)
	
	user_agent = request.environ.get('HTTP_USER_AGENT')
	server_url = '{0}:{1}'.format(engine.getIp(), engine.port)
	print(server_url)
	
	# show battlemap with login screen ontop
	return dict(engine=engine, user_agent=user_agent, server_url=server_url, game=game, playername=playername, playercolor=playercolor, is_gm=gm is not None)

@post('/<gmname>/<url>/upload/<posx:int>/<posy:int>')
def post_image_upload(gmname, url, posx, posy):
	# upload images                       
	urls  = list()
	game  = db.Game.select(lambda g: g.admin.name == gmname and g.url == url).first()
	files = request.files.getall('file[]')
	for handle in files:
		urls.append(game.upload(handle))
	
	# create tokens and broadcast creation
	game_cache = engine.cache.get(game)
	game_cache.onCreate((posx, posy), urls)

@error(404)
@view('error')
def error404(error):
	return dict(engine=engine)

@get('/status')
@view('status')
def status_report():
	data = dict()  
	t = time.time()
	data['cpu_load']    = '{0}%'.format(psutil.cpu_percent())
	data['memory_load'] = '{0}%'.format(psutil.virtual_memory().percent)
	
	size, prefix = engine.getDatabaseSize()
	data['db_size']     = '{0} {1}B'.format(size, prefix)
	
	size, prefix = engine.getImageSizes()
	data['img_size']    = '{0} {1}B'.format(size, prefix)
	
	data['num_gms']     = orm.count(db.GM.select())
	data['num_games']   = orm.count(db.Game.select())
	data['num_scenes']  = orm.count(db.Scene.select())
	data['num_tokens']  = orm.count(db.Token.select())
	data['num_rolls']   = orm.count(db.Roll.select())
	data['num_players'] = PlayerCache.instance_count
	data['gen_time']    = time.time() - t
	
	return dict(engine=engine, data=data)

# --- setup stuff -------------------------------------------------------------

if __name__ == '__main__':
	try:
		engine.run()
	except KeyboardInterrupt:
		pass
