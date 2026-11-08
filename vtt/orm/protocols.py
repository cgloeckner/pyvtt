"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'

import typing

import bottle


class EntityLike(typing.Protocol):
    def delete(self) -> None: ...


class GmLike(EntityLike, typing.Protocol):
    id: int
    name: str
    url: str
    sid: str
    identity: str
    metdata: str | None
    timeid: float

    def make_lock(self) -> None: ...
    def refresh_session(self, response: bottle.Response) -> None: ...

class GameLike(EntityLike, typing.Protocol):
    id: int
    url: str
    scenes: set["SceneLike"]
    timeid: float
    active: int | None
    rolls: set["RollLike"]
    gm_url: str
    order: list[int] | None

    def create_roll(self, name: str, color: str, sides: int) -> "RollLike": ...
    def to_zip(self) -> None: ...
    def from_dict(self, data: dict[str, typing.Any]) -> None: ...

class SceneLike(EntityLike, typing.Protocol):
    id: int
    game: GameLike
    tokens: set["TokenLike"]
    backing: typing.Optional["TokenLike"]

class RollLike(EntityLike, typing.Protocol):
    id: int
    game: GameLike
    name: str
    color: str
    sides: int
    result: int
    timeid: float

class TokenLike(EntityLike, typing.Protocol):
    id: int
    scene: SceneLike
    url: str
    posx: int
    posy: int
    zorder: int
    size: int
    rotate: float
    flipx: bool
    locked: bool
    timeid: float
    back: SceneLike | None
    text: str | None
    color: str | None



