"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2022 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import json
import os
import random
import time

from bottle import request
from gevent import lock
from geventwebsocket.exceptions import WebSocketError

from vtt.orm.register import db_session
from .player import PlayerCache


class GameCache(object):
    """ Thread-safe player dict using name as key. """

    def __init__(self, engine, parent, game):
        # prepare MD5 hashes for all images
        num_generated = game.makeMd5s()

        self.engine = engine
        self.parent = parent
        self.lock = lock.RLock()
        self.url = game.url
        self.players = dict()  # name => player
        self.next_id = 0  # used for player indexing in UI

        self.playback = list()
        for slot_id in range(engine.file_limit['num_music']):
            if self.isMusicSlotUsed(slot_id):
                self.playback.append(False)  # exists but not playing
            else:
                self.playback.append(None)  # empty slot

        if num_generated > 0:
            self.engine.logging.info('{0} MD5 hashes generated'.format(num_generated))

    def getNextId(self):
        with self.lock:
            ret = self.next_id
            self.next_id += 1
            return ret

    def rebuildIndices(self):
        """ This one fixes the player indices by removing gaps.
        This is run when a player is inserted or removed (including
        kicked).
        """
        with self.lock:
            # sort players by old indices
            tmp = dict(sorted(self.players.items(), key=lambda i: i[1].index))

            # generate new_indicex
            for new_index, n in enumerate(tmp):
                self.players[n].index = new_index

    def getAllSlots(self):
        root = self.engine.paths.getGamePath(self.parent.url, self.url)
        slots = list()
        for slot_id in range(self.engine.file_limit['num_music']):
            if os.path.exists(root / '{0}.mp3'.format(slot_id)):
                slots.append(slot_id)
        return slots

    def uploadMusic(self, handle):
        root = self.engine.paths.getGamePath(self.parent.url, self.url)

        with self.engine.locks[self.parent.url]:  # make IO access safe
            # search for next free slot
            slots = self.getAllSlots()
            next_slot = None
            for slot_id in range(self.engine.file_limit['num_music']):
                if slot_id not in slots:
                    next_slot = slot_id
                    break
            if next_slot != None:
                # save file
                fname = root / '{0}.mp3'.format(next_slot)
                handle.save(destination=str(fname), overwrite=True)

        return next_slot

    def isMusicSlotUsed(self, slot_id):
        root = self.engine.paths.getGamePath(self.parent.url, self.url)

        with self.engine.locks[self.parent.url]:  # make IO access safe
            fname = root / '{0}.mp3'.format(int(slot_id))
            return os.path.exists(fname)

    def deleteMusic(self, slots):
        root = self.engine.paths.getGamePath(self.parent.url, self.url)

        # delete these tracks
        with self.engine.locks[self.parent.url]:  # make IO access safe
            for slot_id in slots:
                fname = root / '{0}.mp3'.format(int(slot_id))
                if os.path.exists(fname):
                    os.remove(fname)

    # --- cache implementation ----------------------------------------

    def insert(self, name, color, is_gm):
        with self.lock:
            if name in self.players and self.players[name].isOnline():
                raise KeyError(name)
            self.players[name] = PlayerCache(self.engine, self, name, color, is_gm)
            self.rebuildIndices()
            return self.players[name]

    def get(self, name):
        with self.lock:
            try:
                return self.players[name]
            except KeyError:
                return None

    def getData(self):
        result = list()
        with self.lock:
            for name in self.players:
                p = self.players[name]
                result.append({
                    'name': name,
                    'uuid': p.uuid,
                    'color': p.color,
                    'ip': p.ip,
                    'country': p.country,
                    'agent': p.agent,
                    'flag': p.flag,
                    'index': p.index
                })
        # sort to ensure index-order
        result.sort(key=lambda i: i['index'])
        return result

    def getSelections(self):
        result = dict()
        with self.lock:
            for name in self.players:
                result[name] = self.players[name].selected
        return result

    def remove(self, name):
        with self.lock:
            del self.players[name]
            self.rebuildIndices()

    # --- websocket implementation ------------------------------------

    def login(self, player):
        """ Handle player login. """
        # notify player about all players and  latest rolls
        rolls = list()
        now = time.time()
        recent = now - self.engine.recent_rolls
        since = now - self.engine.latest_rolls  # last 10min
        # query latest rolls and all tokens
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()

            if g is None:
                self.engine.logging.warning(
                    'Player {0} tried to login to {1} by {2}, but the game was not found'.format(player.name, self.url,
                                                                                                 player.ip))
                return;

            for r in self.parent.db.Roll.select(lambda r: r.game == g and r.timeid >= since).order_by(
                    lambda r: r.timeid):
                # search playername
                rolls.append({
                    'color': r.color,
                    'sides': r.sides,
                    'result': r.result,
                    'recent': r.timeid >= recent,
                    'name': r.name
                })

            # query all urls that are currently used by tokens of that game
            urls = [t.url for t in self.parent.db.Token.select(lambda t: t.scene.game == g)]

        player.write({
            'OPID': 'ACCEPT',
            'players': self.getData(),
            'rolls': rolls,
            'urls': list(set(urls)),  # drop duplicates
            'slots': self.getAllSlots(),  # music slots
            'playback': self.playback
        });

        player.write(self.fetchRefresh(g.active))

        # broadcast join to all players
        self.broadcast({
            'OPID': 'JOIN',
            'name': player.name,
            'uuid': player.uuid,
            'color': player.color,
            'country': player.country,
            'ip': player.ip,
            'agent': player.agent,
            'flag': player.flag,
            'index': player.index
        })

        # broadcast all indices
        update = dict()
        for n in self.players:
            p = self.players[n]
            update[p.uuid] = p.index
        self.broadcast({
            'OPID': 'ORDER',
            'indices': update
        });

    def logout(self, player):
        """ Handle player logout. """
        # remove player
        try:
            self.remove(player.name)
        except KeyError:
            # @NOTE: player was kicked
            pass

        # broadcast logout to all players
        self.broadcast({
            'OPID': 'QUIT',
            'name': player.name,
            'uuid': player.uuid
        })

    def disconnect(self, uuid):
        """ Close single socket. """
        with self.lock:
            for name in self.players:
                p = self.players[name]
                if p.uuid == uuid:
                    # close socket and stop thread
                    p.socket = None
                    if p.greenlet is not None:
                        p.greenlet.join(0.1)
                    # trigger logout (just in case he is stuck)
                    self.logout(p)
                    return name

    def cleanup(self):
        """ Cleanup game. """
        # disconnect all players
        with self.lock:
            for name in self.players:
                p = self.players[name]
                if p.socket != None and not p.socket.closed:
                    p.socket.close()
            self.players.clear()

    def broadcast(self, data):
        """ Broadcast given data to all clients. """
        # dump once, send multiple times
        raw = json.dumps(data)

        with self.lock:
            force_logout = list()
            # broadcast
            for name in self.players:
                s = self.players[name].socket
                try:
                    # self.players[name].write(data)
                    if s is not None:
                        s.send(raw)
                except WebSocketError:
                    pass

    def broadcastTokenUpdate(self, player, since):
        """ Broadcast updated tokens. """
        # fetch all changed tokens
        all_data = list()

        now = time.time()
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning(
                    'A token update broadcast could not be performed at {0}/{1} by {2}, because the game was not found'.format(
                        self.parent.url, self.url, self.engine.getClientIp(request)))
                return;
            g.timeid = now

            for t in self.parent.db.Token.select(lambda t: t.scene.id == g.active and t.timeid >= since):
                tmp = t.to_dict()
                tmp['uuid'] = player.uuid
                all_data.append(tmp)

        # broadcast update
        self.broadcast({
            'OPID': 'UPDATE',
            'tokens': all_data
        });

    def broadcastSceneSwitch(self, game):
        """ Broadcast scene switch. """
        # collect all tokens for the given scene
        refresh_data = self.fetchRefresh(game.active)

        # broadcast switch
        self.broadcast(refresh_data);

    def fetchRefresh(self, scene_id):
        """ Performs a full refresh on all tokens. """
        tokens = list()
        background_id = 0
        with db_session:
            scene = self.parent.db.Scene.select(lambda s: s.id == scene_id).first()
            if scene is None:
                self.engine.logging.warning(
                    'Game {0}/{1} switched to scene #{2}, but the scene was not found.'.format(self.parent.url,
                                                                                               self.url, scene_id))
                return;

            # get background if set
            bg = scene.backing
            background_id = bg.id if bg is not None else None

            # fetch token data
            for t in self.parent.db.Token.select(lambda t: t.scene.id == scene_id):
                tokens.append(t.to_dict())

        return {
            'OPID': 'REFRESH',
            'tokens': tokens,
            'background': background_id
        }

    def onPing(self, player, data):
        """ Handle player pinging the server. """
        # pong!
        try:
            player.timeid = time.time()  # NOTE: currently not used but could be useful later
            player.write({
                'OPID': 'PING'
            });
        except:
            # player quit (broken socket or invalid JSON data)
            self.logout(player)

    def onRoll(self, player, data):
        """ Handle player rolling a dice. """
        # roll dice
        now = time.time()
        sides = data['sides']
        result = random.randrange(1, sides + 1)
        roll_id = None

        if sides not in self.engine.getSupportedDice():
            # ignore unsupported dice
            return

        now = time.time()

        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning(
                    'Player {0} tried to roll 1d{1} at {2}/{3} by {4}, but the game was not found'.format(player.name,
                                                                                                          sides,
                                                                                                          self.parent.url,
                                                                                                          self.url,
                                                                                                          player.ip))
                return;

            g.timeid = now

            # roll dice
            self.parent.db.Roll(game=g, name=player.name, color=player.color, sides=sides, result=result, timeid=now)

        # broadcast dice result
        self.broadcast({
            'OPID': 'ROLL',
            'color': player.color,
            'sides': sides,
            'result': result,
            'recent': True,
            'name': player.name
        })

    def onSelect(self, player, data):
        """ Handle player selecting a token. """
        # store selection
        player.selected = data['selected']

        # broadcast selection
        self.broadcast({
            'OPID': 'SELECT',
            'color': player.color,
            'selected': player.selected,
        });

    def onRange(self, player, data):
        """ Handle player selecting multiple tokens. """
        # fetch rectangle data
        adding = data['adding']
        left = data['left']
        top = data['top']
        width = data['width']
        height = data['height']

        if left is None or top is None or width is None or height is None:
            # ignore incomplete range query
            return

        now = time.time()
        # query inside given rectangle
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning(
                    'Player {0} tried range select at {1}/{2} by {3}, but the game was not found'.format(player.name,
                                                                                                         self.parent.url,
                                                                                                         self.url,
                                                                                                         player.ip))
                return
            g.timeid = now

            s = self.parent.db.Scene.select(lambda s: s.id == g.active).first()
            if s is None:
                self.engine.logging.warning(
                    'Player {0} tried range select at {1}/{2} in scene #{3} by {4}, but the scene was not found'.format(
                        player.name, self.parent.url, self.url, g.active, player.ip))
                return

            token_ids = player.selected if adding else list()
            for t in self.parent.db.Token.select(
                    lambda t: t.scene == s and left <= t.posx and t.posx <= left + width and top <= t.posy and t.posy <= top + height):
                if t.size != -1:
                    token_ids.append(t.id)

        # store selection
        player.selected = token_ids

        # broadcast selection
        self.broadcast({
            'OPID': 'SELECT',
            'color': player.color,
            'selected': player.selected,
        });

    def onOrder(self, player, data):
        """ Handle reordering a player box. """
        # fetch name and direction
        name = data['name']
        direction = data['direction']

        if direction not in [1, -1]:
            # ignore invalid directions
            return

        # move in order, fix gaps
        indices = dict()
        update = dict()
        with self.lock:
            # determine source and destination player
            src = self.players[name].index
            dst = src + direction
            for n in self.players:
                if self.players[n].index == dst:
                    # swap indices
                    self.players[name].index = dst
                    self.players[n].index = src
                    break

            # fetch update data for client: uuid => index
            for n in self.players:
                p = self.players[n]
                update[p.uuid] = p.index

        # broadcast ALL indices
        self.broadcast({
            'OPID': 'ORDER',
            'indices': update
        });

    def onUpdateToken(self, player, data):
        """ Handle player changing token data. """
        # fetch changes' data
        changes = data['changes']
        changes.sort(key=lambda elem: elem['id'])
        ids = [item['id'] for item in changes]
        update = list()

        now = time.time()
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning(
                    'Player {0} tried to update token data at {1}/{2} by {3}, but the game was not found'.format(
                        player.name, self.parent.url, self.url, player.ip))
                return;
            g.timeid = now

            # iterate provided tokens
            tokens = self.parent.db.Token.select(lambda t: t.id in ids)

            for i, token in enumerate(tokens):
                if token is None:
                    # ignore deleted token
                    continue

                data = changes[i]
                # fetch changed data (accepting None)
                posx = data.get('posx')
                posy = data.get('posy')
                pos = None if posx is None or posy is None else (posx, posy)
                zorder = data.get('zorder')
                size = data.get('size')
                rotate = data.get('rotate')
                flipx = data.get('flipx')
                locked = data.get('locked')
                text = data.get('text')
                label = None if text is None else (text, player.color)
                if token.update(timeid=now, pos=pos, zorder=zorder, size=size,
                                rotate=rotate, flipx=flipx, locked=locked, label=label):
                    # add to broadcast data
                    tmp = token.to_dict()
                    tmp['uuid'] = player.uuid
                    update.append(tmp)

        self.broadcast({
            'OPID': 'UPDATE',
            'tokens': update
        });

    def onCreateToken(self, player, data):
        """ Handle player creating tokens. """
        # fetch token data
        posx = data['posx']
        posy = data['posy']
        size = data['size']
        urls = data['urls']
        labels = ['' for u in urls]
        color = ''
        if 'labels' in data:
            labels = data['labels']
            color = player.color

        # create tokens
        now = time.time()
        n = len(urls)
        tokens = list()
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning(
                    'Player {0} tried creating a tokens at {1}/{2}, but the game was not found'.format(player.name,
                                                                                                       self.parent.url,
                                                                                                       self.url))
                return
            g.timeid = now

            s = self.parent.db.Scene.select(lambda s: s.id == g.active).first()
            if g is None:
                self.engine.logging.warning(
                    'Player {0} tried creating a tokens at {1}/{2}, but the scene #{4} was not found'.format(
                        player.name, self.parent.url, self.url, g.active))
                return

            for k, url in enumerate(urls):
                # create tokens in circle
                x, y = self.parent.db.Token.getPosByDegree((posx, posy), k, n)
                t = self.parent.db.Token(scene=s.id, timeid=now, url=url,
                                         size=size, posx=x, posy=y, text=labels[k], color=color)

                self.parent.db.commit()

                # use first token as background if necessary
                if s.backing is None:
                    t.size = -1

                # apply as background if size equals -1
                if t.size == -1:
                    if s.backing is not None:
                        s.backing.delete()
                    s.backing = t

                tokens.append(t.to_dict())

        # broadcast creation
        self.broadcast({
            'OPID': 'CREATE',
            'tokens': tokens
        })

    def onCloneToken(self, player, data):
        """ Handle player cloning tokens. """
        # fetch clone data
        ids = data['ids']
        posx = data['posx']
        posy = data['posy']

        # calculate tokens' center of mass
        centerx = 0
        centery = 0
        with db_session:
            for k, tid in enumerate(ids):
                t = self.parent.db.Token.select(lambda t: t.id == tid).first()
                if t is None:
                    continue
                centerx += t.posx
                centery += t.posy
        centerx /= len(ids)
        centery /= len(ids)

        move_dx = posx - centerx
        move_dy = posy - centery

        # create tokens
        tokens = list()
        now = time.time()
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning(
                    'Player {0} tried clone tokens at {1}/{2} by {3}, but the game was not found'.format(player.name,
                                                                                                         self.parent.url,
                                                                                                         self.url,
                                                                                                         player.ip))
                return;

            g.timeid = now
            s = self.parent.db.Scene.select(lambda s: s.id == g.active).first()
            if s is None:
                self.engine.logging.warning(
                    'Player {0} tried clone tokens at {1}/{2} by {4}, but the scene #{3} was not found'.format(
                        player.name, self.parent.url, self.url, g.active, player.ip))
                return;

            # iterate provided tokens
            for k, tid in enumerate(ids):
                t = self.parent.db.Token.select(lambda t: t.id == tid).first()
                if t is None:
                    # ignore, t was deleted in the meantime
                    continue
                # keep relative distance
                x = int(t.posx + move_dx)
                y = int(t.posy + move_dy)
                # clone token
                t = self.parent.db.Token(scene=s, url=t.url, posx=x, posy=y,
                                         zorder=t.zorder, size=t.size, rotate=t.rotate, flipx=t.flipx,
                                         timeid=now, text=t.text, color=t.color)
                # enforce position to be within bounds
                t.update(pos=[x, y], timeid=now)

                self.parent.db.commit()
                tokens.append(t.to_dict())

        # broadcast creation
        self.broadcast({
            'OPID': 'CREATE',
            'tokens': tokens
        })

    def onDeleteToken(self, player, data):
        """ Handle player deleting tokens. """
        # delete tokens
        tokens = data['tokens']
        ids = list()
        with db_session:
            for tid in tokens:
                t = self.parent.db.Token.select(lambda t: t.id == tid).first()
                if t is not None and not t.locked:
                    ids.append(tid)
                    t.delete()

        if len(ids) > 0:
            # broadcast delete
            self.broadcast({
                'OPID': 'DELETE',
                'tokens': ids
            })

    def onBeacon(self, player, data):
        """ Handle player pinging with the mouse. """
        # add player identification
        data['color'] = player.color
        data['uuid'] = player.uuid
        # broadcast beacon
        self.broadcast(data)

    def onMusic(self, player, data):
        """ Handle player uploaded music. """
        slot_id = data['slot_id']

        if data['action'] == 'add':
            for i in slot_id:
                self.playback[i] = False

        elif data['action'] == 'play':
            if self.playback[slot_id] is not None:
                self.playback[slot_id] = True

        elif data['action'] == 'pause':
            if self.playback[slot_id] is not None:
                self.playback[slot_id] = False

        elif data['action'] == 'remove':
            self.playback[slot_id] = None
            self.deleteMusic([slot_id])

        # broadcast notification
        self.broadcast(data)

    def onCreateScene(self, player, data):
        """ GM: Create new scene. """
        if not player.is_gm:
            self.engine.logging.warning('Player tried to create a scene but was not the GM by {0}'.format(player.ip))
            return

        # query game
        now = time.time()
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning('GM tried to create a scene but game not found {0}'.format(player.ip))
                return;
            g.timeid = now

            # create new, active scene at the end of the scene list
            scene = self.parent.db.Scene(game=g)
            self.parent.db.commit()
            g.active = scene.id
            g.order.append(scene.id)

            # broadcast scene switch
            self.broadcastSceneSwitch(g)

    def onMoveScene(self, player, data):
        """ GM: Move a given scene one step (either left or right). """
        if not player.is_gm:
            self.engine.logging.warning('Player tried to move a scene but was not the GM by {0}'.format(player.ip))
            return

        scene_id = data['scene']
        step = data['step']
        if step not in [-1, 1]:
            self.engine.logging.warning(
                'GM tried to move a scene but with invalid stepping, access by {0}'.format(player.ip))
            return

        # query game
        now = time.time()
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning('GM tried to move a scene but game not found {0}'.format(player.ip))
                return
            # test scene id
            scene = self.parent.db.Scene.select(lambda s: s.id == scene_id).first()
            if scene is None:
                self.engine.logging.warning('GM tried to move a scene but scene not found {0}'.format(player.ip))
                return

            # build initial order if not created yet
            if len(g.order) == 0:
                g.reorderScenes()

            # query index within that list
            try:
                old = g.order.index(scene_id)
            except ValueError:
                self.engine.logging.warning('GM tried to move a scene but scene not found {0}'.format(player.ip))
                return

            # determine indices of scenes to swap
            new = old + step
            if new < 0 or new >= len(g.order):
                # ignore edge case
                return

            # swap!
            g.order[old], g.order[new] = g.order[new], g.order[old]
            g.timeid = now

    def onActivateScene(self, player, data):
        """ GM: Activate a given scene. """
        if not player.is_gm:
            self.engine.logging.warning('Player tried to activate a scene but was not the GM by {0}'.format(player.ip))
            return

        scene_id = data['scene']

        # query game
        now = time.time()
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning('GM tried to activate a scene but game not found {0}'.format(player.ip))
                return;
            g.timeid = now
            # test scene id
            s = self.parent.db.Scene.select(lambda s: s.id == scene_id).first()
            if s is None:
                self.engine.logging.warning('GM tried to activate a scene but scene not found {0}'.format(player.ip))
                return
            # active scene
            g.active = scene_id
            self.parent.db.commit()
            # broadcast scene switch
            self.broadcastSceneSwitch(g)

    def onCloneScene(self, player, data):
        """ GM: Clone a given scene. """
        if not player.is_gm:
            self.engine.logging.warning('Player tried to clone a scene but was not the GM by {0}'.format(player.ip))
            return

        scene_id = data['scene']

        # query game
        now = time.time()
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning('GM tried to clone a scene but game not found {0}'.format(player.ip))
                return;
            g.timeid = now
            # test scene id
            s = self.parent.db.Scene.select(lambda s: s.id == scene_id).first()
            if s is None:
                self.engine.logging.warning('GM tried to clone a scene but scene not found {0}'.format(player.ip))
                return
            # clone scene and its tokens (except background)
            clone = self.parent.db.Scene(game=g)
            for t in s.tokens:
                if t.size != -1:
                    self.parent.db.Token(
                        scene=clone, url=t.url, posx=t.posx, posy=t.posy,
                        zorder=t.zorder, size=t.size, rotate=t.rotate,
                        flipx=t.flipx, locked=t.locked, text=t.text,
                        color=t.color
                    )
            self.parent.db.commit()
            g.active = clone.id
            g.order.append(clone.id)
            # broadcast scene switch
            self.broadcastSceneSwitch(g)

    def onDeleteScene(self, player, data):
        """ GM: Delete a given scene. """
        if not player.is_gm:
            self.engine.logging.warning('Player tried to clone a scene but was not the GM by {0}'.format(player.ip))
            return

        scene_id = data['scene']

        # query game
        now = time.time()
        with db_session:
            g = self.parent.db.Game.select(lambda g: g.url == self.url).first()
            if g is None:
                self.engine.logging.warning('GM tried to delete a scene but game not found {0}'.format(player.ip))
                return;
            g.timeid = now
            # delete
            s = self.parent.db.Scene.select(lambda s: s.id == scene_id).first()
            if s is None:
                self.engine.logging.warning('GM tried to delete a scene but scene not found {0}'.format(player.ip))
                return
            s.preDelete()
            s.delete()
            self.parent.db.commit()

            # rebuild order list
            new_order = list()
            for sid in g.order:
                if sid != scene_id:
                    # place that scene
                    new_order.append(sid)
            g.order = new_order

            # set new active scene if necessary
            if g.active == s.id:
                remain = self.parent.db.Scene.select(lambda s: s.game == g).first()
                if remain is None:
                    # create new scene
                    remain = self.parent.db.Scene(game=g)
                    self.parent.db.commit()
                    g.order = [remain.id]
                g.active = remain.id
                self.parent.db.commit()
                # broadcast scene switch
                self.broadcastSceneSwitch(g)
