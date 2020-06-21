#!/usr/bin/python3

from bottle import get, view, run, post, request, static_file, redirect

import os, json

import scene

manager = scene.Manager()


# --- GM routes ---------------------------------------------------------------

@get('/')
@view('gm/game_list')
def get_game_list():
	return dict(games=manager.games)

@post('/create_game/')
def post_create_game():
	game_title = request.forms.game_title
	manager.createGame(game_title)
	manager.saveToFile('example.json')

@get('/setup/<game_title>')
@view('gm/scene_list')
def get_scene_list(game_title):
	game = manager.games[game_title]
	return dict(game=game)

@post('/create_scene/<game_title>')
def post_create_scene(game_title):
	game = manager.games[game_title]
	scene_title = request.forms.scene_title
	game.createScene(scene_title)
	manager.saveToFile('example.json')



# --- player routes -----------------------------------------------------------

@get('/static/<fname>')
def static_files(fname):
	return static_file(fname, root='./static')

@get('/token/<game_title>/<fname>')
def static_token(game_title, fname):
	path = os.path.join('.', 'games', game_title, 'images')
	return static_file(fname, root=path)

@get('/play/<game_title>')
@view('player/battlemap')
def get_player_battlemap(game_title):
	game = manager.games[game_title]
	return dict(game=game)

@get('/ajax/<game_title>/update')
def ajax_get_update(game_title):
	game  = manager.games[game_title]
	scene = game.scenes[game.active]
	return json.dumps(scene.toDict()["tokens"])

@post('/ajax/<game_title>/move/<token_id:int>/<x:int>/<y:int>')
def ajax_post_move(game_title, token_id, x, y):
	game = manager.games[game_title]
	scene = game.scenes[game.active]
	scene.tokens[token_id].pos = (x, y)

@post('/ajax/<game_title>/resize/<token_id:int>/<size:int>')
def ajax_post_resize(game_title, token_id, size):
	game = manager.games[game_title]
	scene = game.scenes[game.active]
	scene.tokens[token_id].size = size

@post('/ajax/<game_title>/rotate/<token_id:int>/<rotate:int>')
def ajax_post_rotate(game_title, token_id, rotate):
	game = manager.games[game_title]
	scene = game.scenes[game.active]
	scene.tokens[token_id].rotate = rotate

@post('/ajax/<game_title>/lock/<token_id:int>/<flag:int>')
def ajax_post_rotate(game_title, token_id, flag):
	game = manager.games[game_title]
	scene = game.scenes[game.active]
	scene.tokens[token_id].locked = flag

@post('/ajax/<game_title>/clone/<token_id:int>')
def ajax_post_clone(game_title, token_id):
	game = manager.games[game_title]
	scene = game.scenes[game.active]
	token = scene.tokens[token_id]
	scene.createToken(
		remote_path=token.remote_path,
		pos=(token.pos[0], token.pos[1] + token.size / 10),
		size=token.size,
		rotate=token.rotate
	)

@post('/ajax/<game_title>/delete/<token_id:int>')
def ajax_post_delete(game_title, token_id):
	game = manager.games[game_title]
	scene = game.scenes[game.active]
	del scene.tokens[token_id]
	scene.dropped.append(token_id)

@post('/upload/<game_title>')
def post_image_upload(game_title):
	game = manager.games[game_title]

	# upload all files to the current game
	# and create a token each
	files = request.files.getall('file[]')
	for fhandle in files:
		remote_path = game.uploadImage(fhandle)
		game.scenes[game.active].createToken(remote_path=remote_path, pos=(50, 50))
	manager.saveToFile('example.json')
	
	redirect('/play/{0}'.format(game_title))


# --- setup stuff -------------------------------------------------------------

if os.path.isfile('example.json'):
	manager.loadFromFile('example.json')

if not os.path.isdir('games'):
	os.mkdir('games')

run(host='localhost', reloader=True, debug=True, port=8080)



