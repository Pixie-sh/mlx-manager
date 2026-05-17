from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlx_manager.providers import (
    ApplyError,
    ProviderContext,
    apply_opencode,
    claude_code_snippet,
    litellm_yaml,
    opencode_snippet,
)


def _ctx() -> ProviderContext:
    return ProviderContext(
        base_url="http://127.0.0.1:8080/v1",
        api_key="mlx-local",
        provider_name="mlx-local",
        model_id="qwen3-8b-4bit",
    )


def test_opencode_merge_snippet_exact_shape():
    out = opencode_snippet(_ctx(), format="merge")
    doc = json.loads(out)
    assert doc == {
        "provider": {
            "mlx-local": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "MLX Local",
                "options": {
                    "baseURL": "http://127.0.0.1:8080/v1",
                    "apiKey": "mlx-local",
                },
                "models": {"qwen3-8b-4bit": {"name": "qwen3-8b-4bit"}},
            }
        }
    }


def test_opencode_full_snippet_includes_schema():
    out = opencode_snippet(_ctx(), format="full")
    doc = json.loads(out)
    assert doc["$schema"] == "https://opencode.ai/config.json"
    assert "provider" in doc


def test_litellm_yaml_pins_format():
    out = litellm_yaml(_ctx())
    assert out == (
        "model_list:\n"
        "  - model_name: mlx-local/qwen3-8b-4bit\n"
        "    litellm_params:\n"
        "      model: openai/qwen3-8b-4bit\n"
        "      api_base: http://127.0.0.1:8080/v1\n"
        "      api_key: mlx-local\n"
    )


def test_apply_creates_file_with_schema(tmp_path):
    target = tmp_path / "opencode.json"
    summary = apply_opencode(_ctx(), target)
    assert "added" in summary
    doc = json.loads(target.read_text())
    assert doc["$schema"] == "https://opencode.ai/config.json"
    assert doc["provider"]["mlx-local"]["options"]["baseURL"] == "http://127.0.0.1:8080/v1"
    assert "qwen3-8b-4bit" in doc["provider"]["mlx-local"]["models"]


def test_apply_merge_preserves_user_per_model_tuning(tmp_path):
    """Without --overwrite, existing model fields like `limit` must survive."""
    target = tmp_path / "opencode.json"
    target.write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "permission": {"edit": "ask"},
                "provider": {
                    "mlx-local": {
                        "npm": "old-package",
                        "name": "stale display",
                        "options": {"baseURL": "http://old:1234/v1", "apiKey": "x"},
                        "models": {
                            "qwen3-8b-4bit": {
                                "name": "Hand tuned name",
                                "limit": {"context": 250000, "output": 8192},
                            }
                        },
                    }
                },
            },
            indent=2,
        )
    )
    summary = apply_opencode(_ctx(), target)
    assert "merged" in summary
    doc = json.loads(target.read_text())
    # Outer keys untouched.
    assert doc["permission"] == {"edit": "ask"}
    prov = doc["provider"]["mlx-local"]
    # mlx-manager-owned fields are refreshed.
    assert prov["npm"] == "@ai-sdk/openai-compatible"
    assert prov["options"]["baseURL"] == "http://127.0.0.1:8080/v1"
    # User-tuned per-model fields survive.
    assert prov["models"]["qwen3-8b-4bit"]["name"] == "Hand tuned name"
    assert prov["models"]["qwen3-8b-4bit"]["limit"] == {"context": 250000, "output": 8192}


def test_apply_overwrite_replaces_provider_block(tmp_path):
    target = tmp_path / "opencode.json"
    target.write_text(
        json.dumps(
            {
                "provider": {
                    "mlx-local": {
                        "npm": "old",
                        "name": "stale",
                        "options": {"baseURL": "http://old", "apiKey": "x"},
                        "models": {"old-model": {"name": "old", "limit": {"output": 1}}},
                    },
                    "other": {"npm": "keep me"},
                }
            }
        )
    )
    summary = apply_opencode(_ctx(), target, overwrite=True)
    assert "overwritten" in summary
    doc = json.loads(target.read_text())
    # Other providers are untouched.
    assert doc["provider"]["other"] == {"npm": "keep me"}
    # Our provider is reset — old-model and its limit are gone.
    assert "old-model" not in doc["provider"]["mlx-local"]["models"]
    assert "qwen3-8b-4bit" in doc["provider"]["mlx-local"]["models"]


def test_apply_writes_backup(tmp_path):
    target = tmp_path / "opencode.json"
    original = {"existing": True, "provider": {}}
    target.write_text(json.dumps(original))
    apply_opencode(_ctx(), target)
    backup = target.with_name(target.name + ".bak")
    assert backup.exists()
    assert json.loads(backup.read_text()) == original


def test_apply_rejects_non_object_top_level(tmp_path):
    target = tmp_path / "opencode.json"
    target.write_text(json.dumps(["not", "an", "object"]))
    with pytest.raises(ApplyError, match="top-level"):
        apply_opencode(_ctx(), target)


def test_apply_rejects_invalid_json(tmp_path):
    target = tmp_path / "opencode.json"
    target.write_text("{ not json")
    with pytest.raises(ApplyError, match="not valid JSON"):
        apply_opencode(_ctx(), target)


def test_claude_code_snippet_marks_experimental_and_recommends_litellm():
    out = claude_code_snippet(_ctx())
    # Experimental label must be present in the env-var section.
    assert "experimental" in out.lower()
    # No ANTHROPIC_BASE_URL leaked (unverified — explicitly forbidden by brief).
    assert "ANTHROPIC_BASE_URL" not in out
    # LiteLLM block must be there and recommended.
    assert "model_list:" in out
    assert "openai/qwen3-8b-4bit" in out
