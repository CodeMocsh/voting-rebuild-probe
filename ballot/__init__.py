"""The vote-casting ballot: a WSGI app that writes each vote to a SQLite tally."""

from .app import BallotApp, create_app

__all__ = ["BallotApp", "create_app"]
