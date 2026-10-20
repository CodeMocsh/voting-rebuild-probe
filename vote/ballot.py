import socket
from dataclasses import dataclass
from random import getrandbits

from vote import page
from vote.votes_queue import VotesQueue

CHOICES = ("a", "b")
LONGEST_VOTER_ID = 255


@dataclass(frozen=True)
class Options:
    a: str
    b: str


@dataclass(frozen=True)
class Ballot:
    page: str
    voter_id: str
    queued: dict[str, str] | None


class RefusedVote(Exception):
    def __init__(self, page: str, line: str) -> None:
        super().__init__(line)
        self.page = page
        self.line = line


def refusal_line(options: Options) -> str:
    return f"That vote was not taken. Choose {options.a} or {options.b}."


def voter_id(cookie: str | None) -> str:
    return cookie if cookie else hex(getrandbits(64))[2:-1]


def show(options: Options, cookie: str | None) -> Ballot:
    return Ballot(page.render(options, None, None, socket.gethostname()), voter_id(cookie), None)


def take_vote(queue: VotesQueue, options: Options, value: str, cookie: str | None) -> Ballot:
    voter = voter_id(cookie)
    if value not in CHOICES or len(voter) > LONGEST_VOTER_ID:
        line = refusal_line(options)
        raise RefusedVote(page.render(options, None, line, socket.gethostname()), line)
    queue.push(voter, value)
    return Ballot(
        page.render(options, value, None, socket.gethostname()),
        voter,
        {"voter_id": voter, "vote": value},
    )
