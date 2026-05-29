from __future__ import annotations

import pytest

from mlx_manager.config import ConfigError, load, write_default


def test_first_run_writes_defaults(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg = load(cfg_path)
    assert cfg_path.exists()
    assert cfg.server.host == "127.0.0.1"
    assert cfg.server.port == 8080
    assert cfg.providers.api_key == "mlx-local"


def test_load_preserves_user_values(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        """
[server]
host = "0.0.0.0"
port = 9000

[providers]
api_key = "secret"
"""
    )
    cfg = load(cfg_path)
    assert cfg.server.host == "0.0.0.0"
    assert cfg.server.port == 9000
    # Defaults still fill in.
    assert cfg.server.startup_timeout_seconds == 120
    assert cfg.providers.api_key == "secret"


def test_base_url_derives_from_host_port(tmp_path):
    cfg = load(tmp_path / "config.toml")
    assert cfg.base_url == "http://127.0.0.1:8080/v1"


def test_unknown_top_level_table_rejected(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text('[wat]\nfoo = 1\n')
    with pytest.raises(ConfigError, match=r"unknown top-level table: \[wat\]"):
        load(cfg_path)


def test_unknown_key_rejected(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text('[server]\nhost = "127.0.0.1"\nfunky = 1\n')
    with pytest.raises(ConfigError, match=r"server\]\.funky"):
        load(cfg_path)


@pytest.mark.parametrize("bad_port", [80, 99, 1023, 65536, 100000])
def test_invalid_port_rejected(tmp_path, bad_port):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(f'[server]\nport = {bad_port}\n')
    with pytest.raises(ConfigError, match=r"port"):
        load(cfg_path)


def test_patch_tool_calls_defaults_true(tmp_path):
    cfg = load(tmp_path / "config.toml")
    assert cfg.server.patch_tool_calls is True


def test_patch_tool_calls_user_override(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("[server]\npatch_tool_calls = false\n")
    assert load(cfg_path).server.patch_tool_calls is False


def test_patch_tool_calls_must_be_bool(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text('[server]\npatch_tool_calls = "yes"\n')
    with pytest.raises(ConfigError, match=r"patch_tool_calls must be a boolean"):
        load(cfg_path)
