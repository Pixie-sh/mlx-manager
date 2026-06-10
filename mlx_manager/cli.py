from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

from mlx_manager import __version__
from mlx_manager import benchmark as bench
from mlx_manager import bot as bot_mod
from mlx_manager.config import (
    Config,
    ConfigError,
    DEFAULT_CONFIG_PATH,
    load,
    update_value,
)
from mlx_manager.context import model_memory_plan, wired_limit_mb
from mlx_manager.models import Model, discover, discover_with_skipped, resolve
from mlx_manager.paths import ensure_parent, expand
from mlx_manager.providers import (
    ApplyError,
    ProviderContext,
    apply_opencode,
    claude_code_snippet,
    managed_provider_name,
    opencode_snippet,
    reset_opencode,
)
from mlx_manager import server as srv


EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_USAGE = 2
EXIT_CONFIG = 3
EXIT_NOT_RUNNING = 4
EXIT_ALREADY_RUNNING = 5
EXIT_STARTUP_TIMEOUT = 6
EXIT_MLX_LM_MISSING = 7

# Canonical TCP port range — mirrors config.py:_validate (server.port).
_PORT_MIN = 1024
_PORT_MAX = 65535

# Default OpenCode config path used by ``start --update-opencode`` (and friends)
# when ``--opencode-target`` is not supplied. Mirrors the default in the
# ``config opencode --target`` flag so the two surfaces stay in sync.
_DEFAULT_OPENCODE_TARGET = "~/.config/opencode/opencode.json"


def _opencode_lock_path(target: Path) -> Path:
    """Return the fcntl lock path used to serialize OpenCode config writes."""
    target = Path(target)
    return target.with_name(target.name + ".lock")


def _add_update_opencode_flags(sp: argparse.ArgumentParser) -> None:
    """Add the shared `--update-opencode` / `--overwrite` / `--opencode-target` flags."""
    sp.add_argument("--update-opencode", action="store_true", help="apply OpenCode provider config after start")
    sp.add_argument("--overwrite", action="store_true", help="replace provider block instead of merging (with --update-opencode)")
    sp.add_argument(
        "--opencode-target",
        default=_DEFAULT_OPENCODE_TARGET,
        help=f"OpenCode config path to update (default: {_DEFAULT_OPENCODE_TARGET})",
    )


def _port_arg(s: str) -> int:
    """argparse type: accept a TCP port string in ``[_PORT_MIN, _PORT_MAX]``."""
    try:
        port = int(s)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"port must be an integer between {_PORT_MIN} and {_PORT_MAX} (got {s!r})"
        )
    if not (_PORT_MIN <= port <= _PORT_MAX):
        raise argparse.ArgumentTypeError(
            f"port must be between {_PORT_MIN} and {_PORT_MAX} (got {port})"
        )
    return port


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _vprint(msg: str, verbose: bool = False) -> None:
    """Print to stderr only when *verbose* is enabled."""
    if verbose:
        _eprint(f"verbose: {msg}")


def _human_size(n: int) -> str:
    """Format a byte count as a human-readable string."""
    if n < 1000:
        return f"{n}B"
    elif n < 1000**2:
        return f"{n/1000:.0f}KB"
    elif n < 1000**3:
        return f"{n/1000**2:.1f}MB"
    elif n < 1000**4:
        return f"{n/1000**3:.1f}GB"
    return f"{n/1000**4:.1f}TB"


