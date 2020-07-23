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

@post('/create_game/')
def post_create_game():
	game_title = request.forms.game_title
	# create game
	game = db.Game(title=game_title)
	
	db.commit()
	redirect('/')

@get('/delete/<game_title>')
def delete_game(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	game.clear()
	game.delete()
	
	db.commit()
	redirect('/')

@get('/setup/<game_title>')
@view('gm/scene_list')
def get_scene_list(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	return dict(game=game)

@post('/create_scene/<game_title>')
def post_create_scene(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	# check existing scenes in this game for title-collision
	title = request.forms.scene_title
	for s in db.Scene.select(lambda s: s.game == game):
		if s.title == title:
			redirect('/setup/{0}'.format(game.title))
	
	# create scene
	scene = db.Scene(title=title, game=game)
	
	if game.active is '':
		game.active = scene.title

	db.commit()
	redirect('/setup/{0}'.format(game.title))

@get('/activate/<game_title>/<scene_title>')
def activate_scene(game_title, scene_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	game.active = scene_title

	db.commit()
	redirect('/setup/{0}'.format(game.title))

@get('/delete_scene/<game_title>/<scene_title>')
def activate_scene(game_title, scene_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()

	# delete requested scene
	scene = db.Scene.select(lambda s: s.game == game and s.title == scene_title).first()
	scene.delete()

	db.commit()
	redirect('/setup/{0}'.format(game.title))

@get('/duplicate/<game_title>/<scene_title>')
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
	redirect('/setup/{0}'.format(game.title))

@get('/gm/<game_title>')
@view('player/battlemap')
def get_player_battlemap(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	return dict(game=game, gm=True, page_title='[GM] {0}'.format(game.title))

@post('/ajax/<game_title>/lock/<token_id:int>/<flag:int>')
def ajax_post_rotate(game_title, token_id, flag):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	# update position
	scene.timeid += 1
	token.update(timeid=scene.timeid, locked=flag)

@post('/ajax/<game_title>/clone/<token_id:int>')
def ajax_post_clone(game_title, token_id):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	# update position
	scene.timeid += 1
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# clone token
	db.Token(scene=token.scene, url=token.url, posx=token.posx,
		posy=token.posy + token.size//2, size=token.size, rotate=token.rotate,
		timeid=scene.timeid)

@post('/ajax/<game_title>/delete/<token_id:int>')
def ajax_post_delete(game_title, token_id):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# delete token
	token.delete()

@post('/upload/<game_title>')
def post_image_upload(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	scene.timeid += 1
	
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

@post('/clear_rolls/<game_title>')
def post_clear_rolls(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	
	# delete old rolls
	old_rolls = db.Roll.select(lambda r: r.game == game and r.timeid < scene.timeid - 20)
	old_rolls.delete()

@post('/clear_tokens/<game_title>/<area>')
def post_clear_tokens(game_title, area):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	
	if area == 'gm':
		# query all tokens within GM area
		tokens = db.Token.select(lambda t: t.scene == scene and t.posx > 1000 and not t.locked)
	else:
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
	player = db.Player(name=playername, game=game)
	
	# save playername in client cookie
	response.set_cookie('playername', playername, path='/')
	
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
		
		return dict(game=game, gm=False, player=player)

@get('/ajax/<game_title>/update/<timeid:int>')
def ajax_get_update(game_title, timeid):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	
	# load player name from cookie
	playername = request.get_cookie('playername')
	# try to load player from db
	player = db.Player.select(lambda p: p.name == playername).first()
	
	# query all existing tokens each 3s
	now = int(time.time())
	if player is None:
		# GMs use buggy refresh (a couple of times at once .__.)
		if now % 3 == 0:
			timeid = 0
			print('Fully updating GM')
	else:
		# players refresh correctly
		if player.alive + 3 < now:
			player.alive = now
			timeid = 0
			print('Fully updating', player.name)
	
	# query token data
	tokens = list()
	for t in scene.tokens:
		if (t.timeid > timeid):
			tokens.append(t.to_dict())
	
	# query rolls 
	rolls = list()
	recent_rolls = db.Roll.select(lambda r: r.game == game)
	for r in recent_rolls:
		if r.timeid > timeid:
			rolls.append('{0} D{1}={2}'.format(r.player, r.sides, r.result))
	
	# return tokens, rolls and timeid
	data = {
		'timeid' : scene.timeid,
		'full'   : timeid == 0,
		'tokens' : tokens,
		'rolls'  : rolls
	}
	return json.dumps(data)

@post('/ajax/<game_title>/move/<token_id:int>/<x:int>/<y:int>')
def ajax_post_move(game_title, token_id, x, y):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	# update position
	scene.timeid += 1
	token.update(timeid=scene.timeid, pos=(x, y))

@post('/ajax/<game_title>/resize/<token_id:int>/<size:int>')
def ajax_post_resize(game_title, token_id, size):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	# update position
	scene.timeid += 1
	token.update(timeid=scene.timeid, size=size)

@post('/ajax/<game_title>/rotate/<token_id:int>/<rotate:int>')
def ajax_post_rotate(game_title, token_id, rotate):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	# update position
	scene.timeid += 1
	token.update(timeid=scene.timeid, rotate=rotate)

@post('/roll/<game_title>/<player>/<sides:int>')
def post_roll_dice(game_title, player, sides):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	scene.timeid += 1
	
	# add player roll
	result = random.randrange(1, sides+1)
	db.Roll(game=game, player=player, sides=sides, result=result, timeid=scene.timeid)


# --- setup stuff -------------------------------------------------------------

if not os.path.isdir('games'):
	os.mkdir('games')

run(host=host, reloader=debug, debug=debug, port=port)



