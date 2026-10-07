"""Every voting rule of the ballot, with no dependency beyond the standard library.

The queue is anything with rpush(key, value): a redis.Redis in the service, a list
stand-in in the tests.
"""
import json
import random

QUEUE_KEY = 'votes'
MAX_LENGTH = 255
DEFAULT_OPTION_A = 'Cats'
DEFAULT_OPTION_B = 'Dogs'


class BadVote(ValueError):
    """A cast that is refused before anything is pushed."""


def options(environ):
    """The two labels on the ballot, read from OPTION_A and OPTION_B."""
    return (environ.get('OPTION_A', DEFAULT_OPTION_A),
            environ.get('OPTION_B', DEFAULT_OPTION_B))


def issue_voter_id(supplied):
    """Keep a non-empty id; otherwise hand out a new one in the original's format."""
    if supplied:
        return supplied
    return hex(random.getrandbits(64))[2:-1]


def cast(queue, voter_id, form):
    """Push one vote onto the votes list and return the choice.

    Refuses with BadVote, pushing nothing, when the form carries no vote field or the
    vote or voter_id is longer than the 255 characters the worker's table holds. An
    empty vote is accepted, as the original accepts it.
    """
    if 'vote' not in form:
        raise BadVote('the form carries no vote')
    vote = form['vote']
    if len(vote) > MAX_LENGTH:
        raise BadVote('the vote is longer than %d characters' % MAX_LENGTH)
    if len(voter_id) > MAX_LENGTH:
        raise BadVote('the voter id is longer than %d characters' % MAX_LENGTH)
    queue.rpush(QUEUE_KEY, json.dumps({'voter_id': voter_id, 'vote': vote}))
    return vote