def _lan_ip() -> str | None:
    """Return this machine's LAN IP address, or None if unavailable.

    Uses a non-blocking socket connection to detect the outgoing interface.
    Falls back to ``socket.gethostbyname(socket.gethostname())``.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setblocking(False)
        # Connect to a non-routable address to discover the local interface.
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        # Skip loopback.
        if ip != "127.0.0.1":
            return ip
    except OSError:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip != "127.0.0.1":
            return ip
    except OSError:
        pass
    return None


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mlx-manager",
        description="Headless controller for the MLX HTTP server.",
    )
    p.add_argument("--version", action="version", version=f"mlx-manager {__version__}")
    p.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="path to config TOML")
    p.add_argument("--verbose", action="store_true", help="enable verbose logging to stderr")

    sub = p.add_subparsers(dest="cmd", metavar="<command>")
    sub.required = True

    sp = sub.add_parser("list", help="show discovered models")
    sp.add_argument("--json", action="store_true", dest="as_json")

    sp = sub.add_parser("start", help="start the MLX server")
    sp.add_argument("--model", help="model id, alias, or absolute path")
    sp.add_argument("--host", help="override server host")
    sp.add_argument("--port", type=_port_arg, help="override server port")
    sp.add_argument("--replace", action="store_true", help="stop running server first")
    sp.add_argument("--choose", action="store_true", help="pick model, host, and port interactively")
    sp.add_argument("--bind-all", action="store_true", help="bind on 0.0.0.0 (insecure)")
    sp.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        metavar="KEY=VAL",
        help="forward extra flag to mlx_lm server (repeatable)",
    )
    _add_update_opencode_flags(sp)

    sp = sub.add_parser("load", help="guided start from the discovered local model list")
    sp.add_argument("--host", help="override server host")
    sp.add_argument("--port", type=_port_arg, help="override server port")
    sp.add_argument("--replace", action="store_true", help="stop running server first")
    sp.add_argument("--bind-all", action="store_true", help="bind on 0.0.0.0 (insecure)")
    sp.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        metavar="KEY=VAL",
        help="forward extra flag to mlx_lm server (repeatable)",
    )
    _add_update_opencode_flags(sp)

    sp = sub.add_parser("stop", help="stop the managed server")
    sp.add_argument("--port", type=_port_arg, help="port of server to stop (required when multiple are running)")
    sp.add_argument("--timeout", type=int, help="seconds to wait for SIGTERM before SIGKILL")

    sp = sub.add_parser("restart", help="stop then start the server")
    sp.add_argument("--model", help="model id, alias, or absolute path")
    sp.add_argument("--host")
    sp.add_argument("--port", type=_port_arg)
    sp.add_argument("--bind-all", action="store_true")
    sp.add_argument("--extra-arg", action="append", default=[], metavar="KEY=VAL")
    _add_update_opencode_flags(sp)

    sp = sub.add_parser("switch", help="swap running server to a different model")
    sp.add_argument("model", help="new model id, alias, or absolute path")
    sp.add_argument("--host", help="override server host")
    sp.add_argument("--port", type=_port_arg, help="override server port")
    sp.add_argument("--bind-all", action="store_true", help="bind on 0.0.0.0 (insecure)")
    sp.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        metavar="KEY=VAL",
        help="forward extra flag to mlx_lm server (repeatable)",
    )
    _add_update_opencode_flags(sp)

    sp = sub.add_parser("status", help="report server state")
    sp.add_argument("--port", type=_port_arg, help="show status for a specific port only")
    sp.add_argument("--json", action="store_true", dest="as_json")

    sp = sub.add_parser("logs", help="tail server log")
    sp.add_argument("--port", type=_port_arg, help="port of server whose log to tail (required when multiple are running)")
    sp.add_argument("--tail", type=int, default=100)
    sp.add_argument("-f", "--follow", action="store_true")

    sp = sub.add_parser("info", help="show model metadata (weights, config.json)")
    sp.add_argument("model", help="model id, alias, or absolute path")
    sp.add_argument("--json", action="store_true", dest="as_json")

    cfg_sp = sub.add_parser("config", help="config & provider snippet helpers")
    cfg_sub = cfg_sp.add_subparsers(dest="config_cmd", metavar="<subcommand>")
    cfg_sub.required = True

    oc = cfg_sub.add_parser("opencode", help="emit OpenCode provider snippet")
    oc.add_argument("--model", help="model id (default: running server, then [models].default_model)")
    oc.add_argument("--format", choices=["merge", "full"], default="merge")
    oc.add_argument(
        "--apply",
        action="store_true",
        help="write into the OpenCode config file instead of stdout",
    )
    oc.add_argument(
        "--target",
        default=_DEFAULT_OPENCODE_TARGET,
        help=f"OpenCode config path (used with --apply or --reset; default: {_DEFAULT_OPENCODE_TARGET})",
    )
    oc.add_argument(
        "--overwrite",
        action="store_true",
        help="replace the entire provider block instead of merging (only used with --apply)",
    )
    oc.add_argument(
        "--reset",
        action="store_true",
        help="remove mlx-manager-managed provider blocks from the OpenCode config and exit",
    )
    oc.add_argument(
        "--remote",
        action="store_true",
        help="use LAN IP instead of localhost in emitted config (for remote clients)",
    )
    oc.add_argument(
        "--choose",
        action="store_true",
        help="prompt for target path, merge/overwrite, and Claude Code snippet (implies --apply)",
    )

    cc = cfg_sub.add_parser("claude-code", help="emit Claude Code / LiteLLM snippet")
    cc.add_argument("--model")
    cc.add_argument(
        "--remote",
        action="store_true",
        help="use LAN IP instead of localhost in emitted config (for remote clients)",
    )

    ss = cfg_sub.add_parser("show", help="display current effective config values")
    ss.add_argument("--json", action="store_true", dest="as_json")

    ed = cfg_sub.add_parser("edit", help="open config.toml in $EDITOR")
    ed.add_argument(
        "--editor",
        help="editor command (default: $EDITOR env var, fallback: vim)",
    )

    sp = sub.add_parser("doctor", help="run diagnostics")
    sp.add_argument("--json", action="store_true", dest="as_json")
    sp.add_argument(
        "--fix",
        action="store_true",
        help="attempt to fix issues (install mlx_lm for the bot, create missing dirs)",
    )

    sp = sub.add_parser(
        "bot", help="chat with a small on-device LLM about your MLX setup"
    )
    sp.add_argument("--model", help="override the bot model (default: [bot].model)")
    sp.add_argument(
        "--choose",
        action="store_true",
        help="re-pick the bot model from the menu (ignores the saved selection)",
    )
    sp.add_argument(
        "--max-tokens", type=int, help="max tokens per reply (default: [bot].max_tokens)"
    )
    sp.add_argument(
        "--temperature", type=float, help="sampling temperature (default: [bot].temperature)"
    )
    sp.add_argument(
        "--no-context",
        action="store_true",
        help="skip injecting live server/doctor state into the system prompt",
    )

    sp = sub.add_parser(
        "benchmark", help="measure TTFT, decode tok/s, and aggregate throughput"
    )
    sp.add_argument(
        "--model",
        help="model id (default: running server's model, then [models].default_model)",
    )
    sp.add_argument(
        "--endpoint",
        help="server base URL (default: running server, else [providers].base_url)",
    )
    sp.add_argument(
        "--prompt", help="prompt text (default: a built-in generation-bound prompt)"
    )
    sp.add_argument(
        "--prompt-file", help="read prompt from this file instead of --prompt"
    )
    sp.add_argument("--max-tokens", type=int, default=256)
    sp.add_argument("--requests", type=int, default=5)
    sp.add_argument("--concurrency", type=int, default=1)
    sp.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="sequential pre-runs that don't count toward the measurement",
    )
    sp.add_argument(
        "--json", action="store_true", dest="as_json", help="emit results as JSON"
    )
    sp.add_argument(
        "--save",
        metavar="FILE",
        help="save benchmark results to FILE (JSON)",
    )

    return p


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_list(cfg: Config, args: argparse.Namespace) -> int:
    models, skipped = discover_with_skipped(cfg.models)
    if args.as_json:
        print(json.dumps([m.to_dict() for m in models], indent=2))
        return EXIT_OK
    if not models and not skipped:
        print("(no models discovered — check [models].directories or add aliases)")
        return EXIT_OK

    def _weight_count(p: Path) -> int:
        n = int((p / "model.safetensors").is_file()) + int((p / "weights.safetensors").is_file())
        n += sum(1 for c in p.iterdir() if c.is_file() and c.name.startswith("model-") and c.name.endswith(".safetensors"))
        return n

    def _dir_size(p: Path) -> str:
        try:
            sz = sum(c.stat().st_size for c in p.rglob("*") if c.is_file())
        except OSError:
            return "?"
        return _human_size(sz)

    if models:
        id_w = max((len(m.id) for m in models), default=8)
        id_w = min(max(id_w, 8), 40)
        print(f"{'ID':<{id_w}}  SOURCE    WEIGHTS  SIZE   PATH")
        for m in models:
            wc = _weight_count(m.path)
            sz = _dir_size(m.path)
            line = f"{m.source:<9} {wc:<7} {sz:<6}  {m.path}"
            if len(m.id) <= id_w:
                print(f"{m.id:<{id_w}}  {line}")
            else:
                print(f"{m.id}")
                print(f"{'':<{id_w}}  {line}")
    else:
        print("(no servable MLX models discovered)")

    if skipped:
        print()
        print(f"Skipped ({len(skipped)} — not servable by mlx_lm):")
        for s in skipped:
            print(f"  {s.path}")
            print(f"    reason: {s.reason}")
    return EXIT_OK


def _resolve_model_for_action(cfg: Config, requested: str | None) -> "tuple[int, object]":
    """Return (exit_code, Model | error message)."""
    requested = requested or cfg.models.default_model
    if not requested:
        return EXIT_USAGE, "no --model given and [models].default_model is empty"
    try:
        m = resolve(cfg.models, requested)
    except LookupError as e:
        return EXIT_CONFIG, str(e)
    return EXIT_OK, m


def _prompt(input_fn: Callable[[str], str], prompt: str) -> str:
    try:
        return input_fn(prompt).strip()
    except EOFError as e:
        raise ValueError("input cancelled") from e


def _choose_model_from_list(
    cfg: Config,
    *,
    input_fn: Callable[[str], str] | None = None,
    out_fn: Callable[[str], None] = print,
) -> Model:
    input_fn = input if input_fn is None else input_fn
    models = discover(cfg.models)
    if not models:
        raise LookupError("no models discovered; check [models].directories or add aliases")

    id_w = min(max(max(len(m.id) for m in models), 8), 40)
    out_fn("Discovered models:")
    for idx, model in enumerate(models, start=1):
        # Truncate over-long IDs so the `source`/`path` columns stay aligned;
        # the full id is always still selectable by typing it in below.
        display_id = model.id if len(model.id) <= id_w else model.id[: id_w - 1] + "…"
        out_fn(f"  {idx:>2}. {display_id:<{id_w}}  {model.source:<9} {model.path}")

    while True:
        default_hint = ", Enter=1" if len(models) == 1 else ""
        answer = _prompt(input_fn, f"model [1-{len(models)}{default_hint}]: ")
        if not answer and len(models) == 1:
            return models[0]
        if answer.lower() in {"q", "quit", "cancel"}:
            raise ValueError("selection cancelled")
        if answer.isdigit():
            idx = int(answer)
            if 1 <= idx <= len(models):
                return models[idx - 1]
        for model in models:
            if answer == model.id or answer == str(model.path):
                return model
        out_fn(f"Enter a number from 1 to {len(models)}, or an exact model id/path.")


def _choose_host(
    default_host: str,
    *,
    input_fn: Callable[[str], str] | None = None,
) -> tuple[str, bool]:
    input_fn = input if input_fn is None else input_fn
    answer = _prompt(input_fn, f"host [{default_host}; all=0.0.0.0]: ")
    if not answer:
        host = default_host
    elif answer.lower() in {"all", "any", "*", "0.0.0.0"}:
        host = "0.0.0.0"
    else:
        host = answer
    return host, host == "0.0.0.0"


def _choose_port(
    default_port: int,
    *,
    input_fn: Callable[[str], str] | None = None,
    out_fn: Callable[[str], None] = print,
) -> int:
    input_fn = input if input_fn is None else input_fn
    while True:
        answer = _prompt(input_fn, f"port [{default_port}]: ")
        if not answer:
            return default_port
        try:
            port = int(answer)
        except ValueError:
            out_fn("Enter a numeric TCP port.")
            continue
        if _PORT_MIN <= port <= _PORT_MAX:
            return port
        out_fn(f"Enter a port between {_PORT_MIN} and {_PORT_MAX}.")


def _choose_replace(
    *,
    input_fn: Callable[[str], str] | None = None,
) -> bool:
    input_fn = input if input_fn is None else input_fn
    answer = _prompt(input_fn, "replace existing managed server on this port if needed? [y/N]: ")
    return answer.lower() in {"y", "yes"}


def _choose_update_opencode(
    *,
    input_fn: Callable[[str], str] | None = None,
) -> bool:
    input_fn = input if input_fn is None else input_fn
    answer = _prompt(
        input_fn,
        "update OpenCode config (~/.config/opencode/opencode.json) to point at this server? [y/N]: ",
    )
    return answer.lower() in {"y", "yes"}


def _choose_opencode_apply_options(
    *,
    default_target: str,
    default_overwrite: bool = False,
    input_fn: Callable[[str], str] | None = None,
    out_fn: Callable[[str], None] = print,
) -> tuple[str, bool, bool]:
    """Prompt for target path, merge/overwrite mode, and Claude Code snippet opt-in.

    Returns ``(target, overwrite, also_claude_code)``. Used by both
    ``_cmd_start_guided`` (after the user opts in to updating OpenCode) and
    ``config opencode --choose``.
    """
    input_fn = input if input_fn is None else input_fn

    # Path prompt: must not collide with y/N answers on the surrounding lines.
    # The previous "[default]" form was being read as a yes/no choice and a
    # bare "y" got accepted as a literal filename — silently writing the
    # JSON to ./y next to the user's cwd. Reword + reject y/n explicitly.
    while True:
        answer = _prompt(
            input_fn,
            f"opencode config path (press Enter to use {default_target}): ",
        )
        if not answer:
            target = default_target
            break
        if answer.lower() in {"y", "yes", "n", "no"}:
            out_fn(
                "That looks like a yes/no answer, not a path. "
                f"Press Enter to keep the default ({default_target}), "
                "or type a file path (e.g. ~/.config/opencode/opencode.json)."
            )
            continue
        target = answer
        break

    default_mode = "o" if default_overwrite else "m"
    while True:
        answer = _prompt(
            input_fn,
            f"merge into existing block, or overwrite/reset the whole block? [m/o, default={default_mode}]: ",
        )
        if not answer:
            overwrite = default_overwrite
            break
        low = answer.lower()
        if low in {"m", "merge"}:
            overwrite = False
            break
        if low in {"o", "overwrite", "reset"}:
            overwrite = True
            break
        out_fn("Enter 'm' (merge) or 'o' (overwrite).")

    answer = _prompt(
        input_fn,
        "also print a Claude Code (LiteLLM) snippet to stdout? [y/N]: ",
    )
    also_claude_code = answer.lower() in {"y", "yes"}

    return target, overwrite, also_claude_code


def _cmd_start(cfg: Config, args: argparse.Namespace) -> int:
    if getattr(args, "choose", False):
        return _cmd_start_guided(cfg, args)

    rc, m_or_err = _resolve_model_for_action(cfg, args.model)
    if rc != EXIT_OK:
        _eprint(f"error: {m_or_err}")
        return rc
    model = m_or_err  # type: ignore[assignment]

    return _start_model(cfg, args, model)


def _extra_arg_has_flag(cli_pairs: list[str], config_flags: list[str], flag: str) -> bool:
    """Return True if *flag* already appears in either input list.

    *cli_pairs* are ``KEY=VAL`` strings from repeated ``--extra-arg`` on the CLI
    (no leading dashes). *config_flags* are raw ``--flag`` / ``--flag=val``
    strings from ``[server].extra_args`` in the TOML config. *flag* is compared
    without leading dashes.
    """
    norm = flag.lstrip("-")
    for kv in cli_pairs:
        if kv.partition("=")[0].lstrip("-") == norm:
            return True
    for item in config_flags:
        item_norm = item.lstrip("-")
        if item_norm == norm or item_norm.startswith(norm + "="):
            return True
    return False


def _start_model(cfg: Config, args: argparse.Namespace, model: Model) -> int:
    """Start the server for an already resolved model."""

    host = args.host or cfg.server.host
    if host == "0.0.0.0" and not args.bind_all:
        _eprint("error: binding on 0.0.0.0 requires --bind-all")
        return EXIT_USAGE
    if args.bind_all:
        host = "0.0.0.0"
        _eprint("warning: binding on 0.0.0.0 — server is reachable from the network")
    port = args.port or cfg.server.port

    plan = model_memory_plan(
        model.path,
        max_context_tokens=cfg.server.max_context_tokens,
        prompt_cache_fraction=cfg.server.prompt_cache_fraction,
    )

    extra_arg_pairs: list[str] = list(args.extra_arg)
    if not _extra_arg_has_flag(
        cli_pairs=extra_arg_pairs,
        config_flags=cfg.server.extra_args,
        flag="prompt-cache-bytes",
    ):
        if plan is not None:
            _, cache_bytes = plan
            extra_arg_pairs = [f"--prompt-cache-bytes={cache_bytes}"] + extra_arg_pairs

    try:
        with srv.acquire_lock(srv.port_lock_path(cfg, port)):
            _vprint("lock acquired", args.verbose)
            state = srv.start(
                cfg,
                model,
                host=host,
                port=port,
                extra_arg_pairs=extra_arg_pairs,
                replace=args.replace,
                on_warning=lambda w: _eprint(f"warning: {w}"),
                on_verbose=(lambda m: _eprint(f"verbose: {m}") if args.verbose else None),
            )
            _vprint("lock released", args.verbose)
    except srv.ServerError as e:
        _eprint(f"error: {e}")
        return e.exit_code

    print(f"started mlx_lm server")
    print(f"  pid:        {state.pid}")
    print(f"  model:      {state.model_alias}")
    print(f"  path:       {state.model_path}")
    print(f"  base_url:   {state.base_url}")
    print(f"  log:        {srv.port_log_path(cfg, port)}")

    ctx_len = plan[0] if plan else None
    if getattr(args, "update_opencode", False):
        ctx = ProviderContext(
            base_url=state.base_url,
            api_key=cfg.providers.api_key,
            provider_name=managed_provider_name(f"{cfg.providers.provider_name}:{port}"),
            model_id=state.model_alias,
            context_length=ctx_len,
        )
        target = expand(getattr(args, "opencode_target", _DEFAULT_OPENCODE_TARGET))
        overwrite = getattr(args, "overwrite", False)
        try:
            with srv.acquire_lock(_opencode_lock_path(target)):
                summary = apply_opencode(ctx, target, overwrite=overwrite)
            print(f"  opencode:   {summary}")
        except (ApplyError, OSError, srv.ServerError) as e:
            _eprint(f"warning: opencode config not updated: {e}")

    if getattr(args, "print_claude_code_snippet", False):
        snippet_ctx = ProviderContext(
            base_url=state.base_url,
            api_key=cfg.providers.api_key,
            provider_name=cfg.providers.provider_name,
            model_id=state.model_alias,
            context_length=ctx_len,
        )
        print()
        print("--- Claude Code (LiteLLM) snippet ---")
        sys.stdout.write(claude_code_snippet(snippet_ctx))

    return EXIT_OK


def _cmd_start_guided(cfg: Config, args: argparse.Namespace) -> int:
    try:
        if getattr(args, "model", None):
            rc, m_or_err = _resolve_model_for_action(cfg, args.model)
            if rc != EXIT_OK:
                _eprint(f"error: {m_or_err}")
                return rc
            model = m_or_err
        else:
            model = _choose_model_from_list(cfg)

        if args.bind_all:
            host = "0.0.0.0"
            bind_all = True
        elif args.host:
            host = args.host
            bind_all = False
        else:
            host, bind_all = _choose_host(cfg.server.host)

        port = args.port or _choose_port(cfg.server.port)
        replace = args.replace or _choose_replace()

        update_opencode_flag = getattr(args, "update_opencode", False)
        opencode_target = getattr(args, "opencode_target", _DEFAULT_OPENCODE_TARGET)
        overwrite = getattr(args, "overwrite", False)
        print_claude_code_snippet = False
        if update_opencode_flag:
            # CLI flags fully specify the apply; skip all OpenCode sub-prompts.
            update_opencode = True
        else:
            update_opencode = _choose_update_opencode()
            if update_opencode:
                opencode_target, overwrite, print_claude_code_snippet = (
                    _choose_opencode_apply_options(
                        default_target=opencode_target,
                        default_overwrite=overwrite,
                    )
                )
    except LookupError as e:
        _eprint(f"error: {e}")
        return EXIT_CONFIG
    except ValueError as e:
        _eprint(f"error: {e}")
        return EXIT_USAGE

    start_args = argparse.Namespace(
        host=host,
        port=port,
        replace=replace,
        bind_all=bind_all,
        extra_arg=args.extra_arg,
        verbose=getattr(args, "verbose", False),
        update_opencode=update_opencode,
        overwrite=overwrite,
        opencode_target=opencode_target,
        print_claude_code_snippet=print_claude_code_snippet,
    )
    return _start_model(cfg, start_args, model)


def _cmd_stop(cfg: Config, args: argparse.Namespace) -> int:
    port = getattr(args, "port", None)
    if port is None:
        # Auto-detect: error if multiple running, proceed if exactly one.
        running = srv.list_running_states(cfg)
        if not running:
            _eprint("error: no managed server is running")
            return EXIT_NOT_RUNNING
        if len(running) > 1:
            lines = "\n".join(f"  port {s.port}: {s.model_alias}" for s in running)
            _eprint(f"error: multiple servers running:\n{lines}\nuse --port to specify which to stop")
            return EXIT_GENERIC
        port = running[0].port

    try:
        with srv.acquire_lock(srv.port_lock_path(cfg, port)):
            _vprint("lock acquired", args.verbose)
            state = srv.stop(cfg, port=port, timeout=args.timeout)
            _vprint("lock released", args.verbose)
    except srv.ServerError as e:
        _eprint(f"error: {e}")
        return e.exit_code
    print(f"stopped pid {state.pid} ({state.model_alias} on port {state.port})")
    _vprint(f"state_file removed: {srv.port_state_path(cfg, state.port)}", args.verbose)
    return EXIT_OK


def _cmd_restart(cfg: Config, args: argparse.Namespace) -> int:
    # Reuse start logic with --replace semantics.
    start_args = argparse.Namespace(
        model=args.model,
        host=args.host,
        port=args.port,
        replace=True,
        bind_all=args.bind_all,
        extra_arg=args.extra_arg,
        verbose=getattr(args, "verbose", False),
        update_opencode=getattr(args, "update_opencode", False),
        overwrite=getattr(args, "overwrite", False),
        opencode_target=getattr(args, "opencode_target", _DEFAULT_OPENCODE_TARGET),
    )
    return _cmd_start(cfg, start_args)


def _cmd_switch(cfg: Config, args: argparse.Namespace) -> int:
    """Swap running server to a different model (convenience alias for restart --replace)."""
    start_args = argparse.Namespace(
        model=args.model,
        host=args.host,
        port=args.port,
        replace=True,
        bind_all=args.bind_all,
        extra_arg=args.extra_arg,
        verbose=args.verbose,
        update_opencode=getattr(args, "update_opencode", False),
        overwrite=getattr(args, "overwrite", False),
        opencode_target=getattr(args, "opencode_target", _DEFAULT_OPENCODE_TARGET),
    )
    return _cmd_start(cfg, start_args)


def _format_uptime(uptime_s: int) -> str:
    if uptime_s >= 86400:
        return f"{uptime_s//86400}d {(uptime_s%86400)//3600}h {(uptime_s%3600)//60}m"
    elif uptime_s >= 3600:
        return f"{uptime_s//3600}h {(uptime_s%3600)//60}m"
    elif uptime_s >= 60:
        return f"{uptime_s//60}m {uptime_s%60}s"
    return f"{uptime_s}s"


def _print_status_dict(d: dict) -> None:
    print(f"running     pid       {d['pid']}")
    print(f"            model     {d['model_alias']}")
    print(f"            path      {d['model_path']}")
    print(f"            host      {d['host']}")
    print(f"            port      {d['port']}")
    print(f"            base_url  {d['base_url']}")
    print(f"            started   {d['started_at']}")
    uptime_s = d["uptime_seconds"]
    print(f"            uptime    {_format_uptime(uptime_s)} ({uptime_s}s)")
    if d.get("mlx_lm_version"):
        print(f"            mlx_lm    {d['mlx_lm_version']}")
    try:
        ps_out = subprocess.run(
            ["ps", "-p", str(d["pid"]), "-o", "rss="],
            capture_output=True, text=True, timeout=5,
        )
        if ps_out.returncode == 0:
            rss = int(ps_out.stdout.strip())
            print(f"            memory    {rss / 1024 / 1024:.0f}MB (rss)")
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    print(f"            endpoint  {'ok' if d['endpoint_ok'] else 'unreachable'}")
    if d.get("health", "ok") != "ok":
        print(f"            health    ERROR — {d.get('health_detail', '')}")
    else:
        print(f"            health    ok")


def _cmd_status(cfg: Config, args: argparse.Namespace) -> int:
    port = getattr(args, "port", None)

    if port is not None:
        # Single-server view.
        d = srv.status_dict(cfg, port)
        if args.as_json:
            print(json.dumps(d, indent=2, sort_keys=True))
            return EXIT_OK if d["running"] else EXIT_NOT_RUNNING
        if not d["running"]:
            if d["pid"] is None:
                print(f"not running (port {port})")
            else:
                print(f"not running (stale: last pid {d['pid']}, model {d['model_alias']})")
            return EXIT_NOT_RUNNING
        _print_status_dict(d)
        return EXIT_OK

    # Multi-server view.
    all_dicts = srv.all_status_dicts(cfg)
    running = [d for d in all_dicts if d["running"]]

    if args.as_json:
        print(json.dumps(all_dicts, indent=2, sort_keys=True))
        return EXIT_OK if running else EXIT_NOT_RUNNING

    if not all_dicts:
        print("not running")
        return EXIT_NOT_RUNNING

    for i, d in enumerate(all_dicts):
        if i > 0:
            print()
        if not d["running"]:
            print(f"not running (stale: port {d['port']}, last pid {d['pid']}, model {d['model_alias']})")
        else:
            _print_status_dict(d)

    return EXIT_OK if running else EXIT_NOT_RUNNING


def _cmd_logs(cfg: Config, args: argparse.Namespace) -> int:
    port = getattr(args, "port", None)
    if port is None:
        running = srv.list_running_states(cfg)
        if not running:
            _eprint("error: no managed server is running")
            return EXIT_NOT_RUNNING
        if len(running) > 1:
            lines = "\n".join(f"  port {s.port}: {s.model_alias}" for s in running)
            _eprint(f"error: multiple servers running:\n{lines}\nuse --port to specify which server's log to tail")
            return EXIT_GENERIC
        port = running[0].port
    log_path = srv.port_log_path(cfg, port)
    if not log_path.exists():
        _eprint(f"error: log file {log_path} does not exist")
        return EXIT_NOT_RUNNING

    for line in srv.tail_lines(log_path, args.tail):
        print(line)

    if not args.follow:
        return EXIT_OK

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                print(line.rstrip("\n"))
    except KeyboardInterrupt:
        return EXIT_OK


def _pick_provider_model(cfg: Config, requested: str | None) -> str | None:
    """Resolve the model id to use for a provider snippet.

    Preference: explicit --model → running server's model_alias → first
    discovered model → [models].default_model.
    """
    if requested:
        return requested
    state = srv.primary_state(cfg)
    if state is not None:
        return state.model_alias
    if cfg.models.default_model:
        return cfg.models.default_model
    found = discover(cfg.models)
    if found:
        return found[0].id
    return None


def _resolve_base_url(base_url: str, *, remote: bool) -> str:
    if remote and base_url.startswith("http://127.0.0.1"):
        lan = _lan_ip()
        if lan:
            return base_url.replace("http://127.0.0.1", f"http://{lan}", 1)
    elif remote and base_url.startswith("http://0.0.0.0"):
        lan = _lan_ip()
        if lan:
            return base_url.replace("http://0.0.0.0", f"http://{lan}", 1)
    return base_url


def _provider_contexts(
    cfg: Config, model_id: str | None, *, remote: bool = False, managed_names: bool = False
) -> list[ProviderContext]:
    """Return one ProviderContext per running server (or one from config if none running).

    OpenCode-managed provider names include a ``:port`` suffix so the same
    naming scheme is used for one or many servers.
    """
    running = srv.list_running_states(cfg)
    hostname = socket.gethostname() if remote else ""

    def _make_name(port: int | None = None) -> str:
        name = cfg.providers.provider_name
        if remote:
            name = f"{name}@{hostname}"
        if managed_names and port is not None:
            name = f"{name}:{port}"
        return managed_provider_name(name) if managed_names else name

    if not running:
        mid = model_id or cfg.models.default_model or ""
        ctx_len: int | None = None
        if mid:
            try:
                m = resolve(cfg.models, mid)
                plan = model_memory_plan(
                    m.path,
                    max_context_tokens=cfg.server.max_context_tokens,
                    prompt_cache_fraction=cfg.server.prompt_cache_fraction,
                )
                ctx_len = plan[0] if plan else None
            except LookupError:
                pass
        base_url = _resolve_base_url(cfg.base_url, remote=remote)
        return [ProviderContext(
            base_url=base_url,
            api_key=cfg.providers.api_key,
            provider_name=_make_name(cfg.server.port),
            model_id=mid,
            context_length=ctx_len,
        )]

    def _ctx_len_for_state(state: srv.State) -> int | None:
        plan = model_memory_plan(
            Path(state.model_path),
            max_context_tokens=cfg.server.max_context_tokens,
            prompt_cache_fraction=cfg.server.prompt_cache_fraction,
        )
        return plan[0] if plan else None

    return [
        ProviderContext(
            base_url=_resolve_base_url(state.base_url, remote=remote),
            api_key=cfg.providers.api_key,
            provider_name=_make_name(state.port),
            model_id=model_id or state.model_alias,
            context_length=_ctx_len_for_state(state),
        )
        for state in running
    ]


def _provider_context(cfg: Config, model_id: str, *, remote: bool = False) -> ProviderContext:
    """Single-context helper used by commands that only need one server (e.g. claude-code)."""
    contexts = _provider_contexts(cfg, model_id, remote=remote)
    return contexts[0]


def _cmd_config_opencode(cfg: Config, args: argparse.Namespace) -> int:
    remote = getattr(args, "remote", False)
    if args.reset:
        target = expand(args.target)
        try:
            with srv.acquire_lock(_opencode_lock_path(target)):
                summary = reset_opencode(target)
        except (ApplyError, OSError, srv.ServerError) as e:
            _eprint(f"error: {e}")
            return EXIT_CONFIG
        print(summary)
        return EXIT_OK
    contexts = _provider_contexts(cfg, args.model, remote=remote, managed_names=True)
    if not any(c.model_id for c in contexts):
        _eprint("error: no model available; pass --model or run `mlx-manager list`")
        return EXIT_CONFIG
    if remote:
        _vprint(f"remote mode: using LAN IP in config", args.verbose)

    print_claude_code = False
    if getattr(args, "choose", False):
        try:
            target_str, overwrite, print_claude_code = _choose_opencode_apply_options(
                default_target=args.target,
                default_overwrite=args.overwrite,
            )
        except ValueError as e:
            _eprint(f"error: {e}")
            return EXIT_USAGE
        args.target = target_str
        args.overwrite = overwrite
        args.apply = True  # --choose implies --apply.

    if args.apply:
        target = expand(args.target)
        try:
            with srv.acquire_lock(_opencode_lock_path(target)):
                summary = apply_opencode(contexts, target, overwrite=args.overwrite)
        except (ApplyError, OSError, srv.ServerError) as e:
            _eprint(f"error: {e}")
            return EXIT_CONFIG
        print(summary)
        if print_claude_code:
            print()
            print("--- Claude Code (LiteLLM) snippet ---")
            sys.stdout.write(claude_code_snippet(contexts[0]))
        return EXIT_OK
    sys.stdout.write(opencode_snippet(contexts, format=args.format))
    return EXIT_OK


def _cmd_config_claude_code(cfg: Config, args: argparse.Namespace) -> int:
    model_id = _pick_provider_model(cfg, args.model)
    if not model_id:
        _eprint("error: no model available; pass --model or run `mlx-manager list`")
        return EXIT_CONFIG
    remote = getattr(args, "remote", False)
    ctx = _provider_context(cfg, model_id, remote=remote)
    if remote:
        _vprint(f"remote mode: using LAN IP in config", args.verbose)
    sys.stdout.write(claude_code_snippet(ctx))
    return EXIT_OK


def _cmd_config_show(cfg: Config, args: argparse.Namespace) -> int:
    """Display current effective config values."""
    if args.as_json:
        out: dict[str, Any] = {
            "path": str(cfg.path),
            "server": cfg.server.to_dict() if hasattr(cfg.server, "to_dict") else {
                "host": cfg.server.host,
                "port": cfg.server.port,
                "log_file": cfg.server.log_file,
                "pid_file": cfg.server.pid_file,
                "state_file": cfg.server.state_file,
                "lock_file": cfg.server.lock_file,
                "python_executable": cfg.server.python_executable,
                "extra_args": cfg.server.extra_args,
                "startup_timeout_seconds": cfg.server.startup_timeout_seconds,
                "stop_timeout_seconds": cfg.server.stop_timeout_seconds,
                "max_log_bytes": cfg.server.max_log_bytes,
                "max_log_files": cfg.server.max_log_files,
                "patch_tool_calls": cfg.server.patch_tool_calls,
            },
            "models": {
                "directories": cfg.models.directories,
                "default_model": cfg.models.default_model,
                "aliases": cfg.models.aliases,
            },
            "providers": {
                "base_url": cfg.providers.base_url,
                "api_key": cfg.providers.api_key,
                "provider_name": cfg.providers.provider_name,
            },
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"config file: {cfg.path}")
        print()
        print("[server]")
        print(f"  host                      = {cfg.server.host}")
        print(f"  port                      = {cfg.server.port}")
        print(f"  log_file                  = {cfg.server.log_file}")
        print(f"  pid_file                  = {cfg.server.pid_file}")
        print(f"  state_file                = {cfg.server.state_file}")
        print(f"  lock_file                 = {cfg.server.lock_file}")
        print(f"  python_executable         = {cfg.server.python_executable}")
        print(f"  extra_args                = {cfg.server.extra_args}")
        print(f"  startup_timeout_seconds   = {cfg.server.startup_timeout_seconds}")
        print(f"  stop_timeout_seconds      = {cfg.server.stop_timeout_seconds}")
        print(f"  max_log_bytes             = {cfg.server.max_log_bytes}")
        print(f"  max_log_files             = {cfg.server.max_log_files}")
        print(f"  patch_tool_calls          = {cfg.server.patch_tool_calls}")
        print()
        print("[models]")
        print(f"  directories               = {cfg.models.directories}")
        print(f"  default_model             = {cfg.models.default_model!r}")
        if cfg.models.aliases:
            print(f"  aliases:")
            for k, v in cfg.models.aliases.items():
                print(f"    {k} = {v}")
        print()
        print("[providers]")
        print(f"  base_url                  = {cfg.providers.base_url!r}")
        print(f"  api_key                   = {cfg.providers.api_key}")
        print(f"  provider_name             = {cfg.providers.provider_name}")
    return EXIT_OK


def _cmd_config_edit(cfg: Config, args: argparse.Namespace) -> int:
    """Open config.toml in $EDITOR."""
    editor = args.editor or os.environ.get("EDITOR", "vim")
    cfg_path = expand(cfg.path)
    if not cfg_path.exists():
        _eprint(f"error: config file {cfg_path} does not exist")
        return EXIT_CONFIG
    _vprint(f"opening {cfg_path} in {editor}", args.verbose)
    try:
        rc = subprocess.call([editor, str(cfg_path)])
    except FileNotFoundError:
        _eprint(f"error: editor {editor!r} not found on PATH")
        return EXIT_GENERIC
    if rc != 0:
        _eprint(f"warning: editor exited with code {rc}")
    # Reload config after editing.
    try:
        new_cfg = load(cfg.path)
        print(f"config reloaded from {new_cfg.path}")
        return EXIT_OK
    except (ConfigError, OSError) as e:
        _eprint(f"error: config is invalid after editing: {e}")
        return EXIT_CONFIG


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


def _mlx_lm_importable_here() -> bool:
    """True if ``mlx_lm`` can be imported by the interpreter running mlx-manager.

    This is what the in-process ``bot`` command needs, and is independent of
    ``server.python_executable`` (which only matters for the ``start`` subprocess).
    """
    importlib.invalidate_caches()
    return importlib.util.find_spec("mlx_lm") is not None


def _pipx_app_name() -> str | None:
    """If the current interpreter is a pipx-managed venv, return its app name.

    pipx venvs live at ``.../pipx/venvs/<app>``; injecting a library into that
    app is the correct way to make it importable here.
    """
    parts = Path(sys.prefix).parts
    if "pipx" in parts and "venvs" in parts:
        i = parts.index("venvs")
        if i + 1 < len(parts):
            return parts[i + 1]
    return None


def _mlx_lm_install_cmd() -> list[str]:
    """Build the command that installs mlx_lm into the bot's runtime."""
    app = _pipx_app_name()
    if app and shutil.which("pipx"):
        return ["pipx", "inject", app, "mlx-lm"]
    return [sys.executable, "-m", "pip", "install", "mlx-lm"]


