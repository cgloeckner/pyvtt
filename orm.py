#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, pathlib, hashlib, threading, logging, time, requests, uuid

from pony.orm import *

__author__ = "Christian Glöckner"


db = Database()

class Engine(object):

	def __init__(self):
		# Setups path object where persistent application data can be stored.
		p = pathlib.Path.home()
		if sys.platform.startswith('linux'):
			p = p / ".local" / "share"
		else:
			raise NotImplementedError('only linux supported yet')
		
		# ensure pyVTT folder exists
		p = p / 'pyVTT'
		
		if not os.path.isdir(p):
			os.mkdir(p)
		
		self.data_dir = p
		
		if not os.path.isdir(p / 'gms'):
			os.mkdir(p / 'gms')
		
		# setup per-game stuff
		self.checksums = dict()
		self.locks     = dict()
		
		# webserver stuff
		self.host  = '0.0.0.0'
		self.port  = 8080
		self.debug = False
		
		# whitelist for game urls etc.
		self.url_whitelist = []
		for i in range(65, 91):
			self.url_whitelist.append(chr(i))
			self.url_whitelist.append(chr(i+32))
		for i in range(10):	
			self.url_whitelist.append('{0}'.format(i))
		self.url_whitelist.append('-')
		self.url_whitelist.append('_')
		
		# blacklist for GM names
		self.gm_blacklist = ['static', 'token', 'vtt']

		# game cache
		self.players = dict()
		self.colors  = dict()
		self.selected  = dict()

	def setup(self, argv):
		for line in argv:
			if line == '--debug':
				print('Debug Mode enabled')
				self.debug = True
				
			if line.startswith('--port'):
				print('Setting custom port')
				self.port = int(line.split('=')[1])
	
		# setup listening ip
		if self.debug:
			self.host = 'localhost'
		else:
			self.host = '0.0.0.0'
		
		# setup logging
		if self.debug:
			logging.basicConfig(filename=self.data_dir / 'pyvtt.log', level=logging.DEBUG)
		else:
			logging.basicConfig(filename=self.data_dir / 'pyvtt.log', level=logging.INFO)
		
		# query public ip
		self.publicip = requests.get('https://api.ipify.org').text
		logging.info('Public IP is {0}'.format(self.publicip))
		
		# prepare existing games' cache
		with db_session:
			s = time.time()
			for gm in db.GM.select():
				gm.makeLock()
			for g in db.Game.select():
				g.makeMd5s()
			t = time.time() - s
			logging.info('Image checksums and threading locks created within {0}s'.format(t))

	def getIp(self):
		if self.debug:
			return 'localhost'
		else:
			return self.publicip

	def applyWhitelist(self, s):
			# secure symbols used in url
			fixed = ''
			for c in s:
				if c in self.url_whitelist:
					fixed += c
				else:
					fixed += '_'
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
	timeid  = Required(int, default=0) # dirty flag
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


# -----------------------------------------------------------------------------

class Scene(db.Entity):
	id      = PrimaryKey(int, auto=True)
	game    = Required("Game")
	timeid  = Required(int, default=0) # keeps time for dirtyflag on tokens
	tokens  = Set("Token", cascade_delete=True, reverse="scene") # forward deletion to tokens
	backing = Optional("Token", reverse="back") # background token

# -----------------------------------------------------------------------------

class Roll(db.Entity):
	id     = PrimaryKey(int, auto=True)
	game   = Required("Game")
	player = Required(str)
	sides  = Required(int)
	result = Required(int)
	timeid = Required(int, unique=0)


# -----------------------------------------------------------------------------

class Game(db.Entity):
	id     = PrimaryKey(int, auto=True)
	url    = Required(str)
	scenes = Set("Scene", cascade_delete=True) # forward deletion to scenes
	active = Optional(int)
	rolls  = Set(Roll)
	admin  = Required("GM", reverse="games")
	# GM options
	d4     = Optional(bool, default=True)
	d6     = Optional(bool, default=True)
	d8     = Optional(bool, default=True)
	d10    = Optional(bool, default=True)
	d12    = Optional(bool, default=True)
	d20    = Optional(bool, default=True)
	multiselect = Optional(bool, default=False)
	
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
		# test for duplicates via md5 checksum
		new_md5 = engine.getMd5(handle.file)
		
		game_root = self.getImagePath()
		
		with engine.locks[self.admin.name]: # make IO access safe
			if new_md5 not in engine.checksums[self.getUrl()]:
				# create new image on disk
				next_id    = self.getNextId()
				image_id   = '{0}.png'.format(next_id)
				local_path = os.path.join(game_root, image_id)
				handle.save(local_path)
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

# -----------------------------------------------------------------------------

class GM(db.Entity):
	id     = PrimaryKey(int, auto=True)
	name   = Required(str, unique=True)
	ip     = Required(str) # note: could be used twice (same internet connection, multiple users)
	sid    = Required(str)
	expire = Optional(int)
	games  = Set("Game", cascade_delete=True, reverse="admin") # forward deletion to games
	
	def makeLock(self):
		engine.locks[self.name] = threading.Lock();
	
	def postSetup(self):
		self.expire = int(time.time()) + 3600 * 24 * 7 * 2 # expire in two weaks
		
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
		ip  = request.environ.get('REMOTE_ADDR')
		return db.GM.select(lambda g: g.ip == ip and g.sid == sid).first()
	
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
		


