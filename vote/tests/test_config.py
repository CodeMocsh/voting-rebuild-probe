import pytest

from config import InvalidSetting, MissingSetting, load_redis_settings

ENV = {"REDIS_HOST": "h", "REDIS_PORT": "6380", "REDIS_USERNAME": "u", "REDIS_PASSWORD": "p", "REDIS_TLS": "true"}


def test_loads():
    s = load_redis_settings(ENV)
    assert (s.host, s.port, s.username, s.password, s.tls) == ("h", 6380, "u", "p", True)


@pytest.mark.parametrize("name", list(ENV))
def test_missing(name):
    env = {k: v for k, v in ENV.items() if k != name}
    with pytest.raises(MissingSetting, match=name):
        load_redis_settings(env)


@pytest.mark.parametrize("v", ["True", "1", "", "yes"])
def test_bad_tls(v):
    with pytest.raises(InvalidSetting):
        load_redis_settings({**ENV, "REDIS_TLS": v})
