from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MANAGED_PROVIDER_PREFIX = "mlx-manager:"


@dataclass(frozen=True)
class ProviderContext:
    """Inputs needed to render a provider snippet."""

    base_url: str
    api_key: str
    provider_name: str
    model_id: str
    context_length: int | None = None


class ApplyError(Exception):
    """Raised when applying a snippet to a config file fails."""


def managed_provider_name(provider_name: str) -> str:
    """Return the OpenCode provider key reserved for mlx-manager entries."""
    if provider_name.startswith(MANAGED_PROVIDER_PREFIX):
        return provider_name
    return f"{MANAGED_PROVIDER_PREFIX}{provider_name}"


def is_managed_provider_name(provider_name: str) -> bool:
    """Return True when *provider_name* is an mlx-manager managed provider key."""
    return provider_name.startswith(MANAGED_PROVIDER_PREFIX)


def _legacy_provider_candidates(managed_name: str) -> list[str]:
    """Return possible pre-`mlx-manager:` keys that this managed name replaces.

    ``"mlx-manager:mlx-local:8080"`` → ``["mlx-local:8080", "mlx-local"]``.
    Used by :func:`apply_opencode` to migrate users who already had a bare
    ``mlx-local`` provider block pointing at our server. The trailing port form
    is included first so callers can match against the most specific candidate.
    """
    if not managed_name.startswith(MANAGED_PROVIDER_PREFIX):
        return []
    stripped = managed_name[len(MANAGED_PROVIDER_PREFIX):]
    candidates = [stripped]
    head, sep, tail = stripped.rpartition(":")
    if sep and head and tail.isdigit():
        candidates.append(head)
    return candidates


def _opencode_provider_block(ctx: ProviderContext) -> dict:
    model_def: dict = {"name": ctx.model_id}
    if ctx.context_length:
        model_def["contextLength"] = ctx.context_length
    return {
        ctx.provider_name: {
            "npm": "@ai-sdk/openai-compatible",
            "name": "MLX Local",
            "options": {
                "baseURL": ctx.base_url,
                "apiKey": ctx.api_key,
            },
            "models": {
                ctx.model_id: model_def,
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
        # Migrate any pre-`mlx-manager:` block that points at the same backend.
        # The baseURL fingerprint check protects users who manually curated a
        # `mlx-local` provider against a different server.
        for legacy in _legacy_provider_candidates(c.provider_name):
            existing_legacy = providers.get(legacy)
            if (
                isinstance(existing_legacy, dict)
                and existing_legacy.get("options", {}).get("baseURL") == c.base_url
            ):
                del providers[legacy]
                actions.append(f"{legacy!r} migrated")

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


def reset_opencode(target: Path) -> str:
    """Remove mlx-manager managed OpenCode provider entries from *target*."""
    target = Path(target)
    if not target.exists():
        return f"no OpenCode config found at {target}"
    try:
        with open(target, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except json.JSONDecodeError as e:
        raise ApplyError(f"{target} is not valid JSON: {e}") from e
    if not isinstance(doc, dict):
        raise ApplyError(f"{target} top-level must be a JSON object")

    providers = doc.get("provider", {})
    if not isinstance(providers, dict):
        raise ApplyError("`provider` key exists but is not a JSON object")

    removed = [name for name in providers if is_managed_provider_name(name)]
    if not removed:
        return f"0 mlx-manager provider(s) removed from {target}"

    for name in removed:
        del providers[name]

    backup = target.with_name(target.name + ".bak")
    shutil.copy2(target, backup)
    tmp = target.with_name(target.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    os.replace(tmp, target)
    return f"{len(removed)} mlx-manager provider(s) removed from {target}"


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


def warp_snippet(ctx: ProviderContext) -> str:
    """Return WARP Terminal BYOK/custom-provider setup values.

    WARP's AI provider file format is not stable enough to mutate directly here,
    so this emits deterministic fields for the WARP settings UI instead.
    """
    lines = [
        "# WARP Terminal custom AI provider",
        "# Paste these values into WARP's BYOK/custom provider settings.",
        "Provider type: OpenAI-compatible",
        f"Provider name: {ctx.provider_name}",
        f"Base URL: {ctx.base_url}",
        f"API key: {ctx.api_key}",
        f"Model: {ctx.model_id}",
    ]
    if ctx.context_length:
        lines.append(f"Context length: {ctx.context_length}")
    return "\n".join(lines) + "\n"
