from __future__ import annotations

from pathlib import Path

from mlx_manager import cli


def _write_cfg(path: Path, tmp_path: Path, models_root: Path | None) -> None:
    directories = "[]" if models_root is None else f'["{models_root}"]'
    path.write_text(
        '[models]\ndirectories = {dirs}\n\n[server]\nport = 18080\n'
        'log_file = "{t}/mlx.log"\npid_file = "{t}/mlx.pid"\n'
        'state_file = "{t}/state.json"\nlock_file = "{t}/mlx.lock"\n'.format(
            dirs=directories, t=tmp_path
        )
    )


def _fake_start(captured):
    def fake_start(
        cfg_obj,
        model,
        *,
        host,
        port,
        extra_arg_pairs,
        replace,
        on_warning,
        on_verbose,
    ):
        captured.update(
            model_id=model.id,
            host=host,
            port=port,
            extra_arg_pairs=extra_arg_pairs,
            replace=replace,
        )
        return cli.srv.State(
            pid=123,
            model_alias=model.id,
            model_path=str(model.path),
            host=host,
            port=port,
            base_url=f"http://{host}:{port}/v1",
            command=["python3", "-m", "mlx_lm", "server"],
            started_at="2026-01-01T00:00:00Z",
            python_executable=cfg_obj.server.python_executable,
        )

    return fake_start


def _inputs(values):
    items = iter(values)

    def fake_input(prompt):
        return next(items)

    return fake_input


