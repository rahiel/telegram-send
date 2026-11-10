import asyncio

import pytest

from telegram_send.telegram_send import ConfigError, send


def make_conf(tmp_path):
    conf = tmp_path / "telegram-send.conf"
    conf.write_text("[telegram]\ntoken = 123:ABC\nchat_id = 12345\n", encoding="utf-8")
    return str(conf)


def test_location_missing_longitude(tmp_path):
    with pytest.raises(ConfigError):
        asyncio.run(send(locations=["35.5"], conf=make_conf(tmp_path)))


def test_location_not_numeric(tmp_path):
    with pytest.raises(ConfigError):
        asyncio.run(send(locations=["north", "east"], conf=make_conf(tmp_path)))
