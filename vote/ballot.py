"""The ballot a voter is shown: option names, button codes, serving host and voter number."""

import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class BallotView:
    option_a: str
    option_b: str
    codes: tuple[str, str]
    hostname: str
    voter_number: str


class Ballot:
    def __init__(
        self,
        environ: Mapping[str, str],
        hostname: str,
        getrandbits: Callable[[int], int] = random.getrandbits,
    ) -> None:
        self._option_a = environ.get("OPTION_A", "Cats")
        self._option_b = environ.get("OPTION_B", "Dogs")
        self._hostname = hostname
        self._getrandbits = getrandbits

    def view(self, sent_voter_id: str | None) -> BallotView:
        return BallotView(
            self._option_a,
            self._option_b,
            ("a", "b"),
            self._hostname,
            self._voter_number(sent_voter_id),
        )

    def _voter_number(self, sent: str | None) -> str:
        return sent or format(self._getrandbits(64), "x")
