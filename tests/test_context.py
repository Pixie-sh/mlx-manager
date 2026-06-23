from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mlxer.context import (
    DEFAULT_PROMPT_CACHE_FRACTION,
    model_memory_plan,
    model_weight_bytes,
    safe_context_tokens,
    system_ram_bytes,
    wired_limit_mb,
)


# ---------------------------------------------------------------------------
# safe_context_tokens
# ---------------------------------------------------------------------------

_QWEN3_4B = {
    "num_hidden_layers": 36,
    "num_attention_heads": 16,
    "num_key_value_heads": 8,
    "hidden_size": 2048,
    "max_position_embeddings": 32768,
}


def test_safe_context_respects_arch_max():
    # Give it unlimited RAM — result must not exceed max_position_embeddings.
    tokens = safe_context_tokens(256 * 1024**3, 0, _QWEN3_4B)
    assert tokens == _QWEN3_4B["max_position_embeddings"]


def test_safe_context_constrained_by_ram():
    # 16 GB total, 4 GB model → headroom=8 GB, usable=4 GB → RAM-constrained.
    tokens = safe_context_tokens(16 * 1024**3, 4 * 1024**3, _QWEN3_4B)
    assert 0 < tokens < _QWEN3_4B["max_position_embeddings"]


def test_safe_context_returns_zero_when_no_headroom():
    tokens = safe_context_tokens(3 * 1024**3, 0, _QWEN3_4B)
    assert tokens == 0


def test_safe_context_uses_kv_heads_over_attention_heads():
    cfg_with_gqa = {**_QWEN3_4B, "num_key_value_heads": 2}
    cfg_mha = {k: v for k, v in _QWEN3_4B.items() if k != "num_key_value_heads"}

    # 16 GB total, 4 GB model → headroom=8 GB, usable=4 GB; MHA is RAM-constrained
    # while GQA still hits arch_max, proving the KV-head count drives the calculation.
    tokens_gqa = safe_context_tokens(16 * 1024**3, 4 * 1024**3, cfg_with_gqa)
    tokens_mha = safe_context_tokens(16 * 1024**3, 4 * 1024**3, cfg_mha)
    assert tokens_gqa > tokens_mha


def test_safe_context_falls_back_to_hidden_size_for_head_dim():
    cfg = {
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "hidden_size": 4096,
        "max_position_embeddings": 8192,
    }
    tokens = safe_context_tokens(32 * 1024**3, 3 * 1024**3, cfg)
    assert tokens > 0


# ---------------------------------------------------------------------------
# model_weight_bytes
# ---------------------------------------------------------------------------

def test_model_weight_bytes_sums_safetensors(tmp_path):
    (tmp_path / "model.safetensors").write_bytes(b"x" * 1000)
    (tmp_path / "model-00001-of-00002.safetensors").write_bytes(b"x" * 2000)
    (tmp_path / "tokenizer.json").write_bytes(b"x" * 500)
    assert model_weight_bytes(tmp_path) == 3000


def test_model_weight_bytes_handles_missing_dir():
    assert model_weight_bytes(Path("/nonexistent/path")) == 0


# ---------------------------------------------------------------------------
# system_ram_bytes
# ---------------------------------------------------------------------------

def test_system_ram_bytes_returns_int():
    ram = system_ram_bytes()
    assert isinstance(ram, int)
    assert ram >= 0


# ---------------------------------------------------------------------------
# model_memory_plan
# ---------------------------------------------------------------------------

def test_model_memory_plan_returns_plan(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps(_QWEN3_4B))
    (tmp_path / "model.safetensors").write_bytes(b"x" * (2 * 1024**3 // 100))

    with patch("mlxer.context.system_ram_bytes", return_value=16 * 1024**3):
        plan = model_memory_plan(tmp_path)

    assert plan is not None
    tokens, cache_bytes = plan
    assert tokens > 0
    assert cache_bytes > 0
    # Cache covers only the configured fraction of the safe context, so per-request
    # working KV and concurrent decodes keep headroom.
    bytes_per_token = 2 * 36 * 8 * 128 * 2
    expected = int(tokens * DEFAULT_PROMPT_CACHE_FRACTION) * bytes_per_token
    assert cache_bytes == pytest.approx(expected, rel=0.01)


def test_model_memory_plan_none_on_missing_config(tmp_path):
    assert model_memory_plan(tmp_path) is None


def test_model_memory_plan_none_when_ram_unavailable(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps(_QWEN3_4B))
    with patch("mlxer.context.system_ram_bytes", return_value=0):
        assert model_memory_plan(tmp_path) is None


def test_safe_context_respects_max_context_tokens():
    # Unlimited RAM would normally hit arch_max; the explicit cap wins.
    tokens = safe_context_tokens(
        256 * 1024**3, 0, _QWEN3_4B, max_context_tokens=8192
    )
    assert tokens == 8192


def test_safe_context_ignores_max_when_zero():
    tokens = safe_context_tokens(256 * 1024**3, 0, _QWEN3_4B, max_context_tokens=0)
    assert tokens == _QWEN3_4B["max_position_embeddings"]


def test_model_memory_plan_honors_max_context_tokens(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps(_QWEN3_4B))
    (tmp_path / "model.safetensors").write_bytes(b"")
    with patch("mlxer.context.system_ram_bytes", return_value=256 * 1024**3):
        plan = model_memory_plan(tmp_path, max_context_tokens=4096)
    assert plan is not None
    tokens, _ = plan
    assert tokens == 4096


def test_model_memory_plan_fraction_scales_cache(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps(_QWEN3_4B))
    (tmp_path / "model.safetensors").write_bytes(b"")
    with patch("mlxer.context.system_ram_bytes", return_value=64 * 1024**3):
        half = model_memory_plan(tmp_path, prompt_cache_fraction=0.5)
        full = model_memory_plan(tmp_path, prompt_cache_fraction=1.0)
    assert half is not None and full is not None
    assert half[0] == full[0]  # context unchanged
    assert half[1] == pytest.approx(full[1] / 2, rel=0.01)


def test_model_memory_plan_invalid_fraction_falls_back(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps(_QWEN3_4B))
    (tmp_path / "model.safetensors").write_bytes(b"")
    with patch("mlxer.context.system_ram_bytes", return_value=64 * 1024**3):
        bad = model_memory_plan(tmp_path, prompt_cache_fraction=1.5)
        default = model_memory_plan(tmp_path)
    assert bad is not None and default is not None
    assert bad[1] == default[1]


def test_wired_limit_mb_returns_int_or_none():
    val = wired_limit_mb()
    assert val is None or isinstance(val, int)
