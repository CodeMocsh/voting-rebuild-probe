import logging
import os

from vote.ballot import Options
from vote.redis_queue import RedisVotesQueue
from vote.settings import RedisSettings
from vote.web import create_app

app = create_app(
    RedisVotesQueue(RedisSettings.from_env(os.environ)),
    Options(a=os.environ.get("OPTION_A", "Cats"), b=os.environ.get("OPTION_B", "Dogs")),
)
app.logger.handlers.extend(logging.getLogger("gunicorn.error").handlers)
app.logger.setLevel(logging.INFO)
