import logging
import os
import socket

from flask import Flask, g, make_response, render_template, request
from redis import Redis

from config import load_redis_settings
from recording import BadChoice, RedisVotesQueue, new_voter_number, record_vote

option_a = os.getenv("OPTION_A", "Cats")
option_b = os.getenv("OPTION_B", "Dogs")
hostname = socket.gethostname()
settings = load_redis_settings(os.environ)

app = Flask(__name__)

gunicorn_error_logger = logging.getLogger("gunicorn.error")
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)
logging.getLogger("vote.recording").handlers.extend(app.logger.handlers)
logging.getLogger("vote.recording").setLevel(logging.INFO)


def get_queue():
    if not hasattr(g, "queue"):
        g.queue = RedisVotesQueue(
            Redis(
                host=settings.host,
                port=settings.port,
                username=settings.username,
                password=settings.password,
                ssl=settings.tls,
                db=0,
                socket_timeout=5,
            )
        )
    return g.queue


@app.errorhandler(BadChoice)
def bad_choice(error):
    return str(error), 400


@app.route("/", methods=["POST", "GET"])
def hello():
    voter_id = request.cookies.get("voter_id")
    vote = None
    if request.method == "POST":
        recorded = record_vote(voter_id, request.form.get("vote"), get_queue())
        voter_id, vote = recorded.voter_id, recorded.vote
    elif not voter_id:
        voter_id = new_voter_number()

    resp = make_response(
        render_template(
            "index.html", option_a=option_a, option_b=option_b, hostname=hostname, vote=vote
        )
    )
    resp.set_cookie("voter_id", voter_id)
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)
