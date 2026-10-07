"""The HTTP contract of /, through the Flask test client and a fake Redis.

Needs Flask and redis installed (vote/requirements.txt).
"""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis  # noqa: E402

import app as vote_app  # noqa: E402


class FakeRedis:
    def __init__(self):
        self.lists = {}
        self.fail = False
        self.rendered_before_push = None

    def rpush(self, key, value):
        if self.fail:
            raise redis.TimeoutError('Timeout reading from socket')
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])

    def votes(self):
        return [json.loads(v) for v in self.lists.get('votes', [])]


@pytest.fixture
def fake(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(vote_app, 'get_redis', lambda: fake)
    return fake


@pytest.fixture
def client():
    vote_app.app.config['TESTING'] = True
    return vote_app.app.test_client()


def voter_cookie(resp):
    cookie = resp.headers.get('Set-Cookie', '')
    match = re.match(r'voter_id=([^;]*)', cookie)
    assert match, cookie
    return match.group(1)


def button(html, which):
    match = re.search(r'<button id="%s"[^>]*>.*?</button>' % which, html, re.S)
    assert match, html
    return match.group(0)


def test_get_sets_voter_id_and_pushes_nothing(client, fake):
    resp = client.get('/')
    assert resp.status_code == 200
    assert re.fullmatch(r'[0-9a-f]{1,15}', voter_cookie(resp))
    assert fake.votes() == []
    html = resp.get_data(as_text=True)
    assert 'Cats' in html and 'Dogs' in html
    assert 'disabled' not in button(html, 'a') and 'disabled' not in button(html, 'b')
    assert 'jquery' not in html.lower() and 'font-awesome' not in html


def test_get_keeps_returning_voter_id(client, fake):
    client.set_cookie('voter_id', '3f2a9c')
    resp = client.get('/')
    assert voter_cookie(resp) == '3f2a9c'
    assert fake.votes() == []


def test_post_pushes_one_entry_then_renders_choice_ticked(client, fake):
    client.set_cookie('voter_id', 'v1')
    resp = client.post('/', data={'vote': 'b'})
    assert resp.status_code == 200
    assert fake.votes() == [{'voter_id': 'v1', 'vote': 'b'}]
    assert voter_cookie(resp) == 'v1'
    html = resp.get_data(as_text=True)
    chosen, other = button(html, 'b'), button(html, 'a')
    assert 'disabled' in chosen and '&#10004;' in chosen
    assert 'faded' in other and 'disabled' not in other


def test_post_without_cookie_issues_id_used_in_entry(client, fake):
    resp = client.post('/', data={'vote': 'a'})
    assert resp.status_code == 200
    assert fake.votes() == [{'voter_id': voter_cookie(resp), 'vote': 'a'}]


def test_unoffered_choice_marks_neither_button(client, fake):
    client.set_cookie('voter_id', 'v2')
    resp = client.post('/', data={'vote': 'c'})
    assert resp.status_code == 200
    assert fake.votes() == [{'voter_id': 'v2', 'vote': 'c'}]
    html = resp.get_data(as_text=True)
    for which in ('a', 'b'):
        assert 'disabled' not in button(html, which)
        assert 'faded' not in button(html, which)


def test_failing_push_returns_503_with_no_choice_marked(client, fake):
    fake.fail = True
    client.set_cookie('voter_id', 'v5')
    resp = client.post('/', data={'vote': 'a'})
    assert resp.status_code == 503
    assert fake.votes() == []
    assert voter_cookie(resp) == 'v5'
    html = resp.get_data(as_text=True)
    assert 'Your vote could not be taken right now. Please try again.' in html
    for which in ('a', 'b'):
        assert 'disabled' not in button(html, which)
        assert '&#10004;' not in button(html, which)


def test_missing_vote_returns_400_and_pushes_nothing(client, fake):
    client.set_cookie('voter_id', 'v1')
    resp = client.post('/', data={})
    assert resp.status_code == 400
    assert fake.votes() == []


@pytest.mark.parametrize('cookie, form', [
    ('v3', {'vote': 'x' * 256}),
    ('v' * 256, {'vote': 'a'}),
])
def test_overlong_vote_or_voter_id_returns_400(client, fake, cookie, form):
    client.set_cookie('voter_id', cookie)
    resp = client.post('/', data=form)
    assert resp.status_code == 400
    assert fake.votes() == []
