import pytest
from redis.exceptions import TimeoutError as RedisTimeout

import app as vote_app
from recording import record_vote


class DownQueue:
    def push(self, payload):
        raise RedisTimeout("down")


def test_propagates():
    with pytest.raises(RedisTimeout):
        record_vote("v", "a", DownQueue())


def test_route_500(monkeypatch):
    monkeypatch.setattr(vote_app, "get_queue", lambda: DownQueue())
    c = vote_app.app.test_client()
    assert c.post("/", data={"vote": "a"}).status_code == 500
