#!/usr/bin/python3 
# -*- coding: utf-8 -*- 
"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2021 Christian Glöckner
License: MIT (see LICENSE for details)
"""

import os, pathlib, time, uuid, tempfile, shutil, zipfile, json, math

from gevent import lock

from pony.orm import *

from PIL import Image, UnidentifiedImageError


__author__ = 'Christian Glöckner'
__licence__ = 'MIT'




def createGmDatabase(engine, filename):
	""" Creates a new database for with GM entities such as Tokens,
	Scenes etc.
	"""
	db = Database()

	class Token(db.Entity):
		id      = PrimaryKey(int, auto=True)
		scene   = Required("Scene")
		url     = Required(str)
		posx    = Required(int)
		posy    = Required(int)
		zorder  = Required(int, default=0)
		size    = Required(int)
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
				# force position onto scene (canvas)
				self.posx = min(1000, max(0, pos[0]))
				self.posy = min(560, max(0, pos[1]))
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
			
			# force position onto scene (canvas)
			x = min(1000, max(0, x))
			y = min(560, max(0, y))
			
			return (x, y)


	# -----------------------------------------------------------------------------

	class Scene(db.Entity):
		id      = PrimaryKey(int, auto=True)
		game    = Required("Game")
		tokens  = Set("Token", cascade_delete=True, reverse="scene") # forward deletion to tokens
		backing = Optional("Token", reverse="back") # background token
		
		def preDelete(self):
			# delete all tokens
			for t in self.tokens:
				t.delete()

	# -----------------------------------------------------------------------------

	class Roll(db.Entity):
		id     = PrimaryKey(int, auto=True)
		game   = Required("Game")
		color  = Required(str)
		sides  = Required(int)
		result = Required(int)
		timeid = Required(float, default=0.0)


	# -----------------------------------------------------------------------------

	class Game(db.Entity):
		id     = PrimaryKey(int, auto=True)
		url    = Required(str)
		scenes = Set("Scene", cascade_delete=True) # forward deletion to scenes
		timeid = Required(float, default=0.0) # used for cleanup
		active = Optional(int)
		rolls  = Set(Roll)
		gm_url = Required(str) # used for internal things
		
		def getUrl(self):
			return '{0}/{1}'.format(self.gm_url, self.url)
		
		def makeMd5s(self):
			data = dict()
			root = engine.paths.getGamePath(self.gm_url, self.url)
			for fname in self.getAllImages():
				with open(root / fname, "rb") as handle:
					md5 = engine.getMd5(handle)
					data[md5] = fname
			engine.checksums[self.getUrl()] = data
		
		def postSetup(self):
			img_path = engine.paths.getGamePath(self.gm_url, self.url)
			
			with engine.locks[self.gm_url]: # make IO access safe
				if not os.path.isdir(img_path):
					os.mkdir(img_path)
			
			self.makeMd5s()
		
		def getAllImages(self):
			"""Note: needs to be called from a threadsafe context."""
			return os.listdir(engine.paths.getGamePath(self.gm_url, self.url))
		
		def getNextId(self):
			"""Note: needs to be called from a threadsafe context."""
			max_id = -1
			for fname in self.getAllImages():
				number = int(fname.split('.png')[0])
				if number > max_id:
					max_id = number
			return max_id + 1

		def getImageUrl(self, image_id):
			return '/token/{0}/{1}/{2}'.format(self.gm_url, self.url, image_id)

		def getFileSize(self, url):
			game_root  = engine.paths.getGamePath(self.gm_url, self.url)
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
							if h > 4000:
								h = 4000
								w = int(h / ratio)
								downscale = True
						else:
							if w > 4000:
								w = 4000
								h = int(w * ratio)
								downscale = True
						if downscale:
							img.resize((w, h)).save(tmpfile.name)
				except UnidentifiedImageError:
					return None
				
				# create md5 checksum for duplication test
				new_md5 = engine.getMd5(tmpfile.file)
				
				game_root = engine.paths.getGamePath(self.gm_url, self.url)
				with engine.locks[self.gm_url]: # make IO access safe
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
			game_root = engine.paths.getGamePath(self.gm_url, self.url)
			all_images = list()
			with engine.locks[self.gm_url]: # make IO access safe
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
			engine.logging.info('|--> Cleaning {0}'.format(self.url))
			
			# query and remove all images that are not used as tokens
			relevant = self.getAbandonedImages()
			with engine.locks[self.gm_url]: # make IO access safe
				for fname in relevant:
					engine.logging.info('     |--x Removing {0}'.format(fname))
					os.remove(fname)
			
		def preDelete(self):
			""" Remove this game from disk before removing it from
			the GM's database. """
			engine.logging.info('|--x Removing {0}'.format(self.url))
			
			# remove game directory (including all images)
			game_path = engine.paths.getGamePath(self.gm_url, self.url)
			with engine.locks[self.gm_url]: # make IO access safe
				shutil.rmtree(game_path)
			
			# remove game from GM's cache
			gm_cache = engine.cache.getFromUrl(self.gm_url)
			gm_cache.remove(self)
			
			# remove all scenes
			for s in self.scenes:
				s.preDelete()
				s.delete()
			
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
			zip_path = engine.paths.getExportPath()
			zip_file = '{0}_{1}.zip'.format(self.gm_url, self.url)
			
			with zipfile.ZipFile(zip_path / zip_file, "w") as h:
				# create temporary file and add it to the zip
				with tempfile.NamedTemporaryFile() as tmp:
					s = json.dumps(data, indent=4)
					tmp.write(s.encode('utf-8'))
					tmp.seek(0) # rewind!
					h.write(tmp.name, 'game.json')
				
				# add images to the zip, too
				p = engine.paths.getGamePath(self.gm_url, self.url)
				for img in self.getAllImages():
					h.write(p / img, img)
			
			return zip_file, zip_path
		
		@staticmethod
		def isUniqueUrl(gm, url):
			return len(db.Game.select(lambda g: g.url == url)) == 0
		
		@staticmethod
		def fromImage(gm, url, handle):
			# create game with that image as background
			game = db.Game(url=url, gm_url=gm.url)
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
			gm_cache = engine.cache.get(gm)
			gm_cache.insert(game)
			
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
				game = db.Game(url=url, gm_url=gm.url)
				game.postSetup()
				db.commit()
				
				# copy images to game directory
				img_path = engine.paths.getGamePath(gm.url, url)
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
				gm_cache = engine.cache.get(gm)
				gm_cache.insert(game)
				
				return game
	 
	# -----------------------------------------------------------------------------
	
	db.bind('sqlite', filename, create_db=True)
	db.generate_mapping(create_tables=True)
	
	return db