def test_load_guides_model_host_port_and_replace(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    monkeypatch.setattr(cli, "model_memory_plan", lambda *args, **kwargs: (4096, 123456))
    monkeypatch.setattr(
        "builtins.input",
        # model, host, port, replace?, update-opencode?
        _inputs(["qwen3-8b-4bit", "all", "1237", "y", "n"]),
    )
    rc = cli.main(["--config", str(cfg), "load"])
    out, err = capsys.readouterr()

    assert rc == 0
    assert captured["model_id"] == "qwen3-8b-4bit"
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 1237
    assert captured["replace"] is True
    # --prompt-cache-bytes is auto-injected when not already set.
    assert len(captured["extra_arg_pairs"]) == 1
    assert captured["extra_arg_pairs"][0].startswith("--prompt-cache-bytes=")
    assert "Discovered models:" in out
    assert "started mlx_lm server" in out
    assert "binding on 0.0.0.0" in err
    # User declined the OpenCode prompt, so no `opencode:` line in stdout.
    assert "opencode:" not in out


def test_start_choose_uses_flags_and_prompts_for_model_only(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    # model selection + decline OpenCode update (everything else is on the CLI).
    monkeypatch.setattr("builtins.input", _inputs(["qwen3-8b-4bit", "n"]))
    rc = cli.main([
        "--config",
        str(cfg),
        "start",
        "--choose",
        "--host",
        "0.0.0.0",
        "--bind-all",
        "--port",
        "1237",
        "--replace",
    ])
    out, err = capsys.readouterr()

    assert rc == 0
    assert captured["model_id"] == "qwen3-8b-4bit"
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 1237
    assert captured["replace"] is True
    assert "Discovered models:" in out
    assert "binding on 0.0.0.0" in err


def test_start_rejects_wildcard_host_without_bind_all(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)

    def fake_start(*args, **kwargs):
        raise AssertionError("start should reject wildcard host before server start")

    monkeypatch.setattr(cli.srv, "start", fake_start)
    rc = cli.main([
        "--config",
        str(cfg),
        "start",
        "--model",
        "qwen3-8b-4bit",
        "--host",
        "0.0.0.0",
    ])
    out, err = capsys.readouterr()

    assert rc == 2
    assert out == ""
    assert "requires --bind-all" in err


def test_start_accepts_localhost_without_bind_all(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    rc = cli.main([
        "--config",
        str(cfg),
        "start",
        "--model",
        "qwen3-8b-4bit",
        "--host",
        "127.0.0.1",
    ])
    out, err = capsys.readouterr()

    assert rc == 0
    assert captured["host"] == "127.0.0.1"
    assert "started mlx_lm server" in out
    assert "binding on 0.0.0.0" not in err


def test_load_prompt_yes_applies_opencode(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    # Redirect the OpenCode write to a tmp file so it doesn't touch real config.
    target = tmp_path / "opencode.json"
    monkeypatch.setattr(cli, "_DEFAULT_OPENCODE_TARGET", str(target))
    monkeypatch.setattr(
        "builtins.input",
        # model, host=default, port=default, replace=N, opencode=Y,
        # then sub-prompts: target=default, mode=default(merge), claude-code=N
        _inputs(["qwen3-8b-4bit", "", "", "n", "y", "", "", "n"]),
    )
    rc = cli.main(["--config", str(cfg), "load"])
    out, _ = capsys.readouterr()

    assert rc == 0
    # `opencode:` line printed and target file actually written.
    assert "opencode:" in out
    assert target.exists()
    import json as _json

    doc = _json.loads(target.read_text())
    # Provider key carries the mlx-manager: prefix and :port suffix.
    keys = list(doc["provider"].keys())
    assert any(k.startswith("mlx-manager:") and k.endswith(":18080") for k in keys)
    # Default sub-prompt mode is merge → no Claude Code snippet block printed.
    assert "Claude Code (LiteLLM) snippet" not in out


def test_load_prompt_yes_with_overwrite_and_claude_code(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    target = tmp_path / "opencode.json"
    # Pre-seed an existing provider block to confirm overwrite resets it.
    target.write_text(
        '{"provider": {"mlx-manager:mlx-local:18080": '
        '{"npm": "stale", "models": {"old-model": {"name": "old-model"}}}}}'
    )
    monkeypatch.setattr(
        "builtins.input",
        # model, host=default, port=default, replace=N, opencode=Y,
        # sub: target=custom, mode=overwrite, claude-code=Y
        _inputs([
            "qwen3-8b-4bit", "", "", "n", "y",
            str(target), "o", "y",
        ]),
    )
    rc = cli.main(["--config", str(cfg), "load"])
    out, _ = capsys.readouterr()

    assert rc == 0
    assert "overwritten" in out
    assert "Claude Code (LiteLLM) snippet" in out
    assert "model_name:" in out  # LiteLLM yaml marker
    import json as _json
    doc = _json.loads(target.read_text())
    block = doc["provider"]["mlx-manager:mlx-local:18080"]
    # Overwrite wiped the legacy `old-model` entry.
    assert "old-model" not in block["models"]
    assert "qwen3-8b-4bit" in block["models"]


def test_load_skips_prompt_when_update_opencode_flag_set(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    target = tmp_path / "opencode.json"
    # No prompt for opencode is expected — exactly 4 inputs feed model/host/port/replace.
    monkeypatch.setattr(
        "builtins.input",
        _inputs(["qwen3-8b-4bit", "", "", "n"]),
    )
    rc = cli.main([
        "--config",
        str(cfg),
        "load",
        "--update-opencode",
        "--opencode-target",
        str(target),
    ])
    out, _ = capsys.readouterr()

    assert rc == 0
    assert "opencode:" in out
    assert target.exists()


def test_load_path_prompt_rejects_yes_no_and_reprompts(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    """A confused 'y' at the path prompt must not be accepted as a literal filename.

    Regression: previously the path prompt's `[~/.config/...]` form looked like
    a `[y/N]` answer, and typing `y` silently wrote the JSON to ./y in cwd.
    """
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    target = tmp_path / "opencode.json"
    monkeypatch.setattr(cli, "_DEFAULT_OPENCODE_TARGET", str(target))
    monkeypatch.setattr(
        "builtins.input",
        # model, host, port, replace=N, opencode=Y,
        # path: "y" (rejected), "Y" (rejected), "no" (rejected), "" (accept default),
        # mode=default(merge), claude-code=N
        _inputs([
            "qwen3-8b-4bit", "", "", "n", "y",
            "y", "Y", "no", "",
            "", "n",
        ]),
    )
    rc = cli.main(["--config", str(cfg), "load"])
    out, _ = capsys.readouterr()

    assert rc == 0
    # Apply landed on the real (tmp) target, NOT on a stray './y' file.
    assert target.exists()
    assert not (tmp_path / "y").exists()
    # Stdout includes the reprompt guidance after each rejected answer.
    assert out.count("That looks like a yes/no answer") == 3


def test_load_without_discovered_models_does_not_start(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, None)

    def fake_start(*args, **kwargs):
        raise AssertionError("load should not start without a selected model")

    monkeypatch.setattr(cli.srv, "start", fake_start)
    rc = cli.main(["--config", str(cfg), "load"])
    out, err = capsys.readouterr()

    assert rc == 3
    assert out == ""
    assert "no models discovered" in err
