#!/usr/bin/python3

from bottle import *

import os, json

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

@get('/play/<game_title>')
@view('player/battlemap')
def get_player_battlemap(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	
	return dict(game=game)

@get('/ajax/<game_title>/update')
def ajax_get_update(game_title):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load active scene
	scene = db.Scene.select(lambda s: s.title == game.active).first()
	# format update data
	tokens = list()
	for t in scene.tokens:
		tokens.append(t.to_dict())
	
	return json.dumps(tokens)

@post('/ajax/<game_title>/move/<token_id:int>/<x:int>/<y:int>')
def ajax_post_move(game_title, token_id, x, y):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# update position
	token.update(pos=(x, y))

@post('/ajax/<game_title>/resize/<token_id:int>/<size:int>')
def ajax_post_resize(game_title, token_id, size):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# update position
	token.update(size=size)

@post('/ajax/<game_title>/rotate/<token_id:int>/<rotate:int>')
def ajax_post_rotate(game_title, token_id, rotate):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# update position
	token.update(rotate=rotate)

@post('/ajax/<game_title>/lock/<token_id:int>/<flag:int>')
def ajax_post_rotate(game_title, token_id, flag):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# update position
	token.update(locked=flag)

@post('/ajax/<game_title>/clone/<token_id:int>')
def ajax_post_clone(game_title, token_id):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
	# load requested token
	token = db.Token.select(lambda t: t.id == token_id).first()
	# clone token
	db.Token(scene=token.scene, url=token.url, posx=token.posx,
		posy=token.posy + token.size//10, size=token.size, rotate=token.rotate)

@post('/ajax/<game_title>/delete/<token_id:int>')
def ajax_post_delete(game_title, token_id):
	# load game
	game = db.Game.select(lambda g: g.title == game_title).first()
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
	
	# upload all files to the current game
	# and create a token each
	files = request.files.getall('file[]')
	for handle in files:
		url = game.upload(handle)
		# create token
		db.Token(scene=scene, url=url, posx=50, posy=50)
	
	db.commit()
	
	redirect('/play/{0}'.format(game_title))


# --- setup stuff -------------------------------------------------------------

if not os.path.isdir('games'):
	os.mkdir('games')

run(host=host, reloader=debug, debug=debug, port=port)



