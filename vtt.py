#!/usr/bin/python3

from gevent import monkey; monkey.patch_all()
from bottle import *

import os, json, time, sys, psutil, random

from pony import orm
from orm import db, db_session, Token, Game
from engine import engine, Engine, logging



__author__ = "Christian Glöckner"



# --- GM routes ---------------------------------------------------------------

# decorator for GM-routes
def asGm(callback):
	def wrapper(*args, **kwargs):
		session = request.get_cookie('session')
		if session is None:
			redirect('/vtt/join')
		return callback(*args, **kwargs)
	return wrapper

# shared login page
@get('/vtt/join')
@view('join')
def gm_login():
	return dict(engine=engine)

# non-patreon login
@post('/vtt/join')
def post_gm_login():
	status = {
		'url'   : None,
		'error' : ''
	}
	
	if engine.patreon_api is not None:
		# not allowed if patreon-login is enabled
		status['error'] = 'FORBIDDEN'
		return status
	
	# test gm name (also as url)
	if not engine.verifyUrlSection(request.forms.gmname):
		# contains invalid characters   
		status['error'] = 'NO SPECIAL CHARS OR SPACES'
		return status
		
	name = request.forms.gmname[:20].lower().strip()
	if name in engine.gm_blacklist:
		# blacklisted name
		status['error'] = 'RESERVED NAME'
		return status
		
	if len(db.GM.select(lambda g: g.name == name or g.url == name)) > 0:
		# collision
		status['error'] = 'ALREADY IN USE'
		return status
	
	# create new GM (use GM name as display name and URL)
	sid = db.GM.genSession()
	gm = db.GM(name=name, url=name, sid=sid)
	gm.postSetup()
	
	expires = time.time() + engine.expire
	response.set_cookie('session', sid, path='/', expires=expires, secure=engine.ssl)
	
	db.commit()
	status['url'] = gm.url
	return status

# patreon-login callback
@get('/vtt/patreon/callback')
def gm_patreon():
	if engine.patreon_api is None:
		# patreon is disabled, let him login normally
		redirect('/vtt/join')
	
	# query session from patreon auth
	session = engine.patreon_api.getSession(request)
	
	if session is None or session['sid'] is None:
		# not allowed, just redirect that poor soul
		redirect('/vtt/join')
	
	# test whether GM is already there
	gm = db.GM.select(lambda g: g.url == session['user']['id']).first()
	if gm is None:
		# create GM (username as display name, patreon-id as url)
		gm = db.GM(
			name=session['user']['username'],
			url=str(session['user']['id']),
			sid=session['sid']
		)
		gm.postSetup()
		
	else:
		# create new session for already existing GM
		gm.sid = session['sid']
	
	expires = time.time() + engine.expire
	response.set_cookie('session', gm.sid, path='/', expires=expires, secure=engine.ssl)
	
	db.commit()
	redirect('/')

@get('/', apply=[asGm])
@view('gm')
def get_game_list():
	gm = db.GM.loadFromSession(request)
	if gm is None:
		redirect('/vtt/join')
	# refresh session
	gm.refreshSession(response)
	
	server = ''
	if engine.local_gm:
		server = 'http://{0}:{1}'.format(engine.getDomain(), engine.port)
	
	# show GM's games
	return dict(engine=engine, gm=gm, server=server, dbScene=db.Scene)

