#!/usr/bin/python3

from bottle import *

import os, json, random, time

from pony import orm
from orm import db, db_session, Token, Game

__author__ = "Christian Glöckner"

host  = ''
debug = True
port  = 8080

db.bind('sqlite', 'data.db', create_db=True)
db.generate_mapping(create_tables=True)

app = default_app()
app.catchall = not debug
app.install(db_session)


# --- GM routes ---------------------------------------------------------------

@get('/')
@view('gm/game_list')
def get_game_list():
	games = db.Game.select()
	
	return dict(games=games)

@post('/setup/create')
def post_create_game():
	game_title = request.forms.game_title
	# create game
	game = db.Game(title=game_title)
	
	db.commit()
	redirect('/')

@get('/setup/delete/<game_title>')
def delete_game(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	game.clear()
	game.delete()
	
	db.commit()
	redirect('/')

@get('/setup/list/<game_title>')
@view('gm/game_details')
def get_game_details(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	return dict(game=game)

@post('/gm/<game_title>/create')
def post_create_scene(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	# check existing scenes in this game for title-collision
	title = request.forms.scene_title
	for s in db.Scene.select(lambda s: s.game == game):
		if s.title == title:
			redirect('/gm/{0}'.format(game.title))
	
	# create scene
	scene = db.Scene(title=title, game=game)
	
	if game.active is '':
		game.active = scene.title

	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@get('/gm/<game_title>/activate/<scene_title>')
def activate_scene(game_title, scene_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	game.active = scene_title

	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@post('/gm/<game_title>/rename/<scene_title>')
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

@get('/gm/<game_title>/delete/<scene_title>')
def activate_scene(game_title, scene_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()

	# delete requested scene
	scene = db.Scene.select(lambda s: s.game == game and s.title == scene_title).first()
	scene.delete()

	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@get('/gm/<game_title>/clone/<scene_title>')
def duplicate_scene(game_title, scene_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	# load required scene
	scene = db.Scene.select(lambda s: s.title == scene_title).first()
	
	# create copy of that scene
	clone = db.Scene(title='{0}_new'.format(scene.title), game=game)
	# copy tokens, too
	for t in scene.tokens:
		db.Token(scene=clone, url=t.url, posx=t.posx, posy=t.posy, size=t.size, rotate=t.rotate, locked=t.locked)
	
	assert(len(scene.tokens) == len(clone.tokens))
	
	db.commit()
	redirect('/setup/list/{0}'.format(game.title))

@get('/gm/<game_title>/kick/<player_name>')
def kick_player(game_title, player_name):
	# query and delete player
	player = db.Player.select(lambda p: p.name == player_name).first()
	player.delete()
	
	db.commit()
	redirect('/setup/list/{0}'.format(game_title))

@get('/gm/<game_title>')
@view('player/battlemap')
def get_player_battlemap(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	return dict(game=game, gm=True, page_title='[GM] {0}'.format(game.title))

@post('/gm/<game_title>/upload')
def post_image_upload(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	scene.timeid = int(time.time())
	
	# upload all files to the current game
	# and create a token each
	files = request.files.getall('file[]')
	yoffset = 0
	for handle in files:
		url = game.upload(handle)
		# create token
		yoffset += 1
		db.Token(scene=scene, timeid=scene.timeid, url=url, posx=1100, posy=50 * yoffset)
	
	db.commit()
	
	redirect('/gm/{0}'.format(game_title))

@post('/gm/<game_title>/clone/<token_id:int>')
def ajax_post_clone(game_title, token_id):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	# update position
	scene.timeid = int(time.time())
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# clone token
	db.Token(scene=token.scene, url=token.url, posx=token.posx,
		posy=token.posy + token.size//2, size=token.size, rotate=token.rotate,
		timeid=int(time.time()))

@post('/gm/<game_title>/delete/<token_id:int>')
def ajax_post_delete(game_title, token_id):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# delete token
	token.delete()

@post('/gm/<game_title>/clear_rolls')
def post_clear_rolls(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	
	# delete old rolls
	old_rolls = db.Roll.select(lambda r: r.game == game and r.timeid < scene.timeid - 20)
	old_rolls.delete()

@post('/gm/<game_title>/clear_tokens')
def post_clear_tokens(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	
	# query all tokens within visible range (players' point of view)
	tokens = db.Token.select(lambda t: t.scene == scene and t.posx <= 1000 and not t.locked)
	
	# delete those tokens
	tokens.delete()



# --- player routes -----------------------------------------------------------

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
	playername = request.forms.get('playername')
	
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	# create player
	player = db.Player(name=playername, game=game, alive=int(time.time()))
	
	# save playername in client cookie
	response.set_cookie('playername', playername, path='/play/{0}'.format(game_title))
	
	return dict(game=game, player=player)

@get('/play/<game_title>')
@view('player/battlemap')
def get_player_battlemap(game_title):
	# load player name from cookie
	playername = request.get_cookie('playername')
	
	# try to load player from db
	player = db.Player.select(lambda p: p.name == playername).first()
	
	# redirect to login if player not found or invalid name ('GM') used
	if playername is None or player is None or playername.upper() == 'GM':
		redirect('/login/{0}'.format(game_title))

	else:
		# load game
		game = db.Game.select(lambda g: g.title == game_title).first()
		
		# keep player alive
		player.alive = int(time.time())
		
		return dict(game=game, gm=False, player=player)

@post('/play/<game_title>/update')
def post_player_update(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	
	now = int(time.time())
	
	# fetch token updates from client
	timeid  = float(request.POST.get('timeid'))
	changes = json.loads(request.POST.get('changes'))
	# update token data
	for data in changes:
		token = scene.tokens.select(lambda s: s.id == data['id']).first()
		token.update(
			timeid=int(timeid),
			pos=(data['posx'], data['posy']),
			size=data['size'],
			rotate=data['rotate'],
			locked=data['locked']
		)

	# keep player alive
	if timeid == 0:
		playername = request.get_cookie('playername')
		player = db.Player.select(lambda p: p.name == playername).first()
		if player is not None:
			player.alive = now

	# query token data
	tokens = list()
	for t in scene.tokens:
		# consider token if it was updated after given timeid
		if t.timeid >= timeid:
			tokens.append(t.to_dict())
	
	# query rolls 
	rolls = list()
	for r in db.Roll.select(lambda r: r.game == game).order_by(lambda r: -r.timeid)[:10]:
		# consider token if it was updated after given timeid
		#if r.timeid >= timeid:
		rolls.append({
			'player': r.player,
			'sides': r.sides,
			'result': r.result
		})
	
	# query players alive
	players = ['GM']
	for p in db.Player.select(lambda p: p.game == game):
		if p.alive >= now - 10:
			players.append(p.name)
		else:
			# player timeout
			p.delete()
	
	# return tokens, rolls and timestamp
	data = {
		'timeid' : time.time(),
		'full'   : timeid == 0,
		'tokens' : tokens,
		'rolls'  : rolls,
		'players': players
	}
	return json.dumps(data)

@post('/play/<game_title>/roll/<sides:int>')
def post_roll_dice(game_title, sides):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	scene.timeid = int(time.time())
	
	# load player name from cookie
	playername = request.get_cookie('playername')
	# try to load player from db
	player = db.Player.select(lambda p: p.name == playername).first()
	if player is None:
		playername = 'GM'
	
	# add player roll
	result = random.randrange(1, sides+1)
	db.Roll(game=game, player=playername, sides=sides, result=result, timeid=int(time.time()))


# --- setup stuff -------------------------------------------------------------

if not os.path.isdir('games'):
	os.mkdir('games')

run(host=host, reloader=debug, debug=debug, port=port)



