#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os

from pony.orm import *

__author__ = "Christian Glöckner"

db = Database()

class Token(db.Entity):
	id     = PrimaryKey(int, auto=True)
	scene  = Required("Scene")
	url    = Required(str)
	posx   = Required(int)
	posy   = Required(int)
	size   = Required(int, default=64)
	rotate = Required(float, default=0.0)
	locked = Required(bool, default=False)
	timeid = Required(int, default=0) # dirty flag
	
	def update(self, timeid, pos=None, size=None, rotate=None, locked=None):
		"""Handle update of several data fields. If locked, the only available
		option is unlocking. Other actions will be ignored. The timeid is set
		if anything has changed.
		"""
		if locked != None:
			self.timeid = timeid
			self.locked = locked
		
		if self.locked:
			# cannot change something else if already locked
			return
		
		if pos != None:
			self.posx = pos[0]
			self.posy = pos[1]
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

class Player(db.Entity):
	id    = PrimaryKey(int, auto=True)
	name  = Required(str)
	game  = Required("Game")
	alive = Required(int, default=0) # timestamp last time seen


# -----------------------------------------------------------------------------

class Game(db.Entity):
	id      = PrimaryKey(int, auto=True)
	title   = Required(str, unique=True)
	scenes  = Set("Scene", cascade_delete=True) # forward deletion to scenes
	active  = Optional(str)
	rolls   = Set(Roll)
	players = Set(Player)

	def getImagePath(self):
		return os.path.join('.', 'games', self.title)

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
		
		# generate internal filename
		image_id   = '{0}.png'.format(len(self.getAllImages()))
		local_path = os.path.join(game_root, image_id)
		handle.save(local_path)
		
		# propagate remote path
		return self.getImageUrl(image_id)

	def clear(self):
		# remove all images
		game_root = self.getImagePath()
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
		