@post('/vtt/import-game/<url>', apply=[asGm])
def post_import_game(url):  
	status = {
		'url_ok'  : False,
		'file_ok' : False,
		'error'   : '',
		'url'     : ''
	}
	
	# trim url length, convert to lowercase and trim whitespaces
	url = url[:20].lower().strip()
	
	# check GM and url
	gm = db.GM.loadFromSession(request) 
	if gm is None:
		status['error'] = 'RELOAD PAGE'
		return status
	
	if not engine.verifyUrlSection(url):
		status['error'] = 'NO SPECIAL CHARS OR SPACES'
		return status
	
	if db.Game.select(lambda g: g.admin == gm and g.url == url).first() is not None:
		status['error'] = 'ALREADY IN USE'
		return status
	
	# upload file
	files = request.files.getall('file')
	if len(files) != 1:
		status['error'] = 'ONE FILE AT ONCE'
		return status
	
	status['url_ok'] = True
	
	fname = files[0].filename
	if fname.endswith('zip'):
		game = db.Game.fromZip(gm, url, files[0])
	else:
		game = db.Game.fromImage(gm, url, files[0])
	
	status['file_ok'] = game is not None
	if not status['file_ok']:
		status['error'] = 'USE AN IMAGE FILE'
	
	status['url'] = game.getUrl();
	return status

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

@post('/vtt/kick-players/<url>', apply=[asGm])
def kick_players(url):
	gm = db.GM.loadFromSession(request)
	
	# load game
	game = db.Game.select(lambda g: g.admin == gm and g.url == url).first()
	
	# fetch game cache and close sockets
	game_cache = engine.cache.get(game)
	game_cache.closeAllSockets()

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
		server = 'http://{0}:{1}'.format(engine.getDomain(), engine.port)
	
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

@get('/token/<gmurl>/<url>/<fname>')
def static_token(gmurl, url, fname):
	# load game
	game = db.Game.select(lambda g: g.admin.url == gmurl and g.url == url).first()
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

@post('/<gmurl>/<url>/login')
def set_player_name(gmurl, url):
	result = {
		'playername'  : '',
		'playercolor' : '',
		'error'       : ''
	}
	
	playername  = template('{{value}}', value=format(request.forms.playername))
	playercolor = request.forms.get('playercolor')
	
	if playername == '':
		result['error'] = 'PLEASE ENTER A NAME'
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
	game = db.Game.select(lambda g: g.admin.url == gmurl and g.url == url).first()
	
	# check for player name collision
	try:
		game_cache = engine.cache.get(game)
		game_cache.insert(playername, playercolor)
	except KeyError:
		result['error'] = 'ALREADY IN USE'
		return result
	
	# save playername in client cookie
	expire = int(time.time() + engine.expire)
	response.set_cookie('playername', playername, path=game.getUrl(), expires=expire, secure=engine.ssl)
	response.set_cookie('playercolor', playercolor, path=game.getUrl(), expires=expire, secure=engine.ssl)
	
	result['playername']  = playername
	result['playercolor'] = playercolor
	return result


@get('/<gmurl>/<url>')
@view('battlemap')
def get_player_battlemap(gmurl, url):
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
	game = db.Game.select(lambda g: g.admin.url == gmurl and g.url == url).first()
	
	if game is None:
		abort(404)
	
	user_agent = request.environ.get('HTTP_USER_AGENT')
	protocol = 'wss' if engine.ssl else 'ws'
	websocket_url = '{0}://{1}:{2}/websocket'.format(protocol, engine.getDomain(), engine.port)
	
	# show battlemap with login screen ontop
	return dict(engine=engine, user_agent=user_agent, websocket_url=websocket_url, game=game, playername=playername, playercolor=playercolor, is_gm=gm is not None)

@post('/<gmurl>/<url>/upload/<posx:int>/<posy:int>/<default_size:int>')
def post_image_upload(gmurl, url, posx, posy, default_size):
	# upload images                       
	urls  = list()
	game  = db.Game.select(lambda g: g.admin.url == gmurl and g.url == url).first()
	files = request.files.getall('file[]')
	for handle in files:
		urls.append(game.upload(handle))
	
	# create tokens and broadcast creation
	game_cache = engine.cache.get(game)
	game_cache.onCreate((posx, posy), urls, default_size)

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
	# setup engine with cli args and db session
	engine.setup(sys.argv) 
	
	try:
		engine.run()
	except KeyboardInterrupt:
		pass

