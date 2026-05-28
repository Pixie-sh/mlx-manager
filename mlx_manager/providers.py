from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderContext:
    """Inputs needed to render a provider snippet."""

    base_url: str
    api_key: str
    provider_name: str
    model_id: str


class ApplyError(Exception):
    """Raised when applying a snippet to a config file fails."""


def _opencode_provider_block(ctx: ProviderContext) -> dict:
    return {
        ctx.provider_name: {
            "npm": "@ai-sdk/openai-compatible",
            "name": "MLX Local",
            "options": {
                "baseURL": ctx.base_url,
                "apiKey": ctx.api_key,
            },
            "models": {
                ctx.model_id: {"name": ctx.model_id},
            },
        }
    }


def opencode_snippet(ctx: ProviderContext | list[ProviderContext], *, format: str = "merge") -> str:
    """Return a JSON snippet for OpenCode.

    ``merge`` form (default): just the ``provider`` map, suitable for merging
    into an existing ``opencode.json``. ``full`` form wraps it in a complete
    ``opencode.json``-shaped document with the public ``$schema`` reference.

    *ctx* may be a single :class:`ProviderContext` or a list; when a list is
    given all provider blocks are merged into one ``provider`` map.
    """
    if format not in ("merge", "full"):
        raise ValueError(f"format must be 'merge' or 'full' (got {format!r})")
    if isinstance(ctx, list):
        merged: dict = {}
        for c in ctx:
            merged.update(_opencode_provider_block(c))
        inner = {"provider": merged}
    else:
        inner = {"provider": _opencode_provider_block(ctx)}
    if format == "full":
        doc = {"$schema": "https://opencode.ai/config.json", **inner}
    else:
        doc = inner
    return json.dumps(doc, indent=2, sort_keys=False) + "\n"


def _merge_opencode_provider(existing: dict, new_block: dict) -> dict:
    """Merge *new_block* into *existing*, preserving user-tuned per-model fields.

    - ``npm``, ``name``, ``options`` are refreshed from *new_block* (these are
      the bits mlx-manager owns).
    - ``models`` is union'd: model ids only present in *new_block* are added;
      model ids already present keep their existing definition entirely
      (so hand-tuned ``limit``, ``name`` overrides, etc. survive).
    - Any other top-level keys the user added under the provider are preserved.
    """
    out: dict[str, Any] = dict(existing)
    out["npm"] = new_block["npm"]
    out["name"] = new_block["name"]
    out["options"] = new_block["options"]
    existing_models = dict(out.get("models", {}))
    for mid, mdef in new_block.get("models", {}).items():
        existing_models.setdefault(mid, mdef)
    out["models"] = existing_models
    return out


def apply_opencode(
    ctx: ProviderContext | list[ProviderContext], target: Path, *, overwrite: bool = False
) -> str:
    """Write the OpenCode provider block(s) into *target*.

    *ctx* may be a single :class:`ProviderContext` or a list (one entry per
    running server). Returns a summary string. Always writes a sibling
    ``<target>.bak`` before replacing the file. The write is atomic.
    """
    contexts = ctx if isinstance(ctx, list) else [ctx]
    target = Path(target)
    if target.exists():
        try:
            with open(target, "r", encoding="utf-8") as f:
                doc = json.load(f)
        except json.JSONDecodeError as e:
            raise ApplyError(f"{target} is not valid JSON: {e}") from e
        if not isinstance(doc, dict):
            raise ApplyError(f"{target} top-level must be a JSON object")
        backup = target.with_name(target.name + ".bak")
        shutil.copy2(target, backup)
    else:
        doc = {"$schema": "https://opencode.ai/config.json"}

    providers = doc.setdefault("provider", {})
    if not isinstance(providers, dict):
        raise ApplyError("`provider` key exists but is not a JSON object")

    actions: list[str] = []
    for c in contexts:
        new_block = _opencode_provider_block(c)[c.provider_name]
        existing = providers.get(c.provider_name)
        if existing is None:
            providers[c.provider_name] = new_block
            actions.append(f"{c.provider_name!r} added")
        elif overwrite:
            providers[c.provider_name] = new_block
            actions.append(f"{c.provider_name!r} overwritten")
        else:
            providers[c.provider_name] = _merge_opencode_provider(existing, new_block)
            actions.append(f"{c.provider_name!r} merged")

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    os.replace(tmp, target)
    return f"{', '.join(actions)} in {target}"


def claude_code_experimental_env(ctx: ProviderContext) -> str:
    """Return a shell snippet that sets OpenAI-compatible env vars.

    This is labeled experimental because Claude Code's stable surface does not
    currently document OpenAI-compatible base-URL routing; verify against your
    Claude Code version before relying on it. Notably, ``ANTHROPIC_BASE_URL``
    is intentionally omitted.
    """
    lines = [
        "# experimental — verify against your Claude Code version",
        f'export OPENAI_API_KEY="{ctx.api_key}"',
        f'export OPENAI_BASE_URL="{ctx.base_url}"',
    ]
    return "\n".join(lines) + "\n"


def litellm_yaml(ctx: ProviderContext) -> str:
    """Return a minimal LiteLLM ``model_list`` YAML.

    Hand-rolled to avoid pulling in PyYAML; the surface is small enough that
    the exact format is stable.
    """
    return (
        "model_list:\n"
        f"  - model_name: {ctx.provider_name}/{ctx.model_id}\n"
        "    litellm_params:\n"
        f"      model: openai/{ctx.model_id}\n"
        f"      api_base: {ctx.base_url}\n"
        f"      api_key: {ctx.api_key}\n"
    )


def claude_code_snippet(ctx: ProviderContext) -> str:
    """Return the combined Claude Code guidance: experimental env + LiteLLM fallback.

    The LiteLLM block is presented as the recommended path; the env-var block
    is offered for users who have already confirmed support on their setup.
    """
    parts = [
        "# Claude Code does not currently document OpenAI-compatible routing.",
        "# Recommended path: run LiteLLM in front of MLX, then point Claude",
        "# Code at LiteLLM (see README, 'Using with Claude Code').",
        "",
        "# --- LiteLLM config.yaml ---",
        litellm_yaml(ctx).rstrip(),
        "",
        "# --- Experimental: direct env vars (verify on your Claude Code build) ---",
        claude_code_experimental_env(ctx).rstrip(),
    ]
    return "\n".join(parts) + "\n"
