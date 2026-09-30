"""The ballot: GET / shows it, POST / records a vote into the tally before answering."""

import logging
import mimetypes
import os
import secrets
import socket
import sys
from http import cookies
from urllib.parse import parse_qs

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .store import MAX_LENGTH, Store, TallyUnavailable

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")
COOKIE = "voter_id"

log = logging.getLogger("ballot")
if not log.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_handler)
    log.setLevel(logging.INFO)
    log.propagate = False

_templates = Environment(
    loader=FileSystemLoader(os.path.join(HERE, "templates")),
    autoescape=select_autoescape(["html"]),
)


def new_voter_id():
    """Sixteen lower-case hex digits: 64 random bits, none dropped."""
    return secrets.token_hex(8)


def _voter_id_from(environ):
    jar = cookies.SimpleCookie()
    try:
        jar.load(environ.get("HTTP_COOKIE", ""))
    except cookies.CookieError:
        return None
    morsel = jar.get(COOKIE)
    return morsel.value if morsel is not None and morsel.value else None


def _read_form(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    body = environ["wsgi.input"].read(length) if length > 0 else b""
    return parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)


class BallotApp:
    def __init__(self, db_path=None, option_a=None, option_b=None, hostname=None):
        self.store = Store(db_path)
        self.option_a = option_a or os.environ.get("OPTION_A", "Cats")
        self.option_b = option_b or os.environ.get("OPTION_B", "Dogs")
        self.hostname = hostname or socket.gethostname()

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/") or "/"
        if path.startswith("/static/"):
            return self._static(path, start_response)
        if path != "/":
            return self._plain(start_response, "404 Not Found", "Not Found")
        if method == "GET":
            return self._page(start_response, _voter_id_from(environ) or new_voter_id(), None)
        if method == "POST":
            return self._cast(environ, start_response)
        return self._plain(start_response, "405 Method Not Allowed", "Method Not Allowed",
                           [("Allow", "GET, POST")])

    def _cast(self, environ, start_response):
        sent_id = _voter_id_from(environ)
        voter_id = sent_id or new_voter_id()
        values = _read_form(environ).get("vote")
        vote = values[0] if values else None
        if vote is None:
            return self._plain(start_response, "400 Bad Request", "Bad Request: no vote was given.")
        if len(vote) > MAX_LENGTH or len(voter_id) > MAX_LENGTH:
            return self._plain(start_response, "400 Bad Request",
                               "Bad Request: the vote or voter identifier is longer than %d characters." % MAX_LENGTH)
        log.info("Received vote for %s", vote)
        log.info("Recording vote for %s by %s", vote, voter_id)
        try:
            self.store.record(voter_id, vote)
        except TallyUnavailable as exc:
            log.error("Vote for %s by %s was not taken: %s", vote, voter_id, exc)
            return self._plain(start_response, "503 Service Unavailable",
                               "Your vote could not be taken. Please try again later.")
        return self._page(start_response, voter_id, vote)

    def _page(self, start_response, voter_id, vote):
        body = _templates.get_template("index.html").render(
            option_a=self.option_a,
            option_b=self.option_b,
            hostname=self.hostname,
            vote=vote,
        ).encode("utf-8")
        jar = cookies.SimpleCookie()
        jar[COOKIE] = voter_id
        jar[COOKIE]["path"] = "/"
        start_response("200 OK", [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Set-Cookie", jar[COOKIE].OutputString()),
        ])
        return [body]

    def _plain(self, start_response, status, text, extra=()):
        body = (text + "\n").encode("utf-8")
        start_response(status, [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(body))),
            *extra,
        ])
        return [body]

    def _static(self, path, start_response):
        relative = os.path.normpath(path[len("/static/"):])
        full = os.path.join(STATIC_DIR, relative)
        if relative.startswith("..") or os.path.isabs(relative) or not os.path.isfile(full):
            return self._plain(start_response, "404 Not Found", "Not Found")
        with open(full, "rb") as handle:
            body = handle.read()
        kind = mimetypes.guess_type(full)[0] or "application/octet-stream"
        start_response("200 OK", [("Content-Type", kind), ("Content-Length", str(len(body)))])
        return [body]


def create_app(db_path=None, **options):
    return BallotApp(db_path=db_path, **options)
