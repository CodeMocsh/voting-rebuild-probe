import re

from vote.app import create_app


def client(environ=None):
    return create_app(environ or {}).test_client()


def test_page_shows_ballot():
    body = client({"OPTION_A": "Tea", "OPTION_B": "Coffee"}).get("/").get_data(as_text=True)
    assert "<title>Tea vs Coffee!</title>" in body
    assert re.search(r'<button id="a"[^>]*value="a"[^>]*>Tea</button>', body)
    assert re.search(r'<button id="b"[^>]*value="b"[^>]*>Coffee</button>', body)
    assert "(Tip: you can change your vote)" in body
    assert "Processed by container ID" in body


def test_new_cookie_is_session_only():
    cookie = client().get("/").headers["Set-Cookie"]
    assert re.match(r"voter_id=[^;]+;", cookie)
    assert "Expires" not in cookie and "Max-Age" not in cookie


def test_sent_cookie_kept():
    c = client()
    c.set_cookie("voter_id", "abc123")
    assert c.get("/").headers["Set-Cookie"].startswith("voter_id=abc123;")


def test_external_urls_are_https():
    body = client().get("/").get_data(as_text=True)
    urls = re.findall(r'(?:src|href)="([^"]+)"', body)
    assert urls
    assert not [u for u in urls if u.startswith("http:") or u.startswith("//")]


def test_post_is_405():
    assert client().post("/").status_code == 405
