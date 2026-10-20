from flask import Flask, Response, make_response, request

from vote import ballot
from vote.ballot import Ballot, Options, RefusedVote
from vote.votes_queue import VotesQueue

COOKIE = "voter_id"


def _answer(shown: Ballot) -> Response:
    response = make_response(shown.page)
    response.set_cookie(COOKIE, shown.voter_id)
    return response


def create_app(queue: VotesQueue, options: Options) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def show_ballot() -> Response:
        return _answer(ballot.show(options, request.cookies.get(COOKIE)))

    @app.post("/")
    def cast_vote() -> Response:
        value = request.form["vote"]
        try:
            taken = ballot.take_vote(queue, options, value, request.cookies.get(COOKIE))
        except RefusedVote as refused:
            return make_response(refused.page, 400)
        app.logger.info("Received vote for %s", value)
        return _answer(taken)

    return app
