#!/usr/bin/python3

from gevent import monkey; monkey.patch_all()
from bottle import *

import os, json, time, sys, psutil, random, subprocess, requests

from pony import orm
from engine import engine
from cache import PlayerCache



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
		engine.logging.access('Failed GM login by {0}: needs to use patreon.'.format(engine.getClientIp(request)))
		return status
	
	# test gm name (also as url)
	gmame = request.forms.gmname
	if not engine.verifyUrlSection(gmname):
		# contains invalid characters   
		status['error'] = 'NO SPECIAL CHARS OR SPACES'
		engine.logging.access('Failed GM login by {0}: invalid name "{1}".'.format(engine.getClientIp(request), gmname))
		return status
		
	name = gmname[:20].lower().strip()
	if name in engine.gm_blacklist:
		# blacklisted name
		status['error'] = 'RESERVED NAME'  
		engine.logging.access('Failed GM login by {0}: reserved name "{1}".'.format(engine.getClientIp(request), gmname))
		return status
		
	if len(engine.main_db.GM.select(lambda g: g.name == name or g.url == name)) > 0:
		# collision
		status['error'] = 'ALREADY IN USE'   
		engine.logging.access('Failed GM login by {0}: name collision "{1}".'.format(engine.getClientIp(request), gmname))
		return status
	
	# create new GM (use GM name as display name and URL)
	sid = engine.main_db.GM.genSession()
	gm = engine.main_db.GM(name=name, url=name, sid=sid)
	gm.postSetup()
	
	expires = time.time() + engine.expire
	response.set_cookie('session', sid, path='/', expires=expires, secure=engine.ssl)
	
	engine.logging.access('GM created with name="{0}" url={1} by {2}.'.format(gm.name, gm.url, engine.getClientIp(request)))
	
	engine.main_db.commit()
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
	gm = engine.main_db.GM.select(lambda g: g.url == session['user']['id']).first()
	if gm is None:
		# create GM (username as display name, patreon-id as url)
		gm = engine.main_db.GM(
			name=session['user']['username'],
			url=str(session['user']['id']),
			sid=session['sid']
		)
		gm.postSetup()
		engine.main_db.commit()
		
		# add to cache and initialize database
		engine.cache.insert(gm)
		#gm_cache = engine.cache.get(gm)
		
		engine.logging.access('GM created using patreon with name="{0}" url={1} by {2}.'.format(gm.name, gm.url, engine.getClientIp(request)))
		
	else:
		# create new session for already existing GM
		gm.sid = session['sid']
		
	gm.refreshSession(response, request)
	
	engine.logging.access('GM name="{0}" url={1} session refreshed using patreon by {2}'.format(gm.name, gm.url, engine.getClientIp(request)))
	
	engine.main_db.commit()
	redirect('/')

@get('/', apply=[asGm])
@view('gm')
def get_game_list():
	gm = engine.main_db.GM.loadFromSession(request)
	if gm is None:
		# remove cookie
		response.set_cookie('session', '', path='/', expires=1, secure=engine.ssl)
		redirect('/')
	
	# refresh session
	gm.refreshSession(response, request)
	
	engine.logging.access('GM name="{0}" url={1} session refreshed by {2}'.format(gm.name, gm.url, engine.getClientIp(request)))
	
	server = ''
	if engine.local_gm:
		server = 'http://{0}:{1}'.format(engine.getDomain(), engine.port)
	
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	# load game from GM's database
	all_games = gm_cache.db.Game.select()
	
	# show GM's games
	return dict(engine=engine, gm=gm, all_games=all_games, server=server)

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
	gm = engine.main_db.GM.loadFromSession(request) 
	if gm is None:
		abort(401)
	
	if not engine.verifyUrlSection(url):
		engine.logging.access('GM name="{0}" url={1} tried to import game by {2} but game url "{3}" is invalid'.format(gm.name, gm.url, engine.getClientIp(request), url))
		status['error'] = 'NO SPECIAL CHARS OR SPACES'
		return status
	
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	if gm_cache.db.Game.select(lambda g: g.url == url).first() is not None:
		engine.logging.access('GM name="{0}" url={1} tried to import game by {2} but game url "{3}" already in use'.format(gm.name, gm.url, engine.getClientIp(request), url))
		status['error'] = 'ALREADY IN USE'
		return status
	
	# upload file
	files = request.files.getall('file')
	if len(files) != 1:
		engine.logging.access('GM name="{0}" url={1} tried to import game by {2} but uploaded {3} files'.format(gm.name, gm.url, engine.getClientIp(request), len(files)))
		status['error'] = 'ONE FILE AT ONCE'
		return status
	
	status['url_ok'] = True
	
	fname = files[0].filename
	is_zip = fname.endswith('zip')
	if is_zip:
		game = gm_cache.db.Game.fromZip(gm, url, files[0])
	else:
		game = gm_cache.db.Game.fromImage(gm, url, files[0])
	
	status['file_ok'] = game is not None
	if not status['file_ok']:
		engine.logging.access('GM name="{0}" url={1} tried to import game by {2} but uploaded neither an image nor a zip file'.format(gm.name, gm.url, engine.getClientIp(request), url))
		status['error'] = 'USE AN IMAGE FILE'
		return status
	
	if is_zip:
		engine.logging.access('Game {0} imported from "{1}" by {2}'.format(game.getUrl(), fname, engine.getClientIp(request)))
	else:
		engine.logging.access('Game {0} created from "{1}" by {2}'.format(game.getUrl(), fname, engine.getClientIp(request)))
	
	status['url'] = game.getUrl();
	return status

