"""Shared fixtures.

The whole suite must run without ``mlx_lm`` installed and without ever
starting a real MLX server, so all model layouts and processes here are
synthetic.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from mlx_manager.config import BotCfg, Config, ModelsCfg, ProvidersCfg, ServerCfg


def _make_model_dir(root: Path, name: str, *, sharded: bool = False) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "config.json").write_text(json.dumps({"model_type": "synthetic"}))
    if sharded:
        (d / "model-00001-of-00002.safetensors").write_bytes(b"")
        (d / "model-00002-of-00002.safetensors").write_bytes(b"")
    else:
        (d / "model.safetensors").write_bytes(b"")
    (d / "tokenizer.json").write_text("{}")
    return d


@pytest.fixture()
def fake_models_root(tmp_path: Path) -> Path:
    """A plain models directory with two model subdirs."""
    root = tmp_path / "models"
    _make_model_dir(root, "qwen3-8b-4bit")
    _make_model_dir(root, "llama-3-8b-4bit", sharded=True)
    # Decoy: looks like a model dir but lacks weights.
    decoy = root / "no-weights"
    decoy.mkdir()
    (decoy / "config.json").write_text("{}")
    return root


@pytest.fixture()
def fake_hf_cache(tmp_path: Path) -> Path:
    """A fake Hugging Face hub cache with one resolvable snapshot."""
    cache = tmp_path / "hf" / "hub"
    cache.mkdir(parents=True)

    repo = cache / "models--mlx-community--Llama-3.2-3B-Instruct-4bit"
    blobs = repo / "blobs"
    snapshots = repo / "snapshots"
    snap = snapshots / "abc123"
    blobs.mkdir(parents=True)
    snap.mkdir(parents=True)
    (snap / "config.json").write_text("{}")
    (snap / "model.safetensors").write_bytes(b"")

    # A second repo whose snapshot has no weights — must be skipped.
    bad_repo = cache / "models--someorg--no-weights"
    (bad_repo / "snapshots" / "deadbeef").mkdir(parents=True)
    (bad_repo / "snapshots" / "deadbeef" / "config.json").write_text("{}")

    return cache


@pytest.fixture()
def fake_lmstudio_root(tmp_path: Path) -> Path:
    """A fake LM Studio models tree: ``<root>/<publisher>/<model-name>/``."""
    root = tmp_path / "lmstudio" / "models"
    _make_model_dir(
        root / "lmstudio-community", "gemma-test-MLX-4bit", sharded=True
    )
    _make_model_dir(root / "someuser", "exotic-model-3bit")
    # Decoy: publisher with no real model dirs underneath.
    (root / "empty-publisher").mkdir(parents=True)
    return root


@pytest.fixture()
def cfg_factory(tmp_path: Path):
    """Build a Config rooted in *tmp_path* with the given knobs overridden."""

    def make(**overrides):
        defaults = {
            "host": "127.0.0.1",
            "port": 18080,
            "log_file": str(tmp_path / "mlx.log"),
            "pid_file": str(tmp_path / "mlx.pid"),
            "state_file": str(tmp_path / "state.json"),
            "lock_file": str(tmp_path / "mlx.lock"),
            "python_executable": "python3",
            "extra_args": [],
            "startup_timeout_seconds": 5,
            "stop_timeout_seconds": 2,
            "max_log_bytes": 1024,
            "max_log_files": 3,
            "patch_tool_calls": True,
            "max_context_tokens": 0,
            "prompt_cache_fraction": 0.5,
            "directories": [],
            "default_model": "",
            "aliases": {},
            "base_url": "",
            "api_key": "mlx-local",
            "provider_name": "mlx-local",
            "bot_model": "mlx-community/gemma-4-e2b-it-4bit",
            "bot_cache_dir": str(tmp_path / "bot"),
            "bot_max_tokens": 1024,
            "bot_temperature": 0.7,
        }
        defaults.update(overrides)
        server = ServerCfg(
            host=defaults["host"],
            port=defaults["port"],
            log_file=defaults["log_file"],
            pid_file=defaults["pid_file"],
            state_file=defaults["state_file"],
            lock_file=defaults["lock_file"],
            python_executable=defaults["python_executable"],
            extra_args=list(defaults["extra_args"]),
            startup_timeout_seconds=defaults["startup_timeout_seconds"],
            stop_timeout_seconds=defaults["stop_timeout_seconds"],
            max_log_bytes=defaults["max_log_bytes"],
            max_log_files=defaults["max_log_files"],
            patch_tool_calls=defaults["patch_tool_calls"],
            max_context_tokens=defaults["max_context_tokens"],
            prompt_cache_fraction=defaults["prompt_cache_fraction"],
        )
        models = ModelsCfg(
            directories=list(defaults["directories"]),
            default_model=defaults["default_model"],
            aliases=dict(defaults["aliases"]),
        )
        providers = ProvidersCfg(
            base_url=defaults["base_url"],
            api_key=defaults["api_key"],
            provider_name=defaults["provider_name"],
        )
        bot = BotCfg(
            model=defaults["bot_model"],
            cache_dir=defaults["bot_cache_dir"],
            max_tokens=defaults["bot_max_tokens"],
            temperature=defaults["bot_temperature"],
        )
        return Config(
            path=tmp_path / "config.toml",
            server=server,
            models=models,
            providers=providers,
            bot=bot,
        )

    return make
