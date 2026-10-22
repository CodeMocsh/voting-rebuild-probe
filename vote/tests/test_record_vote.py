import json

import pytest

import app as vote_app
from recording import RedisVotesQueue


class FakeQueue:
    def __init__(self):
        self.pushed = []

    def push(self, payload):
        self.pushed.append(payload)


@pytest.fixture
def queue(monkeypatch):
    q = FakeQueue()
    monkeypatch.setattr(vote_app, "get_queue", lambda: q)
    return q


@pytest.fixture
def client():
    return vote_app.app.test_client()


def test_push_payload_and_cookie(client, queue):
    r = client.post("/", data={"vote": "a"})
    assert r.status_code == 200
    assert len(queue.pushed) == 1 and set(queue.pushed[0]) == {"voter_id", "vote"}
    assert queue.pushed[0]["vote"] == "a"
    assert f"voter_id={queue.pushed[0]['voter_id']}" in r.headers["Set-Cookie"]


def test_two_posts_same_voter(client, queue):
    client.post("/", data={"vote": "a"})
    client.post("/", data={"vote": "b"})
    assert queue.pushed[0]["voter_id"] == queue.pushed[1]["voter_id"]
    assert queue.pushed[1]["vote"] == "b"


def test_ballot_marks_choice(client, queue):
    assert 'var vote = "b";' in client.post("/", data={"vote": "b"}).get_data(as_text=True)
    assert "var vote" not in client.get("/").get_data(as_text=True)


@pytest.mark.parametrize("data", [{}, {"vote": ""}, {"vote": "c"}])
def test_bad_choice(client, queue, data):
    assert client.post("/", data=data).status_code == 400
    assert queue.pushed == []


def test_redis_queue_payload():
    calls = []

    class R:
        def rpush(self, k, v):
            calls.append((k, v))

    RedisVotesQueue(R()).push({"voter_id": "x", "vote": "a"})
    assert calls[0][0] == "votes" and json.loads(calls[0][1]) == {"voter_id": "x", "vote": "a"}
