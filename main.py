#!/usr/bin/python3

from bottle import *

import os, json, random, time, sys, math, logging

from pony import orm
from orm import db, db_session, Token, Game, vtt_data_dir

__author__ = "Christian Glöckner"

host  = '0.0.0.0'
debug = True
port  = 8080


if 'debug' in sys.argv:
	logging.basicConfig(filename=vtt_data_dir / 'pyvtt.log', level=logging.DEBUG)
else:
	logging.basicConfig(filename=vtt_data_dir / 'pyvtt.log', level=logging.INFO)


# setup database connection
db.bind('sqlite', str(vtt_data_dir / 'data.db'), create_db=True)
db.generate_mapping(create_tables=True)

app = default_app()
app.catchall = not debug
app.install(db_session)

with db_session:
	s = time.time()
	for g in db.Game.select():
		g.makeLock()
		g.makeMd5s()
	t = time.time() - s
	logging.info('Image checksums and threading locks created within {0}s'.format(t))

# -----------------------------------------------------------------------------

lazy_mode = 'lazy' in sys.argv

def asGm(callback):
	def wrapper(*args, **kwargs):
		if lazy_mode or request.environ.get('REMOTE_ADDR') == '127.0.0.1':
			return callback(*args, **kwargs)
		else:
			abort(401)
	return wrapper


gametitle_whitelist = []

players = dict()
colors  = dict()

def applyWhitelist(s):
	# secure symbols used in title
	fixed = ''
	for c in s:
		if c in gametitle_whitelist:
			fixed += c
		else:
			fixed += '_'
	return fixed


# --- GM routes ---------------------------------------------------------------

@get('/', apply=[asGm])
@view('gm/game_list')
def get_game_list():
	games = db.Game.select()
	
	return dict(games=games)

@post('/setup/create', apply=[asGm])
def post_create_game():
	game_title = applyWhitelist(request.forms.game_title)
	
	# create game
	game = db.Game(title=game_title)
	# create first scene
	scene = db.Scene(title='new-scene', game=game)
	game.active = scene.title
	
	# create lock for this game
	game.makeLock()
	
	# generate checksums for this new game (just preparation)
	game.makeMd5s()
	
	db.commit()
	redirect('/')

