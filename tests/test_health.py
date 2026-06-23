from __future__ import annotations

from mlxer import server as srv

_DEEPSEEK_LOG = """\
2026-05-28 10:56:11,064 - INFO - Starting httpd at 0.0.0.0 on port 1236...
Exception in thread Thread-1 (_generate):
Traceback (most recent call last):
ModuleNotFoundError: No module named 'mlx_lm.models.deepseek_v4'
ValueError: Model type deepseek_v4 not supported.
127.0.0.1 - - [28/May/2026 10:56:11] "GET /v1/models HTTP/1.1" 200 -
"""

_CLEAN_LOG = """\
2026-05-28 09:55:05,000 - INFO - Starting httpd at 0.0.0.0 on port 1235...
127.0.0.1 - - [28/May/2026 09:55:30] "POST /v1/chat/completions HTTP/1.1" 200 -
"""

_METAL_OOM_LOG = """\
2026-06-03 23:36:01,909 - INFO - Starting httpd at 0.0.0.0 on port 1236...
libc++abi: terminating due to uncaught exception of type std::runtime_error: [METAL] Command buffer execution failed: Insufficient Memory (00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)
"""


def test_log_health_detects_unsupported_model_type(tmp_path):
    log = tmp_path / "mlx.1236.log"
    log.write_text(_DEEPSEEK_LOG)
    status, detail = srv.log_health(log)
    assert status == "error"
    assert "deepseek_v4" in detail


def test_log_health_detects_metal_oom(tmp_path):
    log = tmp_path / "mlx.1236.log"
    log.write_text(_METAL_OOM_LOG)
    status, detail = srv.log_health(log)
    assert status == "error"
    assert "Metal" in detail
    assert "reduce prompt cache" in detail


def test_log_health_ok_for_clean_log(tmp_path):
    log = tmp_path / "mlx.1235.log"
    log.write_text(_CLEAN_LOG)
    assert srv.log_health(log) == ("ok", "")


def test_log_health_missing_file_is_ok(tmp_path):
    assert srv.log_health(tmp_path / "nope.log") == ("ok", "")


def test_log_health_ignores_error_before_latest_restart(tmp_path):
    """An error before the most recent 'Starting httpd' marker is from a prior
    run of the same appended log and must not flag the current session."""
    log = tmp_path / "mlx.log"
    log.write_text(_DEEPSEEK_LOG + _CLEAN_LOG)
    assert srv.log_health(log) == ("ok", "")


def test_status_reports_log_health_for_stale_state(tmp_path, cfg_factory):
    cfg = cfg_factory()
    srv.write_state(
        srv.port_state_path(cfg, cfg.server.port),
        srv.State(
            pid=999999,
            model_alias="oom-model",
            model_path="/models/oom-model",
            host="127.0.0.1",
            port=cfg.server.port,
            base_url=f"http://127.0.0.1:{cfg.server.port}/v1",
            command=[],
            started_at="2026-01-01T00:00:00Z",
            python_executable="python3",
        ),
    )
    srv.port_log_path(cfg, cfg.server.port).write_text(_METAL_OOM_LOG)

    status = srv.status_dict(cfg, cfg.server.port)

    assert status["running"] is False
    assert status["stale"] is True
    assert status["health"] == "error"
    assert "Metal" in status["health_detail"]
