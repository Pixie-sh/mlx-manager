from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from mlxer.paths import ensure_dir, expand

BASE_SYSTEM_PROMPT = (
    "You are the mlxer bot, a small on-device assistant embedded in the "
    "mlxer CLI — a headless controller for MLX language-model servers on "
    "Apple Silicon. You help the user inspect and fix issues with their local "
    "MLX servers. Be concise and practical. When a server is unhealthy, explain "
    "the likely cause and suggest concrete mlxer commands (start, stop, "
    "restart, switch, status, logs, doctor, list, info) to resolve it. Prefer "
    "short answers. If you are unsure, say so rather than inventing details."
)


def _format_status_block(status_dicts: list[dict[str, Any]]) -> str:
    if not status_dicts:
        return "Running servers: none."
    lines = ["Running servers:"]
    for d in status_dicts:
        if not d.get("running"):
            lines.append(
                f"  - port {d.get('port')}: STALE (last model {d.get('model_alias')})"
            )
            continue
        health = d.get("health", "ok")
        h = "ok" if health == "ok" else f"ERROR — {d.get('health_detail', '')}"
        endpoint = "ok" if d.get("endpoint_ok") else "unreachable"
        lines.append(
            f"  - port {d.get('port')}: model {d.get('model_alias')}, "
            f"endpoint {endpoint}, health {h}"
        )
    return "\n".join(lines)


def _format_doctor_block(doctor_results: list[dict[str, Any]]) -> str:
    notable = [r for r in doctor_results if r.get("status") in ("FAIL", "WARN")]
    if not notable:
        return "Doctor: all checks OK."
    order = {"FAIL": 0, "WARN": 1}
    notable.sort(key=lambda r: order.get(r.get("status", ""), 9))
    lines = ["Doctor findings:"]
    for r in notable:
        lines.append(f"  - [{r['status']}] {r['name']}: {r['detail']}")
    return "\n".join(lines)


def build_system_prompt(
    status_dicts: list[dict[str, Any]],
    doctor_results: list[dict[str, Any]],
    *,
    with_context: bool = True,
) -> str:
    """Assemble the bot system prompt, optionally embedding live setup state."""
    if not with_context:
        return BASE_SYSTEM_PROMPT
    return "\n\n".join(
        [
            BASE_SYSTEM_PROMPT,
            "--- current mlxer state ---",
            _format_status_block(status_dicts),
            _format_doctor_block(doctor_results),
        ]
    )


_HELP = (
    "commands: /help  /context (show injected state)  /reset (clear history)  "
    "/exit (or .exit) (or Ctrl-D)"
)

# Curated lightweight, instruction-tuned MLX models offered on first run. All
# are 4-bit and small enough to run comfortably on Apple Silicon while still
# being capable enough to reason about logs and config. The first entry is the
# default highlighted choice.
BOT_MODELS: list[dict[str, str]] = [
    {
        "id": "mlx-community/gemma-4-e2b-it-4bit",
        "label": "Gemma 4 E2B",
        "size": "~1.5 GB",
        "note": "Google Gemma 4, great quality for its size",
    },
    {
        "id": "mlx-community/Qwen3-1.7B-4bit",
        "label": "Qwen3 1.7B",
        "size": "~1.0 GB",
        "note": "smallest/fastest, punches above its weight on reasoning",
    },
    {
        "id": "mlx-community/Llama-3.2-3B-Instruct-4bit",
        "label": "Llama 3.2 3B",
        "size": "~1.8 GB",
        "note": "well-rounded, very widely used",
    },
    {
        "id": "mlx-community/Ministral-3-3B-Instruct-2512-4bit",
        "label": "Ministral 3B",
        "size": "~1.8 GB",
        "note": "recent Mistral small, agentic-leaning",
    },
    {
        "id": "mlx-community/gemma-4-e4b-it-4bit",
        "label": "Gemma 4 E4B",
        "size": "~2.8 GB",
        "note": "smartest small Gemma, heavier download",
    },
]


def _selection_path(cache_dir: str) -> Path:
    return expand(cache_dir) / "selected_model"


def load_selection(cache_dir: str) -> str | None:
    """Return the previously chosen bot model id, or None if never chosen."""
    p = _selection_path(cache_dir)
    if not p.is_file():
        return None
    text = p.read_text(encoding="utf-8").strip()
    return text or None


def save_selection(cache_dir: str, model_id: str) -> None:
    ensure_dir(expand(cache_dir))
    _selection_path(cache_dir).write_text(model_id + "\n", encoding="utf-8")


