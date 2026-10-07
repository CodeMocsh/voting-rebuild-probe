"""The worked examples, run against the core with a list standing in for Redis."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ballot  # noqa: E402


class ListQueue:
    """An in-memory stand-in for the Redis list the votes are pushed onto."""

    def __init__(self):
        self.lists = {}

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])

    def entries(self, key='votes'):
        return self.lists.get(key, [])


def drain(queue, votes):
    """Apply the worker's contract: pop each entry and upsert it by voter_id."""
    pending = queue.lists.get('votes', [])
    while pending:
        entry = json.loads(pending.pop(0))
        votes[entry['voter_id']] = {'id': entry['voter_id'], 'choice': entry['vote']}
    return votes


def tally(votes):
    """Count the drained votes the way the standing does."""
    scores = {'a': 0, 'b': 0}
    for vote in votes.values():
        scores[vote['choice']] = scores.get(vote['choice'], 0) + 1
    total = scores['a'] + scores['b']
    a_percent = 50 if total == 0 else int(scores['a'] * 100 / total + 0.5)
    return {'scores': scores, 'a_percent': a_percent, 'b_percent': 100 - a_percent}


def test_first_vote_recorded():
    queue, votes = ListQueue(), {}
    voter_id = ballot.issue_voter_id('v1')
    choice = ballot.cast(queue, voter_id, {'vote': 'b'})
    assert choice == 'b'
    assert voter_id == 'v1'
    assert [json.loads(e) for e in queue.entries()] == [{'voter_id': 'v1', 'vote': 'b'}]
    drain(queue, votes)
    assert votes == {'v1': {'id': 'v1', 'choice': 'b'}}


def test_later_vote_replaces_earlier():
    queue = ListQueue()
    votes = {'v1': {'id': 'v1', 'choice': 'a'}}
    ballot.cast(queue, ballot.issue_voter_id('v1'), {'vote': 'b'})
    drain(queue, votes)
    assert len(votes) == 1
    assert votes['v1']['choice'] == 'b'


def test_new_visitor_sees_ballot():
    queue = ListQueue()
    voter_id = ballot.issue_voter_id(None)
    assert voter_id != ''
    assert ballot.options({}) == ('Cats', 'Dogs')
    assert queue.entries() == []
    assert drain(queue, {}) == {}


def test_changes_choice_tally_follows():
    queue, votes = ListQueue(), {}
    voter_id = ballot.issue_voter_id('j1')
    assert voter_id == 'j1'

    ballot.cast(queue, voter_id, {'vote': 'a'})
    drain(queue, votes)
    assert votes['j1']['choice'] == 'a'
    standing = tally(votes)
    assert standing['scores'] == {'a': 1, 'b': 0}
    assert standing['a_percent'] == 100

    ballot.cast(queue, voter_id, {'vote': 'b'})
    drain(queue, votes)
    assert len(votes) == 1
    assert votes['j1']['choice'] == 'b'
    standing = tally(votes)
    assert standing['scores'] == {'a': 0, 'b': 1}
    assert standing['b_percent'] == 100