@get('/vtt/export-game/<url>', apply=[asGm])
def export_game(url):
	gm = engine.main_db.GM.loadFromSession(request)
	# note: asGm guards this
	
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	
	# export game to zip-file
	zip_file, zip_path = game.toZip()
	 
	engine.logging.access('Game {0} exported by {1}'.format(game.getUrl(), engine.getClientIp(request)))
	
	# offer file for downloading
	return static_file(zip_file, root=zip_path, download=zip_file, mimetype='application/zip')

@post('/vtt/kick-players/<url>', apply=[asGm])
def kick_players(url):
	gm = engine.main_db.GM.loadFromSession(request)
	# note: asGm guards this
	
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	
	# load game from cache and close sockets
	game_cache = gm_cache.get(game)
	game_cache.closeAllSockets()
	
	engine.logging.access('Players kicked from {0} by {1}'.format(game.getUrl(), engine.getClientIp(request)))

@post('/vtt/kick-player/<url>/<uuid>', apply=[asGm])
def kick_player(url, uuid):
	gm = engine.main_db.GM.loadFromSession(request)
	# note: asGm guards this
	
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	
	# fetch game cache and close sockets
	game_cache = gm_cache.get(game)
	name = game_cache.closeSocket(uuid)
	
	engine.logging.access('Player {0} ({1}) kicked from {2} by {3}'.format(name, uuid, game.getUrl(), engine.getClientIp(request)))


@post('/vtt/delete-game/<url>', apply=[asGm])
@view('games')
def delete_game(url):
	gm = engine.main_db.GM.loadFromSession(request)
	if gm is None:
		abort(401)
	
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	
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
	
	engine.logging.access('Game {0} deleted by {1}'.format(game.getUrl(), engine.getClientIp(request)))
	
	server = ''
	if engine.local_gm:
		server = 'http://{0}:{1}'.format(engine.getDomain(), engine.port)
	
	return dict(gm=gm, server=server)

@post('/vtt/create-scene/<url>', apply=[asGm])
@view('scenes')
def post_create_scene(url):
	gm = engine.main_db.GM.loadFromSession(request)  
	if gm is None:
		abort(401)
	
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	
	# create scene
	scene = gm_cache.db.Scene(game=game)
	gm_cache.db.commit()
	
	engine.logging.access('Game {0} got a new scene by {1}'.format(game.getUrl(), engine.getClientIp(request)))
	
	return dict(engine=engine, game=game)

@post('/vtt/activate-scene/<url>/<scene_id>', apply=[asGm])
@view('scenes')
def activate_scene(url, scene_id):
	gm = engine.main_db.GM.loadFromSession(request) 
	if gm is None:
		abort(401)
	
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	game.active = scene_id

	gm_cache.db.commit()  
	
	# broadcase scene switch to all players
	game_cache = gm_cache.get(game)
	game_cache.broadcastSceneSwitch(game)
	
	engine.logging.access('Game {0} switched scene to #{1} by {2}'.format(game.getUrl(), scene_id, engine.getClientIp(request)))
	
	return dict(engine=engine, game=game)

