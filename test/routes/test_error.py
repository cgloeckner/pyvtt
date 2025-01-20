"""
https://github.com/cgloeckner/pyvtt/

Copyright (c) 2020-2023 Christian Glöckner
License: MIT (see LICENSE for details)
"""

from test.common import EngineBaseTest
from vtt import routes


class ErrorRoutesTests(EngineBaseTest):

    def setUp(self):
        super().setUp()
        routes.register_gm(self.engine)
        routes.register_player(self.engine)
        routes.register_resources(self.engine)
        # @NOTE: custom error pages are not routed here

    def test_401(self):
        # FIXME
        ...

    def test_404(self):
        ret = self.app.get('/non-existing/page-error', expect_errors=True)
        self.assertEqual(ret.status_int, 404)

    def test_500(self):
        # FIXME
        ...
