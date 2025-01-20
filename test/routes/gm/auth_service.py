"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.common import EngineBaseTest
from vtt import routes


class GmAuthLoginRoutesTest(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        # @NOTE: custom error pages are not routed here

    # FIXME: callback process via fake auth service via /vtt/callback/fake
