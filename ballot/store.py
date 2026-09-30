"""The tally: one row per voter in a SQLite votes table.

The columns match the table the original worker creates (id VARCHAR(255) PRIMARY
KEY, vote VARCHAR(255) NOT NULL), so standing reporting can count with
GROUP BY vote over the same file.
"""

import os
import sqlite3

DEFAULT_PATH = os.path.join("data", "votes.db")
MAX_LENGTH = 255
BUSY_TIMEOUT_SECONDS = 5.0

CREATE_TABLE = (
    "CREATE TABLE IF NOT EXISTS votes ("
    "id VARCHAR(255) NOT NULL UNIQUE PRIMARY KEY, "
    "vote VARCHAR(255) NOT NULL)"
)

UPSERT = (
    "INSERT INTO votes (id, vote) VALUES (?, ?) "
    "ON CONFLICT(id) DO UPDATE SET vote = excluded.vote"
)


class TallyUnavailable(Exception):
    """The tally could not be opened or written; nothing was recorded."""


def default_path():
    return os.environ.get("VOTES_DB") or DEFAULT_PATH


class Store:
    def __init__(self, path=None):
        self.path = path or default_path()

    def _connect(self):
        directory = os.path.dirname(self.path)
        if directory and not os.path.isdir(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except OSError as exc:
                raise TallyUnavailable(str(exc)) from exc
        try:
            conn = sqlite3.connect(self.path, timeout=BUSY_TIMEOUT_SECONDS)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=%d" % int(BUSY_TIMEOUT_SECONDS * 1000))
            conn.execute(CREATE_TABLE)
            conn.commit()
        except sqlite3.Error as exc:
            raise TallyUnavailable(str(exc)) from exc
        return conn

    def record(self, voter_id, choice):
        """Upsert the voter's choice and commit before returning."""
        conn = self._connect()
        try:
            with conn:
                conn.execute(UPSERT, (voter_id, choice))
        except sqlite3.Error as exc:
            raise TallyUnavailable(str(exc)) from exc
        finally:
            conn.close()

    def votes(self):
        """Every recorded vote as {voter_id: choice}."""
        conn = self._connect()
        try:
            rows = conn.execute("SELECT id, vote FROM votes").fetchall()
        except sqlite3.Error as exc:
            raise TallyUnavailable(str(exc)) from exc
        finally:
            conn.close()
        return {voter_id: choice for voter_id, choice in rows}
