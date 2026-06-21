from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlx_manager.providers import (
    ApplyError,
    MANAGED_PROVIDER_PREFIX,
    ProviderContext,
    apply_opencode,
    claude_code_snippet,
    managed_provider_name,
    litellm_yaml,
    opencode_snippet,
    reset_opencode,
    warp_snippet,
)


def _ctx() -> ProviderContext:
    return ProviderContext(
        base_url="http://127.0.0.1:8080/v1",
        api_key="mlx-local",
        provider_name="mlx-manager:mlx-local:8080",
        model_id="qwen3-8b-4bit",
    )


def test_opencode_merge_snippet_exact_shape():
    out = opencode_snippet(_ctx(), format="merge")
    doc = json.loads(out)
    assert doc == {
        "provider": {
            "mlx-manager:mlx-local:8080": {
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


def test_opencode_snippet_omits_context_length_when_none():
    out = opencode_snippet(_ctx(), format="merge")
    doc = json.loads(out)
    model_def = doc["provider"]["mlx-manager:mlx-local:8080"]["models"]["qwen3-8b-4bit"]
    assert "contextLength" not in model_def


def test_opencode_snippet_includes_context_length_when_set():
    ctx = ProviderContext(
        base_url="http://127.0.0.1:8080/v1",
        api_key="mlx-local",
        provider_name="mlx-manager:mlx-local:8080",
        model_id="qwen3-8b-4bit",
        context_length=32768,
    )
    out = opencode_snippet(ctx, format="merge")
    doc = json.loads(out)
    model_def = doc["provider"]["mlx-manager:mlx-local:8080"]["models"]["qwen3-8b-4bit"]
    assert model_def["contextLength"] == 32768


def test_managed_provider_name_marks_mlx_manager_entries():
    assert MANAGED_PROVIDER_PREFIX == "mlx-manager:"
    assert managed_provider_name("mlx-local") == "mlx-manager:mlx-local"
    assert managed_provider_name("mlx-manager:mlx-local") == "mlx-manager:mlx-local"


def test_opencode_full_snippet_includes_schema():
    out = opencode_snippet(_ctx(), format="full")
    doc = json.loads(out)
    assert doc["$schema"] == "https://opencode.ai/config.json"
    assert "provider" in doc


def test_litellm_yaml_pins_format():
    out = litellm_yaml(
        ProviderContext(
            base_url="http://127.0.0.1:8080/v1",
            api_key="mlx-local",
            provider_name="mlx-local",
            model_id="qwen3-8b-4bit",
        )
    )
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
    assert doc["provider"]["mlx-manager:mlx-local:8080"]["options"]["baseURL"] == "http://127.0.0.1:8080/v1"
    assert "qwen3-8b-4bit" in doc["provider"]["mlx-manager:mlx-local:8080"]["models"]


def test_apply_merge_preserves_user_per_model_tuning(tmp_path):
    """Without --overwrite, existing model fields like `limit` must survive."""
    target = tmp_path / "opencode.json"
    target.write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "permission": {"edit": "ask"},
                "provider": {
                    "mlx-manager:mlx-local:8080": {
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
    prov = doc["provider"]["mlx-manager:mlx-local:8080"]
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
                    "mlx-manager:mlx-local:8080": {
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
    assert "old-model" not in doc["provider"]["mlx-manager:mlx-local:8080"]["models"]
    assert "qwen3-8b-4bit" in doc["provider"]["mlx-manager:mlx-local:8080"]["models"]


def test_apply_writes_backup(tmp_path):
    target = tmp_path / "opencode.json"
    original = {"existing": True, "provider": {}}
    target.write_text(json.dumps(original))
    apply_opencode(_ctx(), target)
    backup = target.with_name(target.name + ".bak")
    assert backup.exists()
    assert json.loads(backup.read_text()) == original


def test_apply_migrates_matching_legacy_bare_key(tmp_path):
    target = tmp_path / "opencode.json"
    ctx = _ctx()  # provider_name == "mlx-manager:mlx-local:8080", base_url 8080.
    target.write_text(
        json.dumps(
            {
                "provider": {
                    "mlx-local": {
                        "npm": "@ai-sdk/openai-compatible",
                        "name": "MLX Local",
                        "options": {
                            "baseURL": ctx.base_url,
                            "apiKey": "stale",
                        },
                        "models": {"qwen3-8b-4bit": {"name": "qwen3-8b-4bit"}},
                    },
                    "anthropic": {"npm": "keep"},
                },
            }
        )
    )
    summary = apply_opencode(ctx, target)
    doc = json.loads(target.read_text())
    assert "mlx-local" not in doc["provider"]
    assert "mlx-manager:mlx-local:8080" in doc["provider"]
    assert doc["provider"]["anthropic"] == {"npm": "keep"}
    assert "migrated" in summary


def test_apply_preserves_unrelated_legacy_bare_key(tmp_path):
    target = tmp_path / "opencode.json"
    ctx = _ctx()  # base_url == http://127.0.0.1:8080/v1
    target.write_text(
        json.dumps(
            {
                "provider": {
                    # User-curated `mlx-local` pointing at a different backend
                    # (e.g. LiteLLM): must survive an --apply.
                    "mlx-local": {
                        "npm": "@ai-sdk/openai-compatible",
                        "name": "LiteLLM",
                        "options": {
                            "baseURL": "http://localhost:9999/v1",
                            "apiKey": "keep",
                        },
                        "models": {"some-model": {"name": "some-model"}},
                    },
                },
            }
        )
    )
    summary = apply_opencode(ctx, target)
    doc = json.loads(target.read_text())
    assert "mlx-local" in doc["provider"]
    assert doc["provider"]["mlx-local"]["options"]["baseURL"] == "http://localhost:9999/v1"
    assert "mlx-manager:mlx-local:8080" in doc["provider"]
    assert "migrated" not in summary


def test_reset_removes_only_mlx_manager_providers(tmp_path):
    target = tmp_path / "opencode.json"
    target.write_text(
        json.dumps(
            {
                "provider": {
                    "mlx-manager:mlx-local:8080": {"npm": "remove"},
                    "mlx-manager:mlx-local@studio:8081": {"npm": "remove too"},
                    "mlx-local": {"npm": "keep"},
                    "anthropic": {"npm": "keep"},
                },
                "permission": {"edit": "ask"},
            }
        )
    )
    summary = reset_opencode(target)
    assert "2 mlx-manager provider(s) removed" in summary
    doc = json.loads(target.read_text())
    assert doc["provider"] == {
        "mlx-local": {"npm": "keep"},
        "anthropic": {"npm": "keep"},
    }
    assert doc["permission"] == {"edit": "ask"}


def test_reset_is_idempotent(tmp_path):
    target = tmp_path / "opencode.json"
    original = {"provider": {"anthropic": {"npm": "keep"}}}
    target.write_text(json.dumps(original))
    summary = reset_opencode(target)
    assert "0 mlx-manager provider(s) removed" in summary
    assert json.loads(target.read_text()) == original


def test_reset_skips_backup_when_no_managed_providers(tmp_path):
    target = tmp_path / "opencode.json"
    original = {"provider": {"anthropic": {"npm": "keep"}}}
    target.write_text(json.dumps(original))
    reset_opencode(target)
    # No managed providers to remove → reset is a no-op and must not touch disk.
    assert not target.with_name(target.name + ".bak").exists()


def test_reset_writes_backup_when_managed_providers_removed(tmp_path):
    target = tmp_path / "opencode.json"
    original = {
        "provider": {
            "mlx-manager:mlx-local:8080": {"npm": "remove"},
            "anthropic": {"npm": "keep"},
        }
    }
    target.write_text(json.dumps(original))
    reset_opencode(target)
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


def test_warp_snippet_emits_manual_byok_fields():
    out = warp_snippet(_ctx())
    assert out == (
        "# WARP Terminal custom AI provider\n"
        "# Paste these values into WARP's BYOK/custom provider settings.\n"
        "Provider type: OpenAI-compatible\n"
        "Provider name: mlx-manager:mlx-local:8080\n"
        "Base URL: http://127.0.0.1:8080/v1\n"
        "API key: mlx-local\n"
        "Model: qwen3-8b-4bit\n"
    )


def test_warp_snippet_includes_context_length_when_set():
    ctx = ProviderContext(
        base_url="http://127.0.0.1:8080/v1",
        api_key="dummy-key",
        provider_name="mlx-local",
        model_id="qwen3-8b-4bit",
        context_length=32768,
    )
    out = warp_snippet(ctx)
    assert "Context length: 32768" in out