@post('/vtt/delete-scene/<url>/<scene_id>', apply=[asGm]) 
@view('scenes')
def activate_scene(url, scene_id):
	gm = engine.main_db.GM.loadFromSession(request)
	if gm is None:
		abort(401)
	 
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()

	# delete given scene
	scene = gm_cache.db.Scene.select(lambda s: s.id == scene_id).first()
	scene.backing = None
	scene.delete()
	
	# check if active scene is still valid
	active = gm_cache.db.Scene.select(lambda s: s.id == game.active).first()
	if active is None:
		# check for remaining scenes
		remain = gm_cache.db.Scene.select(lambda s: s.game == game).first()
		if remain is None:
			# create new scene
			remain = gm_cache.db.Scene(game=game)
			gm_cache.db.commit()
		# adjust active scene
		game.active = remain.id
		gm_cache.db.commit()
		
	# broadcase scene switch to all players
	game_cache = gm_cache.get(game)
	game_cache.broadcastSceneSwitch(game)
	
	engine.logging.access('Game {0} got scene #{1} deleted by {2}'.format(game.getUrl(), scene_id, engine.getClientIp(request)))
	
	return dict(engine=engine, game=game)
	
@post('/vtt/clone-scene/<url>/<scene_id>', apply=[asGm]) 
@view('scenes')
def duplicate_scene(url, scene_id):
	gm = engine.main_db.GM.loadFromSession(request)
	if gm is None:
		abort(401)
			  
	# load GM from cache
	gm_cache = engine.cache.get(gm)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	
	# load required scene
	scene = gm_cache.db.Scene.select(lambda s: s.id == scene_id).first()
	
	# create copy of that scene
	clone = gm_cache.db.Scene(game=game)
	# copy tokens (but ignore background)
	for t in scene.tokens:
		if t.size != -1:
			n = gm_cache.db.Token(
				scene=clone, url=t.url, posx=t.posx, posy=t.posy, zorder=t.zorder,
				size=t.size, rotate=t.rotate, flipx=t.flipx, locked=t.locked
			)
	
	gm_cache.db.commit()
	
	game.active = clone.id 
	
	# broadcase scene switch to all players
	game_cache = gm_cache.get(game)
	game_cache.broadcastSceneSwitch(game)
	
	engine.logging.access('Game {0} got clone of scene #{1} as #{2} by {1}'.format(game.getUrl(), scene_id, clone.id, engine.getClientIp(request)))
	
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
	# load GM from cache
	gm_cache = engine.cache.getFromUrl(gmurl)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	path = game.getImagePath()
	
	return static_file(fname, root=path)

@get('/websocket')
def accept_websocket():
	socket = request.environ.get('wsgi.websocket')
	
	if socket is not None:
		# note: this keeps the websocket open during the session
		engine.cache.listen(socket)

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
		engine.logging.access('Player tried to login {0} by {1}, but did not provide a username.'.format(game.getUrl(), engine.getClientIp(request)))
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
			  
	# load GM from cache
	gm_cache = engine.cache.getFromUrl(gmurl)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	
	# check for player name collision
	try:
		game_cache = gm_cache.get(game)
		game_cache.insert(playername, playercolor)
	except KeyError:
		engine.logging.access('Player tried to login {0} by {1}, but username "{2}" is already in use.'.format(game.getUrl(), engine.getClientIp(request), playername))
		result['error'] = 'ALREADY IN USE'
		return result
	
	# save playername in client cookie
	expire = int(time.time() + engine.expire)
	response.set_cookie('playername', playername, path=game.getUrl(), expires=expire, secure=engine.ssl)
	response.set_cookie('playercolor', playercolor, path=game.getUrl(), expires=expire, secure=engine.ssl)
	
	engine.logging.access('Player logged in to {0} by {1}.'.format(game.getUrl(), engine.getClientIp(request)))
	
	result['playername']  = playername
	result['playercolor'] = playercolor
	return result


