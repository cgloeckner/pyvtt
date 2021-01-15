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
	
	def __init__(self, engine, parent, name, color, is_gm):
		PlayerCache.instance_count += 1
		
		self.engine   = engine
		self.parent   = parent # parent cache object
		self.name     = name
		self.color    = color
		self.uuid     = uuid.uuid1().hex # used for HTML DOM id
		self.selected = list()
		self.index    = parent.getNextId() # used for ordering players in the UI
		self.is_gm    = is_gm # whether this player is the GM or not
		
		self.greenlet = None
		
		# fetch country from ip
		self.ip       = self.engine.getClientIp(request)
		d = json.loads(requests.get('http://ip-api.com/json/{0}'.format(self.ip)).text)
		if 'countryCode' in d:
			self.country = d['countryCode'].lower()
		else:
			self.country = '?'
		
		#self.lock     = lock.RLock() # note: atm deadlocking
		self.socket   = None
		
		self.dispatch_map = {
			'PING'   : self.parent.onPing,
			'ROLL'   : self.parent.onRoll,
			'SELECT' : self.parent.onSelect,
			'RANGE'  : self.parent.onRange,
			'CLONE'  : self.parent.onClone,
			'UPDATE' : self.parent.onUpdate,
			'DELETE' : self.parent.onDelete,
			'ORDER'  : self.parent.onOrder,
			'GM-CREATE'   : self.parent.onCreateScene,
			'GM-ACTIVATE' : self.parent.onActivateScene,
			'GM-CLONE'    : self.parent.onCloneScene,
			'GM-DELETE'   : self.parent.onDeleteScene
		}
		
	def __del__(self):
		PlayerCache.instance_count -= 1
		
	# --- websocket implementation ------------------------------------
		
	def read(self):
		""" Return JSON object read from socket. """
		try:
			#with self.lock: # note: atm deadlocking
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
		raw = json.dumps(data)
		#with self.lock: # note: atm deadlocking
		if self.socket is not None and not self.socket.closed:           
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
		try:
			self.greenlet.get()
		except:
			# reraise greenlet's exception to trigger proper error reporting
			raise
		
	def handle(self):
		""" Thread-handle for dispatching player actions. """
		try:
			while True:
				# query data and operation id
				data = self.read()
				if data is None:
					# player quit
					break
				
				# dispatch operation
				opid = self.fetch(data, 'OPID')
				func = self.dispatch_map[opid]
				func(self, data)
			
		except WebSocketError as e:
			# player quit
			self.engine.logging('Player closed WebSocket by {0}'.format(self.ip))
			return
			
		except:
			# any other exception - make sure player is logged out
			self.parent.logout(self)
			raise
		
		# regular logout player
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
		self.next_id = 0 # used for player indexing in UI
		
		self.engine.logging.info('GameCache {0} for GM {1} created'.format(self.url, self.parent.url))
		
	def getNextId(self):
		with self.lock:
			ret = self.next_id
			self.next_id += 1
			return ret
		
	def consolidateIndices(self):
		""" This one fixes the player indices by removing gaps.
		This is run when a player is inserted or removed (including
		kicked).
		"""
		with self.lock:
			# sort players by old indices
			tmp = dict(sorted(self.players.items(), key=lambda i: i[1].index))
			
			# generate new_indicex
			for new_index, n in enumerate(tmp):
				self.players[n].index = new_index
		
	# --- cache implementation ----------------------------------------
		
	def insert(self, name, color, is_gm):
		with self.lock:
			if name in self.players:
				raise KeyError
			self.players[name] = PlayerCache(self.engine, self, name, color, is_gm)
			self.consolidateIndices()
			return self.players[name]
		
	def get(self, name):
		with self.lock:
			return self.players[name]
		
	def getData(self):
		result = list()
		with self.lock:
			for name in self.players:
				p = self.players[name]
				result.append({
					'name'    : name,
					'uuid'    : p.uuid,
					'color'   : p.color,
					'ip'      : p.ip,
					'country' : p.country,
					'index'   : p.index
				})
		# sort to ensure index-order
		result.sort(key=lambda i: i['index'])
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
			self.consolidateIndices()
		
	# --- websocket implementation ------------------------------------
		
	def closeSocket(self, uuid):
		""" Close single socket. """
		with self.lock:
			for name in self.players:
				p = self.players[name]
				if p.uuid == uuid:
					with p.lock:
						p.socket.close()
					return name
			self.consolidateIndices()
		
	def closeAllSockets(self):
		""" Closes all sockets. """
		with self.lock:
			for name in self.players:
				p = self.players[name]
				with p.lock:
					if p.socket is not None and not p.socket.closed:
						p.socket.close()
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
			if g is None:
				engine.logging.warning('Player {0} tried to login to {1} by {2}, but the game was not found'.format(player.name, self.url, player.ip))
				return;
			
			for r in self.parent.db.Roll.select(lambda r: r.game == g and r.timeid >= since).order_by(lambda r: r.timeid):
				# search playername
				rolls.append({
					'color'  : r.color,
					'sides'  : r.sides,
					'result' : r.result,
					'recent' : r.timeid >= recent,
					'name'   : r.name
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
			'country' : player.country,
			'index'   : player.index
		})
		
		# broadcast all indices
		update = dict()
		for n in self.players:
			p = self.players[n]
			update[p.uuid] = p.index
		self.broadcast({
			'OPID'    : 'ORDER',
			'indices' : update
		});
		
	def fetchRefresh(self, scene_id):
		""" Performs a full refresh on all tokens. """  
		tokens = list()
		background_id = 0
		with db_session:
			scene = self.parent.db.Scene.select(lambda s: s.id == scene_id).first()
			if scene is None:
				self.engine.logging.warning('Game {0}/{1} switched to scene #{2}, but the scene was not found.'.format(self.parent.url, self.url, scene_id))
				return;
			
			# get background if set
			bg = scene.backing
			background_id = bg.id if bg is not None else None
			
			# fetch token data
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
		
	def onPing(self, player, data):
		""" Handle player pinging the server. """
		# pong!
		player.write({
			'OPID'    : 'PING'
		}); 
		
	def onRoll(self, player, data):
		""" Handle player rolling a dice. """
		# roll dice
		now = time.time()
		sides  = data['sides']
		result = random.randrange(1, sides+1)
		roll_id = None
		
		if sides not in [2, 4, 6, 8, 10, 12, 20]:
			# ignore unsupported dice
			return
		
		now = time.time()
		
		with db_session: 
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			if g is None:
				engine.logging.warning('Player {0} tried to roll 1d{1} at {2}/{3} by {4}, but the game was not found'.format(player.name, sides, self.parent.url, self.url, player.ip))
				return;
			
			g.timeid = now
			
			# roll dice
			self.parent.db.Roll(game=g, name=player.name, color=player.color, sides=sides, result=result, timeid=now)
		
		# broadcast dice result
		self.broadcast({
			'OPID'   : 'ROLL',
			'color'  : player.color,
			'sides'  : sides,
			'result' : result,
			'recent' : True,
			'name'   : player.name
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
			if g is None:
				engine.logging.warning('Player {0} tried range select at {1}/{2} by {3}, but the game was not found'.format(player.name, self.parent.url, self.url, player.ip))
				return;
			g.timeid = now
			
			s = self.parent.db.Scene.select(lambda s: s.id == g.active).first()
			if s is None:
				engine.logging.warning('Player {0} tried range select at {1}/{2} in scene #{3} by {4}, but the scene was not found'.format(player.name, self.parent.url, self.url, g.active, player.ip))
				return;
				
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
			if g is None:
				engine.logging.warning('Player {0} tried clone tokens at {1}/{2} by {3}, but the game was not found'.format(player.name, self.parent.url, self.url, player.ip))
				return;
				
			g.timeid = now
			s = self.parent.db.Scene.select(lambda s: s.id == g.active).first()
			if s is None:
				engine.logging.warning('Player {0} tried clone tokens at {1}/{2} by {4}, but the scene #{3} was not found'.format(player.name, self.parent.url, self.url, g.active, player.ip))
				return;
			
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
			if g is None:
				engine.logging.warning('Player {0} tried to update token data at {1}/{2} by {3}, but the game was not found'.format(player.name, self.parent.url, self.url, player.ip))
				return;
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
				locked = data.get('locked')
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
			if g is None:
				engine.logging.warning('Player {0} tried creating a tokens at {1}/{2}, but the game was not found'.format(player.name, self.parent.url, self.url))
				return
			g.timeid = now
			
			s = self.parent.db.Scene.select(lambda s: s.id == g.active).first()
			if g is None:
				engine.logging.warning('Player {0} tried creating a tokens at {1}/{2}, but the scene #{4} was not found'.format(player.name, self.parent.url, self.url, g.active))
				return
			
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
		
	def onOrder(self, player, data):
		""" Handle reordering a player box. """
		# fetch name and direction
		name      = data['name']
		direction = data['direction']
		
		if direction not in [1, -1]:
			# ignore invalid directions
			return
		
		# move in order, fix gaps
		indices = dict()
		update  = dict()
		with self.lock:
			# determine source and destination player
			src = self.players[name].index
			dst = src + direction
			for n in self.players:
				if self.players[n].index == dst:
					# swap indices
					self.players[name].index = dst
					self.players[n].index    = src
					break
			
			# fetch update data for client: uuid => index
			for n in self.players:
				p = self.players[n]
				update[p.uuid] = p.index
		
		# broadcast ALL indices
		self.broadcast({
			'OPID'    : 'ORDER',
			'indices' : update
		});
		
	def onCreateScene(self, player, data):
		""" GM: Create new scene. """
		if not player.is_gm:
			self.engine.logging.warning('Player tried to create a scene but was not the GM by {0}'.format(player.ip))
			return
		 
		# query game 
		now = time.time()
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			if g is None:
				self.engine.logging.warning('GM tried to create a scene but game not found {0}'.format(player.ip))
				return;
			g.timeid = now
			# create new, active scene
			scene = self.parent.db.Scene(game=g)
			self.parent.db.commit()
			g.active = scene.id
			# broadcast scene switch
			self.broadcastSceneSwitch(g) 
		
	def onActivateScene(self, player, data):
		""" GM: Activate a given scene. """
		if not player.is_gm:
			self.engine.logging.warning('Player tried to activate a scene but was not the GM by {0}'.format(player.ip))
			return
		
		scene_id = data['scene']
		 
		# query game 
		now = time.time()
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			if g is None:
				self.engine.logging.warning('GM tried to activate a scene but game not found {0}'.format(player.ip))
				return;
			g.timeid = now
			# test scene id
			s = self.parent.db.Scene.select(lambda s: s.id == scene_id).first()
			if s is None: 
				self.engine.logging.warning('GM tried to activate a scene but scene not found {0}'.format(player.ip))
				return
			# active scene
			g.active = scene_id
			self.parent.db.commit()
			# broadcast scene switch
			self.broadcastSceneSwitch(g) 
		
	def onCloneScene(self, player, data):
		""" GM: Clone a given scene. """
		if not player.is_gm:
			self.engine.logging.warning('Player tried to clone a scene but was not the GM by {0}'.format(player.ip))
			return
		
		scene_id = data['scene']
		 
		# query game 
		now = time.time()
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			if g is None:
				self.engine.logging.warning('GM tried to clone a scene but game not found {0}'.format(player.ip))
				return;
			g.timeid = now
			# test scene id
			s = self.parent.db.Scene.select(lambda s: s.id == scene_id).first()
			if s is None: 
				self.engine.logging.warning('GM tried to clone a scene but scene not found {0}'.format(player.ip))
				return
			# clone scene and its tokens (except background)
			clone = self.parent.db.Scene(game=g)
			for t in s.tokens:
				if t.size != -1:
				   self.parent.db.Token(
						scene=clone, url=t.url, posx=t.posx, posy=t.posy,
						zorder=t.zorder, size=t.size, rotate=t.rotate,
						flipx=t.flipx, locked=t.locked
					)
			self.parent.db.commit()
			g.active = clone.id
			# broadcast scene switch
			self.broadcastSceneSwitch(g)
		
	def onDeleteScene(self, player, data):
		""" GM: Delete a given scene. """
		if not player.is_gm:
			self.engine.logging.warning('Player tried to clone a scene but was not the GM by {0}'.format(player.ip))
			return
		
		scene_id = data['scene']
		 
		# query game 
		now = time.time()
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			if g is None:
				self.engine.logging.warning('GM tried to delete a scene but game not found {0}'.format(player.ip))
				return;
			g.timeid = now
			# delete
			s = self.parent.db.Scene.select(lambda s: s.id == scene_id).first()
			if s is None: 
				self.engine.logging.warning('GM tried to delete a scene but scene not found {0}'.format(player.ip))
				return
			s.preDelete()
			s.delete()
			self.parent.db.commit()
			# set new active scene if necessary
			if g.active == s.id:
				remain = self.parent.db.Scene.select(lambda s: s.game == g).first()
				if remain is None:
					# create new scene
					remain = self.parent.db.Scene(game=g)
					self.parent.db.commit()
				g.active = remain.id
				self.parent.db.commit()
				# broadcast scene switch
				self.broadcastSceneSwitch(g) 
		
	def broadcastTokenUpdate(self, player, since):
		""" Broadcast updated tokens. """
		# fetch all changed tokens
		all_data = list()    
		
		now = time.time()
		with db_session:
			g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
			if g is None:
				self.engine.logging.warning('A token update broadcast could not be performed at {0}/{1} by {2}, because the game was not found'.format(self.parent.url, self.url, self.engine.getClientIp(request)))
				return;
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
		
		#with player_cache.lock: # note: atm deadlocking
		player_cache.socket = socket
		game_cache.login(player_cache)
		
		# handle incomming data
		# NOTE: needs to be done async, else db_session will block,
		# because the route, which calls this listen() has its own
		# db_session due to the bottle configuration
		player_cache.handle_async()

