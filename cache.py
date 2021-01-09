#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import time, requests, uuid, json, random

from bottle import request
import gevent

from gevent import lock
from geventwebsocket.exceptions import WebSocketError

from orm import db_session, createGmDatabase


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'



class ProtocolError(Exception):
	""" Used if the communication between server and client behaves
	unexpected.
	"""
	
	def __init__(self, msg):
		super().__init__(msg)


# ---------------------------------------------------------------------

class PlayerCache(object):
	"""Holds a single player.
	"""
	instance_count = 0 # instance counter for server status
	
	def __init__(self, engine, parent, name, color):
		PlayerCache.instance_count += 1
		
		self.engine   = engine
		self.parent   = parent # parent cache object
		self.name     = name
		self.color    = color
		self.uuid     = uuid.uuid1().hex # used for HTML DOM id
		self.selected = list()
		
		self.greenlet = None
		
		# fetch country from ip
		self.ip       = self.engine.getClientIp(request)
		d = json.loads(requests.get('http://ip-api.com/json/{0}'.format(self.ip)).text)
		if 'countryCode' in d:
			self.country = d['countryCode'].lower()
		else:
			self.country = '?'
		
		self.socket   = None
		
		self.dispatch_map = {
			'ROLL'   : self.parent.onRoll,
			'SELECT' : self.parent.onSelect,
			'RANGE'  : self.parent.onRange,
			'CLONE'  : self.parent.onClone,
			'UPDATE' : self.parent.onUpdate,
			'DELETE' : self.parent.onDelete
		}
		
	def __del__(self):
		PlayerCache.instance_count -= 1
		
	# --- websocket implementation ------------------------------------
		
	def read(self):
		""" Return JSON object read from socket. """
		try:
			raw = self.socket.receive()
			if raw is None:
				return None
			return json.loads(raw)
		except Exception as e:
			# send error msg back to client
			self.socket.send(str(e)) 
			self.socket.close()
			raise ProtocolError('Broken JSON message')
		
	def write(self, data):
		""" Write JSON object to socket. """
		if self.socket is not None and not self.socket.closed:
			raw = json.dumps(data)
			self.socket.send(raw)
		
	def fetch(self, data, key):
		""" Try to fetch key from data or raise ProtocolError. """
		try:
			return data[key]
		except KeyError as e:
			# send error msg back to client
			self.socket.send(str(e))
			self.socket.close()
			raise ProtocolError('Key "{0}" not provided by client'.format(key))
		
	def handle_async(self):
		""" Runs a greenlet to handle asyncronously. """
		self.greenlet = gevent.Greenlet(run=self.handle)
		self.greenlet.start()
		self.greenlet.join()
		
	def handle(self):
		""" Thread-handle for dispatching player actions. """
		try:
			while True:
				# query data and operation id
				data = self.read()
				if data is not None:
					# dispatch operation
					opid = self.fetch(data, 'OPID')
					func = self.dispatch_map[opid]
					func(self, data)
				else:
					break
			
		except WebSocketError as e:
			# player quit   
			print('\t{0}\tERROR\t{1}'.format(name, e))
			
		except ProtocolError as e:
			# error occured
			print('\t{0}\\\tPROTOCOL\t{1}'.format(name, e))
		
		# logout player
		self.parent.logout(self)


# ---------------------------------------------------------------------

