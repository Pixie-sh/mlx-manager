from __future__ import annotations

import pytest

from mlx_manager.config import ModelsCfg
from mlx_manager.models import discover, discover_with_skipped, resolve


def test_discover_plain_directory(fake_models_root):
    cfg = ModelsCfg(directories=[str(fake_models_root)], default_model="", aliases={})
    found = discover(cfg)
    ids = {m.id for m in found}
    assert "qwen3-8b-4bit" in ids
    assert "llama-3-8b-4bit" in ids  # sharded
    assert "no-weights" not in ids
    for m in found:
        assert m.source == "directory"


def test_discover_hf_cache_keeps_org_prefix(fake_hf_cache):
    cfg = ModelsCfg(directories=[str(fake_hf_cache)], default_model="", aliases={})
    found = discover(cfg)
    ids = {m.id for m in found}
    # Full HF-style id is preserved so the API can serve it under the same name.
    assert "mlx-community/Llama-3.2-3B-Instruct-4bit" in ids
    # Repo with no usable snapshot is skipped.
    assert all("no-weights" not in i for i in ids)
    # Resolved path is the snapshot dir, not the bare hash.
    m = next(m for m in found if m.id == "mlx-community/Llama-3.2-3B-Instruct-4bit")
    assert m.source == "hf_cache"
    assert m.path.name == "abc123"
    assert m.path.parent.name == "snapshots"


def test_alias_takes_precedence(fake_models_root):
    cfg = ModelsCfg(
        directories=[str(fake_models_root)],
        default_model="",
        aliases={"qwen3-8b-4bit": str(fake_models_root / "qwen3-8b-4bit")},
    )
    found = discover(cfg)
    alias_entry = next(m for m in found if m.id == "qwen3-8b-4bit")
    assert alias_entry.source == "alias"


def test_resolve_alias_then_id_then_path(fake_models_root, tmp_path):
    alias_target = fake_models_root / "qwen3-8b-4bit"
    cfg = ModelsCfg(
        directories=[str(fake_models_root)],
        default_model="",
        aliases={"speedy": str(alias_target)},
    )
    # By alias
    assert resolve(cfg, "speedy").path == alias_target.resolve()
    # By discovered id
    assert resolve(cfg, "llama-3-8b-4bit").id == "llama-3-8b-4bit"
    # By absolute path
    extra = fake_models_root / "other-model"
    extra.mkdir()
    (extra / "config.json").write_text("{}")
    (extra / "model.safetensors").write_bytes(b"")
    assert resolve(cfg, str(extra)).path == extra.resolve()


def test_discover_lmstudio_nested_layout(fake_lmstudio_root):
    """LM Studio uses ``<root>/<publisher>/<model-name>/``.

    The id is the model directory's basename (no publisher prefix) so the
    spawned ``mlx_lm.server --model <basename>`` exposes that exact id on the
    wire — matching what users naturally type in OpenCode-style configs.
    """
    cfg = ModelsCfg(
        directories=[str(fake_lmstudio_root)], default_model="", aliases={}
    )
    found = discover(cfg)
    ids = {m.id for m in found}
    assert "gemma-test-MLX-4bit" in ids
    assert "exotic-model-3bit" in ids
    for m in found:
        assert m.source == "directory"
        # Display id is always the deepest path segment.
        assert m.id == m.path.name


def test_discover_mixed_roots_dedupes_by_id(
    tmp_path, fake_models_root, fake_lmstudio_root, fake_hf_cache
):
    """All three layouts coexist; ids are unique in the output."""
    cfg = ModelsCfg(
        directories=[
            str(fake_models_root),
            str(fake_lmstudio_root),
            str(fake_hf_cache),
        ],
        default_model="",
        aliases={},
    )
    found = discover(cfg)
    ids = [m.id for m in found]
    assert len(ids) == len(set(ids))
    # At least one entry from each layout is present.
    sources = {m.source for m in found}
    assert {"directory", "hf_cache"} <= sources


def test_resolve_unknown_raises(tmp_path):
    cfg = ModelsCfg(directories=[str(tmp_path)], default_model="", aliases={})
    with pytest.raises(LookupError):
        resolve(cfg, "ghost-model")


def test_discover_with_skipped_surfaces_gguf_and_partial_dirs(tmp_path):
    """GGUF-only dirs and half-formed model dirs are returned as SkippedDir
    with a human-readable reason — they don't appear in `discover()` itself."""
    root = tmp_path / "models"
    root.mkdir()

    # Valid MLX model.
    good = root / "good-mlx"
    good.mkdir()
    (good / "config.json").write_text("{}")
    (good / "model.safetensors").write_bytes(b"")

    # GGUF-only dir (the reported "missing model" case).
    gguf = root / "some-gguf-model"
    gguf.mkdir()
    (gguf / "model.gguf").write_bytes(b"")

    # config.json but no weights.
    no_weights = root / "no-weights"
    no_weights.mkdir()
    (no_weights / "config.json").write_text("{}")

    # Safetensors but no config.json.
    no_config = root / "no-config"
    no_config.mkdir()
    (no_config / "model.safetensors").write_bytes(b"")

    cfg = ModelsCfg(directories=[str(root)], default_model="", aliases={})
    models, skipped = discover_with_skipped(cfg)

    assert {m.id for m in models} == {"good-mlx"}

    by_name = {s.path.name: s.reason for s in skipped}
    assert "GGUF" in by_name["some-gguf-model"]
    assert "no safetensors" in by_name["no-weights"]
    assert "missing config.json" in by_name["no-config"]

    # `discover()` keeps its old shape (models only).
    assert [m.id for m in discover(cfg)] == ["good-mlx"]


def test_discover_with_skipped_reports_unusable_hf_repo(fake_hf_cache):
    """HF cache repos whose snapshots have no weights surface as skipped."""
    cfg = ModelsCfg(directories=[str(fake_hf_cache)], default_model="", aliases={})
    _, skipped = discover_with_skipped(cfg)
    paths = {s.path.name for s in skipped}
    assert "models--someorg--no-weights" in paths
