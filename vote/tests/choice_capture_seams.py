from types import ModuleType
from typing import Any

from vote import ballot
from vote.ballot import Options, RefusedVote
from vote.votes_queue import MemoryVotesQueue

OPTIONS = Options(a="Cats", b="Dogs")


class ChoiceCapture:
    def __init__(self, host: ModuleType) -> None:
        self._host = host
        self._queue = MemoryVotesQueue()

    def reset(self) -> None:
        self._queue = MemoryVotesQueue()

    def seed(self, rows: dict[str, Any]) -> None:
        for row in rows.values():
            self._queue.push(row.voter, row.choice)

    def read(self) -> dict[str, Any]:
        return {
            one["voter_id"]: self._host.Vote(id=one["voter_id"], choice=one["vote"], voter=one["voter_id"])
            for one in self._queue.pending()
        }

    def show_ballot(self, given: Any) -> Any:
        return self._host.ShowBallotOut(page=ballot.show(OPTIONS, given.voter_id).page)

    def cast_vote(self, given: Any) -> Any:
        try:
            taken = ballot.take_vote(self._queue, OPTIONS, given.vote, given.voter_id)
        except RefusedVote as refused:
            return self._host.CastVoteOut(refusal=refused.line)
        return self._host.CastVoteOut(page=taken.page, queued=taken.queued)


def seams(host: ModuleType) -> Any:
    capture = ChoiceCapture(host)
    return host.Seams(
        reset=capture.reset,
        vote_store=capture,
        show_ballot=capture.show_ballot,
        cast_vote=capture.cast_vote,
    )