def _run_fix_cmd(cmd: list[str]) -> int:
    """Run a remediation command, echoing it and a short output tail to stderr."""
    _eprint(f"  $ {' '.join(cmd)}")
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        _eprint(f"  → could not run: {e}")
        return 1
    tail = (out.stdout or "").strip().splitlines()[-3:]
    tail += (out.stderr or "").strip().splitlines()[-3:]
    for line in tail:
        _eprint(f"    {line}")
    return out.returncode


def _doctor_fix(cfg: Config) -> None:
    """Attempt to remediate fixable doctor issues. Progress goes to stderr."""
    _eprint("doctor --fix: attempting remediations")
    fixed_any = False

    if not _mlx_lm_importable_here():
        fixed_any = True
        cmd = _mlx_lm_install_cmd()
        _eprint(f"- installing mlx_lm for the bot runtime ({sys.executable})")
        rc = _run_fix_cmd(cmd)
        if rc == 0 and _mlx_lm_importable_here():
            _eprint("  → ok")
        else:
            _eprint("  → still missing; install mlx_lm manually into this environment")

    for raw_dir in cfg.models.directories:
        d = expand(raw_dir)
        if not d.exists():
            fixed_any = True
            try:
                d.mkdir(parents=True, exist_ok=True)
                _eprint(f"- created models dir {d}")
            except OSError as e:
                _eprint(f"- could not create {d}: {e}")

    # Make `start` work too: the server runs `<python_executable> -m mlx_lm
    # server` as a subprocess. If that interpreter can't import mlx_lm but this
    # one can (e.g. mlx-manager is pipx-isolated and the server default is a
    # Homebrew python without mlx_lm), repoint the default at this interpreter
    # rather than touching an externally-managed Python.
    if not srv.mlx_lm_installed(cfg.server.python_executable) and _mlx_lm_importable_here():
        if cfg.server.python_executable == "python3":
            try:
                update_value(cfg.path, "server", "python_executable", sys.executable)
                fixed_any = True
                _eprint(
                    f"- set server.python_executable = {sys.executable} "
                    "(was 'python3', which lacked mlx_lm)"
                )
            except (OSError, ConfigError) as e:
                _eprint(f"- could not update config: {e}")
        else:
            _eprint(
                f"- note: server.python_executable ({cfg.server.python_executable}) "
                f"cannot import mlx_lm; point it at {sys.executable} or install "
                "mlx-lm there"
            )

    if not fixed_any:
        _eprint("- nothing to fix")
    _eprint("")


