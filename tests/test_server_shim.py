"""Tests for the launch shim that patches mlx_lm.server's tool-call handling.

The patch behavior tests need a real ``mlx_lm`` to patch, so they skip when it
isn't installed (the rest of the suite must run without it).
"""
from __future__ import annotations

import sys

import pytest

from mlxer import _server_shim as shim

mlx_server = pytest.importorskip("mlx_lm.server")


@pytest.fixture(autouse=True)
def _patched():
    shim._apply_patch()  # idempotent; mutates mlx_lm.server classes in-process


def _make_handler(*, object_type="chat.completion.chunk", stream=True):
    h = mlx_server.APIHandler.__new__(mlx_server.APIHandler)
    h.request_id = "req-1"
    h.system_fingerprint = "fp"
    h.object_type = object_type
    h.requested_model = "m"
    h.created = 0
    h.stream = stream
    return h


def test_formatter_flags_parse_failure_and_drops_call():
    def raising_parser(text, tools):
        raise ValueError("truncated")

    f = mlx_server.ToolCallFormatter(raising_parser, [], streaming=False)
    assert shim._state.tool_parse_failed is False  # reset on construction
    assert f(["{half-a-tool"]) == []  # dropped, as stock mlx_lm does
    assert shim._state.tool_parse_failed is True  # ...but now flagged


def test_formatter_leaves_flag_clear_on_success():
    def ok_parser(text, tools):
        return {"name": "get_weather", "arguments": {"city": "NYC"}}

    f = mlx_server.ToolCallFormatter(ok_parser, [], streaming=False)
    assert shim._state.tool_parse_failed is False
    out = f(['{"name": "get_weather"}'])
    assert shim._state.tool_parse_failed is False
    assert len(out) == 1 and out[0]["type"] == "function"


def test_generate_response_forces_length_after_parse_failure():
    h = _make_handler()
    shim._state.tool_parse_failed = True
    resp = h.generate_response("hi", "tool_calls")
    assert resp["choices"][0]["finish_reason"] == "length"


def test_generate_response_untouched_when_no_failure():
    h = _make_handler()
    shim._state.tool_parse_failed = False
    resp = h.generate_response("hi", "tool_calls")
    assert resp["choices"][0]["finish_reason"] == "tool_calls"


def test_generate_response_ignores_streaming_delta_packets():
    """Intermediate stream packets carry finish_reason=None and must stay None
    even if a parse failure has been flagged."""
    h = _make_handler()
    shim._state.tool_parse_failed = True
    resp = h.generate_response("hi", None)
    assert resp["choices"][0]["finish_reason"] is None


def test_main_rebuilds_argv_and_dispatches_to_mlx_cli(monkeypatch):
    import mlx_lm.cli as cli

    captured = {}
    monkeypatch.setattr(cli, "main", lambda: captured.setdefault("argv", list(sys.argv)))
    monkeypatch.setattr(shim, "_apply_patch", lambda: None)
    monkeypatch.setattr(shim, "_announce_when_logging_ready", lambda msg: None)

    shim.main(["/abs/_server_shim.py", "server", "--model", "foo", "--port", "9001"])

    # Reconstructs exactly what `python -m mlx_lm server ...` would hand the CLI.
    assert captured["argv"] == ["mlx_lm", "server", "--model", "foo", "--port", "9001"]