@get('/<gmurl>/<url>')
@view('battlemap')
def get_player_battlemap(gmurl, url):
	# try to load playername from cookie (or from GM name)
	playername = request.get_cookie('playername')
	gm         = engine.main_db.GM.loadFromSession(request)
	if playername is None:
		if gm is not None:
			playername = gm.name
		else:
			playername = ''
	
	# query the hosting GM
	host_gm = engine.main_db.GM.select(lambda g: g.url == gmurl).first()
	if host_gm is None:
		# no such GM
		abort(404)
	
	# try to load playercolor from cookieplayercolor = request.get_cookie('playercolor')
	playercolor = request.get_cookie('playercolor')
	if playercolor is None:   
		colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff', '#00ffff']
		playercolor = colors[random.randrange(len(colors))]
		  
	# load GM from cache
	gm_cache = engine.cache.getFromUrl(gmurl)
	
	# load game from GM's database
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	
	if game is None:
		abort(404)
	
	user_agent = request.environ.get('HTTP_USER_AGENT')
	protocol = 'wss' if engine.ssl else 'ws'
	websocket_url = '{0}://{1}:{2}/websocket'.format(protocol, engine.getDomain(), engine.port)
	
	# show battlemap with login screen ontop
	return dict(engine=engine, user_agent=user_agent, websocket_url=websocket_url, game=game, playername=playername, playercolor=playercolor, gm=host_gm, is_gm=gm is not None)

@post('/<gmurl>/<url>/upload/<posx:int>/<posy:int>/<default_size:int>')
def post_image_upload(gmurl, url, posx, posy, default_size):
	# load GM from cache
	gm_cache = engine.cache.getFromUrl(gmurl)
	
	# load game from GM's database to upload files
	urls  = list()
	game = gm_cache.db.Game.select(lambda g: g.url == url).first()
	files = request.files.getall('file[]')
	for handle in files:
		url = game.upload(handle)
		urls.append(url)
		engine.logging.access('Image upload {0} by {1}'.format(url, engine.getClientIp(request)))
	
	# create tokens and broadcast creation
	game_cache = gm_cache.get(game)
	game_cache.onCreate((posx, posy), urls, default_size)

@error(401)
@view('error401')
def error401(error):
	return dict(engine=engine)

@error(404)
@view('error404')
def error404(error):
	return dict(engine=engine)

@get('/vtt/status')
def status_report():
	pid = os.getpid()
	data = dict()
	
	# query cpu load
	ret = subprocess.run(["ps", "-p", str(pid), "-o", "%cpu"], capture_output=True)
	val = ret.stdout.decode('utf-8').split('\n')[1].strip()
	data['cpu'] = float(val)
	
	# query memory load
	ret = subprocess.run(["ps", "-p", str(pid), "-o", "%mem"], capture_output=True)
	val = ret.stdout.decode('utf-8').split('\n')[1].strip()
	data['memory'] = float(val)
	
	# query number of players
	data['num_players'] = PlayerCache.instance_count
	
	return data

@get('/vtt/query/<index:int>')
def status_query(index):
	# ask server
	host = engine.shards[index]
	data = dict()   
	data['countryCode'] = None
	data['status']      = None
	
	# query server location
	ip = host.split('://')[1].split(':')[0]
	d = json.loads(requests.get('http://ip-api.com/json/{0}'.format(ip)).text)
	if 'countryCode' in d:
		data['countryCode'] = d['countryCode'].lower()
	
	# query server status
	try:
		data['status'] = requests.get(host + '/vtt/status').text;
	except requests.exceptions.ConnectionError as e:
		engine.logging.error('Server {0} seems to be offline'.format(host))
	
	return data

@get('/vtt/shard')
@view('shard')
def shard_list():
	protocol = 'https' if engine.ssl else 'http'
	own = '{0}://{1}:{2}'.format(protocol, engine.getDomain(), engine.port)
	return dict(engine=engine, own=own)

# --- setup stuff -------------------------------------------------------------

if __name__ == '__main__':
	# setup engine with cli args and db session
	engine.setup(sys.argv) 
	
	try:
		engine.run()
	except KeyboardInterrupt:
		pass

