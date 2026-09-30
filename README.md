# voting-rebuild-probe

A rebuild of [dockersamples/example-voting-app](https://github.com/dockersamples/example-voting-app), built from its specification: `metamodel.json` names the model and the records.

## The ballot

`ballot/` is the vote-casting capability: a WSGI app that serves `GET /` and `POST /` and writes each vote into a SQLite tally, committing before it answers.

Run it (needs Python 3 and Jinja2):

    python3 -m ballot

Settings come from the environment:

- `PORT`: the port to listen on, default `8080`.
- `VOTES_DB`: the tally file, default `data/votes.db`. It holds one `votes(id, vote)` row per voter.
- `OPTION_A` and `OPTION_B`: the two labels, default `Cats` and `Dogs`.

A post with no `vote`, or with a vote or `voter_id` cookie longer than 255 characters, gets `400 Bad Request`. A vote the tally cannot take gets `503 Service Unavailable`, and nothing is recorded.

Run the tests (needs pytest and cel-expr-python):

    python3 -m pytest -q tests

`tests/test_cases.py` runs every show-ballot and cast-vote case in `records/` against the app. `tests/test_ballot.py` covers a vote surviving a restart, the marked page and the log lines.
