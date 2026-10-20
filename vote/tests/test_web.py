import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from vote import redis_queue
from vote.ballot import Options
from vote.redis_queue import RedisVotesQueue
from vote.settings import RedisSettings
from vote.votes_queue import MemoryVotesQueue
from vote.web import create_app

OPTIONS = Options(a="Cats", b="Dogs")
REFUSAL = "That vote was not taken. Choose Cats or Dogs."


class RecordedRedis:
    made: list[dict] = []
    pushed: list[tuple[str, str]] = []
    failure: Exception | None = None

    def __init__(self, **given):
        RecordedRedis.made.append(given)

    def rpush(self, name, data):
        if RecordedRedis.failure is not None:
            raise RecordedRedis.failure
        RecordedRedis.pushed.append((name, data))


@pytest.fixture
def recorded(monkeypatch):
    monkeypatch.setattr(redis_queue, "Redis", RecordedRedis)
    monkeypatch.setattr(RecordedRedis, "made", [])
    monkeypatch.setattr(RecordedRedis, "pushed", [])
    monkeypatch.setattr(RecordedRedis, "failure", None)
    return RecordedRedis


@pytest.fixture
def redis_client(recorded):
    settings = RedisSettings(host="redis.example", port=6380, password="secret", tls=True)
    return create_app(RedisVotesQueue(settings), OPTIONS).test_client()


@pytest.fixture
def queue():
    return MemoryVotesQueue()


@pytest.fixture
def client(queue):
    return create_app(queue, OPTIONS).test_client()


def test_cast_pushes_json_onto_votes_over_a_tls_client(redis_client, recorded):
    redis_client.set_cookie("voter_id", "v1")
    response = redis_client.post("/", data={"vote": "a"})
    assert recorded.made == [
        {"host": "redis.example", "port": 6380, "password": "secret", "ssl": True, "socket_timeout": 5}
    ]
    assert recorded.pushed == [("votes", '{"voter_id": "v1", "vote": "a"}')]
    assert response.status_code == 200
    assert 'var vote = "a";' in response.get_data(as_text=True)
    assert redis_client.get_cookie("voter_id").value == "v1"


def test_cast_by_a_new_voter_queues_under_the_issued_cookie(client, queue):
    response = client.post("/", data={"vote": "b"})
    issued = client.get_cookie("voter_id").value
    assert response.status_code == 200
    assert 'var vote = "b";' in response.get_data(as_text=True)
    assert queue.pending() == [{"voter_id": issued, "vote": "b"}]


@pytest.mark.parametrize("value", ["", "c"])
def test_refusal_of_a_vote_other_than_a_or_b_answers_400(client, queue, value):
    response = client.post("/", data={"vote": value})
    page = response.get_data(as_text=True)
    assert response.status_code == 400
    assert f'<div id="refusal">{REFUSAL}</div>' in page
    assert "var vote" not in page
    assert queue.pending() == []


def test_refusal_of_a_voter_id_over_255_characters_answers_400(client, queue):
    client.set_cookie("voter_id", "v" * 300)
    response = client.post("/", data={"vote": "a"})
    assert response.status_code == 400
    assert f'<div id="refusal">{REFUSAL}</div>' in response.get_data(as_text=True)
    assert queue.pending() == []


def test_missing_field_answers_400_and_queues_nothing(client, queue):
    response = client.post("/", data={})
    assert response.status_code == 400
    assert "var vote" not in response.get_data(as_text=True)
    assert queue.pending() == []


def test_unavailable_queue_answers_500_without_a_tick(redis_client, recorded):
    recorded.failure = RedisConnectionError("Redis is not reachable")
    response = redis_client.post("/", data={"vote": "a"})
    assert response.status_code == 500
    assert "var vote" not in response.get_data(as_text=True)
    assert recorded.pushed == []


def test_ballot_route_gives_a_new_visitor_the_ballot_and_a_new_cookie(client, queue):
    response = client.get("/")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "<h3>Cats vs Dogs!</h3>" in page
    assert "var vote" not in page
    assert client.get_cookie("voter_id").value
    assert queue.pending() == []


def test_ballot_route_keeps_the_cookie_of_a_returning_voter(client):
    client.set_cookie("voter_id", "v1")
    client.get("/")
    assert client.get_cookie("voter_id").value == "v1"


def test_ballot_route_serves_the_stylesheet(client):
    response = client.get("/static/stylesheets/style.css")
    assert response.status_code == 200
    assert "#refusal" in response.get_data(as_text=True)
