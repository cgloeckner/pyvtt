#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, pathlib, hashlib, threading, logging, time, requests, uuid, json, re, random

import bottle 
from geventwebsocket.exceptions import WebSocketError

from orm import db, db_session
from server import VttServer


__author__ = "Christian Glöckner"



class ProtocolError(Exception):
	""" Used if the communication between server and client behaves
	unexpected.
	"""
	
	def __init__(self, msg):
		super().__init__(msg)


class PlayerCache(object):
	instance_count = 0
	
	def __init__(self, parent, name, color):
		PlayerCache.instance_count += 1
		
		self.parent   = parent # parent cache object
		self.name     = name
		self.color    = color
		self.uuid     = uuid.uuid1().hex # used for HTML DOM id
		self.selected = list()
		
		# fetch country from ip
		self.ip       = engine.getClientIp(bottle.request)
		d = json.loads(requests.get('http://ip-api.com/json/{0}'.format(self.ip)).text)
		if 'countryCode' in d:
			self.country = d['countryCode'].lower()
		else:
			self.country = '?'
		
		self.socket   = None
		self.thread   = None
		
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
		
	def listen(self, socket):
		""" Start socket handling thread. """
		self.socket = socket
		self.thread = threading.Thread(target=self.handle, args=[self])
		self.thread.start()
		
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
		
	def handle(self, player):
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
		player.parent.logout(player)
		