@get('/setup/delete/<game_title>', apply=[asGm])
def delete_game(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	game.clear()
	game.delete()
	
	db.commit()
	redirect('/')

@get('/setup/list/<game_title>', apply=[asGm])
@view('gm/game_details')
def get_game_details(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	return dict(game=game)

@post('/gm/<game_title>/create', apply=[asGm])
def post_create_scene(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	# check existing scenes in this game for title-collision
	title = applyWhitelist(request.forms.scene_title)
	for s in db.Scene.select(lambda s: s.game == game):
		if s.title == title:
			redirect('/gm/{0}'.format(game.title))
	
	# create scene
	scene = db.Scene(title=title, game=game)
	
	if game.active is '':
		game.active = scene.title

	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@get('/gm/<game_title>/activate/<scene_title>', apply=[asGm])
def activate_scene(game_title, scene_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	game.active = scene_title

	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@post('/gm/<game_title>/rename/<scene_title>', apply=[asGm])
def activate_scene(game_title, scene_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()

	new_title = request.forms.scene_title

	# rename scene
	scene = db.Scene.select(lambda s: s.game == game and s.title == scene_title).first()
	if game.active == scene.title:
		game.active = new_title
	scene.title = new_title

	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@get('/gm/<game_title>/delete/<scene_title>', apply=[asGm])
def activate_scene(game_title, scene_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()

	# delete requested scene
	old_active = game.active
	scene = db.Scene.select(lambda s: s.game == game and s.title == scene_title).first()
	scene.delete()
	
	# check for remaining scenes
	remain = db.Scene.select(lambda s: s.game == game).first()
	if remain is None:
		# create new scene
		scene = db.Scene(title='new-scene', game=game)
		game.active = scene.title
	
	# fix active scene
	if game.active == old_active:
		game.active = db.Scene.select(lambda s: s.game == game).first().title

	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@get('/gm/<game_title>/clone/<scene_title>', apply=[asGm])
def duplicate_scene(game_title, scene_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	# load required scene
	scene = db.Scene.select(lambda s: s.title == scene_title).first()
	
	# create copy of that scene
	clone = db.Scene(title='{0}_new'.format(scene.title), game=game)
	# copy tokens, too
	for t in scene.tokens:
		db.Token(scene=clone, url=t.url, posx=t.posx, posy=t.posy, zorder=t.zorder, size=t.size, rotate=t.rotate, locked=t.locked)
	
	assert(len(scene.tokens) == len(clone.tokens))
	
	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@get('/gm/<game_title>/clearRolls', apply=[asGm])
def clear_rolls(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	now = int(time.time())
	
	# clear old rolls
	for r in game.rolls:
		if r.timeid < now - 60:
			r.delete()
	
	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@get('/gm/<game_title>/clearImages', apply=[asGm])
def clear_images(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	# query and remove abandoned images (those without any token)
	cleanup, count = game.removeAbandonedImages()
	megs = cleanup / (1024.0*1024.0)
	logging.info('{0} abandoned images deleted, {1} MB freed'.format(count, megs))
	
	# refresh checksums
	s = time.time()
	game.makeMd5s()
	logging.info('Image checksums for {1} created within {0}s'.format(time.time() - s, game.title))
	
	redirect('/setup/list/{0}'.format(game.title))


# --- playing routes ----------------------------------------------------------

@get('/static/<fname>')
def static_files(fname):
	return static_file(fname, root='./static')

@get('/token/<game_title>/<fname>')
def static_token(game_title, fname):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	path = game.getImagePath()
	
	return static_file(fname, root=path)

@get('/login/<game_title>')
@view('player/login')
def player_login(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	return dict(game=game)

@post('/login/<game_title>')
@view('player/redirect')
def set_player_name(game_title):
	playername = applyWhitelist(request.forms.get('playername'))[:12]
	playercolor  = request.forms.get('playercolor')
	
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	# save playername in client cookie (expire after 14 days)
	expire = int(time.time() + 3600 * 24 * 14)
	response.set_cookie('playername', playername, path='/play/{0}'.format(game_title), expires=expire)
	response.set_cookie('playercolor', playercolor, path='/play/{0}'.format(game_title), expires=expire)
	
	return dict(game=game, playername=playername)

@get('/play/<game_title>')
@view('player/battlemap')
def get_player_battlemap(game_title):
	# load player name and color from cookie
	playername = request.get_cookie('playername')
	playercolor = request.get_cookie('playercolor')
	
	# redirect to login if player not found
	if playername is None:
		redirect('/login/{0}'.format(game_title))

	else:
		# load game
		game = db.Game.select(lambda g: g.title == game_title).first()
		
		return dict(game=game, playername=playername, playercolor=playercolor)

# on window open
@post('/play/<game_title>/join')
def join_game(game_title):
	# load player name from cookie
	playername = request.get_cookie('playername')
	playercolor = request.get_cookie('playercolor')
	
	# save this playername
	if game_title not in players:
		players[game_title] = set()
	players[game_title].add(playername)
	
	# save this playercolor
	if game_title not in colors:
		colors[game_title] = dict()
	colors[game_title][playername] = playercolor
		

# on window close
@post('/play/<game_title>/disconnect')
def quit_game(game_title):
	# load player name from cookie
	playername = request.get_cookie('playername')
	
	# remove player
	if game_title in players and playername in players[game_title]:
		players[game_title].remove(playername)
	
	# note: color is kept


# on logout purpose
@get('/play/<game_title>/logout')
def quit_game(game_title):
	# load player name from cookie
	playername = request.get_cookie('playername')
	playercolor = request.get_cookie('playercolor')
	
	# reset cookie
	response.set_cookie('playername', playername, path='/play/{0}'.format(game_title), expires=0)
	response.set_cookie('playercolor', playercolor, path='/play/{0}'.format(game_title), expires=0)
	
	# remove player
	if game_title in players and playername in players[game_title]:
		players[game_title].remove(playername)

	# note: color is kept
	
	# show login page
	redirect('/play/{0}'.format(game_title))

@post('/play/<game_title>/update')
def post_player_update(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.game == game and s.title == game.active).first()
	
	now = int(time.time())
	
	# fetch token updates from client
	timeid  = float(request.POST.get('timeid'))
	changes = json.loads(request.POST.get('changes'))
	# update token data
	for data in changes:
		token = scene.tokens.select(lambda s: s.id == data['id']).first()
		token.update(
			timeid=int(timeid),
			pos=(int(data['posx']), int(data['posy'])),
			zorder=data['zorder'],
			size=data['size'],
			rotate=data['rotate'],
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
		if game_title in colors and r.player in colors[game_title]:
			color = colors[game_title][r.player]
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
	if game_title in players:
		for playername in players[game_title]:
			playercolor = '#000000'
			if game_title in colors and playername in colors[game_title]:
				playercolor = colors[game_title][playername]
			playerlist.append('{0}:{1}'.format(playername, playercolor))
	
	# return tokens, rolls and timestamp
	data = {
		'active' : game.active,
		'timeid' : time.time(),
		'full'   : timeid == 0,
		'tokens' : tokens,
		'rolls'  : rolls,
		'players': playerlist
	}
	return json.dumps(data)

@post('/play/<game_title>/roll/<sides:int>')
def post_roll_dice(game_title, sides):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.game == game and s.title == game.active).first()
	scene.timeid = int(time.time())
	
	# load player name from cookie
	playername = request.get_cookie('playername')
	
	# add player roll
	result = random.randrange(1, sides+1)
	db.Roll(game=game, player=playername, sides=sides, result=result, timeid=int(time.time()))

@post('/play/<game_title>/upload/<posx:int>/<posy:int>')
def post_image_upload(game_title, posx, posy):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.game == game and s.title == game.active).first()
	scene.timeid = int(time.time())
	
	# upload all files to the current game
	# and create a token each
	files = request.files.getall('file[]')
	
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
			x = posx - radius * s
			y = posy + radius * c
			url = game.upload(handle)
			# create token
			db.Token(scene=scene, timeid=scene.timeid, url=url, posx=int(x), posy=int(y))
		
	db.commit()

@post('/play/<game_title>/clone/<token_id:int>/<x:int>/<y:int>')
def ajax_post_clone(game_title, token_id, x, y):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.game == game and s.title == game.active).first()
	# update position
	scene.timeid = int(time.time())
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# clone token
	db.Token(scene=token.scene, url=token.url, posx=x, posy=y, zorder=token.zorder,
		size=token.size, rotate=token.rotate, timeid=int(time.time()))

@post('/play/<game_title>/delete/<token_id:int>')
def ajax_post_delete(game_title, token_id):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.game == game and s.title == game.active).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# delete token
	token.delete()


# --- setup stuff -------------------------------------------------------------

for i in range(65, 91):
	gametitle_whitelist.append(chr(i))
	gametitle_whitelist.append(chr(i+32))
for i in range(10):	
	gametitle_whitelist.append('{0}'.format(i))
gametitle_whitelist.append('-')
gametitle_whitelist.append('_')

app = default_app()

if 'debug' in sys.argv:
	run(host=host, reloader=debug, debug=debug, port=port)	
else:
	from paste import httpserver
	httpserver.serve(app, host=host, port=port)

