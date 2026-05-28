from __future__ import annotations

import sys
from typing import Any, Callable

BASE_SYSTEM_PROMPT = (
    "You are the mlx-manager bot, a small on-device assistant embedded in the "
    "mlx-manager CLI — a headless controller for MLX language-model servers on "
    "Apple Silicon. You help the user inspect and fix issues with their local "
    "MLX servers. Be concise and practical. When a server is unhealthy, explain "
    "the likely cause and suggest concrete mlx-manager commands (start, stop, "
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
            "--- current mlx-manager state ---",
            _format_status_block(status_dicts),
            _format_doctor_block(doctor_results),
        ]
    )


_HELP = (
    "commands: /help  /context (show injected state)  /reset (clear history)  "
    "/exit (or Ctrl-D)"
)


def run(
    *,
    model_id: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float,
    on_status: Callable[[str], None] = print,
) -> int:
    """Load *model_id* and run an interactive chat REPL. Returns an exit code."""
    try:
        from mlx_lm import load, stream_generate
        from mlx_lm.sample_utils import make_sampler
    except ImportError:
        on_status("error: mlx_lm is not installed; run `pip install mlx-lm`")
        return 7

    on_status(f"loading bot model {model_id} (first run downloads from Hugging Face)…")
    try:
        model, tokenizer = load(model_id)
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
