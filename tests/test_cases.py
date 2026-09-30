"""Run the specification's vote-casting cases against the ballot.

Every case in records/cases.jsonl whose steps are all show-ballot or cast-vote
becomes one test, named by the last segment of its id. Each step is played
against the WSGI app in process and its expect is evaluated with CEL over
Vote (the tally after the step) and out (what the response carried).
"""

import io
import json
import os
import sqlite3
import sys
from http import cookies
from urllib.parse import urlencode

import pytest
from cel_expr_python import cel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ballot.app import create_app  # noqa: E402
from ballot.store import CREATE_TABLE  # noqa: E402

RECORDS = os.path.join(ROOT, "records")
ACTION = "urn:estate:voting-app:action:"
BALLOT_ACTIONS = {ACTION + "show-ballot": "GET", ACTION + "cast-vote": "POST"}

# How each fault named in the records is caused. Both point the tally at a path
# that cannot be opened, so the ballot cannot write the vote.
UNOPENABLE = os.path.join(os.devnull, "unreachable", "votes.db")
FAULTS = {
    "ballots cannot be taken in": UNOPENABLE,
    "the tally of votes is unreachable": UNOPENABLE,
}


def _load(name):
    with open(os.path.join(RECORDS, name), encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _ballot_cases():
    steps = {}
    for step in _load("case_steps.jsonl"):
        steps.setdefault(step["case"], []).append(step)
    chosen = []
    for case in _load("cases.jsonl"):
        own = sorted(steps.get(case["id"], []), key=lambda s: s["order"])
        if own and all(s["action"] in BALLOT_ACTIONS for s in own):
            chosen.append(pytest.param(case, own, id=case["id"].rsplit(":", 1)[-1]))
    return chosen


CASES = _ballot_cases()
ENV = cel.NewEnv(variables={"Vote": cel.Type.MAP, "out": cel.Type.MAP})


def _seed(path, votes):
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    with conn:
        conn.execute(CREATE_TABLE)
        conn.executemany(
            "INSERT INTO votes (id, vote) VALUES (?, ?)",
            [(v["id"], v["choice"]) for v in votes.values()],
        )
    conn.close()


def _tally(path):
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT id, vote FROM votes").fetchall()
    finally:
        conn.close()
    return {voter_id: {"id": voter_id, "choice": choice} for voter_id, choice in rows}


def _call(app, method, inputs):
    form = {"vote": inputs["choice"]} if "choice" in inputs else {}
    body = urlencode(form).encode("utf-8") if method == "POST" else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": "/",
        "SERVER_NAME": "ballot",
        "SERVER_PORT": "80",
        "wsgi.input": io.BytesIO(body),
        "wsgi.url_scheme": "http",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/x-www-form-urlencoded",
    }
    if "voter_id" in inputs:
        environ["HTTP_COOKIE"] = "voter_id=" + inputs["voter_id"]
    seen = {}

    def start_response(status, headers, exc_info=None):
        seen["status"] = int(status.split()[0])
        seen["headers"] = headers

    text = b"".join(app(environ, start_response)).decode("utf-8")
    return seen["status"], seen["headers"], text


def _out(status, headers, text):
    out = {}
    if status == 200:
        out["page"] = text
    elif status == 400:
        out["refusal"] = text
    elif status == 503:
        out["unavailable"] = text
    for name, value in headers:
        if name.lower() == "set-cookie":
            jar = cookies.SimpleCookie()
            jar.load(value)
            if "voter_id" in jar:
                out["voter_id"] = jar["voter_id"].value
    return out


@pytest.mark.parametrize("case, steps", CASES)
def test_case(case, steps, tmp_path):
    tally = str(tmp_path / "votes.db")
    options = {}
    for step in steps:
        given = json.loads(step.get("given") or "null")
        if given is not None:
            _seed(tally, given.get("Vote", {}))
            labels = given.get("Option", {})
            options = {
                "option_a": labels.get("a", {}).get("label"),
                "option_b": labels.get("b", {}).get("label"),
            }
        fault = step.get("fault")
        db_path = FAULTS[fault] if fault else tally
        app = create_app(db_path=db_path, hostname="case-runner", **options)
        inputs = json.loads(step.get("input") or "{}")
        status, headers, text = _call(app, BALLOT_ACTIONS[step["action"]], inputs)
        data = {"Vote": _tally(tally), "out": _out(status, headers, text)}
        result = ENV.compile(step["expect"]).eval(data=data).value()
        assert result is True, "%s: %s gave status %d; expect %s was %r" % (
            step["id"], step.get("note", ""), status, step["expect"], result)


def test_every_ballot_case_is_run():
    assert len(CASES) == 11
