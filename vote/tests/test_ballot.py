import re

import pytest

from vote import ballot
from vote.ballot import Options, RefusedVote
from vote.votes_queue import MemoryVotesQueue

OPTIONS = Options(a="Cats", b="Dogs")
REFUSAL = "That vote was not taken. Choose Cats or Dogs."


@pytest.mark.parametrize("choice, ticked, faded", [("a", "Cats", "b"), ("b", "Dogs", "a")])
def test_cast_queues_the_choice_and_shows_it_back(choice, ticked, faded):
    queue = MemoryVotesQueue()
    taken = ballot.take_vote(queue, OPTIONS, choice, "v1")
    assert queue.pending() == [{"voter_id": "v1", "vote": choice}]
    assert taken.queued == {"voter_id": "v1", "vote": choice}
    assert taken.voter_id == "v1"
    assert f'var vote = "{choice}";' in taken.page
    assert f"$(\".{choice}\").prop('disabled', true);" in taken.page
    assert f'"{ticked} <i class=\\"fa fa-check-circle\\"></i>"' in taken.page
    assert f"$(\".{faded}\").css('opacity','0.5');" in taken.page
    assert 'id="refusal"' not in taken.page


@pytest.mark.parametrize("value", ["", "c", "A", "a "])
def test_refusal_of_a_vote_other_than_a_or_b_queues_nothing(value):
    queue = MemoryVotesQueue()
    with pytest.raises(RefusedVote) as refused:
        ballot.take_vote(queue, OPTIONS, value, "v1")
    assert queue.pending() == []
    assert refused.value.line == REFUSAL
    assert f'<div id="refusal">{REFUSAL}</div>' in refused.value.page
    assert "var vote" not in refused.value.page


def test_refusal_of_a_voter_id_over_255_characters_queues_nothing():
    queue = MemoryVotesQueue()
    with pytest.raises(RefusedVote):
        ballot.take_vote(queue, OPTIONS, "a", "v" * 300)
    with pytest.raises(RefusedVote):
        ballot.take_vote(queue, OPTIONS, "a", "v" * 256)
    assert queue.pending() == []


def test_cast_takes_a_voter_id_of_255_characters():
    queue = MemoryVotesQueue()
    ballot.take_vote(queue, OPTIONS, "a", "v" * 255)
    assert queue.pending() == [{"voter_id": "v" * 255, "vote": "a"}]


@pytest.mark.parametrize("cookie", [None, ""])
def test_cast_without_a_voter_id_queues_under_a_new_one(cookie):
    queue = MemoryVotesQueue()
    taken = ballot.take_vote(queue, OPTIONS, "b", cookie)
    assert re.fullmatch(r"[0-9a-f]+", taken.voter_id)
    assert queue.pending() == [{"voter_id": taken.voter_id, "vote": "b"}]


@pytest.mark.parametrize("cookie", [None, ""])
def test_show_issues_a_new_voter_id_on_a_first_visit(cookie):
    first = ballot.show(OPTIONS, cookie)
    second = ballot.show(OPTIONS, cookie)
    assert re.fullmatch(r"[0-9a-f]+", first.voter_id)
    assert first.voter_id != second.voter_id
    assert first.queued is None


def test_show_keeps_the_voter_id_of_a_returning_voter():
    assert ballot.show(OPTIONS, "v1").voter_id == "v1"


def test_show_gives_the_ballot_with_both_labels_and_no_tick():
    shown = ballot.show(OPTIONS, "v1")
    assert "<title>Cats vs Dogs!</title>" in shown.page
    assert '<button id="a" type="submit" name="vote" class="a" value="a">Cats</button>' in shown.page
    assert '<button id="b" type="submit" name="vote" class="b" value="b">Dogs</button>' in shown.page
    assert "(Tip: you can change your vote)" in shown.page
    assert "Processed by container ID" in shown.page
    assert "var vote" not in shown.page
    assert 'id="refusal"' not in shown.page


def test_show_escapes_the_option_labels():
    shown = ballot.show(Options(a="<b>Cats</b>", b="Dogs"), "v1")
    assert "&lt;b&gt;Cats&lt;/b&gt; vs Dogs!" in shown.page
    assert "<b>Cats</b>" not in shown.page
