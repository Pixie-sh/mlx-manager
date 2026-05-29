from __future__ import annotations

import sys

from mlx_manager import cli


def test_pipx_app_name_detects_venv(monkeypatch):
    monkeypatch.setattr(sys, "prefix", "/Users/rs/.local/pipx/venvs/mlx-manager")
    assert cli._pipx_app_name() == "mlx-manager"


def test_pipx_app_name_none_for_regular_venv(monkeypatch):
    monkeypatch.setattr(sys, "prefix", "/Library/Frameworks/Python.framework/Versions/3.12")
    assert cli._pipx_app_name() is None


def test_install_cmd_uses_pipx_inject_when_isolated(monkeypatch):
    monkeypatch.setattr(cli, "_pipx_app_name", lambda: "mlx-manager")
    monkeypatch.setattr(cli.shutil, "which", lambda _name: "/opt/homebrew/bin/pipx")
    assert cli._mlx_lm_install_cmd() == ["pipx", "inject", "mlx-manager", "mlx-lm"]


def test_install_cmd_falls_back_to_pip(monkeypatch):
    monkeypatch.setattr(cli, "_pipx_app_name", lambda: None)
    assert cli._mlx_lm_install_cmd() == [sys.executable, "-m", "pip", "install", "mlx-lm"]


def test_install_cmd_pip_when_pipx_missing(monkeypatch):
    monkeypatch.setattr(cli, "_pipx_app_name", lambda: "mlx-manager")
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)
    assert cli._mlx_lm_install_cmd() == [sys.executable, "-m", "pip", "install", "mlx-lm"]


def test_doctor_fix_creates_missing_model_dirs(monkeypatch, tmp_path, capsys, cfg_factory):
    missing = tmp_path / "new-models"
    cfg = cfg_factory(directories=[str(missing)])
    # Pretend mlx_lm is already importable so the fixer only handles dirs.
    monkeypatch.setattr(cli, "_mlx_lm_importable_here", lambda: True)
    cli._doctor_fix(cfg)
    assert missing.is_dir()


def test_doctor_fix_installs_when_bot_runtime_missing(monkeypatch, capsys, cfg_factory):
    cfg = cfg_factory(directories=[])
    states = iter([False, True])  # missing before, present after install
    monkeypatch.setattr(cli, "_mlx_lm_importable_here", lambda: next(states))
    ran = []
    monkeypatch.setattr(cli, "_mlx_lm_install_cmd", lambda: ["echo", "install"])
    monkeypatch.setattr(cli, "_run_fix_cmd", lambda cmd: ran.append(cmd) or 0)
    # Server python already has mlx_lm, so no repoint.
    monkeypatch.setattr(cli.srv, "mlx_lm_installed", lambda _py: True)
    cli._doctor_fix(cfg)
    assert ran == [["echo", "install"]]
    err = capsys.readouterr().err
    assert "ok" in err


def test_doctor_fix_repoints_server_python_when_default_lacks_mlx_lm(
    monkeypatch, tmp_path, capsys
):
    from mlx_manager.config import load

    cfg_path = tmp_path / "cfg.toml"
    cfg_path.write_text(
        '[server]\npython_executable = "python3"\n'
        'log_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'
        "[models]\ndirectories = []\n".format(tmp_path)
    )
    cfg = load(cfg_path)
    monkeypatch.setattr(cli, "_mlx_lm_importable_here", lambda: True)
    monkeypatch.setattr(cli.srv, "mlx_lm_installed", lambda _py: False)
    monkeypatch.setattr(cli.sys, "executable", "/venv/bin/python")
    cli._doctor_fix(cfg)
    # Config file updated to the working interpreter.
    assert load(cfg_path).server.python_executable == "/venv/bin/python"
    assert "set server.python_executable" in capsys.readouterr().err


def test_doctor_fix_advises_when_custom_server_python_lacks_mlx_lm(
    monkeypatch, tmp_path, capsys
):
    from mlx_manager.config import load

    cfg_path = tmp_path / "cfg.toml"
    cfg_path.write_text(
        '[server]\npython_executable = "/custom/python"\n'
        'log_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'
        "[models]\ndirectories = []\n".format(tmp_path)
    )
    cfg = load(cfg_path)
    monkeypatch.setattr(cli, "_mlx_lm_importable_here", lambda: True)
    monkeypatch.setattr(cli.srv, "mlx_lm_installed", lambda _py: False)
    cli._doctor_fix(cfg)
    # Custom value is NOT overwritten; user is advised instead.
    assert load(cfg_path).server.python_executable == "/custom/python"
    assert "cannot import mlx_lm" in capsys.readouterr().err
