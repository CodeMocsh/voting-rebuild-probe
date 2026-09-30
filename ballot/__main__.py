"""python -m ballot: serve the ballot with a threaded WSGI server on PORT (default 8080)."""

import os
import sys
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from .app import create_app


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main():
    port = int(os.environ.get("PORT", "8080"))
    server = make_server("0.0.0.0", port, create_app(), server_class=ThreadingWSGIServer)
    print("Ballot serving on port %d" % port, file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
