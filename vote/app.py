"""The voting page: serves the ballot only."""

import os
import socket
from collections.abc import Mapping

from flask import Flask, render_template, request

from vote.ballot import Ballot


def create_app(environ: Mapping[str, str] = os.environ) -> Flask:
    app = Flask(__name__)
    ballot = Ballot(environ, socket.gethostname())

    @app.get("/")
    def index():
        view = ballot.view(request.cookies.get("voter_id"))
        response = app.make_response(render_template("index.html", ballot=view))
        response.set_cookie("voter_id", view.voter_number)
        return response

    return app