def _doctor_checks(cfg: Config) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    def add(name: str, status: str, detail: str) -> None:
        results.append({"name": name, "status": status, "detail": detail})

    py = cfg.server.python_executable
    py_path = shutil.which(py) or ""
    if not py_path:
        add("python", "FAIL", f"{py!r} not found on PATH")
    else:
        try:
            out = subprocess.run(
                [py, "--version"], capture_output=True, text=True, timeout=10
            )
            ver = (out.stdout or out.stderr).strip()
            add("python", "OK", f"{py_path} ({ver})")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            add("python", "FAIL", f"could not run {py}: {e}")

    if srv.mlx_lm_installed(py):
        v = srv.mlx_lm_version(py) or "unknown"
        add("mlx_lm import", "OK", f"version {v}")
        flags = srv.supported_server_flags(py)
        if flags:
            add("mlx_lm server --help", "OK", f"{len(flags)} flags parsed")
        else:
            add("mlx_lm server --help", "WARN", "could not parse --help output")
    else:
        add(
            "mlx_lm import",
            "FAIL",
            "`import mlx_lm` failed; install with `pip install mlx-lm`",
        )
        add("mlx_lm server --help", "WARN", "skipped (mlx_lm missing)")

    # The `bot` command imports mlx_lm into THIS interpreter, which can differ
    # from server.python_executable (e.g. when mlx-manager is pipx-isolated).
    if _mlx_lm_importable_here():
        add("bot runtime", "OK", f"mlx_lm importable here ({sys.executable})")
    else:
        app = _pipx_app_name()
        hint = (
            f"run `mlx-manager doctor --fix` (will run `pipx inject {app} mlx-lm`)"
            if app
            else "run `mlx-manager doctor --fix`"
        )
        add(
            "bot runtime",
            "FAIL",
            f"mlx_lm not importable in {sys.executable} (needed by `bot`); {hint}",
        )

    for raw_dir in cfg.models.directories:
        d = expand(raw_dir)
        if not d.exists():
            add(f"models dir {raw_dir}", "WARN", f"does not exist ({d})")
            continue
        if not os.access(d, os.R_OK):
            add(f"models dir {raw_dir}", "FAIL", f"not readable ({d})")
            continue
        # Light-weight count: discover() over a single-directory snapshot.
        snapshot = type(cfg.models)(
            directories=[raw_dir], default_model="", aliases={}
        )
        models, skipped = discover_with_skipped(snapshot)
        detail = f"{len(models)} model(s) found at {d}"
        if skipped:
            sample = "; ".join(f"{s.path.name} ({s.reason})" for s in skipped[:3])
            more = f", +{len(skipped) - 3} more" if len(skipped) > 3 else ""
            detail += f"; {len(skipped)} skipped: {sample}{more}"
            add(f"models dir {raw_dir}", "WARN", detail)
        else:
            add(f"models dir {raw_dir}", "OK", detail)

    # Alias resolution (warn if missing, per Config schema).
    for alias, raw_target in cfg.models.aliases.items():
        target = expand(raw_target)
        if target.exists():
            add(f"alias {alias}", "OK", str(target))
        else:
            add(f"alias {alias}", "WARN", f"{target} does not exist")

    # Path writability.
    for key in ("log_file", "pid_file", "state_file", "lock_file"):
        raw = getattr(cfg.server, key)
        try:
            p = ensure_parent(raw)
            if os.access(p.parent, os.W_OK):
                add(f"{key} parent writable", "OK", str(p.parent))
            else:
                add(f"{key} parent writable", "FAIL", f"{p.parent} not writable")
        except OSError as e:
            add(f"{key} parent writable", "FAIL", f"{raw}: {e}")

    # Port reachability — check all running servers, fall back to config default.
    running_states = srv.list_running_states(cfg)
    if running_states:
        for st in running_states:
            ok = srv.endpoint_ok(st.host, st.port)
            add(
                f"endpoint :{st.port}",
                "OK" if ok else "FAIL",
                f"{st.host}:{st.port} {'reachable' if ok else 'unreachable'}",
            )
            health, detail = srv.log_health(srv.port_log_path(cfg, st.port))
            if health == "ok":
                add(f"model :{st.port}", "OK", f"{st.model_alias}: no load errors in log")
            else:
                add(f"model :{st.port}", "FAIL", f"{st.model_alias}: {detail}")
    else:
        host, port = cfg.server.host, cfg.server.port
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.bind((host, port))
            add("port", "OK", f"{host}:{port} bindable")
        except OSError as e:
            add("port", "WARN", f"{host}:{port} not bindable ({e})")

    # Platform.
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        add("platform", "OK", "Darwin/arm64")
    else:
        add(
            "platform",
            "WARN",
            f"expected Darwin/arm64, got {platform.system()}/{platform.machine()}",
        )

    # System memory.
    try:
        mem_out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5)
        if mem_out.returncode == 0:
            mem_bytes = int(mem_out.stdout.strip())
            mem_gb = mem_bytes / 1024 / 1024 / 1024
            add("memory", "OK", f"{mem_gb:.0f}GB physical")
        else:
            add("memory", "WARN", "could not determine physical memory")
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        add("memory", "WARN", "sysctl hw.memsize unavailable")

    # Metal/GPU wired-memory limit. The kernel default (0) caps at ~75% of RAM,
    # which is enough for moderate models but a common source of OOM under
    # concurrent decodes or long contexts. Surface the value so the user can
    # tune `sudo sysctl iogpu.wired_limit_mb=N` before raising context.
    if platform.system() == "Darwin":
        wired = wired_limit_mb()
        if wired is None:
            add("wired_limit", "WARN", "sysctl iogpu.wired_limit_mb unavailable")
        elif wired == 0:
            add(
                "wired_limit",
                "WARN",
                "iogpu.wired_limit_mb=0 (kernel default ~75% of RAM); "
                "raise with `sudo sysctl iogpu.wired_limit_mb=N` to reduce Metal OOM risk",
            )
        else:
            add("wired_limit", "OK", f"iogpu.wired_limit_mb={wired}")

    # Firewall status (macOS pf).
    try:
        fw_out = subprocess.run(["pfctl", "--status"], capture_output=True, text=True, timeout=5)
        if "is enabled" in (fw_out.stdout or fw_out.stderr or ""):
            add("firewall", "WARN", "pf is enabled (may block inbound connections)")
        else:
            add("firewall", "OK", "pf is disabled")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        add("firewall", "WARN", "could not determine pf status")

    return results


