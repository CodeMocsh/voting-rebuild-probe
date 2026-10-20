import importlib
import sys

import pytest

from vote.settings import MissingSetting, RedisSettings

ENVIRONMENT = {
    "REDIS_HOST": "redis.example",
    "REDIS_PORT": "6380",
    "REDIS_PASSWORD": "secret",
    "REDIS_TLS": "true",
}


def test_settings_read_every_redis_variable():
    assert RedisSettings.from_env(ENVIRONMENT) == RedisSettings(
        host="redis.example", port=6380, password="secret", tls=True
    )
    assert RedisSettings.from_env({**ENVIRONMENT, "REDIS_TLS": "false"}).tls is False


@pytest.mark.parametrize("name", sorted(ENVIRONMENT))
def test_settings_refuse_a_missing_variable(name):
    given = {key: value for key, value in ENVIRONMENT.items() if key != name}
    with pytest.raises(MissingSetting, match=name):
        RedisSettings.from_env(given)


@pytest.mark.parametrize("given", ["True", "yes", "1", ""])
def test_settings_refuse_a_tls_value_other_than_true_or_false(given):
    with pytest.raises(MissingSetting, match="REDIS_TLS"):
        RedisSettings.from_env({**ENVIRONMENT, "REDIS_TLS": given})


def test_settings_refuse_a_port_that_is_not_a_number():
    with pytest.raises(MissingSetting, match="REDIS_PORT"):
        RedisSettings.from_env({**ENVIRONMENT, "REDIS_PORT": "redis"})


def _import_app(monkeypatch, environment):
    for name in ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delitem(sys.modules, "vote.app", raising=False)
    return importlib.import_module("vote.app")


def test_settings_let_vote_start_when_every_variable_is_set(monkeypatch):
    assert _import_app(monkeypatch, ENVIRONMENT).app.name == "vote.web"


@pytest.mark.parametrize("name", sorted(ENVIRONMENT))
def test_settings_stop_vote_starting_without_a_variable(monkeypatch, name):
    with pytest.raises(MissingSetting, match=name):
        _import_app(monkeypatch, {key: value for key, value in ENVIRONMENT.items() if key != name})
