"""Binds the ballot to the host's seams, with in-memory stores."""

from contextlib import contextmanager

from specification.vote_casting_ballot_presentation.seams import (
    Seams,
    Unavailable,
    ViewBallotInput,
    ViewBallotOut,
)
from vote.ballot import Ballot


class _Store:
    def __init__(self) -> None:
        self._rows: dict = {}

    def seed(self, rows: dict) -> None:
        self._rows.update(rows)

    def read(self) -> dict:
        return dict(self._rows)

    def clear(self) -> None:
        self._rows.clear()


class _ViewBallot:
    def __init__(self, options: _Store) -> None:
        self._options = options

    def __call__(self, given: ViewBallotInput) -> ViewBallotOut:
        names = {o.code: o.name for o in self._options.read().values()}
        environ = {"OPTION_A": names["a"], "OPTION_B": names["b"]}
        view = Ballot(environ, "ballot-host").view(given.voter_id)
        ballot = {
            "option_a": view.option_a,
            "option_b": view.option_b,
            "codes": {"a": view.codes[0], "b": view.codes[1]},
            "hostname": view.hostname,
        }
        return ViewBallotOut(ballot=ballot, voter_cookie=view.voter_number)


@contextmanager
def _never_read():
    yield


def seams() -> Seams:
    votes: _Store = _Store()
    options: _Store = _Store()

    def reset() -> None:
        votes.clear()
        options.clear()

    return Seams(
        reset=reset,
        vote_store=votes,
        option_store=options,
        view_ballot=_ViewBallot(options),
        unavailable=Unavailable(the_line_of_votes_is_unreachable=_never_read),
    )
