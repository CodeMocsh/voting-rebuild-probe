import logging
import os
import socket

from flask import Flask, abort, g, make_response, render_template, request
from redis import Redis, RedisError

from ballot import BadVote, cast, issue_voter_id, options

option_a, option_b = options(os.environ)
hostname = socket.gethostname()

app = Flask(__name__)

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.INFO)


def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host='redis', db=0, socket_timeout=5)
    return g.redis


def page(voter_id, vote=None, unavailable=False, status=200):
    resp = make_response(render_template(
        'index.html',
        option_a=option_a,
        option_b=option_b,
        hostname=hostname,
        vote=vote,
        unavailable=unavailable,
    ), status)
    resp.set_cookie('voter_id', voter_id)
    return resp


@app.route('/', methods=['POST', 'GET'])
def hello():
    voter_id = issue_voter_id(request.cookies.get('voter_id'))

    if request.method == 'GET':
        return page(voter_id)

    app.logger.info('Received vote for %s', request.form.get('vote'))
    try:
        vote = cast(get_redis(), voter_id, request.form)
    except BadVote:
        abort(400)
    except RedisError:
        app.logger.exception('The vote could not be pushed to the votes list')
        return page(voter_id, unavailable=True, status=503)
    return page(voter_id, vote=vote)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
