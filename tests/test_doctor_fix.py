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
    cli._doctor_fix(cfg)
    assert ran == [["echo", "install"]]
    err = capsys.readouterr().err
    assert "ok" in err
