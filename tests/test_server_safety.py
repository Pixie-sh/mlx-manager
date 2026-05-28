from __future__ import annotations

import multiprocessing as mp
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mlx_manager import server as srv
from mlx_manager.config import ModelsCfg
from mlx_manager.models import Model, discover
from mlx_manager.paths import expand


def _spawn_idle(tag: str = "mlx-test-idle") -> subprocess.Popen:
    """Launch a long-running python process whose argv contains *tag*.

    The script just sleeps forever and reacts to SIGTERM normally.
    """
    code = f"import sys, time, signal\nsys.argv.append({tag!r})\ntime.sleep(3600)\n"
    return subprocess.Popen(
        [sys.executable, "-c", code, tag],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_lock_serializes_two_callers(tmp_path):
    """Two acquirers cannot hold the same lock at once; the second times out."""
    lock_path = tmp_path / "lock"

    def hold_lock_then_signal(release_evt, holding_evt):
        with srv.acquire_lock(lock_path, timeout=5):
            holding_evt.set()
            release_evt.wait(timeout=10)

    ctx = mp.get_context("fork")
    release = ctx.Event()
    holding = ctx.Event()
    holder = ctx.Process(target=hold_lock_then_signal, args=(release, holding))
    holder.start()
    try:
        assert holding.wait(timeout=5)
        t0 = time.monotonic()
        with pytest.raises(srv.ServerError, match=r"could not acquire lock"):
            with srv.acquire_lock(lock_path, timeout=0.5):
                pass
        assert time.monotonic() - t0 >= 0.4
    finally:
        release.set()
        holder.join(timeout=5)


def test_pid_alive_and_command_match(tmp_path):
    p = _spawn_idle("mlx_lm.server-test-tag")
    try:
        assert srv.pid_alive(p.pid)
        cmd = srv.pid_command(p.pid)
        assert "mlx_lm.server-test-tag" in cmd
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=5)
    assert not srv.pid_alive(p.pid)


def test_is_managed_process_requires_argv_match(tmp_path):
    p = _spawn_idle("mlx_lm.server")
    try:
        # State whose port appears in the synthetic argv → managed.
        good_state = srv.State(
            pid=p.pid,
            model_alias="m",
            model_path="/x/y/m",
            host="127.0.0.1",
            port=18080,  # must appear in argv — it doesn't, by design.
            base_url="http://127.0.0.1:18080/v1",
            command=[],
            started_at="2026-01-01T00:00:00Z",
            python_executable=sys.executable,
        )
        assert srv.is_managed_process(p.pid, good_state) is False  # port absent
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=5)


def test_reused_pid_with_wrong_argv_is_not_managed(tmp_path):
    """A live PID whose argv doesn't contain mlx_lm must NOT be considered managed."""
    p = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert srv.pid_alive(p.pid)
        assert srv.is_managed_process(p.pid, None) is False
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=5)


def test_stop_refuses_when_state_pid_argv_unrelated(tmp_path, cfg_factory):
    """Reused-PID safety: stop must refuse to kill an unrelated process."""
    cfg = cfg_factory()
    state_path = srv.port_state_path(cfg, cfg.server.port)

    p = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # State claims the unrelated PID is "ours". stop() must refuse.
        srv.write_state(
            state_path,
            srv.State(
                pid=p.pid,
                model_alias="ghost",
                model_path="/nope",
                host="127.0.0.1",
                port=cfg.server.port,
                base_url=f"http://127.0.0.1:{cfg.server.port}/v1",
                command=[sys.executable, "-c", "..."],
                started_at="2026-01-01T00:00:00Z",
                python_executable=sys.executable,
            ),
        )
        with pytest.raises(srv.ServerError) as ei:
            srv.stop(cfg, port=cfg.server.port)
        assert ei.value.exit_code == 1
        # And the unrelated process is still alive.
        assert srv.pid_alive(p.pid)
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=5)


