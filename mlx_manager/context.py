from __future__ import annotations

import json
import subprocess
from pathlib import Path

DEFAULT_PROMPT_CACHE_FRACTION = 0.5


def system_ram_bytes() -> int:
    """Return total unified memory in bytes (macOS sysctl). Returns 0 on failure."""
    try:
        out = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return int(out.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return 0


def model_weight_bytes(model_path: Path) -> int:
    """Sum of safetensors weight file sizes under *model_path*."""
    total = 0
    try:
        for c in model_path.iterdir():
            if c.is_file() and (
                c.name in ("model.safetensors", "weights.safetensors")
                or (c.name.startswith("model-") and c.name.endswith(".safetensors"))
            ):
                total += c.stat().st_size
    except OSError:
        pass
    return total


def _kv_bytes_per_token(cfg_json: dict) -> int:
    layers = cfg_json.get("num_hidden_layers", 32)
    kv_heads = cfg_json.get("num_key_value_heads") or cfg_json.get("num_attention_heads", 8)
    head_dim = cfg_json.get("head_dim") or (
        cfg_json.get("hidden_size", 4096) // max(int(cfg_json.get("num_attention_heads", 32)), 1)
    )
    return 2 * int(layers) * int(kv_heads) * int(head_dim) * 2  # K+V, fp16


def safe_context_tokens(
    total_ram: int,
    model_bytes: int,
    cfg_json: dict,
    *,
    max_context_tokens: int = 0,
) -> int:
    """Return the largest context (in tokens) that fits in unified memory.

    Derives KV cache bytes-per-token from the model config, subtracts model
    weights and a 3 GB system headroom from available RAM, then caps at the
    model's architectural maximum.  When *max_context_tokens* is positive it
    further caps the result (LM Studio-style hard ceiling).  Returns 0 when
    inputs are insufficient.
    """
    bytes_per_token = _kv_bytes_per_token(cfg_json)
    if not bytes_per_token:
        return 0
    # Scale headroom with machine size: Metal on Apple Silicon tops out at ~75% of
    # unified RAM; generation buffers add to weights. 30% reservation is empirically
    # safe across 16–128 GB machines; floor at 8 GB for small machines.
    headroom = max(8 * 1024 ** 3, int(total_ram * 0.30))
    usable = max(0, total_ram - model_bytes - headroom)
    arch_max = int(cfg_json.get("max_position_embeddings", 32768))
    tokens = min(usable // bytes_per_token, arch_max)
    if max_context_tokens > 0:
        tokens = min(tokens, int(max_context_tokens))
    return tokens


def model_memory_plan(
    model_path: Path,
    *,
    max_context_tokens: int = 0,
    prompt_cache_fraction: float = DEFAULT_PROMPT_CACHE_FRACTION,
) -> tuple[int, int] | None:
    """Return ``(context_tokens, kv_cache_bytes)`` for this model on this machine.

    ``context_tokens`` is the safe ceiling (capped by *max_context_tokens* when
    set). ``kv_cache_bytes`` sizes ``--prompt-cache-bytes``; it covers only a
    *fraction* of the context so per-request working KV and concurrent decodes
    keep headroom (LM Studio behavior). Returns ``None`` when any input is
    unavailable or the result is zero.
    """
    try:
        with open(model_path / "config.json", encoding="utf-8") as f:
            cfg_json: dict = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    total_ram = system_ram_bytes()
    if not total_ram:
        return None

    m_bytes = model_weight_bytes(model_path)
    tokens = safe_context_tokens(
        total_ram, m_bytes, cfg_json, max_context_tokens=max_context_tokens
    )
    if tokens <= 0:
        return None

    fraction = prompt_cache_fraction
    if not (0.0 < fraction <= 1.0):
        fraction = DEFAULT_PROMPT_CACHE_FRACTION
    cache_tokens = max(1, int(tokens * fraction))
    return tokens, cache_tokens * _kv_bytes_per_token(cfg_json)


def wired_limit_mb() -> int | None:
    """Return ``iogpu.wired_limit_mb`` on macOS, or None when unavailable.

    A value of 0 means the kernel default (~75% of physical RAM) is in effect.
    """
    try:
        out = subprocess.run(
            ["sysctl", "-n", "iogpu.wired_limit_mb"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return int(out.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return None