def _cmd_info(cfg: Config, args: argparse.Namespace) -> int:
    """Show model metadata: id, source, path, weights, config.json fields."""
    rc, m_or_err = _resolve_model_for_action(cfg, args.model)
    if rc != EXIT_OK:
        _eprint(f"error: {m_or_err}")
        return rc
    m = m_or_err  # type: ignore[attribute-error]

    # Count weight files and total size.
    weight_files = []
    total_size = 0
    try:
        for c in m.path.iterdir():
            if c.is_file() and (
                c.name == "model.safetensors"
                or c.name == "weights.safetensors"
                or (c.name.startswith("model-") and c.name.endswith(".safetensors"))
            ):
                st = c.stat()
                weight_files.append(c.name)
                total_size += st.st_size
    except OSError:
        pass

    # Read config.json if present.
    cfg_json: dict[str, Any] = {}
    cfg_path = m.path / "config.json"
    if cfg_path.is_file():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg_json = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    if args.as_json:
        out = {
            "id": m.id,
            "source": m.source,
            "path": str(m.path),
            "weight_files": weight_files,
            "weight_count": len(weight_files),
            "total_size": total_size,
            "config": cfg_json,
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"id          {m.id}")
        print(f"source      {m.source}")
        print(f"path        {m.path}")
        print(f"weights     {len(weight_files)} file(s), {_human_size(total_size)}")
        if weight_files:
            for wf in weight_files:
                wp = m.path / wf
                print(f"           {wf} ({_human_size(wp.stat().st_size) if wp.is_file() else '?'})")
        if cfg_json:
            print(f"config.json:")
            for k in ("model_type", "num_parameters", "num_hidden_layers",
                       "hidden_size", "num_attention_heads", "tokenizer_class"):
                if k in cfg_json:
                    print(f"           {k} = {cfg_json[k]}")

    return EXIT_OK