class GameCache(object):
	""" Thread-safe player dict using name as key. """
	
	def __init__(self, engine, parent, game):
		# prepare MD5 hashes for all images
		game.makeMd5s()
		
		self.engine  = engine
		self.parent  = parent
		self.lock    = lock.RLock()
		self.url     = game.url
		self.players = dict() # name => player
		
		self.engine.logging.info('GameCache {0} for GM {1} created'.format(self.url, self.parent.url))
		
	# --- cache implementation ----------------------------------------
		
	def insert(self, name, color):
		with self.lock:
			if name in self.players:
				raise KeyError
			self.players[name] = PlayerCache(self.engine, self, name, color)
			return self.players[name]
		
	def get(self, name):
		with self.lock:
			return self.players[name]
		
	def getData(self):
		result = dict()
		with self.lock:
			for name in self.players:
				p = self.players[name]
				result[name] = {
					'name'    : name,
					'uuid'    : p.uuid,
					'color'   : p.color,
					'ip'      : p.ip,
					'country' : p.country
				}
		return result
		
	def getSelections(self):
		result = dict()
		with self.lock:
			for name in self.players:
				result[name] = self.players[name].selected
		return result
		
	def remove(self, name):
		with self.lock:
			del self.players[name]
		
	# --- websocket implementation ------------------------------------
		
	def closeSocket(self, uuid):
		""" Close single socket. """
		with self.lock:
			for name in self.players:
				p = self.players[name]
				if p.uuid == uuid:
					p.socket.close()
					return name
		
	def closeAllSockets(self):
		""" Closes all sockets. """
		with self.lock:
			for name in self.players:
				socket = self.players[name].socket
				if socket is not None and not socket.closed:
					socket.close()
				else:
					del self.players[name]
			self.players = dict()
		
	def broadcast(self, data):
		""" Broadcast given data to all clients. """
		with self.lock:
			for name in self.players:
				self.players[name].write(data)
		
	def login(self, player):
		""" Handle player login. """
		# notify player about all players and  latest rolls
		rolls  = list()
		recent = time.time() - self.engine.recent_rolls
		since  = time.time() - self.engine.latest_rolls # last 10min
		# query latest rolls and all tokens
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			
			for r in self.parent.db.Roll.select(lambda r: r.game == g and r.timeid >= since).order_by(lambda r: r.timeid):
				rolls.append({
					'color'  : r.color,
					'sides'  : r.sides,
					'result' : r.result,
					'recent' : r.timeid >= recent
				})
		
		player.write({
			'OPID'    : 'ACCEPT',
			'uuid'    : player.uuid,
			'players' : self.getData(),
			'rolls'   : rolls,
		}); 
		
		player.write(self.fetchRefresh(g.active))
		
		# broadcast join to all players
		self.broadcast({
			'OPID'    : 'JOIN',
			'name'    : player.name,
			'uuid'    : player.uuid,
			'color'   : player.color,
			'country' : player.country
		})
		
	def fetchRefresh(self, scene_id):
		""" Performs a full refresh on all tokens. """  
		tokens = list()
		background_id = 0
		with db_session:
			scene = self.parent.db.Scene.select(lambda s: s.id == scene_id).first().backing
			background_id = scene.id if scene is not None else None
			for t in self.parent.db.Token.select(lambda t: t.scene.id == scene_id):
				tokens.append(t.to_dict())
		
		return {
			'OPID'       : 'REFRESH',
			'tokens'     : tokens,
			'background' : background_id
		}
		
	def logout(self, player):
		""" Handle player logout. """
		# broadcast logout to all players
		self.broadcast({
			'OPID' : 'QUIT',
			'name' : player.name,
			'uuid'  : player.uuid
		})
		
		# remve player
		self.remove(player.name)
		
	def onRoll(self, player, data):
		""" Handle player rolling a dice. """
		# roll dice
		now = time.time()
		sides  = data['sides']
		result = random.randrange(1, sides+1)
		roll_id = None
		
		now = time.time()
		
		with db_session: 
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			g.timeid = now
			
			# roll dice
			self.parent.db.Roll(game=g, color=player.color, sides=sides, result=result, timeid=now)
		
		# broadcast dice result
		self.broadcast({
			'OPID'    : 'ROLL',
			'color'   : player.color,
			'sides'   : sides,
			'result'  : result,
			'recent'  : True
		})
		
	def onSelect(self, player, data):
		""" Handle player selecting a token. """
		# store selection
		player.selected = data['selected']
		
		# broadcast selection
		self.broadcast({
			'OPID'     : 'SELECT',
			'color'    : player.color,
			'selected' : player.selected,
		});
		
	def onRange(self, player, data):
		""" Handle player selecting multiple tokens. """
		# fetch rectangle data
		adding = data['adding']
		left   = data['left']
		top    = data['top']
		width  = data['width']
		height = data['height']
		
		now = time.time()
		# query inside given rectangle
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			g.timeid = now
			
			s = self.parent.db.Scene.select(lambda s: s.id == g.active).first()
			token_ids = player.selected if adding else list()
			for t in self.parent.db.Token.select(lambda t: t.scene == s and left <= t.posx and t.posx <= left + width and top <= t.posy and t.posy <= top + height): 
				if t.size != -1:
					token_ids.append(t.id)
		
		# store selection
		player.selected = token_ids
		
		# broadcast selection
		self.broadcast({
			'OPID'     : 'SELECT',
			'color'    : player.color,
			'selected' : player.selected,
		});
		
	def onClone(self, player, data):
		""" Handle player cloning tokens. """
		# fetch clone data
		ids  = data['ids']
		posx = data['posx']
		posy = data['posy']
		
		# create tokens
		tokens = list()
		now = time.time()
		with db_session: 
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first() 
			g.timeid = now
			s = self.parent.db.Scene.select(lambda s: s.id == g.active).first()
			
			# iterate provided tokens
			for k, tid in enumerate(ids):
				t = self.parent.db.Token.select(lambda t: t.id == tid).first()
				if t is None:
					# ignore, t was deleted in the meantime
					continue
				# clone token
				pos = self.parent.db.Token.getPosByDegree((posx, posy), k, len(ids))
				t = self.parent.db.Token(scene=s, url=t.url, posx=pos[0], posy=pos[1],
					zorder=t.zorder, size=t.size, rotate=t.rotate,
					flipx=t.flipx, timeid=now)
				
				self.parent.db.commit()
				tokens.append(t.to_dict())
		
		# broadcast creation
		self.broadcast({
			'OPID'   : 'CREATE',
			'tokens' : tokens
		})
		
	def onUpdate(self, player, data):
		""" Handle player changing token data. """
		# fetch changes' data
		changes = data['changes']
		
		now = time.time()
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			g.timeid = now
			
			# iterate provided tokens
			for data in changes:
				t = self.parent.db.Token.select(lambda t: t.id == data['id']).first()
				# fetch changed data (accepting None)
				posx   = data.get('posx')
				posy   = data.get('posy')
				pos    = None if posx is None or posy is None else (posx, posy)
				zorder = data.get('zorder')
				size   = data.get('size')
				rotate = data.get('rotate')
				flipx  = data.get('flipx')
				locked = data.get('locked', False)
				t.update(timeid=now, pos=pos, zorder=zorder, size=size,
					rotate=rotate, flipx=flipx, locked=locked)
		
		self.broadcastTokenUpdate(player, now)  
		
	def onCreate(self, pos, urls, default_size):
		""" Handle player creating tokens. """
		# create tokens
		now = time.time()
		n = len(urls)
		tokens = list()
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			g.timeid = now
			
			s = self.parent.db.Scene.select(lambda s: s.id == g.active).first()
			
			for k, url in enumerate(urls):
				# create tokens in circle
				x, y = self.parent.db.Token.getPosByDegree(pos, k, n)
				t = self.parent.db.Token(scene=s.id, timeid=now, url=url,
					size=default_size, posx=x, posy=y)
				
				self.parent.db.commit()
				
				# use first token as background if necessary
				if s.backing is None:
					t.size    = -1
					s.backing = t
				
				tokens.append(t.to_dict())
		
		# broadcast creation
		self.broadcast({
			'OPID'   : 'CREATE',
			'tokens' : tokens
		})
		
	def onDelete(self, player, data):
		""" Handle player deleting tokens. """
		# delete tokens
		tokens = data['tokens']
		data   = list()
		with db_session:
			for tid in tokens:
				t = self.parent.db.Token.select(lambda t: t.id == tid).first()
				if t is not None:
					data.append(t.to_dict())
					t.delete()
		
		# broadcast delete
		self.broadcast({
			'OPID'   : 'DELETE',
			'tokens' : data
		})
		
	def broadcastTokenUpdate(self, player, since):
		""" Broadcast updated tokens. """
		# fetch all changed tokens
		all_data = list()    
		
		now = time.time()
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			g.timeid = now
			
			for t in self.parent.db.Token.select(lambda t: t.scene.id == g.active and t.timeid >= since):
				all_data.append(t.to_dict())
		
		# broadcast update
		self.broadcast({
			'OPID'    : 'UPDATE',
			'tokens'  : all_data
		});
		
	def broadcastSceneSwitch(self, game):
		""" Broadcast scene switch. """
		# collect all tokens for the given scene
		refresh_data = self.fetchRefresh(game.active)
		
		# broadcast switch
		self.broadcast(refresh_data);


