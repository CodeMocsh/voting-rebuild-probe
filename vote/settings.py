from collections.abc import Mapping
from dataclasses import dataclass

TLS_VALUES = {"true": True, "false": False}


class MissingSetting(RuntimeError):
    pass


def _required(environ: Mapping[str, str], name: str) -> str:
    if name not in environ:
        raise MissingSetting(f"{name} is not set")
    return environ[name]


@dataclass(frozen=True)
class RedisSettings:
    host: str
    port: int
    password: str
    tls: bool

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "RedisSettings":
        host = _required(environ, "REDIS_HOST")
        port = _required(environ, "REDIS_PORT")
        password = _required(environ, "REDIS_PASSWORD")
        tls = _required(environ, "REDIS_TLS")
        if not port.isdigit():
            raise MissingSetting(f"REDIS_PORT must be a port number, not {port!r}")
        if tls not in TLS_VALUES:
            raise MissingSetting(f"REDIS_TLS must be 'true' or 'false', not {tls!r}")
        return cls(host=host, port=int(port), password=password, tls=TLS_VALUES[tls])
