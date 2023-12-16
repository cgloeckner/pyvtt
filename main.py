from gevent import monkey; monkey.patch_all()

import sys

from vtt.engine import Engine
from vtt.routes import setup_resource_routes, setup_gm_routes, setup_player_routes, setup_error_routes
from vtt.cleanup import CleanupThread


if __name__ == '__main__':
    try:
        argv = sys.argv

        engine = Engine(argv=argv)
        setup_resource_routes(engine)
        setup_gm_routes(engine)
        setup_player_routes(engine)
        setup_error_routes(engine)

        engine.cleanup_worker = CleanupThread(engine)
        engine.run()
    except KeyboardInterrupt:
        pass

