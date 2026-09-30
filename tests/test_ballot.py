"""Restart durability, the marked page and the two log lines."""

import io
import logging
import os
import re
import sys
from urllib.parse import urlencode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ballot.app import create_app  # noqa: E402
from ballot.store import Store  # noqa: E402


def _request(app, method, form=None, voter_id=None):
    body = urlencode(form or {}).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": "/",
        "wsgi.input": io.BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/x-www-form-urlencoded",
    }
    if voter_id is not None:
        environ["HTTP_COOKIE"] = "voter_id=" + voter_id
    seen = {}

    def start_response(status, headers, exc_info=None):
        seen["status"] = int(status.split()[0])
        seen["headers"] = dict(headers)

    text = b"".join(app(environ, start_response)).decode("utf-8")
    return seen["status"], seen["headers"], text


def _button(page, key):
    match = re.search(r'<button id="%s"[^>]*>.*?</button>' % key, page, re.S)
    assert match, "no button %s in page" % key
    return match.group(0)


def test_vote_survives_restart(tmp_path):
    db = str(tmp_path / "votes.db")
    first = create_app(db_path=db)
    status, _, _ = _request(first, "POST", {"vote": "b"}, voter_id="r1")
    assert status == 200
    del first
    second = create_app(db_path=db)
    assert Store(db).votes() == {"r1": "b"}
    status, _, _ = _request(second, "POST", {"vote": "a"}, voter_id="r2")
    assert status == 200
    assert Store(db).votes() == {"r1": "b", "r2": "a"}


def test_page_marks_chosen_button(tmp_path):
    app = create_app(db_path=str(tmp_path / "votes.db"), option_a="Cats", option_b="Dogs")
    status, _, page = _request(app, "POST", {"vote": "a"}, voter_id="m1")
    assert status == 200
    chosen, other = _button(page, "a"), _button(page, "b")
    assert "disabled" in chosen and "&#10004;" in chosen and "Cats" in chosen
    assert "opacity:0.5" in other and "disabled" not in other
    assert "<script" not in page
    assert "Cats vs Dogs!" in page
    assert "(Tip: you can change your vote)" in page
    assert "Processed by container ID" in page


def test_page_marks_neither_for_unoffered_choice(tmp_path):
    app = create_app(db_path=str(tmp_path / "votes.db"))
    _, _, page = _request(app, "POST", {"vote": "c"}, voter_id="m2")
    for key in ("a", "b"):
        button = _button(page, key)
        assert "disabled" not in button and "opacity" not in button and "&#10004;" not in button


def test_page_marks_nothing_before_a_vote(tmp_path):
    app = create_app(db_path=str(tmp_path / "votes.db"))
    status, headers, page = _request(app, "GET")
    assert status == 200
    assert re.match(r"voter_id=[0-9a-f]{16}(;|$)", headers["Set-Cookie"])
    for key in ("a", "b"):
        assert "disabled" not in _button(page, key)


def test_log_lines(tmp_path, caplog):
    logger = logging.getLogger("ballot")
    logger.addHandler(caplog.handler)
    try:
        app = create_app(db_path=str(tmp_path / "votes.db"))
        _request(app, "POST", {"vote": "b"}, voter_id="l1")
    finally:
        logger.removeHandler(caplog.handler)
    messages = [record.getMessage() for record in caplog.records]
    assert "Received vote for b" in messages
    assert "Recording vote for b by l1" in messages
