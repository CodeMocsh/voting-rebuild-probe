import json
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from seams import (
    Option,
    OptionStore,
    Unavailable,
    Vote,
    VoteStore,
    ViewResultInput,
    ViewResultOut,
)

REPLAY_SCRIPT = Path(__file__).resolve().parents[2] / "result" / "replay" / "replay.js"
OUT_FIELDS = ("greeting", "scores", "a_percent", "b_percent", "total", "query_error_log")


class MemoryVoteStore(VoteStore):
    def __init__(self) -> None:
        self.rows: dict[str, Vote] = {}

    def seed(self, rows: dict[str, Vote]) -> None:
        self.rows.update(rows)

    def read(self) -> dict[str, Vote]:
        return dict(self.rows)

    def reset(self) -> None:
        self.rows.clear()


class MemoryOptionStore(OptionStore):
    def __init__(self) -> None:
        self.rows: dict[str, Option] = {}

    def seed(self, rows: dict[str, Option]) -> None:
        self.rows.update(rows)

    def read(self) -> dict[str, Option]:
        return dict(self.rows)

    def reset(self) -> None:
        self.rows.clear()


class Outage:
    def __init__(self) -> None:
        self.unreachable = False

    @contextmanager
    def the_votes_are_unreachable(self) -> Iterator[None]:
        self.unreachable = True
        try:
            yield
        finally:
            self.unreachable = False


class ReplayedViewResult:
    def __init__(self, votes: MemoryVoteStore, outage: Outage) -> None:
        self.votes = votes
        self.outage = outage

    def __call__(self, given: ViewResultInput) -> ViewResultOut:
        payload = {
            "votes": [vote.option for vote in self.votes.rows.values()],
            "unreachable": self.outage.unreachable,
        }
        done = subprocess.run(
            ["node", str(REPLAY_SCRIPT)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=True,
        )
        sent = json.loads(done.stdout)
        return ViewResultOut(**{field: sent.get(field) for field in OUT_FIELDS})


def build() -> tuple[MemoryVoteStore, MemoryOptionStore, ReplayedViewResult, Unavailable]:
    votes = MemoryVoteStore()
    outage = Outage()
    return (
        votes,
        MemoryOptionStore(),
        ReplayedViewResult(votes, outage),
        Unavailable(the_votes_are_unreachable=outage.the_votes_are_unreachable),
    )
