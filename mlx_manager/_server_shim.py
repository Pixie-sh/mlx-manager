"""Launch shim: run mlx_lm's server with mlx-manager's tool-call patch applied.

mlx-manager invokes this exactly as it would invoke ``python -m mlx_lm server``,
i.e. ``python <this file> server --model ... --host ... --port ...``. The shim
patches ``mlx_lm.server`` in memory, then hands off to ``mlx_lm.cli.main()`` so
the server behaves identically apart from the patch.

Two patches are applied:

1. Tool-call finish_reason: when a tool call fails to parse (it gets dropped —
   typically because the model was cut off mid-call and the JSON is incomplete),
   force the response's ``finish_reason`` to ``"length"``. Stock mlx_lm logs a
   warning and silently drops the call while still reporting
   ``finish_reason: "stop"``/``"tool_calls"``, so an API client sees a clean turn
   with no tool call and no error signal. With the patch the client gets
   ``length``, the standard OpenAI marker for a cut-off generation, and can react
   instead of flying blind.

2. System-message merge: some clients (notably OpenCode) split their system
   prompt into several consecutive ``system``-role messages. Strict chat
   templates — the Qwen3 family in particular — raise
   ``System message must be at the beginning.`` for any system message past the
   first, which mlx_lm surfaces as an HTTP 404. We collapse consecutive system
   messages into a single leading block before the template runs, so those
   models accept multi-part system prompts. Lenient templates (Gemma, etc.)
   render the merged block identically, so the patch is safe for every model.

This runs as a *script* under the server's interpreter, which need not have
mlx-manager importable — only stdlib and mlx_lm. The patch is best-effort: if
mlx_lm's internals don't match (e.g. a future version renames things), it logs a
warning and the server starts unpatched rather than failing to boot.
"""
from __future__ import annotations

import logging
import sys
import threading

# Per-request flag, isolated per thread (mlx_lm serves on a ThreadingHTTPServer,
# one thread per request). Set when a tool call fails to parse, read when the
# response is assembled — both happen in the same request thread.
_state = threading.local()


def _join_system_content(a, b):
    """Concatenate two system-message ``content`` values.

    Content is usually a plain string (OpenAI chat shape) but may be a list of
    content parts (multimodal). Strings join with a blank line; anything else is
    normalised to a parts list and concatenated so no content is lost.
    """
    if isinstance(a, str) and isinstance(b, str):
        if a and b:
            return a + "\n\n" + b
        return a or b
    la = a if isinstance(a, list) else ([{"type": "text", "text": a}] if a else [])
    lb = b if isinstance(b, list) else ([{"type": "text", "text": b}] if b else [])
    return la + lb


def _merge_system_messages(messages):
    """Collapse runs of consecutive ``system`` messages into a single message.

    Returns a new list; the input is not mutated. Non-system messages and their
    order are preserved exactly. This keeps strict chat templates (Qwen3) from
    raising on a second system message while leaving every other model's render
    unchanged.
    """
    if not isinstance(messages, list):
        return messages
    merged = []
    for msg in messages:
        if (
            isinstance(msg, dict)
            and msg.get("role") == "system"
            and merged
            and isinstance(merged[-1], dict)
            and merged[-1].get("role") == "system"
        ):
            prev = merged[-1]
            merged[-1] = {
                **prev,
                "content": _join_system_content(prev.get("content"), msg.get("content")),
            }
        else:
            merged.append(msg)
    return merged


def _apply_patch() -> None:
    import mlx_lm.server as server_mod

    formatter_cls = getattr(server_mod, "ToolCallFormatter", None)
    handler_cls = getattr(server_mod, "APIHandler", None)
    if formatter_cls is None or handler_cls is None:
        raise AttributeError("mlx_lm.server lacks ToolCallFormatter/APIHandler")
    if not hasattr(handler_cls, "handle_chat_completions"):
        raise AttributeError("mlx_lm.server.APIHandler lacks handle_chat_completions")
    if getattr(formatter_cls, "_mlxmgr_patched", False):
        return

    orig_init = formatter_cls.__init__
    orig_generate_response = handler_cls.generate_response
    orig_handle_chat = handler_cls.handle_chat_completions

    def patched_init(self, *args, **kwargs):
        _state.tool_parse_failed = False
        orig_init(self, *args, **kwargs)
        inner_parser = self._tool_parser

        def guarded_parser(*a, **k):
            try:
                return inner_parser(*a, **k)
            except Exception:
                _state.tool_parse_failed = True
                raise

        self._tool_parser = guarded_parser

    def patched_generate_response(self, text, finish_reason, *args, **kwargs):
        resp = orig_generate_response(self, text, finish_reason, *args, **kwargs)
        # Only the terminal packet carries a finish_reason; leave streaming
        # deltas (finish_reason=None) untouched.
        if finish_reason is not None and getattr(_state, "tool_parse_failed", False):
            for choice in resp.get("choices", []):
                if choice.get("finish_reason") is not None:
                    choice["finish_reason"] = "length"
        return resp

    def patched_handle_chat(self, *args, **kwargs):
        # mlx_lm reads self.body["messages"] inside handle_chat_completions;
        # normalise it first so strict templates accept multi-part system prompts.
        body = getattr(self, "body", None)
        if isinstance(body, dict) and isinstance(body.get("messages"), list):
            body["messages"] = _merge_system_messages(body["messages"])
        return orig_handle_chat(self, *args, **kwargs)

    formatter_cls.__init__ = patched_init
    handler_cls.generate_response = patched_generate_response
    handler_cls.handle_chat_completions = patched_handle_chat
    formatter_cls._mlxmgr_patched = True


def _announce_when_logging_ready(message: str) -> None:
    """Emit *message* right after mlx_lm configures logging, so it lands in the
    server log with the same format. mlx_lm calls ``logging.basicConfig`` once,
    near the end of ``server.main()``; wrap it to fire our line, then restore."""
    orig_basic_config = logging.basicConfig

    def wrapper(*args, **kwargs):
        orig_basic_config(*args, **kwargs)
        logging.basicConfig = orig_basic_config
        logging.getLogger(__name__).info(message)

    logging.basicConfig = wrapper


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv if argv is None else argv)
    try:
        _apply_patch()
        _announce_when_logging_ready(
            "mlx-manager: patches active "
            "(unparseable tool calls report finish_reason=length; "
            "consecutive system messages merged for strict chat templates)"
        )
    except Exception as e:  # never block startup on a patch failure
        logging.getLogger(__name__).warning(
            "mlx-manager: tool-call patch not applied (%s: %s); "
            "server will run unpatched",
            type(e).__name__,
            e,
        )

    # Re-create the argv `python -m mlx_lm <argv[1:]>` would have, then dispatch
    # through mlx_lm's own CLI so subcommand handling stays identical.
    sys.argv = ["mlx_lm", *argv[1:]]
    from mlx_lm import cli

    cli.main()


if __name__ == "__main__":
    main()
