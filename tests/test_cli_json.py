from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from mlx_manager import cli


def _run(monkeypatch, capsys, args, *, config_path: Path) -> tuple[int, str, str]:
    rc = cli.main(["--config", str(config_path), *args])
    out, err = capsys.readouterr()
    return rc, out, err


def test_list_json_empty_when_no_models(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[models]\ndirectories = []\n\n[server]\nlog_file = "{0}/mlx.log"\n'
        'pid_file = "{0}/mlx.pid"\nstate_file = "{0}/state.json"\n'
        'lock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    rc, out, _ = _run(monkeypatch, capsys, ["list", "--json"], config_path=cfg)
    assert rc == 0
    assert json.loads(out) == []


def test_list_json_shape(tmp_path, monkeypatch, capsys, fake_models_root):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[models]\ndirectories = ["{r}"]\n\n[server]\n'
        'log_file = "{t}/mlx.log"\npid_file = "{t}/mlx.pid"\n'
        'state_file = "{t}/state.json"\nlock_file = "{t}/mlx.lock"\n'.format(
            r=fake_models_root, t=tmp_path
        )
    )
    rc, out, _ = _run(monkeypatch, capsys, ["list", "--json"], config_path=cfg)
    assert rc == 0
    items = json.loads(out)
    assert isinstance(items, list)
    assert all({"id", "path", "source"} <= set(item.keys()) for item in items)
    ids = {i["id"] for i in items}
    assert "qwen3-8b-4bit" in ids


def test_status_json_when_not_running(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    # Without --port: returns a list (empty when nothing is running).
    rc, out, _ = _run(monkeypatch, capsys, ["status", "--json"], config_path=cfg)
    assert rc == 4
    items = json.loads(out)
    assert isinstance(items, list)
    assert items == []

    # With --port: returns a single status dict.
    rc, out, _ = _run(monkeypatch, capsys, ["status", "--port", "8080", "--json"], config_path=cfg)
    assert rc == 4
    d = json.loads(out)
    assert d["running"] is False
    assert d["stale"] is False
    assert d["uptime_seconds"] == 0


def test_doctor_json_emits_check_array(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    rc, out, _ = _run(monkeypatch, capsys, ["doctor", "--json"], config_path=cfg)
    # Doctor exits 0 or 1 depending on system state, but JSON must always parse.
    assert rc in (0, 1)
    items = json.loads(out)
    assert isinstance(items, list)
    assert all({"name", "status", "detail"} <= set(i.keys()) for i in items)
    for i in items:
        assert i["status"] in ("OK", "WARN", "FAIL")


def test_config_opencode_emits_json(tmp_path, monkeypatch, capsys, fake_models_root):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[models]\ndirectories = ["{r}"]\ndefault_model = "qwen3-8b-4bit"\n\n'
        '[server]\nlog_file = "{t}/mlx.log"\npid_file = "{t}/mlx.pid"\n'
        'state_file = "{t}/state.json"\nlock_file = "{t}/mlx.lock"\n'.format(
            r=fake_models_root, t=tmp_path
        )
    )
    rc, out, _ = _run(
        monkeypatch,
        capsys,
        ["config", "opencode", "--model", "qwen3-8b-4bit"],
        config_path=cfg,
    )
    assert rc == 0
    doc = json.loads(out)
    assert "provider" in doc
    assert "mlx-manager:mlx-local:8080" in doc["provider"]


def test_config_opencode_running_single_server_name_includes_port(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    monkeypatch.setattr(
        cli.srv,
        "list_running_states",
        lambda cfg_obj: [
            cli.srv.State(
                pid=123,
                model_alias="qwen3-8b-4bit",
                model_path="/tmp/qwen3-8b-4bit",
                host="127.0.0.1",
                port=18081,
                base_url="http://127.0.0.1:18081/v1",
                command=["python3", "-m", "mlx_lm", "server"],
                started_at="2026-01-01T00:00:00Z",
                python_executable=cfg_obj.server.python_executable,
            )
        ],
    )
    rc, out, _ = _run(monkeypatch, capsys, ["config", "opencode"], config_path=cfg)
    assert rc == 0
    doc = json.loads(out)
    assert "mlx-manager:mlx-local:18081" in doc["provider"]


def test_config_opencode_choose_prompts_and_applies(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    target = tmp_path / "opencode.json"
    cfg.write_text(
        '[models]\ndirectories = ["{r}"]\ndefault_model = "qwen3-8b-4bit"\n\n'
        '[server]\nlog_file = "{t}/mlx.log"\npid_file = "{t}/mlx.pid"\n'
        'state_file = "{t}/state.json"\nlock_file = "{t}/mlx.lock"\n'.format(
            r=fake_models_root, t=tmp_path
        )
    )

    answers = iter([str(target), "o", "y"])  # target, overwrite, claude-code
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    rc, out, _ = _run(
        monkeypatch,
        capsys,
        ["config", "opencode", "--choose"],
        config_path=cfg,
    )
    assert rc == 0
    assert target.exists()
    assert "Claude Code (LiteLLM) snippet" in out
    doc = json.loads(target.read_text())
    keys = list(doc["provider"].keys())
    assert any(k.startswith("mlx-manager:") for k in keys)


def test_config_opencode_reset_clears_managed_providers(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    target = tmp_path / "opencode.json"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    target.write_text(
        json.dumps(
            {
                "provider": {
                    "mlx-manager:mlx-local:8080": {"npm": "remove"},
                    "anthropic": {"npm": "keep"},
                }
            }
        )
    )
    rc, out, err = _run(
        monkeypatch,
        capsys,
        ["config", "opencode", "--reset", "--target", str(target)],
        config_path=cfg,
    )
    assert rc == 0
    assert err == ""
    assert "1 mlx-manager provider(s) removed" in out
    assert json.loads(target.read_text())["provider"] == {"anthropic": {"npm": "keep"}}


def test_stop_when_nothing_running_exits_4(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    rc, _, err = _run(monkeypatch, capsys, ["stop"], config_path=cfg)
    assert rc == 4
    assert "no managed server" in err
