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
	
	def update(self, pos=None, size=None, rotate=None, locked=None):
		"""Handle update of several data fields. If locked, the only available
		option is unlocking. Other actions will be ignored.
		"""
		if locked != None:
			self.locked = locked
		
		if self.locked:
			# cannot change something else if already locked
			return
		if pos != None:
			self.posx = pos[0]
			self.posy = pos[1]
		if size != None:
			self.size = size
		if rotate != None:
			self.rotate = rotate


# -----------------------------------------------------------------------------

class Scene(db.Entity):
	id     = PrimaryKey(int, auto=True)
	title  = Required(str)
	game   = Required("Game")
	tokens = Set("Token", cascade_delete=True) # forward deletion to tokens


# -----------------------------------------------------------------------------

class Game(db.Entity):
	id     = PrimaryKey(int, auto=True)
	title  = Required(str, unique=True)
	scenes = Set("Scene", cascade_delete=True) # forward deletion to scenes
	active = Optional(str)

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
		t.update(pos=(4, 7), size=32, rotate=22)
		self.assertEqual(t.posx, 4)
		self.assertEqual(t.posy, 7)
		self.assertEqual(t.size, 32)
		self.assertEqual(t.rotate, 22)
		self.assertEqual(t.locked, False)
		
		# lock it
		t.update(locked=True)
		self.assertEqual(t.locked, True)
		
		# no update when locked
		t.update(pos=(5, 11), size=40, rotate=80)
		self.assertEqual(t.posx, 4)
		self.assertEqual(t.posy, 7)
		self.assertEqual(t.size, 32)
		self.assertEqual(t.rotate, 22)
		
		# update with unlocking
		t.update(pos=(5, 11), size=40, rotate=80, locked=False)
		self.assertEqual(t.posx, 5)
		self.assertEqual(t.posy, 11)
		self.assertEqual(t.size, 40)
		self.assertEqual(t.rotate, 80)
		self.assertEqual(t.locked, False)
		