class GameCache(object):
	""" Thread-safe player dict using name as key. """
	
	def __init__(self, game):
		self.lock    = threading.Lock()
		self.gmname  = game.admin.name
		self.url     = game.url
		self.players = dict() # name => player
		
	# --- cache implementation ----------------------------------------
		
	def insert(self, name, color):
		with self.lock:
			if name in self.players:
				raise KeyError
			self.players[name] = PlayerCache(self, name, color)
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
		since = time.time() - 20
		# query latest rolls and all tokens
		with db_session:
			g = db.Game.select(lambda g: g.admin.name == self.gmname and g.url == self.url).first()
			
			for r in db.Roll.select(lambda r: r.game == g and r.timeid >= since).order_by(lambda r: r.timeid):
				rolls.append({
					'color'  : r.color,
					'sides'  : r.sides,
					'result' : r.result
				})
		
		player.write({
			'OPID'    : 'ACCEPT',
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
			scene = db.Scene.select(lambda s: s.id == scene_id).first().backing
			background_id = scene.id if scene is not None else None
			for t in db.Token.select(lambda t: t.scene.id == scene_id):
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
		
		with db_session: 
			g = db.Game.select(lambda g: g.admin.name == self.gmname and g.url == self.url).first()
			# update active scene's timeid
			scene = db.Scene.select(lambda s: s.id == g.active).first()
			scene.timeid = now
			# roll dice
			db.Roll(game=g, color=player.color, sides=sides, result=result, timeid=now)
			
		# broadcast dice result
		self.broadcast({
			'OPID'    : 'ROLL',
			'color'   : player.color,
			'sides'   : sides,
			'result'  : result
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
		left   = data['left']
		top    = data['top']
		width  = data['width']
		height = data['height']
		
		# query inside given rectangle
		with db_session:
			g = db.Game.select(lambda g: g.admin.name == self.gmname and g.url == self.url).first()
			s = db.Scene.select(lambda s: s.id == g.active).first()
			token_ids = list()
			for t in db.Token.select(lambda t: t.scene == s and left <= t.posx and t.posx <= left + width and top <= t.posy and t.posy <= top + height): 
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
			g = db.Game.select(lambda g: g.admin.name == self.gmname and g.url == self.url).first()
			# update active scene's timeid
			scene = db.Scene.select(lambda s: s.id == g.active).first()
			scene.timeid = now
			
			# iterate provided tokens
			for k, tid in enumerate(ids):
				t = db.Token.select(lambda t: t.id == tid).first()
				# clone token
				pos = db.Token.getPosByDegree((posx, posy), k, len(ids))
				t = db.Token(scene=scene, url=t.url, posx=pos[0], posy=pos[1],
					zorder=t.zorder, size=t.size, rotate=t.rotate,
					flipx=t.flipx, timeid=now)
				
				db.commit()
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
			g = db.Game.select(lambda g: g.admin.name == self.gmname and g.url == self.url).first()
			# update active scene's timeid
			scene = db.Scene.select(lambda s: s.id == g.active).first()
			scene.timeid = now
			
			# iterate provided tokens
			for data in changes:
				t = db.Token.select(lambda t: t.id == data['id']).first()
				# fetch changed data (accepting None)
				posx   = data.get('posx')
				posy   = data.get('posy')
				pos    = None if posx is None or posy is None else (posx, posy)
				zorder = data.get('zorder')
				size   = data.get('size')
				rotate = data.get('rotate')
				flipx  = data.get('flipx')
				locked = data.get('locked', False)
				old_time = t.timeid
				t.update(timeid=now, pos=pos, zorder=zorder, size=size,
					rotate=rotate, flipx=flipx, locked=locked)
		
		self.broadcastTokenUpdate(player, now)  
		
	def onCreate(self, pos, urls):
		""" Handle player creating tokens. """
		# create tokens
		now = time.time()
		n = len(urls)
		tokens = list()
		with db_session:
			g = db.Game.select(lambda g: g.admin.name == self.gmname and g.url == self.url).first()
			s = db.Scene.select(lambda s: s.id == g.active).first()
			
			for k, url in enumerate(urls):
				# create tokens in circle
				x, y = db.Token.getPosByDegree(pos, k, n)
				t = db.Token(scene=s.id, timeid=now, url=url, posx=x, posy=y)
				
				db.commit()
				
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
				t = db.Token.select(lambda t: t.id == tid).first()
				data.append(t.to_dict())
				if t is not None:
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
		
		with db_session:
			g = db.Game.select(lambda g: g.admin.name == self.gmname and g.url == self.url).first()
			for t in db.Token.select(lambda t: t.scene.id == g.active and t.timeid >= since):
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


class EngineCache(object):
	""" Thread-safe game dict using gm/url as key. """
	
	def __init__(self):
		self.lock  = threading.Lock()
		self.games = dict()
		
	# --- cache implementation ----------------------------------------
		
	def insert(self, game):
		url = game.getUrl()
		with self.lock:
			self.games[url] = GameCache(game)
			return self.games[url]
		
	def get(self, game, url=None):
		if game is not None:
			url = game.getUrl()
		with self.lock:
			return self.games[url]
		
	def remove(self, game):
		url = game.getUrl()
		with self.lock:
			del self.games[url]
		
	# --- websocket implementation ------------------------------------
		
	def accept(self, socket):
		""" Handle new connection. """
		# read name and color
		raw = socket.receive()
		data = json.loads(raw)
		name  = data['name']
		url   = data['url']
		
		# insert player
		game_cache   = self.get(game=None, url=url)
		player_cache = game_cache.get(name)
		player_cache.listen(socket)
		game_cache.login(player_cache)
		


def convertBytes(size):
	prefix = ''
	if size > 1024 * 10:
		size //= 1024
		prefix = 'Ki'
		if size > 1024 * 10:
			size //= 1024
			prefix = 'Mi'
			
	return (size, prefix)


class Engine(object):         

	def __init__(self):  
		p = self.getPrefDir()
		
		# ensure pyVTT folder exists
		if not os.path.isdir(p):
			os.mkdir(p)
		
		self.data_dir = p
		
		if not os.path.isdir(p / 'gms'):
			os.mkdir(p / 'gms')
			
		if not os.path.isdir(p / 'ssl'):
			os.mkdir(p / 'ssl')
		
		# setup per-game stuff
		self.checksums = dict()
		self.locks     = dict()
		
		# webserver stuff
		self.host   = '0.0.0.0'
		self.domain = 'localhost'
		self.port   = 8080 
		self.socket = ''
		self.debug  = False
		self.quiet  = False
		self.ssl    = False
		
		# blacklist for GM names and game URLs
		self.gm_blacklist = ['', 'static', 'token', 'vtt', 'status', 'websocket']
		self.url_regex    = '^[A-Za-z0-9_\-.]+$'
		
		self.local_gm    = False
		self.localhost   = False
		self.title       = 'PyVTT'
		self.imprint_url = ''
		self.expire      = 3600 * 24 * 30 # default: 30d
		
		# game cache
		self.cache = EngineCache()
		
	def getPrefDir(self):
		p = pathlib.Path.home()
		if sys.platform.startswith('linux'):
			p = p / ".local" / "share"
		else:
			raise NotImplementedError('only linux supported yet')
		
		return p / 'pyvtt'
		
	def setup(self, argv):
		self.debug     = '--debug' in argv
		self.quiet     = '--quiet' in argv
		self.local_gm  = '--local-gm' in argv
		self.localhost = '--localhost' in argv
		
		if self.localhost:
			assert(not self.local_gm)
		
		# setup logging
		log_format = '[%(asctime)s] %(message)s'
		if self.debug:
			logging.basicConfig(stream=sys.stdout, format=log_format, level=logging.DEBUG)
		else:
			logging.basicConfig(filename=self.data_dir / 'pyvtt.log', format=log_format, level=logging.INFO)
		
		logging.info('Started Modes: debug={0}, quiet={1}, local_gm={2} localhost={3}'.format(self.debug, self.quiet, self.local_gm, self.localhost))
		
		# handle settings
		settings_path = self.data_dir / 'settings.json'
		if not os.path.exists(settings_path):
			# create default settings
			settings = {
				'title'       : self.title,
				'imprint_url' : self.imprint_url,
				'expire'      : self.expire,
				'listener'    : 'ip',
				'domain'      : self.domain,
				'port'        : self.port,
				'socket'      : self.socket,
				'ssl'         : self.ssl
			}
			with open(settings_path, 'w') as h:
				json.dump(settings, h, indent=4)
				logging.warn('Created default settings file')
		else:
			# load settings
			with open(settings_path, 'r') as h:
				settings = json.load(h)
				self.title       = settings['title']
				self.imprint_url = settings['imprint_url']
				self.expire      = settings['expire']
				self.domain      = settings['domain']
				self.port        = settings['port']
				self.socket      = settings['socket']
				self.ssl         = settings['ssl']
			logging.info('Settings loaded')
		
		# show argv help
		if '--help' in argv:
			print('Commandline args:')
			print('    --debug       Starts in debug mode.')
			print('    --quiet       Starts in quiet mode.')
			print('    --local-gm    Starts in local-GM-mode.')
			print('    --localhost   Starts in localhost mode.')
			print('')
			print('Debug Mode:     Enables debug level logging.')
			print('Quiet Mode:     Disables verbose outputs.')
			print('Local-GM Mode:  Replaces `localhost` in all created links by the public ip.')
			print('Localhost Mode: Restricts server for being used via localhost only. CANNOT BE USED WITH --local-gm')
			print('')
			print('See {0} for custom settings.'.format(settings_path))
			sys.exit(0)
		
		if self.localhost:
			# overwrite domain and host to localhost
			self.host   = '127.0.0.1'
			self.domain = 'localhost'
			logging.info('Overwriting connections to localhost')
		elif self.local_gm or self.domain == '':
			# overwrite domain with public ip
			self.domain = requests.get('https://api.ipify.org').text
			logging.info('Overwriting Domain by Public IP: {0}'.format(self.domain))
		
		# prepare engine cache
		with db_session:
			s = time.time()
			for gm in db.GM.select():
				gm.makeLock()
			for g in db.Game.select():
				g.makeMd5s()         
				self.cache.insert(g)
			t = time.time() - s
			logging.info('Image checksums and threading locks created within {0}s'.format(t))
		
	def run(self):
		certfile = ''
		keyfile  = ''
		if self.ssl:
			# enable SSL
			p = self.getPrefDir()
			certfile = p / 'ssl' / 'cacert.pem'
			keyfile  = p / 'ssl' / 'privkey.pem'
			assert(os.path.exists(certfile))
			assert(os.path.exists(keyfile))
		
		bottle.run(
			host       = self.host,
			port       = self.port,
			reloader   = self.debug,
			debug      = self.debug,
			quiet      = self.quiet,
			server     = VttServer,
			# SSL-specific
			certfile   = certfile,
			keyfile    = keyfile,
			# VttServer-specific:
			unixsocket = self.socket
		)
		
	def getDomain(self):
		if self.localhost:
			# because of forced localhost mode
			return 'localhost'
		else:
			# use domain (might be replaced by public ip)
			return self.domain
		
	def verifyUrlSection(self, s):
		return bool(re.match(self.url_regex, s))
		
	def getClientIp(self, request):
		if self.socket != '':
			return request.environ.get('HTTP_X_FORWARDED_FOR')
		else:
			return request.environ.get('REMOTE_ADDR')
		
	@staticmethod
	def getMd5(handle):
		hash_md5 = hashlib.md5()
		offset = handle.tell()
		for chunk in iter(lambda: handle.read(4096), b""):
			hash_md5.update(chunk)
		# rewind after reading
		handle.seek(offset)
		return hash_md5.hexdigest()
		
	def getDatabaseSize(self):
		size = os.stat(engine.data_dir / 'data.db').st_size
		return convertBytes(size)
		
	def getImageSizes(self):
		size = os.stat(engine.data_dir / 'gms').st_size
		return convertBytes(size)
		
	def cleanup(self):
		now = time.time()      
		with db_session:
			for gm in db.GM.select():
				if gm.timeid > 0 and gm.timeid + engine.expire < now:
					# clear expired GM
					gm.clear()
				else:
					# try to cleanup
					gm.cleanup(now)
			
			# finally delete all expired GMs
			# note: idk why but pony's cascade_delete isn't working
			for gm in db.GM.select(lambda g: g.timeid > 0 and g.timeid + engine.expire < now):
				for game in db.Game.select(lambda g: g.admin.name == gm.name):
					for scene in game.scenes:
						for token in scene.tokens:
							token.delete() 
						scene.delete()
					game.delete()
				gm.delete()
		
engine = Engine()

