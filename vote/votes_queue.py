import json
from typing import Protocol


def entry(voter_id: str, vote: str) -> str:
    return json.dumps({"voter_id": voter_id, "vote": vote})


class VotesQueue(Protocol):
    def push(self, voter_id: str, vote: str) -> None: ...


class MemoryVotesQueue:
    def __init__(self) -> None:
        self._entries: list[str] = []

    def push(self, voter_id: str, vote: str) -> None:
        self._entries.append(entry(voter_id, vote))

    def pending(self) -> list[dict[str, str]]:
        return [json.loads(one) for one in self._entries]
