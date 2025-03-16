import os
import hashlib
import json

from gevent import lock
from PIL import Image, UnidentifiedImageError
import bottle

from vtt import utils


class DiskStorage:
    def __init__(self, paths: utils.PathApi) -> None:
        # setup per-game stuff
        self.checksums = dict()
        self.locks = dict()
        
        self.paths = paths

    def setup_gm(self, gm_url: str) -> None:
        """Setup GM data directory"""
        if gm_url not in self.locks:
            self.locks[gm_url] = lock.RLock()
        
        root_path = self.paths.get_gms_path(gm_url)

        with self.locks[gm_url]:  # make IO access safe
            if not os.path.isdir(root_path):
                os.mkdir(root_path)

    def setup_game(self, gm_url: str, game_url: str) -> None:
        """Setup game data directory"""
        if gm_url not in self.locks:
            self.locks[gm_url] = lock.RLock()
        
        md5_key = DiskStorage.to_md5_key(gm_url, game_url)
        if md5_key not in self.checksums:
            self.checksums[md5_key] = {}
        
        img_path = self.paths.get_game_path(gm_url, game_url)
        with self.locks[gm_url]:  # make IO access safe
            if not os.path.isdir(img_path):
                os.mkdir(img_path)
 
    @staticmethod
    def to_md5_key(gm_url: str, game_url: str) -> str:
        return f'{gm_url}/{game_url}'

    @staticmethod
    def get_md5(handle):
        hash_md5 = hashlib.md5()
        offset = handle.tell()
        for chunk in iter(lambda: handle.read(4096), b""):
            hash_md5.update(chunk)
        # rewind after reading
        handle.seek(offset)
        return hash_md5.hexdigest()
    
    def get_all_images(self, gm_url: str, game_url: str) -> list[str]:
        """Returns a list of all image files (local filename).
        @NOTE: needs to be called from a threadsafe context.
        """
        root = self.paths.get_game_path(gm_url, game_url)
        return [f for f in os.listdir(root) if f.endswith('.png')]

    def get_next_id(self, gm_url: str, game_url: str) -> int:
        """Returns the next free image number that's not used yet.
        @NOTE: needs to be called from a threadsafe context.
        """
        max_id = 0
        filenames = self.get_all_images(gm_url, game_url)

        def split(s: str) -> int:
            return int(s.split('.png')[0])

        if len(filenames) > 0:
            last_png = max(filenames, key=split)
            max_id = split(last_png) + 1
        return max_id

    def make_md5s(self, gm_url: str, game_url: str) -> int:
        """Update MD5 hash sums for all images and return the number of hashes created for those
        image that were not hashed yet.
        """
        md5_path = self.paths.get_md5_path(gm_url, game_url)
        root = self.paths.get_game_path(gm_url, game_url)
        all_images = self.get_all_images(gm_url, game_url)

        # load md5 hashes from json-file
        data = dict()
        if os.path.exists(md5_path):
            with open(md5_path, 'r') as handle:
                data = json.load(handle)

        # check if image exists for all md5 hashes
        for md5 in data.copy():
            filename = '{0}.png'.format(data[md5])
            if not os.path.exists(root / filename):
                del data[md5]

        # check for images without md5
        missing = list()
        for filename in all_images:
            filename_id = int(filename.split('.')[0])
            if filename_id not in data.values():
                missing.append(filename)

        # create missing md5 hashes
        for filename in missing:
            # create md5 of file (assumed to be images)
            with open(root / filename, "rb") as handle:
                md5 = self.get_md5(handle)
                data[md5] = int(filename.split('.')[0])
        
        md5_key = DiskStorage.to_md5_key(gm_url, game_url)
        self.checksums[md5_key] = data

        # save md5 hashes to json-file
        with open(md5_path, 'w') as handle:
            json.dump(data, handle)

        return len(missing)
