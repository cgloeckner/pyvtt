from gevent import monkey; monkey.patch_all()

from vtt.engine import Engine
from vtt.cleanup import CleanupThread
from vtt import routes
from vtt.settings import flag_settings


def main() -> None:
    flags = flag_settings()
    
    # run engin 
    try:
        engine = Engine(**flags)
        routes.register_gm(engine)
        routes.register_player(engine)
        routes.register_resources(engine)
        routes.register_error(engine)
        routes.register_api(engine)

        engine.cleanup_worker = CleanupThread(engine)
        engine.run()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