def _cmd_doctor(cfg: Config, args: argparse.Namespace) -> int:
    if getattr(args, "fix", False):
        _doctor_fix(cfg)
    results = _doctor_checks(cfg)
    has_fail = any(r["status"] == "FAIL" for r in results)
    if args.as_json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"  [{r['status']:<4}] {r['name']}: {r['detail']}")
        if has_fail:
            print("\nresult: FAIL")
        else:
            print("\nresult: OK")
    return EXIT_GENERIC if has_fail else EXIT_OK


def _cmd_bot(cfg: Config, args: argparse.Namespace) -> int:
    max_tokens = args.max_tokens or cfg.bot.max_tokens
    temperature = cfg.bot.temperature if args.temperature is None else args.temperature

    with_context = not args.no_context
    status_dicts = srv.all_status_dicts(cfg) if with_context else []
    doctor_results = _doctor_checks(cfg) if with_context else []
    system_prompt = bot_mod.build_system_prompt(
        status_dicts, doctor_results, with_context=with_context
    )

    return bot_mod.run(
        model_override=args.model,
        default_model=cfg.bot.model,
        cache_dir=cfg.bot.cache_dir,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        force_choose=args.choose,
        on_status=lambda m: _eprint(m),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _cmd_benchmark(cfg: Config, args: argparse.Namespace) -> int:
    state = srv.primary_state(cfg)
    running = state is not None

    if args.endpoint:
        endpoint = args.endpoint.rstrip("/")
        if not endpoint.endswith("/v1"):
            endpoint = endpoint + "/v1"
    elif running:
        endpoint = state.base_url
    else:
        endpoint = cfg.base_url

    if args.model:
        model_id = args.model
    elif running:
        model_id = state.model_alias
    elif cfg.models.default_model:
        model_id = cfg.models.default_model
    else:
        _eprint(
            "error: no --model and no running server; pass --model or start a server first"
        )
        return EXIT_USAGE

    if args.prompt_file:
        try:
            prompt = expand(args.prompt_file).read_text(encoding="utf-8")
        except OSError as e:
            _eprint(f"error: cannot read --prompt-file: {e}")
            return EXIT_CONFIG
    else:
        prompt = args.prompt or bench.DEFAULT_PROMPT

    # Collect results as they complete so the on_event callback can format them.
    _results: list[bench.RequestResult] = []

    # Progress tracker for concurrent runs.
    completed_count = 0

    def _progress(done: int, total: int) -> None:
        nonlocal completed_count
        completed_count = done
        if not args.as_json:
            bar_len = min(total, 20)
            filled = int(done / total * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            sys.stdout.write(f"\r  [{bar}] {done}/{total} done   ")
            sys.stdout.flush()

    def _on_event(msg: str) -> None:
        if not args.as_json:
            # Warmup messages pass through as simple text.
            if msg.startswith("warmup"):
                print(f"  {msg}")
                return
            # Measured requests get table-formatted output with bars.
            if not _results:
                print(f"\n  {'#':<3} {'TTFT':<8} {'Total':<8} {'Tokens':<8} {'Decode':<12} {'Bar'}")
            last = _results[-1]
            idx = len(_results)
            ttft_str = "-" if last.ttft_s is None else f"{last.ttft_s:.2f}s"
            total_str = f"{last.total_s:.2f}s"
            tok_str = str(last.completion_tokens)
            tps_str = f"{last.decode_tps:.1f} tok/s"
            max_tps = max((r.decode_tps for r in _results if r.decode_tps > 0), default=1)
            bar = bench._ascii_bar(last.decode_tps, max_tps, 16) if last.decode_tps > 0 else ""
            err_str = f" ERR {last.error}" if not last.ok else ""
            print(f"  {idx:<3} {ttft_str:<8} {total_str:<8} {tok_str:<8} {tps_str:<12} {bar}{err_str}")

    if not args.as_json:
        print(f"benchmark   endpoint    {endpoint}")
        print(f"            model       {model_id}")
        print(
            f"            requests    {args.requests} "
            f"(concurrency={args.concurrency}, max_tokens={args.max_tokens}, "
            f"warmup={args.warmup}, prompt_chars={len(prompt)})"
        )

    try:
        summary = bench.run(
            endpoint,
            model_id,
            prompt,
            requests=args.requests,
            concurrency=args.concurrency,
            max_tokens=args.max_tokens,
            warmup=args.warmup,
            api_key=cfg.providers.api_key,
            on_event=(None if args.as_json else _on_event),
            on_progress=(None if args.as_json else _progress),
            results=_results,
        )
    except ValueError as e:
        _eprint(f"error: {e}")
        return EXIT_USAGE

    # Save results if requested.
    if args.save:
        save_path = expand(args.save)
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(summary.to_dict(), f, indent=2)
            _vprint(f"results saved to {save_path}", args.verbose)
        except OSError as e:
            _eprint(f"warning: could not save to {save_path}: {e}")

    if args.as_json:
        print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
        return EXIT_OK if summary.requests_ok > 0 else EXIT_GENERIC

    # Visual summary output.
    if not args.as_json:
        print()

    # Sort per-request results by total time for display.
    sorted_results = sorted(summary.per_request, key=lambda r: r.total_s)

    print("")
    print("─── Summary ──────────────────────────────────────────────────────")
    print(f"  wall time:        {summary.wall_seconds:.2f}s")
    print(f"  requests:         {summary.requests_ok}/{summary.requests_total} succeeded")
    if summary.ttft_p50 is not None:
        ttft_bar = bench._ascii_bar(summary.ttft_p50, max(summary.ttft_p95 or summary.ttft_p50, 0.01), 16)
        print(f"  ttft:             p50={summary.ttft_p50:.2f}s  p95={summary.ttft_p95:.2f}s  {ttft_bar}")
    if summary.decode_tps_p50 is not None:
        max_decode = max(summary.decode_tps_p95 or summary.decode_tps_p50, 0.01)
        decode_bar = bench._ascii_bar(summary.decode_tps_p50, max_decode, 16)
        print(f"  decode rate:      p50={summary.decode_tps_p50:.1f} tok/s  p95={summary.decode_tps_p95:.1f} tok/s  {decode_bar} (per stream)")
    if summary.total_p50 is not None:
        total_bar = bench._ascii_bar(summary.total_p50, max(summary.total_p95 or summary.total_p50, 0.01), 16)
        print(f"  total time:       p50={summary.total_p50:.2f}s  p95={summary.total_p95:.2f}s  {total_bar}")

    # Aggregate throughput with bar.
    max_agg = max(summary.aggregate_decode_tps, 0.01)
    agg_bar = bench._ascii_bar(summary.aggregate_decode_tps, max_agg * 2, 16)
    print(f"  aggregate rate:   {summary.aggregate_decode_tps:.1f} tok/s  {agg_bar}")

    # Parallelism analysis.
    if summary.concurrency > 1 and summary.single_stream_tps is not None:
        ratio = summary.parallelism_ratio
        degradation = summary.degradation_pct
        if ratio:
            print(f"  parallelism gain: {ratio:.2f}×")
        if degradation is not None:
            sign = "+" if degradation < 0 else ""
            print(f"  per-stream delta: {sign}{degradation:+.1f}% (vs single-stream)")

    print("───")
    return EXIT_OK if summary.requests_ok > 0 else EXIT_GENERIC


_HANDLERS = {
    "list": _cmd_list,
    "start": _cmd_start,
    "load": _cmd_start_guided,
    "stop": _cmd_stop,
    "restart": _cmd_restart,
    "switch": _cmd_switch,
    "status": _cmd_status,
    "logs": _cmd_logs,
    "info": _cmd_info,
    "doctor": _cmd_doctor,
    "benchmark": _cmd_benchmark,
    "bot": _cmd_bot,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        cfg = load(args.config)
    except ConfigError as e:
        _eprint(f"config error: {e}")
        return EXIT_CONFIG
    except OSError as e:
        _eprint(f"config error: {e}")
        return EXIT_CONFIG

    _vprint(f"config loaded from {cfg.path}", args.verbose)

    if args.cmd == "config":
        if args.config_cmd == "opencode":
            return _cmd_config_opencode(cfg, args)
        if args.config_cmd == "claude-code":
            return _cmd_config_claude_code(cfg, args)
        if args.config_cmd == "show":
            return _cmd_config_show(cfg, args)
        if args.config_cmd == "edit":
            return _cmd_config_edit(cfg, args)
        parser.error(f"unknown config subcommand: {args.config_cmd!r}")
        return EXIT_USAGE

    handler = _HANDLERS.get(args.cmd)
    if handler is None:
        parser.error(f"unknown command: {args.cmd!r}")
        return EXIT_USAGE
    return handler(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
