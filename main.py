from gevent import monkey; monkey.patch_all()

import sys

from vtt.engine import Engine
from vtt.cleanup import CleanupThread
from vtt import routes


if __name__ == '__main__':
    try:
        argv = sys.argv

        engine = Engine(argv=argv)
        routes.register_gm(engine)
        routes.register_player(engine)
        routes.register_resources(engine)
        routes.register_error(engine)

        engine.cleanup_worker = CleanupThread(engine)
        engine.run()
    except KeyboardInterrupt:
        pass

