#!/usr/bin/python3

import os, json

next_token_id = 1

class Token(object):
	def __init__(self, remote_path, pos, size=64, rotate=0.0):
		"""Create a new token using a `remote_path`, placed on a given `pos`.
		Its `size` can be changed without breaking the aspect ratio. Also each
		token can `rotate` using a couple of degree. A token is not locked at
		default. If locked, its other properties cannot be changed
		"""
		global next_token_id
		self._token_id = next_token_id
		next_token_id += 1
		
		self._remote_path = remote_path
		self._pos    = pos
		self._size   = size
		self._rotate = rotate
		# note: all other data is build via properties
		self.locked = False

	def toDict(self):
		return {
			'token_id'   : self._token_id,
			'remote_path': self._remote_path,
			'pos'        : self._pos,
			'size'       : self._size,
			'rotate'     : self._rotate,
			'locked'     : self.locked
		}
		
	@staticmethod
	def fromDict(data):
		obj = Token(data['remote_path'], data['pos'])
		obj.size  = data['size']
		obj.rotate = data['rotate']
		obj.locked = data['locked']
		return obj

	def getTokenId(self):
		return self._token_id

	def getRemotePath(self):
		return self._remote_path

	def getPos(self):
		return self._pos
	
	def getSize(self):
		return self._size
	
	def getRotate(self):
		return self._rotate
	
	def setPos(self, pos):
		if not self.locked:
			self._pos = pos
	
	def setSize(self, size):
		if not self.locked:
			self._size = size
	
	def setRotate(self, rotate):
		if not self.locked:
			self._rotate = rotate
	
	token_id    = property(getTokenId)
	remote_path = property(getRemotePath)
	pos         = property(getPos, setPos)
	size        = property(getSize, setSize)
	rotate      = property(getRotate, setRotate)


class Scene(object):
	def __init__(self, title):
		self._title  = title
		self.tokens  = dict()
		self.dropped = list() # token ids
	
	def toDict(self):
		data = {
			'title'  : self._title,
			'tokens' : dict()
		}
		for t in self.tokens:
			data['tokens'][int(t)] = self.tokens[t].toDict()
		return data
	
	@staticmethod
	def fromDict(data):
		obj = Scene(data['title'])
		for token_id in data['tokens']:
			t = Token.fromDict(data['tokens'][token_id])
			obj.tokens[t.token_id] = t
		return obj
	
	def getTitle(self):
		return self._title
	
	def createToken(self, **kwargs):
		t = Token(**kwargs)
		self.tokens[t.token_id] = t
	
	title = property(getTitle)


class Game(object):

	def __init__(self, title):
		"""Create an empty game.
		"""
		self._title = title
		self.images = list()
		self.scenes = dict()
		self.active = None
		
		# create paths
		game_path = os.path.join('.', 'games', self._title)
		img_path = os.path.join('.', 'games', self._title, 'images')
		if not os.path.isdir(game_path):
			os.mkdir(game_path)
		if not os.path.isdir(img_path):
			os.mkdir(img_path)
	
	def toDict(self):
		data = {
			'title'  : self._title,
			'images' : self.images,
			'scenes' : dict(),
			'active' : self.active
		}
		for title in self.scenes:
			data['scenes'][title] = self.scenes[title].toDict()
		return data
	
	@staticmethod
	def fromDict(data):
		obj = Game(data['title'])
		obj.images = data['images']
		for title in data['scenes']:
			obj.scenes[title] = Scene.fromDict(data['scenes'][title])
		obj.active = data['active']
		return obj
	
	def getTitle(self):
		return self._title
	
	title = property(getTitle)
	
	def createScene(self, title):
		self.scenes[title] = Scene(title)
		return self.scenes[title]
	
	def uploadImage(self, fhandle):
		"""Save the given image file handle `fhandle` to a internal file
		and return the remote path to that image.
		"""
		# generate internal filename
		image_id   = '{0}.png'.format(len(self.images))
		local_path = os.path.join('.', 'games', self._title, 'images', image_id)
		fhandle.save(local_path)
		# propagate remote path
		remote_path = '/token/{0}/{1}'.format(self._title, image_id)
		self.images.append(remote_path)
		return remote_path


class Manager(object):

	def __init__(self):
		self.games = dict()
	
	def createGame(self, title):
		self.games[title] = Game(title)
	
	def saveToFile(self, path):
		# fetch data
		raw = dict()
		for title in self.games:
			raw[title] = self.games[title].toDict()
		# dump data to json file
		with open(path, 'w') as fhandle:
			json.dump(raw, fhandle, indent=4)
	
	def loadFromFile(self, path):
		# load data from json file
		tmp = dict()
		with open(path, 'r') as fhandle:
			tmp = json.load(fhandle)
		# apply data
		self.games.clear()
		for title in tmp:
			self.games[title] = Game.fromDict(tmp[title])