def choose_model(
    default_id: str,
    *,
    input_fn: Callable[[str], str] = input,
    out_fn: Callable[[str], None] = print,
) -> str:
    """Render the first-run menu and return the chosen model id.

    Default options come from BOT_MODELS, with *default_id* highlighted. An
    empty answer picks the default; an unrecognized answer is treated as a
    custom Hugging Face repo id.
    """
    default_idx = next(
        (i for i, m in enumerate(BOT_MODELS) if m["id"] == default_id), 0
    )
    out_fn("Pick a bot model (downloaded once, then remembered):")
    for i, m in enumerate(BOT_MODELS, start=1):
        marker = " (default)" if (i - 1) == default_idx else ""
        out_fn(f"  {i}. {m['label']:<14} {m['size']:<9} — {m['note']}{marker}")
    out_fn("  or paste any Hugging Face repo id or local model path")
    answer = input_fn(f"choice [1-{len(BOT_MODELS)}, default {default_idx + 1}]: ").strip()
    if not answer:
        return BOT_MODELS[default_idx]["id"]
    if answer.isdigit():
        n = int(answer)
        if 1 <= n <= len(BOT_MODELS):
            return BOT_MODELS[n - 1]["id"]
    return answer


def select_model(
    model_override: str | None,
    default_id: str,
    cache_dir: str,
) -> str | None:
    """Decide which model to use without prompting.

    Returns the resolved model id, or None when a first-run prompt is needed.
    Precedence: explicit override → saved selection → default if already
    downloaded. None signals the caller to run the interactive picker.
    """
    if model_override:
        return model_override
    saved = load_selection(cache_dir)
    if saved:
        return saved
    default_dir = expand(cache_dir) / default_id.replace("/", "--")
    if _model_complete(default_dir):
        return default_id
    return None


def _model_complete(path: Path) -> bool:
    """True if *path* holds a loadable model (config.json + weights)."""
    if not (path / "config.json").is_file():
        return False
    return any(path.glob("*.safetensors"))


def resolve_model(
    model_id: str,
    cache_dir: str,
    *,
    on_status: Callable[[str], None] = print,
) -> str:
    """Return a local directory path for *model_id*, downloading it once.

    - If *model_id* is already a local directory with weights, use it as-is.
    - Otherwise treat it as a Hugging Face repo id and materialize it under
      *cache_dir*/<org--name>. If those files already exist, reuse them with no
      network access; otherwise download the snapshot once.
    """
    direct = expand(model_id)
    if direct.is_dir() and _model_complete(direct):
        return str(direct)

    target = expand(cache_dir) / model_id.replace("/", "--")
    if _model_complete(target):
        return str(target)

    ensure_dir(target.parent)
    on_status(f"downloading {model_id} → {target} (one-time)…")
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=model_id, local_dir=str(target))
    return str(target)


def run(
    *,
    model_override: str | None,
    default_model: str,
    cache_dir: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float,
    force_choose: bool = False,
    on_status: Callable[[str], None] = print,
) -> int:
    """Pick/resolve a bot model into *cache_dir*, load it, and run a chat REPL.

    Returns an exit code.
    """
    try:
        from mlx_lm import load, stream_generate
        from mlx_lm.sample_utils import make_sampler
    except ImportError:
        on_status(
            "error: mlx_lm is not importable in this environment (the bot runs "
            "it in-process). Run `mlxer doctor --fix` to install it here."
        )
        return 7

    model_id = None if force_choose and not model_override else select_model(
        model_override, default_model, cache_dir
    )
    if model_id is None:
        if sys.stdin.isatty():
            model_id = choose_model(default_model)
            save_selection(cache_dir, model_id)
        else:
            model_id = default_model

    try:
        local_path = resolve_model(model_id, cache_dir, on_status=on_status)
    except Exception as e:  # noqa: BLE001 — surface any download failure
        on_status(f"error: could not fetch bot model {model_id!r}: {e}")
        return 1

    on_status(f"loading bot model from {local_path}…")
    try:
        model, tokenizer = load(local_path)
    except Exception as e:  # noqa: BLE001 — surface any load failure to the user
        on_status(f"error: could not load bot model {model_id!r}: {e}")
        return 1

    sampler = make_sampler(temp=temperature)
    history: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    on_status(f"ready — chatting with {model_id}. {_HELP}")

    while True:
        try:
            user = input("\n\033[1myou ›\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not user:
            continue
        if user in ("/exit", "/quit"):
            return 0
        if user == "/help":
            on_status(_HELP)
            continue
        if user == "/context":
            on_status(system_prompt)
            continue
        if user == "/reset":
            history = [{"role": "system", "content": system_prompt}]
            on_status("history cleared.")
            continue

        history.append({"role": "user", "content": user})
        prompt = tokenizer.apply_chat_template(
            history, add_generation_prompt=True
        )

        sys.stdout.write("\033[1mbot ›\033[0m ")
        sys.stdout.flush()
        reply_parts: list[str] = []
        try:
            for resp in stream_generate(
                model,
                tokenizer,
                prompt,
                max_tokens=max_tokens,
                sampler=sampler,
            ):
                sys.stdout.write(resp.text)
                sys.stdout.flush()
                reply_parts.append(resp.text)
        except KeyboardInterrupt:
            print("\n(interrupted)")
        print()
        history.append({"role": "assistant", "content": "".join(reply_parts)})
