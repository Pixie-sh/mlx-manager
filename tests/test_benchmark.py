"""Benchmark tests use an in-process fake SSE server so no real model is needed."""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest

from mlx_manager.benchmark import run, stream_one


def _make_handler(
    *,
    completion_tokens: int = 10,
    prompt_tokens: int = 4,
    first_chunk_delay_s: float = 0.0,
    inter_chunk_delay_s: float = 0.0,
    finish_reason: str = "stop",
):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *a, **kw):  # silence test output
            return

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            _ = self.rfile.read(length)  # discard body
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            def write_chunk(obj: dict) -> None:
                self.wfile.write(b"data: " + json.dumps(obj).encode() + b"\n\n")
                self.wfile.flush()

            # initial "role" delta with no content — must NOT mark TTFT.
            write_chunk({"choices": [{"delta": {"role": "assistant"}}]})
            if first_chunk_delay_s:
                time.sleep(first_chunk_delay_s)
            # content chunks — first one marks TTFT.
            for i in range(completion_tokens):
                write_chunk(
                    {"choices": [{"delta": {"content": f"tok{i} "}}]}
                )
                if inter_chunk_delay_s:
                    time.sleep(inter_chunk_delay_s)
            # final chunk with finish_reason + usage
            write_chunk(
                {
                    "choices": [{"delta": {}, "finish_reason": finish_reason}],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                    },
                }
            )
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    return _Handler


@pytest.fixture()
def fake_server():
    """Start a ThreadingHTTPServer on a random port. Yields its base URL."""
    server: dict[str, object] = {}

    def start(handler_cls):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        port = srv.server_address[1]
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        server["srv"] = srv
        server["thread"] = thread
        return f"http://127.0.0.1:{port}/v1"

    yield start

    s = server.get("srv")
    if s is not None:
        s.shutdown()
        s.server_close()


def test_stream_one_parses_ttft_and_tokens(fake_server):
    endpoint = fake_server(
        _make_handler(
            completion_tokens=8,
            prompt_tokens=3,
            first_chunk_delay_s=0.05,
        )
    )
    r = stream_one(endpoint, "test-model", "hi", max_tokens=16)
    assert r.ok
    assert r.completion_tokens == 8
    assert r.prompt_tokens == 3
    assert r.finish_reason == "stop"
    # TTFT must be set, and must reflect the artificial delay (not zero).
    assert r.ttft_s is not None and r.ttft_s >= 0.04
    # decode_tps is positive.
    assert r.decode_tps > 0


def test_stream_one_returns_error_on_connection_failure():
    # Port 1 is reserved; should fail to connect.
    r = stream_one("http://127.0.0.1:1/v1", "any", "hi", max_tokens=4)
    assert not r.ok
    assert r.completion_tokens == 0
    assert "error" not in r.error.lower() or r.error  # any message is fine


def test_run_concurrency_and_summary(fake_server):
    endpoint = fake_server(
        _make_handler(completion_tokens=5, prompt_tokens=2, inter_chunk_delay_s=0.01)
    )
    summary = run(
        endpoint,
        "test-model",
        "hello",
        requests=4,
        concurrency=2,
        max_tokens=16,
        warmup=0,
    )
    assert summary.requests_total == 4
    assert summary.requests_ok == 4
    assert summary.concurrency == 2
    # Sum of completion tokens / wall time.
    assert summary.aggregate_decode_tps > 0
    # Per-stream stats populated.
    assert summary.ttft_p50 is not None
    assert summary.decode_tps_p50 is not None
    assert summary.total_p50 is not None
    # Each request reported.
    assert len(summary.per_request) == 4
    assert all(r.ok and r.completion_tokens == 5 for r in summary.per_request)


def test_run_validates_arguments():
    with pytest.raises(ValueError, match="concurrency"):
        run("http://x/v1", "m", "p", requests=1, concurrency=0, max_tokens=4)
    with pytest.raises(ValueError, match="requests"):
        run("http://x/v1", "m", "p", requests=0, concurrency=1, max_tokens=4)
    with pytest.raises(ValueError, match="warmup"):
        run("http://x/v1", "m", "p", requests=1, concurrency=1, warmup=-1, max_tokens=4)


def test_run_summary_to_dict_is_json_serializable(fake_server):
    endpoint = fake_server(_make_handler())
    summary = run(endpoint, "test-model", "hi", requests=2, concurrency=1, max_tokens=8)
    # If this doesn't raise, the shape is fine for `--json` output.
    json.dumps(summary.to_dict())