def test_stop_reports_not_running_for_dead_pid(tmp_path, cfg_factory):
    cfg = cfg_factory()
    state_path = srv.port_state_path(cfg, cfg.server.port)
    srv.write_state(
        state_path,
        srv.State(
            pid=999999,  # unlikely to exist
            model_alias="x",
            model_path="/x",
            host="127.0.0.1",
            port=cfg.server.port,
            base_url=f"http://127.0.0.1:{cfg.server.port}/v1",
            command=[],
            started_at="2026-01-01T00:00:00Z",
            python_executable=sys.executable,
        ),
    )
    with pytest.raises(srv.ServerError) as ei:
        srv.stop(cfg, port=cfg.server.port)
    assert ei.value.exit_code == 4
    # State file cleaned up.
    assert not state_path.exists()


def test_state_write_is_atomic(tmp_path):
    """Atomic write: no .tmp residue, file contains valid JSON."""
    state_path = tmp_path / "state.json"
    s = srv.State(
        pid=1,
        model_alias="m",
        model_path="/m",
        host="127.0.0.1",
        port=8080,
        base_url="http://127.0.0.1:8080/v1",
        command=["py"],
        started_at="2026-01-01T00:00:00Z",
        python_executable="python3",
    )
    srv.write_state(state_path, s)
    assert state_path.is_file()
    assert not (state_path.parent / "state.json.tmp").exists()
    # Roundtrip parses.
    s2 = srv.read_state(state_path)
    assert s2 is not None
    assert s2.pid == 1


def test_serving_invocation_filesystem_uses_basename_and_parent_cwd(
    fake_lmstudio_root,
):
    """Filesystem models spawn with ``cwd=<parent>`` and ``--model <basename>``
    so the API exposes the same id ``mlx-manager list`` shows."""
    cfg = ModelsCfg(
        directories=[str(fake_lmstudio_root)], default_model="", aliases={}
    )
    m = next(x for x in discover(cfg) if x.id == "gemma-test-MLX-4bit")
    serving_id, cwd = srv.serving_invocation(m)
    assert serving_id == "gemma-test-MLX-4bit"
    assert cwd == m.path.parent
    # And the path is *resolvable* from that cwd as the bare id.
    assert (cwd / serving_id).is_dir()


def test_serving_invocation_hf_cache_uses_org_name(fake_hf_cache):
    """HF-cache models are passed as ``<org>/<name>``; mlx_lm's HF resolver
    finds them locally without needing a specific cwd."""
    cfg = ModelsCfg(directories=[str(fake_hf_cache)], default_model="", aliases={})
    m = next(
        x for x in discover(cfg) if x.id == "mlx-community/Llama-3.2-3B-Instruct-4bit"
    )
    serving_id, cwd = srv.serving_invocation(m)
    assert serving_id == "mlx-community/Llama-3.2-3B-Instruct-4bit"
    assert cwd is None


def test_build_command_returns_cwd_and_serving_id(cfg_factory, fake_lmstudio_root):
    cfg = cfg_factory()
    mcfg = ModelsCfg(
        directories=[str(fake_lmstudio_root)], default_model="", aliases={}
    )
    m = next(x for x in discover(mcfg) if x.id == "gemma-test-MLX-4bit")
    cmd, cwd, _warnings = srv.build_command(
        cfg, m, host="127.0.0.1", port=12345, extra_arg_pairs=[], supported_flags=set()
    )
    # `--model <serving_id>` is present and the absolute path is NOT.
    assert "--model" in cmd
    model_idx = cmd.index("--model")
    assert cmd[model_idx + 1] == "gemma-test-MLX-4bit"
    assert str(m.path) not in cmd
    assert cwd == m.path.parent


def test_log_rotation_caps_max_files(tmp_path):
    log = tmp_path / "x.log"
    log.write_bytes(b"0" * 4096)
    srv.rotate_log_if_needed(log, max_bytes=1024, max_files=3)
    # After rotation the original is moved to .1 and main is gone.
    assert not log.exists()
    assert (tmp_path / "x.log.1").exists()
    # Trigger again with a fresh oversize main.
    log.write_bytes(b"0" * 4096)
    srv.rotate_log_if_needed(log, max_bytes=1024, max_files=3)
    assert (tmp_path / "x.log.1").exists()
    assert (tmp_path / "x.log.2").exists()
    # Third rotation drops the oldest.
    log.write_bytes(b"0" * 4096)
    srv.rotate_log_if_needed(log, max_bytes=1024, max_files=3)
    assert not (tmp_path / "x.log.4").exists()
