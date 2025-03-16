import os
import hashlib
import json

from gevent import lock
from PIL import Image, UnidentifiedImageError
import bottle

from vtt import utils


class Md5Manager:
    def __init__(self, paths: utils.PathApi) -> None:
        self.checksums = dict()
        self.paths = paths
    
    @staticmethod
    def to_key(gm_url: str, game_url: str) -> str:
        return f'{gm_url}/{game_url}'

    @staticmethod
    def generate(handle) -> str:
        """Generate an md5 hash from a given file handle"""
        hash_md5 = hashlib.md5()
        offset = handle.tell()
        for chunk in iter(lambda: handle.read(4096), b""):
            hash_md5.update(chunk)
        # rewind after reading
        handle.seek(offset)
        return hash_md5.hexdigest()
    
    def init(self, gm_url: str, game_url: str, all_images: list[str]) -> int:
        """Initialize md5 cache in memory"""
        game_root_path = self.paths.get_game_path(gm_url, game_url)

        # load previous cache from disk (if possible)
        data = dict()
        md5_cache_path = self.paths.get_md5_path(gm_url, game_url)
        if os.path.exists(md5_cache_path):
            with open(md5_cache_path, 'r') as handle:
                data = json.load(handle)

        # remove cache entries for missing images
        for md5 in list(data.keys()):
            image_path = game_root_path / '{0}.png'.format(data[md5])
            if not os.path.exists(image_path):
                del data[md5]

        # add cache entries for new images
        missing = list()
        for filename in all_images:
            filename_id = int(filename.split('.')[0])
            if filename_id not in data.values():
                missing.append(filename)

        # create missing md5 hashes
        for filename in missing:
            # create md5 of file (assumed to be images)
            with open(game_root_path / filename, "rb") as handle:
                md5 = self.generate(handle)
                data[md5] = int(filename.split('.')[0])
        
        # save hashes to json-file
        with open(md5_cache_path, 'w') as handle:
            json.dump(data, handle)

        key = self.to_key(gm_url, game_url)
        self.checksums[key] = data
        return len(missing)

    def load(self, gm_url: str, game_url: str, md5: str) -> int | None:
        """Query image id by hash"""
        md5_key = self.to_key(gm_url, game_url)
        return self.checksums[md5_key].get(md5, None)

    def store(self, gm_url: str, game_url: str, md5: str, id: int) -> None:
        """Set image id to hash associated"""
        md5_key = self.to_key(gm_url, game_url)
        self.checksums[md5_key][md5] = id

    def delete(self, gm_url: str, game_url: str, img_id: int) -> None:
        """Remove cache entry"""
        md5_key = self.to_key(gm_url, game_url)
        cache = self.checksums[md5_key]
        
        # linear search for image hash
        for k, v in cache.items():
            if v == img_id:
                del cache[k]
                return


class DiskStorage:
    def __init__(self, paths: utils.PathApi) -> None:
        self.locks = dict()
        self.paths = paths
        self.md5 = Md5Manager(paths)

    def setup_gm(self, gm_url: str) -> None:
        """Setup GM data directory"""
        if gm_url not in self.locks:
            self.locks[gm_url] = lock.RLock()
        
        root_path = self.paths.get_gms_path(gm_url)

        with self.locks[gm_url]:  # make IO access safe
            if not os.path.isdir(root_path):
                os.mkdir(root_path)

    def init_game(self, gm_url: str, game_url: str) -> int:
        """Setup game data directory"""
        # setup lock for os-access
        if gm_url not in self.locks:
            self.locks[gm_url] = lock.RLock()
        
        # setup game directory
        img_path = self.paths.get_game_path(gm_url, game_url)
        with self.locks[gm_url]:  # make IO access safe
            if not os.path.isdir(img_path):
                os.mkdir(img_path)
 
        # setup md5 cache
        all_images = self.get_all_images(gm_url, game_url)
        return self.md5.init(gm_url, game_url, all_images)

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

    def get_local_image_path(self, gm_url: str, game_url: str, image_id: int) -> str:
        return self.paths.get_game_path(gm_url, game_url) / f'{image_id}.png'

    def upload_image(self, gm_url: str, game_url: str, handle: bottle.FileUpload) -> str | None:
        """Save the given image via file handle and return the url to the image."""
        # check file format
        try:
            Image.open(handle.file)
        except UnidentifiedImageError:
            # unsupported file format
            return None

        # create md5 from file
        handle.file.seek(0)
        new_md5 = self.md5.generate(handle.file)
        
        with self.locks[gm_url]:  # make IO access safe
            # look up image in cache
            image_id = self.md5.load(gm_url, game_url, new_md5)
            if image_id is None:
                image_id = self.get_next_id(gm_url, game_url)

            # make sure the file is on disk
            img_path = self.get_local_image_path(gm_url, game_url, image_id)
            if not os.path.exists(img_path):
                handle.save(str(img_path))
                self.md5.store(gm_url, game_url, new_md5, image_id)
            
            return image_id
