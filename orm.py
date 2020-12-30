#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, pathlib, hashlib, threading, logging, time, requests, uuid, tempfile, shutil, zipfile, json, math, re, random

import bottle 
from bottle.ext.websocket import GeventWebSocketServer
from geventwebsocket.exceptions import WebSocketError

from pony.orm import *

from PIL import Image, UnidentifiedImageError

__author__ = "Christian Glöckner"


db = Database()


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
		
	def getColors(self):
		result = dict()
		with self.lock:
			for name in self.players:
				result[name] = [self.players[name].uuid, self.players[name].color]
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
			'players' : self.getColors(),
			'rolls'   : rolls,
		}); 
		
		player.write(self.fetchRefresh(g.active))
		
		# broadcast join to all players
		self.broadcast({
			'OPID'  : 'JOIN',
			'name'  : player.name,
			'uuid'  : player.uuid,
			'color' : player.color
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
		# Setups path object where persistent application data can be stored.
		p = pathlib.Path.home()
		if sys.platform.startswith('linux'):
			p = p / ".local" / "share"
		else:
			raise NotImplementedError('only linux supported yet')
		
		# ensure pyVTT folder exists
		p = p / 'pyvtt'
		
		if not os.path.isdir(p):
			os.mkdir(p)
		
		self.data_dir = p
		
		if not os.path.isdir(p / 'gms'):
			os.mkdir(p / 'gms')
		
		# setup per-game stuff
		self.checksums = dict()
		self.locks     = dict()
		
		# webserver stuff
		self.host   = '0.0.0.0'
		self.port   = 8080 
		self.socket = ''
		self.debug  = False
		self.quiet  = False
		
		# blacklist for GM names and game URLs
		self.gm_blacklist = ['', 'static', 'token', 'vtt', 'status', 'websocket']
		self.url_regex    = '^[A-Za-z0-9_\-.]+$'
		
		self.local_gm    = False
		self.title       = 'PyVTT'
		self.imprint_url = ''
		self.expire      = 3600 * 24 * 30 # default: 30d

		# game cache
		self.cache = EngineCache()

	def setup(self, argv):
		self.debug    = '--debug' in argv
		self.quiet    = '--quiet' in argv
		self.local_gm = '--local-gm' in argv
		
		# setup logging
		log_format = '[%(asctime)s] %(message)s'
		if self.debug:
			logging.basicConfig(stream=sys.stdout, format=log_format, level=logging.DEBUG)
		else:
			logging.basicConfig(filename=self.data_dir / 'pyvtt.log', format=log_format, level=logging.INFO)
		
		logging.info('Started Modes: debug={0}, quiet={1}, local_gm={2}'.format(self.debug, self.quiet, self.local_gm))
		
		# handle settings
		settings_path = self.data_dir / 'settings.json'
		if not os.path.exists(settings_path):
			# create default settings
			settings = {
				'title'       : self.title,
				'imprint_url' : self.imprint_url,
				'expire'      : self.expire,
				'listener'    : 'ip',
				'host'        : self.host,
				'port'        : self.port,
				'socket'      : self.socket
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
				self.host        = settings['host']
				self.port        = settings['port']
				self.socket      = settings['socket']
			logging.info('Settings loaded')
		
		# show argv help
		if '--help' in argv:
			print('Commandline args:')
			print('    --debug       Starts in debug mode.')
			print('    --quiet       Starts in quiet mode.')
			print('    --local-gm    Starts in local-GM-mode.')
			print('')
			print('Debug Mode:    Enables debug level logging and restricts to localhost (overrides unix socket settings).')
			print('Quiet Mode:    Disables verbose outputs.')
			print('Local-GM Mode: Replaces `localhost` in all created links by the public ip.')
			print('')
			print('See {0} for custom settings.'.format(settings_path))
			sys.exit(0)
		
		if self.local_gm:
			# query public ip
			self.publicip = requests.get('https://api.ipify.org').text
			logging.info('Public IP is {0}'.format(self.publicip))
		 
		# setup listening ip
		if self.debug:
			self.host = 'localhost'
			logging.info('Restricted to localhost')
		else:
			self.host = '0.0.0.0'
		
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
		if self.debug or self.socket == '':
			# run via host and port
			logging.info('Running server on {0}:{1}'.format(self.host, self.port))
			bottle.run(
				host     = self.host,
				port     = self.port,
				reloader = self.debug,
				debug    = self.debug,
				quiet    = self.quiet,
				server   = GeventWebSocketServer
			)
		else:
			raise NotImplementedError('unix socket NOT compatible with websocket ATM')
			"""
			# run via unix socket
			from gevent.pywsgi import WSGIServer
			from gevent import socket
			
			if os.path.exists(self.socket):
				os.remove(self.socket)
			
			listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			listener.bind(self.socket)
			listener.listen(1)
			
			server = WSGIServer(listener, bottle.default_app())
			# TODO: use `log` and `error_log` to redirect logging (because unix socket is only used in non-debug mode)
			
			logging.info('Running server via {0}'.format(self.socket))
			print('Running server via unix socket')
			try:
				server.serve_forever()
			except KeyboardInterrupt:
				pass
			"""
		
	def verifyUrlSection(self, s):
		return bool(re.match(self.url_regex, s))
		
	def getIp(self):
		if self.local_gm:
			return self.publicip
		elif self.host == '':
			return 'localhost'
		else:
			return self.host 
		
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

# -----------------------------------------------------------------------------

class Token(db.Entity):
	id      = PrimaryKey(int, auto=True)
	scene   = Required("Scene")
	url     = Required(str)
	posx    = Required(int)
	posy    = Required(int)
	zorder  = Required(int, default=0)
	size    = Required(int, default=80)
	rotate  = Required(float, default=0.0)
	flipx   = Required(bool, default=False)
	locked  = Required(bool, default=False)
	timeid  = Required(float, default=0.0) # dirty flag
	back    = Optional("Scene") # link to same scene as above but may be None
	
	def update(self, timeid, pos=None, zorder=None, size=None, rotate=None, flipx=None, locked=None):
		"""Handle update of several data fields. The timeid is set if anything
		has actually changed.
		"""
		if self.locked != locked:
			self.timeid = timeid
			self.locked = locked
		
		if pos != None:
			self.posx = pos[0]
			self.posy = pos[1]
			self.timeid = timeid
		
		if zorder != None:
			self.zorder = zorder
			self.timeid = timeid
		
		if size != None:
			self.size = size
			self.timeid = timeid
			
		if rotate != None:
			self.rotate = rotate
			self.timeid = timeid
	
		if flipx != None:
			self.flipx  = flipx
			self.timeid = timeid
	
	@staticmethod
	def getPosByDegree(origin, k, n):
		""" Get Position in circle around origin of the k-th item of n. """
		# determine degree and radius
		degree = k * 360 / n
		radius = 32 * n ** 0.5
		if n == 1:
			radius = 0
		
		# calculate position in unit circle
		s = math.sin(degree * 3.14 / 180)
		c = math.cos(degree * 3.14 / 180) 
		
		# calculate actual position
		x = int(origin[0] - radius * s)
		y = int(origin[1] + radius * c)
		
		return (x, y)


# -----------------------------------------------------------------------------

class Scene(db.Entity):
	id      = PrimaryKey(int, auto=True)
	game    = Required("Game")
	timeid  = Required(float, default=0.0) # keeps time for dirtyflag on tokens
	tokens  = Set("Token", cascade_delete=True, reverse="scene") # forward deletion to tokens
	backing = Optional("Token", reverse="back") # background token


# -----------------------------------------------------------------------------

class Roll(db.Entity):
	id     = PrimaryKey(int, auto=True)
	game   = Required("Game")
	color  = Required(str)
	sides  = Required(int)
	result = Required(int)
	timeid = Required(float, unique=0.0)


# -----------------------------------------------------------------------------

class Game(db.Entity):
	id     = PrimaryKey(int, auto=True)
	url    = Required(str)
	scenes = Set("Scene", cascade_delete=True) # forward deletion to scenes
	active = Optional(int)
	rolls  = Set(Roll)
	admin  = Required("GM", reverse="games")
	
	def getUrl(self):
		return '{0}/{1}'.format(self.admin.name, self.url)
	
	def makeMd5s(self):
		data = dict()
		for fname in self.getAllImages():
			with open(self.getImagePath() / fname, "rb") as handle:
				md5 = engine.getMd5(handle)
				data[md5] = fname
		engine.checksums[self.getUrl()] = data
	
	def postSetup(self):
		img_path = self.getImagePath()
		
		with engine.locks[self.admin.name]: # make IO access safe
			if not os.path.isdir(img_path):
				os.mkdir(img_path)
		
		self.makeMd5s()
	
	def getImagePath(self):
		return self.admin.getGamesPath() / self.url

	def getAllImages(self):
		"""Note: needs to be called from a threadsafe context."""
		return os.listdir(self.getImagePath())

	def getNextId(self):
		"""Note: needs to be called from a threadsafe context."""
		max_id = -1
		for fname in os.listdir(self.getImagePath()):
			number = int(fname.split('.png')[0])
			if number > max_id:
				max_id = number
		return max_id + 1

	def getImageUrl(self, image_id):
		return '/token/{0}/{1}/{2}'.format(self.admin.name, self.url, image_id)

	def getFileSize(self, url):
		game_root  = self.getImagePath()
		image_id   = url.split('/')[-1]
		local_path = os.path.join(game_root, image_id)
		return os.path.getsize(local_path)

	def upload(self, handle):
		"""Save the given image via file handle and return the url to the image.
		"""
		suffix  = '.{0}'.format(handle.filename.split(".")[-1])
		with tempfile.NamedTemporaryFile(suffix=suffix) as tmpfile:
			# save image to tempfile
			handle.save(tmpfile.name, overwrite=True)
			
			# shrink image
			try:
				with Image.open(tmpfile.name) as img:
					w = img.size[0]
					h = img.size[1]
					ratio = h / w
					downscale = False
					if h > w:
						if h > 2000:
							h = 2000
							w = int(h / ratio)
							downscale = True
					else:
						if w > 2000:
							w = 2000
							h = int(w * ratio)
							downscale = True
					if downscale:
						img.resize((w, h)).save(tmpfile.name)
			except UnidentifiedImageError:
				return None
			
			# create md5 checksum for duplication test
			new_md5 = engine.getMd5(tmpfile.file)
			
			game_root = self.getImagePath()
			with engine.locks[self.admin.name]: # make IO access safe
				if new_md5 not in engine.checksums[self.getUrl()]:
					# copy image to target
					next_id    = self.getNextId()
					image_id   = '{0}.png'.format(next_id)
					local_path = os.path.join(game_root, image_id)
					shutil.copyfile(tmpfile.name, local_path)
					
					# store checksum
					engine.checksums[self.getUrl()][new_md5] = image_id
			
			# propagate remote path
			return self.getImageUrl(engine.checksums[self.getUrl()][new_md5])

	def getAbandonedImages(self):
		# check all existing images
		game_root = self.getImagePath()
		all_images = list()
		with engine.locks[self.admin.name]: # make IO access safe
			all_images = self.getAllImages()
		
		abandoned = list()
		for image_id in all_images:
			url = self.getImageUrl(image_id)
			# check for any tokens
			t = db.Token.select(lambda t: t.url == url).first()
			if t is None:
				# found abandoned image
				abandoned.append(os.path.join(game_root, image_id))
			
		return abandoned
		
	def cleanup(self):
		""" Cleanup game's unused image data. """   
		logging.info('\tCleaning {0}'.format(self.url))
		
		relevant = self.getAbandonedImages()
		with engine.locks[self.admin.name]: # make IO access safe
			for fname in relevant:
				os.remove(fname)
		
	def clear(self):
		""" Remove this game from disk. """
		logging.info('\tRemoving {0}'.format(self.url))
		
		img_path = self.getImagePath()
		with engine.locks[self.admin.name]: # make IO access safe
			if os.path.isdir(img_path):
				# remove all images
				for img in self.getAllImages():
					path = os.path.join(img_path, img)
					os.remove(path)
				# remove image dir (= game dir)
				os.rmdir(img_path)
		
		# remove from cache
		engine.cache.remove(self)
		
	def toZip(self):
		# remove abandoned images
		self.cleanup()
		
		# collect all tokens in this game
		tokens = list()
		id_translation = dict() # required because the current token ids will not persist
		game_tokens = db.Token.select(
			lambda t: t.scene is not None
				and t.scene.game is not None 
				and t.scene.game == self
		)
		for t in game_tokens:
			tokens.append({
				"url"    : t.url.split('/')[-1], # remove game url (will not persist!)
				"posx"   : t.posx,
				"posy"   : t.posy,
				"zorder" : t.zorder,
				"size"   : t.size,
				"rotate" : t.rotate,
				"flipx"  : t.flipx,
				"locked" : t.locked
			})
			id_translation[t.id] = len(tokens) - 1
		
		# collect all scenes in this game
		scenes = list()
		active = 0
		for s in self.scenes.order_by(lambda s: s.id):
			tkns = list()
			for t in s.tokens:
				# query new id from translation dict
				tkns.append(id_translation[t.id])
			backing_file = None
			if s.backing is not None:
				backing_file = id_translation[s.backing.id]
			scenes.append({
				"tokens"  : tkns,
				"backing" : backing_file
			})
			if self.active == s.id:
				active = len(scenes) - 1
		
		data = {
			"tokens" : tokens,
			"scenes" : scenes
		}
		
		# build zip file
		zip_path = self.admin.getExportPath()
		zip_file = '{0}.zip'.format(self.url)
		
		with zipfile.ZipFile(zip_path / zip_file, "w") as h:
			# create temporary file and add it to the zip
			with tempfile.NamedTemporaryFile() as tmp:
				s = json.dumps(data, indent=4)
				tmp.write(s.encode('utf-8'))
				tmp.seek(0) # rewind!
				h.write(tmp.name, 'game.json')
			
			# add images to the zip, too
			p = self.getImagePath()
			for img in self.getAllImages():
				h.write(p / img, img)
		
		return zip_file, zip_path
	
	@staticmethod
	def isUniqueUrl(gm, url):
		return len(db.Game.select(lambda g: g.admin == gm and g.url == url)) == 0
	
	@staticmethod
	def fromImage(gm, url, handle):
		# create game with that image as background
		game = db.Game(url=url, admin=gm)
		game.postSetup()      
		db.commit()
		
		# create initial scene
		scene = db.Scene(game=game)
		db.commit()
		game.active = scene.id
		
		# set image as background
		token_url = game.upload(handle)
		if token_url is None:
			# rollback
			game.delete()
			return None
		
		t = db.Token(scene=scene, timeid=0, url=token_url, posx=0, posy=0, size=-1)
		db.commit()
		
		scene.backing = t
		db.commit() 
		engine.cache.insert(game)
		
		return game
	
	@staticmethod
	def fromZip(gm, url, handle):
		# unzip uploaded file to temp dir
		with tempfile.TemporaryDirectory() as tmp_dir:
			zip_path = os.path.join(tmp_dir, handle.filename)
			handle.save(str(zip_path))
			with zipfile.ZipFile(zip_path, 'r') as fp:
				fp.extractall(tmp_dir)
			
			# create game
			game = db.Game(url=url, admin=gm)
			game.postSetup()
			db.commit()
			
			# copy images to game directory
			img_path = game.getImagePath()
			for fname in os.listdir(tmp_dir):
				if fname.endswith('.png'):
					src_path = os.path.join(tmp_dir, fname)
					dst_path = img_path / fname
					shutil.copyfile(src_path, dst_path)
			
			# create all game data
			data = dict()
			json_path = os.path.join(tmp_dir, 'game.json')
			with open(json_path , 'r') as h:
				data = json.load(h)
			
			# create scenes
			for sid, s in enumerate(data["scenes"]):
				scene = db.Scene(game=game)
				
				# create tokens for that scene
				for token_id in s["tokens"]:
					token_data = data["tokens"][token_id]
					t = db.Token(                                
						scene=scene, url=game.getImageUrl(token_data['url']),
						posx=token_data['posx'], posy=token_data['posy'],
						zorder=token_data['zorder'], size=token_data['size'],
						rotate=token_data['rotate'], flipx=token_data['flipx'],
						locked=token_data['locked']
					)
					if s["backing"] == token_id:
						db.commit()
						scene.backing = t
				
				if game.active is None:
					# select first scene as active
					game.active = scene.id
			
			db.commit()
			engine.cache.insert(game)
			
			return game
 
# -----------------------------------------------------------------------------

class GM(db.Entity):
	id     = PrimaryKey(int, auto=True)
	name   = Required(str, unique=True)
	ip     = Required(str, default='127.0.0.1') # note: could be used twice (same internet connection, multiple users)
	sid    = Required(str)
	timeid = Optional(float) # dirtyflag
	games  = Set("Game", cascade_delete=True, reverse="admin") # forward deletion to games
	
	def makeLock(self):
		engine.locks[self.name] = threading.Lock();
	
	def postSetup(self):
		self.timeid = int(time.time())
		
		self.makeLock()
		
		root_path = self.getBasePath()
		games_path = self.getGamesPath()
		export_path = self.getExportPath()
		
		with engine.locks[self.name]: # make IO access safe	
			if not os.path.isdir(root_path):
				os.mkdir(root_path)
			
			if not os.path.isdir(games_path):
				os.mkdir(games_path)
		
			if not os.path.isdir(export_path):
				os.mkdir(export_path)
		
	def cleanup(self, now):
		""" Cleanup GM's expired games. """
		logging.info('Cleaning GM {0}'.format(self.name))
		
		for g in self.games:
			# query timeid of active scene
			timeid = g.scenes.select(lambda s: s.id == g.active).first().timeid
			
			if timeid > 0 and timeid + engine.expire < now:
				# remove this game
				g.clear()
			else:
				# cleanup this game
				g.cleanup()
		
	def clear(self):
		""" Remove this GM from disk. """  
		logging.info('Removing GM {0}'.format(self.name))
		
		# remove GM's directory
		root_path = self.getBasePath()
		
		with engine.locks[self.name]: # make IO access safe
			shutil.rmtree(root_path)
		
	def getBasePath(self):
		return engine.data_dir / 'gms' / self.name
	
	def getGamesPath(self):
		return self.getBasePath() / 'games'

	def getExportPath(self):
		return self.getBasePath() / 'export'

	@staticmethod
	def loadFromSession(request):
		""" Fetch GM from session id and ip address. """
		sid = request.get_cookie('session')
		return db.GM.select(lambda g: g.sid == sid).first()
	
	@staticmethod
	def genSession():
		return uuid.uuid4().hex
	


# --- UNIT TESTS --------------------------------------------------------------

import unittest

class Tests(unittest.TestCase):
	
	@db_session
	def prepare(self):
		g = db.Game(url='demo-game')
		s1 = db.Scene(game=g)
		db.Scene(game=g)
		t = db.Token(scene=s1, url='/foo', posx=10, posy=20)
	
	def setUp(self):
		db.create_tables()
		
	def tearDown(self):
		db.drop_all_tables(with_all_data=True)

	@db_session
	def test_Token_update(self):
		self.prepare()
		t = db.Token[1]
		
		# update everything
		t.update(timeid=42, pos=(4, 7), size=32, rotate=22, flipx=True)
		self.assertEqual(t.posx, 4)
		self.assertEqual(t.posy, 7)
		self.assertEqual(t.size, 32)
		self.assertEqual(t.rotate, 22)
		self.assertEqual(t.flipx, True)
		self.assertEqual(t.locked, False)
		self.assertEqual(t.timeid, 42)
		
		# lock it
		t.update(timeid=47, locked=True)
		self.assertEqual(t.locked, True)
		self.assertEqual(t.timeid, 47)
		
		# no update when locked
		t.update(timeid=50, pos=(5, 11), size=40, rotate=80, flipx=False)
		self.assertEqual(t.posx, 4)
		self.assertEqual(t.posy, 7)
		self.assertEqual(t.size, 32)
		self.assertEqual(t.rotate, 22)
		self.assertEqual(t.flipx, True)
		self.assertEqual(t.timeid, 47)
		
		# update with unlocking
		t.update(timeid=53, pos=(5, 11), size=40, rotate=80, locked=False, flipx=False)
		self.assertEqual(t.posx, 5)
		self.assertEqual(t.posy, 11)
		self.assertEqual(t.size, 40)
		self.assertEqual(t.rotate, 80)
		self.assertEqual(t.flipx, False)
		self.assertEqual(t.locked, False)
		self.assertEqual(t.timeid, 53)
		