def createMainDatabase(engine):
	""" Creates main database for GM data.
	"""
	
	db = Database()
	
	class GM(db.Entity):
		id        = PrimaryKey(int, auto=True)
		name      = Required(str)
		url       = Required(str, unique=True)
		sid       = Required(str, unique=True)
		timeid    = Optional(float) # used for cleanup
		
		def makeLock(self):
			engine.locks[self.url] = lock.RLock();
		
		def postSetup(self):
			self.timeid = int(time.time())
			
			self.makeLock()
			
			root_path = engine.paths.getGmsPath(self.url)
			
			with engine.locks[self.url]: # make IO access safe
				if not os.path.isdir(root_path):
					os.mkdir(root_path)
			
		def cleanup(self, gm_db, now):
			""" Cleanup GM's games' outdated rolls, unused images or
			event remove expired games (see engine.expire). """
			engine.logging.info('Cleaning GM {0} <{1}>'.format(self.name, self.url))
			
			# delete all outdated rolls
			rolls = gm_db.Roll.select(lambda r: r.timeid < now - engine.latest_rolls)
			engine.logging.info('|--> {0} outdated rolls'.format(len(rolls)))
			rolls.delete()
			
			for g in gm_db.Game.select():
				if g.timeid > 0 and g.timeid + engine.expire < now:
					# remove this game
					g.preDelete()
					g.delete()
					
				else:
					# cleanup this game
					g.cleanup()
			
		def preDelete(self):
			""" Remove this GM from disk to allow removing him from
			the main database.
			"""  
			engine.logging.info('Removing GM {0} <{1}>'.format(self.name, self.url))
			
			# remove GM's directory (including his database, all games and images)
			root_path = engine.paths.getGmsPath(self.url)
			
			with engine.locks[self.url]: # make IO access safe
				shutil.rmtree(root_path)
			
			# remove GM from engine's cache
			engine.cache.remove(self)
			
		def refreshSession(self, response, request):
			""" Refresh session id. """
			now = time.time()
			self.timeid = now
			response.set_cookie('session', self.sid, path='/', expires=now + engine.expire)
			
		@staticmethod
		def loadFromSession(request):
			""" Fetch GM from session id and ip address. """
			sid = request.get_cookie('session')
			return db.GM.select(lambda g: g.sid == sid).first()
		
		@staticmethod
		def genSession():
			return uuid.uuid4().hex
		
	# -----------------------------------------------------------------
	
	db.bind('sqlite', str(engine.paths.getMainDatabasePath()), create_db=True)
	db.generate_mapping(create_tables=True)
	
	return db

