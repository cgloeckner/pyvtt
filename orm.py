#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys, pathlib, hashlib

from pony.orm import *

__author__ = "Christian Glöckner"



def getDataDir():
	"""Returns a path object where persistent application data can be stored."""
	# query home
	p = pathlib.Path.home()
	
	# query system-specific appdata path
	if sys.platform.startswith('linux'):
		p = p / ".local" / "share"
	else:
		raise NotImplementedError('only linux supported yet')
	
	# ensure pyVTT folder exists
	p = p / "pyVTT"
	if not os.path.isdir(p):
		print('Creating {0}'.format(p))
		os.mkdir(p)
	
	return p



def getMd5(handle):
	hash_md5 = hashlib.md5()
	for chunk in iter(lambda: handle.read(4096), b""):
		hash_md5.update(chunk)
	return hash_md5.hexdigest()


checksums = dict()

def generateChecksums(game):
	global checksums
	checksums[game.title] = dict()
	for fname in game.getAllImages():
		with open(game.getImagePath() / fname, "rb") as handle:
			md5 = getMd5(handle)
			checksums[game.title][md5] = fname



db = Database()

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
	
	def getImagePath(self):
		return getDataDir() / 'games' / self.title

	def getAllImages(self):
		return os.listdir(self.getImagePath())

	def getImageUrl(self, image_id):
		return '/token/{0}/{1}'.format(self.title, image_id)

	def upload(self, handle):
		"""Save the given image via file handle and return the url to the image.
		"""
		game_root = self.getImagePath()
		if not os.path.isdir(game_root):
			os.mkdir(game_root)

		# test for duplicates via md5 checksum
		new_md5 = getMd5(handle.file)
		if new_md5 not in checksums[self.title]:
			# create new image on disk
			image_id   = '{0}.png'.format(len(self.getAllImages()))
			local_path = os.path.join(game_root, image_id)
			handle.save(local_path)
			checksums[self.title][new_md5] = image_id
		
		# propagate remote path
		return self.getImageUrl(checksums[self.title][new_md5])

	def clear(self):
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
		