# ---------------------------------------------------------------------

class GmCache(object):
	""" Thread-safe GM dict using game-url as key.
	Holds GM-databases.
	"""
	
	def __init__(self, engine, gm):
		# ensure engine can lock for this GM if required
		gm.makeLock()
		self.db_path = engine.paths.getDatabasePath(gm.url)
		
		self.engine = engine
		self.lock   = lock.RLock()
		self.url    = gm.url
		self.games  = dict()
		
		self.engine.logging.info('GmCache {0} with {0} created'.format(self.url, self.db_path))
		
	def connect_db(self):
		# connect to GM's database 
		self.db = createGmDatabase(self.engine, str(self.db_path))
		
		# add all existing games to the cache
		with db_session:
			for game in self.db.Game.select():
				self.insert(game)
		
		self.engine.logging.info('GmCache {0} with {0} loaded'.format(self.url, self.db_path))
		
	# --- cache implementation ----------------------------------------
		
	def insert(self, game):
		url = game.url
		with self.lock:
			self.games[url] = GameCache(self.engine, self, game)
			return self.games[url]
		
	def get(self, game):
		return self.getFromUrl(game.url)
		
	def getFromUrl(self, url):
		with self.lock:
			return self.games[url]
		
	def remove(self, game):
		with self.lock:
			del self.games[game.url]


