"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

__author__ = 'Christian Glöckner'
__licence__ = 'MIT'


import typing


class GmLike(typing.Protocol):
    id: int
    name: str
    url: str
    sid: str
    identity: str
    metdata: str | None
    timeid: float

    def make_lock(self) -> None: ...

class GameLike(typing.Protocol):
    id: int
    url: str
    scenes: set["SceneLike"]
    timeid: float
    active: int | None
    rolls: set["RollLike"]
    gm_url: str
    order: list[int] | None

class SceneLike(typing.Protocol):
    id: int
    game: GameLike
    tokens: set["TokenLike"]
    backing: typing.Optional["TokenLike"]

class RollLike(typing.Protocol):
    id: int
    game: GameLike
    name: str
    color: str
    sides: int
    result: int
    timeid: float

class TokenLike(typing.Protocol):
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



