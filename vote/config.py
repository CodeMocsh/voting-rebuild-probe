"""Redis settings, read from the environment so the app does not start without them."""

from collections.abc import Mapping
from dataclasses import dataclass


class MissingSetting(Exception):
    """A required environment variable is absent."""


class InvalidSetting(Exception):
    """An environment variable holds a value that is not allowed."""


@dataclass(frozen=True)
class RedisSettings:
    host: str
    port: int
    username: str
    password: str
    tls: bool


def _required(environ: Mapping[str, str], name: str) -> str:
    if name not in environ:
        raise MissingSetting(name)
    return environ[name]


def load_redis_settings(environ: Mapping[str, str]) -> RedisSettings:
    host = _required(environ, "REDIS_HOST")
    port_text = _required(environ, "REDIS_PORT")
    username = _required(environ, "REDIS_USERNAME")
    password = _required(environ, "REDIS_PASSWORD")
    tls_text = _required(environ, "REDIS_TLS")
    if tls_text not in ("true", "false"):
        raise InvalidSetting(f"REDIS_TLS must be 'true' or 'false', not {tls_text!r}")
    try:
        port = int(port_text)
    except ValueError:
        raise InvalidSetting(f"REDIS_PORT must be an integer, not {port_text!r}") from None
    return RedisSettings(host, port, username, password, tls_text == "true")