# ---------------------------------------------------------------------

class EngineCache(object):
	""" Thread-safe gms dict using gm-url as key. """
	
	def __init__(self, engine):
		self.engine = engine
		self.lock   = lock.RLock()
		self.gms    = dict()
		
		# add all GMs from database
		with db_session:
			for gm in self.engine.main_db.GM.select():
				self.insert(gm)
		
		# initialize GMs databases
		for gm in self.gms:
			self.gms[gm].connect_db()
		
		self.engine.logging.info('EngineCache created')
		
	# --- cache implementation ----------------------------------------
		
	def insert(self, gm):
		url = gm.url
		with self.lock:
			self.gms[url] = GmCache(self.engine, gm)
			return self.gms[url]
		
	def get(self, gm):
		return self.getFromUrl(gm.url)
		
	def getFromUrl(self, url):
		with self.lock:
			return self.gms[url]
		
	def remove(self, gm):
		with self.lock:
			del self.gms[gm.url]
	
	# --- websocket implementation ------------------------------------
	
	def listen(self, socket):
		""" Handle new connection. """
		# read name and color
		raw = socket.receive()
		data = json.loads(raw)
		name     = data['name']
		gm_url   = data['gm_url']
		game_url = data['game_url']
		
		# insert player
		gm_cache     = self.getFromUrl(gm_url)
		game_cache   = gm_cache.getFromUrl(game_url)
		player_cache = game_cache.get(name)
		player_cache.socket = socket
		game_cache.login(player_cache)
		
		# handle incomming data
		# NOTE: needs to be done async, else db_session will block,
		# because the route, which calls this listen() has its own
		# db_session due to the bottle configuration
		player_cache.handle_async()

