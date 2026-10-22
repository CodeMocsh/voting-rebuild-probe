"""In-memory seams the host replays through."""

import logging
import sys
from contextlib import contextmanager
from pathlib import Path

from redis.exceptions import TimeoutError as RedisTimeout

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "specification" / "vote_casting_vote_recording"))

import recording  # noqa: E402
from seams import Option, OptionStore, RecordVoteInput, RecordVoteOut, Seams, Unavailable, Vote, VoteStore  # noqa: E402,F401


class MemoryStore:
    def __init__(self):
        self.rows = {}

    def seed(self, rows):
        self.rows.update(rows)

    def read(self):
        return dict(self.rows)


class MemoryQueue:
    def __init__(self, store, down):
        self.store, self.down = store, down

    def push(self, payload):
        if self.down["on"]:
            raise RedisTimeout("Timeout reading from socket")
        # the recorder: upsert by voter number, in cast order
        voter, choice = payload["voter_id"], payload["vote"]
        for key, row in self.store.rows.items():
            if row.voter_id == voter:
                self.store.rows[key] = Vote(key, voter, choice)
                return
        key = f"v{len(self.store.rows) + 1}"
        while key in self.store.rows:
            key += "_"
        self.store.rows[key] = Vote(key, voter, choice)


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


def build_seams() -> Seams:
    votes, options, down = MemoryStore(), MemoryStore(), {"on": False}
    queue = MemoryQueue(votes, down)

    def reset():
        votes.rows.clear()
        options.rows.clear()
        down["on"] = False

    def record_vote(given: RecordVoteInput) -> RecordVoteOut:
        capture = _Capture()
        recording.log.addHandler(capture)
        recording.log.setLevel(logging.INFO)
        try:
            recorded = recording.record_vote(given.voter_id, given.vote, queue)
        except recording.BadChoice as bad:
            if given.vote is None:
                return RecordVoteOut(missing_choice=str(bad))
            return RecordVoteOut(unknown_choice=str(bad))
        finally:
            recording.log.removeHandler(capture)
        return RecordVoteOut(
            received_log=capture.lines[0] if capture.lines else None,
            processing_log=f"Processing vote for '{recorded.vote}' by '{recorded.voter_id}'",
            ballot={"marked": recorded.vote},
            voter_cookie=recorded.voter_id,
        )

    @contextmanager
    def unreachable():
        down["on"] = True
        try:
            yield
        finally:
            down["on"] = False

    return Seams(reset, votes, options, record_vote, Unavailable(unreachable))
