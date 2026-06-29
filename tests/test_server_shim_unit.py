from __future__ import annotations

import io
import sys
import types

from mlxer import _server_shim as shim


def _install_fake_mlx_server(monkeypatch, *, handle_completion=None):
    class FakeFormatter:
        def __init__(self, parser, tools, streaming=False):
            self._tool_parser = parser

    class FakeHandler:
        path = "/"

        def generate_response(self, text, finish_reason, *args, **kwargs):
            return {"choices": [{"finish_reason": finish_reason}]}

        def handle_chat_completions(self):
            return None

        def handle_completion(self, *args, **kwargs):
            if handle_completion is not None:
                return handle_completion(self, *args, **kwargs)
            return None

        def log_request(self, code="-", size="-"):
            print(f"LOG {self.path} {code} {size}", file=sys.stderr)

    server_mod = types.ModuleType("mlx_lm.server")
    setattr(server_mod, "ToolCallFormatter", FakeFormatter)
    setattr(server_mod, "APIHandler", FakeHandler)
    mlx_mod = types.ModuleType("mlx_lm")
    setattr(mlx_mod, "server", server_mod)

    monkeypatch.setitem(sys.modules, "mlx_lm", mlx_mod)
    monkeypatch.setitem(sys.modules, "mlx_lm.server", server_mod)
    return server_mod


def test_patch_suppresses_broken_pipe_from_streaming_response(monkeypatch):
    def disconnected(_self, *_args, **_kwargs):
        raise BrokenPipeError("client went away")

    server_mod = _install_fake_mlx_server(monkeypatch, handle_completion=disconnected)

    shim._apply_patch()

    handler = server_mod.APIHandler()
    assert handler.handle_completion(object(), []) is None


def test_patch_suppresses_known_compat_probe_404_logs(monkeypatch):
    server_mod = _install_fake_mlx_server(monkeypatch)
    stderr = io.StringIO()
    monkeypatch.setattr(sys, "stderr", stderr)

    shim._apply_patch()

    handler = server_mod.APIHandler()
    handler.path = "/api/tags"
    handler.log_request(404, "-")
    assert stderr.getvalue() == ""

    handler.path = "/unrelated"
    handler.log_request(404, "-")
    assert "LOG /unrelated 404" in stderr.getvalue()
