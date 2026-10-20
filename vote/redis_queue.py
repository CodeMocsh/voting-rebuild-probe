from redis import Redis

from vote.settings import RedisSettings
from vote.votes_queue import entry

SOCKET_TIMEOUT = 5


class RedisVotesQueue:
    def __init__(self, settings: RedisSettings) -> None:
        self._client = Redis(
            host=settings.host,
            port=settings.port,
            password=settings.password,
            ssl=settings.tls,
            socket_timeout=SOCKET_TIMEOUT,
        )

    def push(self, voter_id: str, vote: str) -> None:
        self._client.rpush("votes", entry(voter_id, vote))
