#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, pathlib, hashlib, threading, logging, time, requests

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
		p = p / "pyVTT"
		
		if not os.path.isdir(p):
			os.mkdir(p)
		
		self.data_dir = p
		
		# setup per-game stuff
		self.checksums = dict()
		self.locks     = dict()
		
		# webserver stuff
		self.host  = '0.0.0.0'
		self.port  = 8080
		self.debug = True
		self.lazy  = False
		
		# whitelist for game titles etc.
		self.gametitle_whitelist = []
		for i in range(65, 91):
			self.gametitle_whitelist.append(chr(i))
			self.gametitle_whitelist.append(chr(i+32))
		for i in range(10):	
			self.gametitle_whitelist.append('{0}'.format(i))
		self.gametitle_whitelist.append('-')
		self.gametitle_whitelist.append('_')

		# game cache
		self.players = dict()
		self.colors  = dict()
		self.selected  = dict()

	def setup(self, argv):
		self.debug = '--debug' in argv
		self.lazy  = '--lazy' in argv
		
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
			for g in db.Game.select():
				g.makeLock()
				g.makeMd5s()
			t = time.time() - s
			logging.info('Image checksums and threading locks created within {0}s'.format(t))

	def getIp(self):
		if self.debug:
			return 'localhost'
		else:
			return self.publicip

	def applyWhitelist(self, s):
			# secure symbols used in title
			fixed = ''
			for c in s:
				if c in self.gametitle_whitelist:
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
	id     = PrimaryKey(int, auto=True)
	scene  = Required("Scene")
	url    = Required(str)
	posx   = Required(int)
	posy   = Required(int)
	zorder = Required(int, default=0)
	size   = Required(int, default=64)
	rotate = Required(float, default=0.0)
	locked = Required(bool, default=False)
	timeid = Required(int, default=0) # dirty flag
	
	def update(self, timeid, pos=None, zorder=None, size=None, rotate=None, locked=None):
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
	
	
# -----------------------------------------------------------------------------

class Scene(db.Entity):
	id      = PrimaryKey(int, auto=True)
	title   = Required(str)
	game    = Required("Game")
	timeid  = Required(int, default=0) # keeps time for dirtyflag on tokens
	tokens  = Set("Token", cascade_delete=True) # forward deletion to tokens


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
	id      = PrimaryKey(int, auto=True)
	title   = Required(str, unique=True)
	scenes  = Set("Scene", cascade_delete=True) # forward deletion to scenes
	active  = Optional(str)
	rolls   = Set(Roll)
	
	def makeLock(self):
		engine.locks[self.title] = threading.Lock();
	
	def makeMd5s(self):
		data = dict()
		for fname in self.getAllImages():
			with open(self.getImagePath() / fname, "rb") as handle:
				md5 = engine.getMd5(handle)
				data[md5] = fname
		engine.checksums[self.title] = data
	
	def postSetup(self):
		self.makeLock()
		
		game_root = self.getImagePath()
		with engine.locks[self.title]: # make IO access safe
			if not os.path.isdir(game_root):
				os.mkdir(game_root)
		
		self.makeMd5s()
	
	def getImagePath(self):
		return engine.data_dir / 'games' / self.title

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
		return '/token/{0}/{1}'.format(self.title, image_id)

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
		
		with engine.locks[self.title]: # make IO access safe
			if new_md5 not in engine.checksums[self.title]:
				# create new image on disk
				next_id    = self.getNextId()
				image_id   = '{0}.png'.format(next_id)
				local_path = os.path.join(game_root, image_id)
				handle.save(local_path)
				engine.checksums[self.title][new_md5] = image_id
		
		# propagate remote path
		return self.getImageUrl(engine.checksums[self.title][new_md5])

	def getAbandonedImages(self):
		# check all existing images
		game_root = self.getImagePath()
		all_images = list()
		with engine.locks[self.title]: # make IO access safe
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
		with engine.locks[self.title]: # make IO access safe
			for fname in relevant:
				cleanup += os.path.getsize(fname)
				os.remove(fname)
		return cleanup, len(relevant)

	def clear(self):
		with engine.locks[self.title]: # make IO access saf
			game_root = self.getImagePath()
			if os.path.isdir(game_root):
				# remove all images
				for img in self.getAllImages():
					path = os.path.join(game_root, img)
					os.remove(path)
				# remove game directory
				os.rmdir(game_root)


# --- UNIT TESTS --------------------------------------------------------------

import unittest

class Tests(unittest.TestCase):
	
	@db_session
	def prepare(self):
		g = db.Game(title='demo-game')
		s1 = db.Scene(title='scene1', game=g)
		db.Scene(title='scene2', game=g)
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
		t.update(timeid=42, pos=(4, 7), size=32, rotate=22)
		self.assertEqual(t.posx, 4)
		self.assertEqual(t.posy, 7)
		self.assertEqual(t.size, 32)
		self.assertEqual(t.rotate, 22)
		self.assertEqual(t.locked, False)
		self.assertEqual(t.timeid, 42)
		
		# lock it
		t.update(timeid=47, locked=True)
		self.assertEqual(t.locked, True)
		self.assertEqual(t.timeid, 47)
		
		# no update when locked
		t.update(timeid=50, pos=(5, 11), size=40, rotate=80)
		self.assertEqual(t.posx, 4)
		self.assertEqual(t.posy, 7)
		self.assertEqual(t.size, 32)
		self.assertEqual(t.rotate, 22)
		self.assertEqual(t.timeid, 47)
		
		# update with unlocking
		t.update(timeid=53, pos=(5, 11), size=40, rotate=80, locked=False)
		self.assertEqual(t.posx, 5)
		self.assertEqual(t.posy, 11)
		self.assertEqual(t.size, 40)
		self.assertEqual(t.rotate, 80)
		self.assertEqual(t.locked, False)
		self.assertEqual(t.timeid, 53)
		


