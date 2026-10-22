import subprocess
import sys
from pathlib import Path

from vote.ballot import Ballot


def test_defaults_and_names():
    view = Ballot({}, "host-1").view("x")
    assert (view.option_a, view.option_b, view.codes, view.hostname) == (
        "Cats", "Dogs", ("a", "b"), "host-1")
    view = Ballot({"OPTION_A": "Tea", "OPTION_B": "Coffee"}, "h").view("x")
    assert (view.option_a, view.option_b) == ("Tea", "Coffee")


def test_sent_number_kept():
    assert Ballot({}, "h").view("abc123").voter_number == "abc123"


def test_new_number_non_empty_even_for_small_draw():
    for draw, expected in ((5, "5"), (0, "0"), (255, "ff")):
        assert Ballot({}, "h", lambda _bits, d=draw: d).view(None).voter_number == expected
    assert Ballot({}, "h", lambda _bits: 7).view("").voter_number == "7"


def test_options_read_once():
    environ = {"OPTION_A": "Tea"}
    ballot = Ballot(environ, "h")
    environ["OPTION_A"] = "Changed"
    assert ballot.view(None).option_a == "Tea"


def test_no_redis_import():
    code = "import sys, vote.ballot; sys.exit('redis' in sys.modules)"
    assert subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parents[2]).returncode == 0
