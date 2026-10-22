import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.update(
    REDIS_HOST="h", REDIS_PORT="6379", REDIS_USERNAME="u", REDIS_PASSWORD="p", REDIS_TLS="false"
)
