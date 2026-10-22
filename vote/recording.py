"""The rules of recording a vote; the Flask route only calls this."""

import json
import logging
import random
from dataclasses import dataclass
from typing import Protocol

from redis import Redis

CHOICES = ("a", "b")
QUEUE_KEY = "votes"
log = logging.getLogger("vote.recording")


class BadChoice(Exception):
    """The submitted option is missing or is not a or b."""


@dataclass(frozen=True)
class RecordedVote:
    voter_id: str
    vote: str


class VotesQueue(Protocol):
    def push(self, payload: dict[str, str]) -> None: ...


class RedisVotesQueue:
    def __init__(self, client: Redis) -> None:
        self._client = client

    def push(self, payload: dict[str, str]) -> None:
        self._client.rpush(QUEUE_KEY, json.dumps(payload))


def validate_choice(vote: str | None) -> str:
    if vote not in CHOICES:
        raise BadChoice(f"vote must be one of {CHOICES}, not {vote!r}")
    return vote


def new_voter_number() -> str:
    return hex(random.getrandbits(64))[2:-1]


def record_vote(voter_id: str | None, vote: str | None, queue: VotesQueue) -> RecordedVote:
    choice = validate_choice(vote)
    voter = voter_id or new_voter_number()
    log.info("Received vote for %s", choice)
    queue.push({"voter_id": voter, "vote": choice})
    return RecordedVote(voter, choice)
