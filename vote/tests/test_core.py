"""The voter id rule and the refusals of the ballot core."""
import json
import os
import random
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ballot  # noqa: E402


class ListQueue:
    def __init__(self):
        self.pushed = []

    def rpush(self, key, value):
        self.pushed.append((key, value))
        return len(self.pushed)


def test_supplied_voter_id_is_kept():
    assert ballot.issue_voter_id('3f2a9c') == '3f2a9c'


@pytest.mark.parametrize('supplied', [None, ''])
def test_missing_or_empty_voter_id_is_replaced(supplied):
    random.seed(7)
    for _ in range(200):
        voter_id = ballot.issue_voter_id(supplied)
        assert re.fullmatch(r'[0-9a-f]{1,15}', voter_id), voter_id


def test_new_voter_id_drops_the_last_hex_digit(monkeypatch):
    monkeypatch.setattr(ballot.random, 'getrandbits', lambda bits: 0xfedcba9876543210)
    assert ballot.issue_voter_id(None) == 'fedcba987654321'


def test_cast_pushes_one_entry_onto_votes():
    queue = ListQueue()
    assert ballot.cast(queue, 'v1', {'vote': 'a'}) == 'a'
    assert len(queue.pushed) == 1
    key, value = queue.pushed[0]
    assert key == 'votes'
    assert json.loads(value) == {'voter_id': 'v1', 'vote': 'a'}


@pytest.mark.parametrize('vote', ['', 'c'])
def test_empty_or_unoffered_vote_is_accepted(vote):
    queue = ListQueue()
    assert ballot.cast(queue, 'v2', {'vote': vote}) == vote
    assert json.loads(queue.pushed[0][1]) == {'voter_id': 'v2', 'vote': vote}


def test_cast_without_vote_field_pushes_nothing():
    queue = ListQueue()
    with pytest.raises(ballot.BadVote):
        ballot.cast(queue, 'v1', {})
    assert queue.pushed == []


def test_vote_over_255_characters_pushes_nothing():
    queue = ListQueue()
    with pytest.raises(ballot.BadVote):
        ballot.cast(queue, 'v3', {'vote': 'x' * 256})
    assert queue.pushed == []


def test_vote_of_255_characters_is_accepted():
    queue = ListQueue()
    ballot.cast(queue, 'v3', {'vote': 'x' * 255})
    assert len(queue.pushed) == 1


def test_voter_id_over_255_characters_pushes_nothing():
    queue = ListQueue()
    with pytest.raises(ballot.BadVote):
        ballot.cast(queue, 'v' * 256, {'vote': 'a'})
    assert queue.pushed == []


def test_later_votes_still_recorded_after_a_refusal():
    queue = ListQueue()
    with pytest.raises(ballot.BadVote):
        ballot.cast(queue, 'v3', {'vote': 'x' * 300})
    ballot.cast(queue, 'v6', {'vote': 'a'})
    assert [json.loads(v) for _, v in queue.pushed] == [{'voter_id': 'v6', 'vote': 'a'}]
