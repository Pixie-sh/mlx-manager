"""Minimal streaming benchmark for the MLX HTTP server.

Hits ``/v1/chat/completions`` with ``stream: true`` so we can record
*time-to-first-token* in addition to total wall-clock and decode throughput.
Pure stdlib — ``urllib`` for HTTP, ``concurrent.futures`` for fan-out.
"""
from __future__ import annotations

import concurrent.futures
import json
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable


DEFAULT_PROMPT = (
    "Write a five-paragraph technical explanation of how unified memory on "
    "Apple Silicon differs from traditional discrete-GPU memory hierarchies. "
    "Cover bandwidth, latency, and what it means for ML inference workloads."
)

REQUEST_READ_TIMEOUT_S = 600.0  # generous; slow models on long completions.


@dataclass
class RequestResult:
    ok: bool
    ttft_s: float | None
    total_s: float
    prompt_tokens: int
    completion_tokens: int
    decode_tps: float
    finish_reason: str
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkSummary:
    endpoint: str
    model: str
    requests_total: int
    requests_ok: int
    concurrency: int
    warmup: int
    max_tokens: int
    prompt_chars: int
    wall_seconds: float
    aggregate_decode_tps: float  # tokens/s across all parallel streams
    per_request: list[RequestResult] = field(default_factory=list)
    ttft_p50: float | None = None
    ttft_p95: float | None = None
    decode_tps_p50: float | None = None
    decode_tps_p95: float | None = None
    total_p50: float | None = None
    total_p95: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["per_request"] = [r.to_dict() for r in self.per_request]
        return d


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    # ``statistics.quantiles`` with n=100 gives 99 cut points; index q-1.
    qs = statistics.quantiles(sorted(values), n=100, method="inclusive")
    idx = max(0, min(98, int(round(q)) - 1))
    return qs[idx]


def stream_one(
    endpoint: str,
    model: str,
    prompt: str,
    *,
    max_tokens: int,
    api_key: str = "",
    temperature: float = 0.0,
    timeout: float = REQUEST_READ_TIMEOUT_S,
) -> RequestResult:
    """Send one streaming chat-completions request; return measured stats."""
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": True,
            "temperature": temperature,
            # OpenAI-compat opt-in for the final usage chunk on streamed
            # responses. mlx_lm.server honors this; servers that don't will
            # just ignore the field and we fall back to chunk-counting below.
            "stream_options": {"include_usage": True},
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = endpoint.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    t0 = time.monotonic()
    ttft: float | None = None
    completion_tokens = 0
    prompt_tokens = 0
    finish_reason = ""
    content_chunks = 0  # fallback when the server doesn't return `usage`
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                delta = choices[0].get("delta", {}) if choices else {}
                if delta.get("content") or delta.get("reasoning"):
                    content_chunks += 1
                    if ttft is None:
                        ttft = time.monotonic() - t0
                if choices and choices[0].get("finish_reason"):
                    finish_reason = choices[0]["finish_reason"]
                usage = chunk.get("usage")
                if isinstance(usage, dict):
                    completion_tokens = int(
                        usage.get("completion_tokens", completion_tokens) or 0
                    )
                    prompt_tokens = int(
                        usage.get("prompt_tokens", prompt_tokens) or 0
                    )
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        return RequestResult(
            ok=False,
            ttft_s=ttft,
            total_s=time.monotonic() - t0,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            decode_tps=0.0,
            finish_reason=finish_reason,
            error=str(e),
        )

    total = time.monotonic() - t0
    # Fall back to chunk count when the server didn't report usage.
    if completion_tokens == 0 and content_chunks > 0:
        completion_tokens = content_chunks
    decode_window = max(total - (ttft or 0.0), 1e-6)
    decode_tps = completion_tokens / decode_window if completion_tokens else 0.0
    return RequestResult(
        ok=True,
        ttft_s=ttft,
        total_s=total,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        decode_tps=decode_tps,
        finish_reason=finish_reason,
    )


def run(
    endpoint: str,
    model: str,
    prompt: str,
    *,
    requests: int,
    concurrency: int,
    max_tokens: int,
    warmup: int = 0,
    api_key: str = "",
    on_event: Callable[[str], None] | None = None,
) -> BenchmarkSummary:
    """Run *requests* total at *concurrency*, after *warmup* sequential calls."""
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    if requests < 1:
        raise ValueError("requests must be >= 1")
    if warmup < 0:
        raise ValueError("warmup must be >= 0")

    def emit(msg: str) -> None:
        if on_event:
            on_event(msg)

    # Warmup runs are sequential and not part of the measurement.
    for i in range(warmup):
        emit(f"warmup {i + 1}/{warmup}")
        stream_one(
            endpoint, model, prompt, max_tokens=max_tokens, api_key=api_key
        )

    results: list[RequestResult] = []
    t_start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [
            ex.submit(
                stream_one,
                endpoint,
                model,
                prompt,
                max_tokens=max_tokens,
                api_key=api_key,
            )
            for _ in range(requests)
        ]
        for i, fut in enumerate(concurrent.futures.as_completed(futures), start=1):
            r = fut.result()
            results.append(r)
            emit(
                f"request {i}/{requests}  "
                f"ttft={'-' if r.ttft_s is None else f'{r.ttft_s:.2f}s'}  "
                f"total={r.total_s:.2f}s  "
                f"completion={r.completion_tokens}  "
                f"decode={r.decode_tps:.1f} tok/s"
                + (f"  ERR {r.error}" if not r.ok else "")
            )
    wall = time.monotonic() - t_start

    ok = [r for r in results if r.ok]
    completion_total = sum(r.completion_tokens for r in ok)
    aggregate_tps = completion_total / wall if wall > 0 else 0.0

    ttft_vals = [r.ttft_s for r in ok if r.ttft_s is not None]
    decode_vals = [r.decode_tps for r in ok if r.completion_tokens > 0]
    total_vals = [r.total_s for r in ok]

    return BenchmarkSummary(
        endpoint=endpoint,
        model=model,
        requests_total=requests,
        requests_ok=len(ok),
        concurrency=concurrency,
        warmup=warmup,
        max_tokens=max_tokens,
        prompt_chars=len(prompt),
        wall_seconds=wall,
        aggregate_decode_tps=aggregate_tps,
        per_request=results,
        ttft_p50=_percentile(ttft_vals, 50),
        ttft_p95=_percentile(ttft_vals, 95),
        decode_tps_p50=_percentile(decode_vals, 50),
        decode_tps_p95=_percentile(decode_vals, 95),
        total_p50=_percentile(total_vals, 50),
        total_p95=_percentile(total_vals, 95),
    )
