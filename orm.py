#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, pathlib, hashlib, threading, logging, time, requests, uuid, tempfile, shutil, zipfile, json, math

import bottle

from pony.orm import *

from PIL import Image, UnidentifiedImageError

__author__ = "Christian Glöckner"


db = Database()


class GameCache(object):
	
	def __init__(self):
		self.lock     = threading.Lock()
		self.players  = dict() # key: name, value: color
		self.colors   = dict() # key: color, value: name
		self.selected = dict() # key: name, value: list of token IDs
	
	def insert(self, name, color):
		with self.lock:
			self.players[color] = name
			self.colors[name]   = color
			self.selected[name] = list()
		
	def remove(self, name):
		with self.lock:
			color = self.colors[name]
			del self.players[color]
			del self.colors[name]
			del self.selected[name]
		
	def getList(self):
		result = list()
		with self.lock:
			for name in self.colors:
				result.append('{0}:{1}'.format(name, self.colors[name]))
		return result
		
	def getColor(self, name):
		with self.lock:
			return self.colors[name]
		
	def getSelected(self):
		with self.lock:
			return self.selected  
		
	def setSelection(self, name, ids):
		with self.lock:
			self.selected[name] = ids


class EngineCache(object):
	
	def __init__(self):
		self.lock  = threading.Lock()
		self.games = dict() # key: url, value: PlayerCache
		
	def insert(self, game, name, color):
		url   = game.getUrl()
		cache = None
		with self.lock:
			if url not in self.games:
				self.games[url] = GameCache()
			cache = self.games[url]
		cache.insert(name, color)
		
	def remove(self, game, name):
		url = game.getUrl()
		cahe = None
		with self.lock:
			cache = self.games[url]
		cache.remove(name)
		
	def contains(self, game): 
		url = game.getUrl()
		with self.lock:
			return url in self.games
		
	def getList(self, game):
		result = list()
		cache  = None   
		url = game.getUrl()
		with self.lock:
			cache = self.games[url]
		return cache.getList()
		
	def getColor(self, game, name):
		cache = None   
		url = game.getUrl()
		with self.lock:
			cache = self.games[url]
		return cache.getColor(name)
		
	def getSelected(self, game):
		cache = None   
		url = game.getUrl()
		with self.lock:
			cache = self.games[url]
		return cache.getSelected()
		
	def setSelection(self, game, name, ids):
		cache = None    
		url = game.getUrl()
		with self.lock:
			cache = self.games[url]
		cache.setSelection(name, ids)


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
		
		# whitelist for game urls etc.
		self.url_whitelist = []
		# allow lower/upper case characters
		for i in range(65, 91):
			self.url_whitelist.append(chr(i))
			self.url_whitelist.append(chr(i+32))
		# allow numbers
		for i in range(10):	
			self.url_whitelist.append('{0}'.format(i))
		# allow some symbols
		self.url_whitelist.append('-')
		self.url_whitelist.append('_')
		self.url_whitelist.append('.')
		
		# setup blacklist replacemap
		self.url_replacemap = {
			'ä': 'ae',
			'Ä': 'Ae',
			'ö': 'oe',
			'Ö': 'Oe',
			'ü': 'ue',
			'Ü': 'Ue',
			'ß': 'ss'
		}
		
		# blacklist for GM names
		self.gm_blacklist = ['static', 'token', 'vtt']
		
		self.local_gm    = False
		self.title       = 'PyVTT'
		self.imprint_url = ''

		# game cache
		self.cache = EngineCache()

	def setup(self, argv):
		self.debug    = '--debug' in argv
		self.local_gm = '--local_gm' in argv
		
		# setup logging
		if self.debug:
			logging.basicConfig(filename=self.data_dir / 'pyvtt.log', level=logging.DEBUG)
		else:
			logging.basicConfig(filename=self.data_dir / 'pyvtt.log', level=logging.INFO)
		
		logging.info('Started Modes: debug={0}, local_gm={1}'.format(self.debug, self.local_gm))
		
		# handle settings
		settings_path = self.data_dir / 'settings.json'
		if not os.path.exists(settings_path):
			# create default settings
			settings = {
				'title'       : self.title,
				'imprint_url' : self.imprint_url,
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
				self.host        = settings['host']
				self.port        = settings['port']
				self.socket      = settings['socket']
			logging.info('Settings loaded')
		
		# show argv help
		if '--help' in argv:
			print('Commandline args:')
			print('    --debug       Starts in debug mode.')
			print('    --local_gm    Starts in local-GM-mode.')
			print('')
			print('Debug Mode:    Enables debug level logging and restricts to localhost (overrides unix socket settings).')
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
		
		# prepare existing games' cache
		with db_session:
			s = time.time()
			for gm in db.GM.select():
				gm.makeLock()
			for g in db.Game.select():
				g.makeMd5s()
			t = time.time() - s
			logging.info('Image checksums and threading locks created within {0}s'.format(t))
		
		if not self.local_gm:
			# trigger cleanup every 24h
			self.cleanup()
		
	def run(self):
		if self.debug or self.socket == '':
			# run via host and port
			logging.info('Running server on {0}:{1}'.format(self.host, self.port))
			bottle.run(
				host     = self.host,
				port     = self.port,
				reloader = self.debug,
				debug    = self.debug,
				quiet    = not self.debug,
				server   = 'gevent'
			)
		else:
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

	def getIp(self):
		if self.local_gm:
			return self.publicip
		elif self.host == '0.0.0.0':
			return 'localhost'
		else:
			return self.host 
	
	def getClientIp(self, request):
		if self.socket is not None:
			return request.environ.get('HTTP_X_FORWARDED_FOR')
		else:
			return request.environ.get('REMOTE_ADDR')
	
	def applyWhitelist(self, s):
		# apply replace map                      
		for key in self.url_replacemap:
			s = s.replace(key, self.url_replacemap[key])
		# apply whitelist (replace everything else by '-')
		fixed = ''
		for c in s:
			if c in self.url_whitelist:
				fixed += c
			else:
				fixed += '-'
		if len(fixed) == 0: # is this really necessary? gonna return '' here instead @TODO
			return None
		return fixed
	
	@staticmethod
	def getMd5(handle):
		hash_md5 = hashlib.md5()
		offset = handle.tell()
		for chunk in iter(lambda: handle.read(4096), b""):
			hash_md5.update(chunk)
		# rewind after reading
		handle.seek(offset)
		return hash_md5.hexdigest()
	
	def cleanup(self):
		""" Cleanup all expired GM data. """
		with db_session:
			now = int(time.time())
			num_gms   = 0
			num_games = 0
			for gm in db.GM.select():
				if gm.expire < now:
					num_gms += 1
					for g in gm.games:
						g.clear()
						num_games += 1
					gm.clear()
		
		logging.info('Database cleanup: {0} GMs and {1} Games removed'.format(num_gms, num_games))
		
		# schedule next cleanup
		self.cleaner = threading.Thread(target=Engine.clean_handle, args=self)
	
	def clean_handle(self):
		time.sleep(3600 * 24) # 24h
		self.cleanup()

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
	player = Required(str)
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
		return '/{0}/{1}'.format(self.admin.name, self.url)
	
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
			if db.Token.select(lambda t: t.url == url).first() is None:
				# found abandoned image
				abandoned.append(os.path.join(game_root, image_id))
			
		return abandoned

	def removeAbandonedImages(self):
		relevant = self.getAbandonedImages()
		cleanup = 0
		with engine.locks[self.admin.name]: # make IO access safe
			for fname in relevant:
				cleanup += os.path.getsize(fname)
				os.remove(fname)
		return cleanup, len(relevant)

	def clear(self):
		img_path = self.getImagePath()
		with engine.locks[self.admin.name]: # make IO access safe
			if os.path.isdir(img_path):
				# remove all images
				for img in self.getAllImages():
					path = os.path.join(img_path, img)
					os.remove(path)
				# remove image dir (= game dir)
				os.rmdir(img_path)

	def toZip(self):
		# remove abandoned images
		self.removeAbandonedImages()
		
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
				"locked" : t.locked
			})
			id_translation[t.id] = len(tokens) - 1
		
		# collect all scenes in this game
		scenes = list()
		active = 0
		for s in self.scenes:
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
			"scenes" : scenes,
			"active" : active
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
			
				if data["active"] == sid:
					db.commit()
					game.active = scene.id
			
			db.commit()
			
			return game
 
# -----------------------------------------------------------------------------

class GM(db.Entity):
	id     = PrimaryKey(int, auto=True)
	name   = Required(str, unique=True)
	ip     = Required(str, default='127.0.0.1') # note: could be used twice (same internet connection, multiple users)
	sid    = Required(str)
	expire = Optional(int)
	games  = Set("Game", cascade_delete=True, reverse="admin") # forward deletion to games
	
	def makeLock(self):
		engine.locks[self.name] = threading.Lock();
	
	def postSetup(self):
		self.expire = int(time.time()) + 3600 * 24 * 30 # expire after 30d
		
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
		
	def clear(self):
		root_path = self.getBasePath()
		games_path = self.getGamesPath()
		export_path = self.getExportPath()
		
		with engine.locks[self.name]: # make IO access safe
			if os.path.isdir(export_path):
				# remove all export files
				for fname in self.getAllImages():
					path = os.path.join(export_path, fname)
					os.remove(path)
				# remove export dir
				os.rmdir(export_path)
			if os.path.isdir(games_path):
				# remove games dir
				os.rmdir(games_path)
			if os.path.isdir(root_path):
				# remove root dir
				os.rmdir(root_path)

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
		


