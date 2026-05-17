from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mlx_manager import __version__
from mlx_manager import benchmark as bench
from mlx_manager.config import Config, ConfigError, DEFAULT_CONFIG_PATH, load
from mlx_manager.models import discover, resolve
from mlx_manager.paths import ensure_parent, expand
from mlx_manager.providers import (
    ApplyError,
    ProviderContext,
    apply_opencode,
    claude_code_snippet,
    opencode_snippet,
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


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


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
    sp.add_argument("--port", type=int, help="override server port")
    sp.add_argument("--replace", action="store_true", help="stop running server first")
    sp.add_argument("--bind-all", action="store_true", help="bind on 0.0.0.0 (insecure)")
    sp.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        metavar="KEY=VAL",
        help="forward extra flag to mlx_lm.server (repeatable)",
    )

    sp = sub.add_parser("stop", help="stop the managed server")
    sp.add_argument("--timeout", type=int, help="seconds to wait for SIGTERM before SIGKILL")

    sp = sub.add_parser("restart", help="stop then start the server")
    sp.add_argument("--model", help="model id, alias, or absolute path")
    sp.add_argument("--host")
    sp.add_argument("--port", type=int)
    sp.add_argument("--bind-all", action="store_true")
    sp.add_argument("--extra-arg", action="append", default=[], metavar="KEY=VAL")

    sp = sub.add_parser("status", help="report server state")
    sp.add_argument("--json", action="store_true", dest="as_json")

    sp = sub.add_parser("logs", help="tail server log")
    sp.add_argument("--tail", type=int, default=100)
    sp.add_argument("-f", "--follow", action="store_true")

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
        default="~/.config/opencode/opencode.json",
        help="OpenCode config path (only used with --apply)",
    )
    oc.add_argument(
        "--overwrite",
        action="store_true",
        help="replace the entire provider block instead of merging (only used with --apply)",
    )

    cc = cfg_sub.add_parser("claude-code", help="emit Claude Code / LiteLLM snippet")
    cc.add_argument("--model")

    sp = sub.add_parser("doctor", help="run diagnostics")
    sp.add_argument("--json", action="store_true", dest="as_json")

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

    return p


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_list(cfg: Config, args: argparse.Namespace) -> int:
    models = discover(cfg.models)
    if args.as_json:
        print(json.dumps([m.to_dict() for m in models], indent=2))
        return EXIT_OK
    if not models:
        print("(no models discovered — check [models].directories or add aliases)")
        return EXIT_OK
    width = max((len(m.id) for m in models), default=8)
    width = min(max(width, 8), 40)
    print(f"{'ALIAS':<{width}}  PATH")
    for m in models:
        if len(m.id) <= width:
            print(f"{m.id:<{width}}  {m.path}")
        else:
            print(m.id)
            print(f"{'':<{width}}  {m.path}")
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


def _cmd_start(cfg: Config, args: argparse.Namespace) -> int:
    rc, m_or_err = _resolve_model_for_action(cfg, args.model)
    if rc != EXIT_OK:
        _eprint(f"error: {m_or_err}")
        return rc
    model = m_or_err  # type: ignore[assignment]

    host = args.host or cfg.server.host
    if args.bind_all:
        host = "0.0.0.0"
        _eprint("warning: binding on 0.0.0.0 — server is reachable from the network")
    port = args.port or cfg.server.port

    try:
        with srv.acquire_lock(expand(cfg.server.lock_file)):
            state = srv.start(
                cfg,
                model,
                host=host,
                port=port,
                extra_arg_pairs=args.extra_arg,
                replace=args.replace,
                on_warning=lambda w: _eprint(f"warning: {w}"),
            )
    except srv.ServerError as e:
        _eprint(f"error: {e}")
        return e.exit_code

    print(f"started mlx_lm.server")
    print(f"  pid:        {state.pid}")
    print(f"  model:      {state.model_alias}")
    print(f"  path:       {state.model_path}")
    print(f"  base_url:   {state.base_url}")
    print(f"  log:        {expand(cfg.server.log_file)}")
    return EXIT_OK


def _cmd_stop(cfg: Config, args: argparse.Namespace) -> int:
    try:
        with srv.acquire_lock(expand(cfg.server.lock_file)):
            state = srv.stop(cfg, timeout=args.timeout)
    except srv.ServerError as e:
        _eprint(f"error: {e}")
        return e.exit_code
    print(f"stopped pid {state.pid} ({state.model_alias})")
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
    )
    return _cmd_start(cfg, start_args)


def _cmd_status(cfg: Config, args: argparse.Namespace) -> int:
    d = srv.status_dict(cfg)
    if args.as_json:
        print(json.dumps(d, indent=2, sort_keys=True))
        return EXIT_OK if d["running"] else EXIT_NOT_RUNNING

    if not d["running"]:
        if d["pid"] is None:
            print("not running")
        else:
            print(f"not running (stale state: last pid {d['pid']}, model {d['model_alias']})")
        return EXIT_NOT_RUNNING

    print(f"running     pid       {d['pid']}")
    print(f"            model     {d['model_alias']}")
    print(f"            path      {d['model_path']}")
    print(f"            host      {d['host']}")
    print(f"            port      {d['port']}")
    print(f"            base_url  {d['base_url']}")
    print(f"            started   {d['started_at']}")
    print(f"            uptime    {d['uptime_seconds']}s")
    print(f"            endpoint  {'ok' if d['endpoint_ok'] else 'unreachable'}")
    return EXIT_OK


def _cmd_logs(cfg: Config, args: argparse.Namespace) -> int:
    log_path = expand(cfg.server.log_file)
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
    state = srv.read_state(expand(cfg.server.state_file))
    if state is not None:
        return state.model_alias
    if cfg.models.default_model:
        return cfg.models.default_model
    found = discover(cfg.models)
    if found:
        return found[0].id
    return None


def _provider_context(cfg: Config, model_id: str) -> ProviderContext:
    state = srv.read_state(expand(cfg.server.state_file))
    if state is not None and srv.is_managed_process(state.pid, state):
        base_url = state.base_url
    else:
        base_url = cfg.base_url
    return ProviderContext(
        base_url=base_url,
        api_key=cfg.providers.api_key,
        provider_name=cfg.providers.provider_name,
        model_id=model_id,
    )


def _cmd_config_opencode(cfg: Config, args: argparse.Namespace) -> int:
    model_id = _pick_provider_model(cfg, args.model)
    if not model_id:
        _eprint("error: no model available; pass --model or run `mlx-manager list`")
        return EXIT_CONFIG
    ctx = _provider_context(cfg, model_id)
    if args.apply:
        target = expand(args.target)
        try:
            summary = apply_opencode(ctx, target, overwrite=args.overwrite)
        except (ApplyError, OSError) as e:
            _eprint(f"error: {e}")
            return EXIT_CONFIG
        print(summary)
        return EXIT_OK
    sys.stdout.write(opencode_snippet(ctx, format=args.format))
    return EXIT_OK


def _cmd_config_claude_code(cfg: Config, args: argparse.Namespace) -> int:
    model_id = _pick_provider_model(cfg, args.model)
    if not model_id:
        _eprint("error: no model available; pass --model or run `mlx-manager list`")
        return EXIT_CONFIG
    ctx = _provider_context(cfg, model_id)
    sys.stdout.write(claude_code_snippet(ctx))
    return EXIT_OK


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


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
            add("mlx_lm.server --help", "OK", f"{len(flags)} flags parsed")
        else:
            add("mlx_lm.server --help", "WARN", "could not parse --help output")
    else:
        add(
            "mlx_lm import",
            "FAIL",
            "`import mlx_lm` failed; install with `pip install mlx-lm`",
        )
        add("mlx_lm.server --help", "WARN", "skipped (mlx_lm missing)")

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
        n = len(discover(snapshot))
        add(f"models dir {raw_dir}", "OK", f"{n} model(s) found at {d}")

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

    # Port reachability.
    state = srv.read_state(expand(cfg.server.state_file))
    host, port = cfg.server.host, cfg.server.port
    if state is not None and srv.is_managed_process(state.pid, state):
        ok = srv.endpoint_ok(state.host, state.port)
        add(
            "endpoint",
            "OK" if ok else "FAIL",
            f"{state.host}:{state.port} {'reachable' if ok else 'unreachable'}",
        )
    else:
        # Best-effort: see if the port can be bound (then immediately release).
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

    return results


def _cmd_doctor(cfg: Config, args: argparse.Namespace) -> int:
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _cmd_benchmark(cfg: Config, args: argparse.Namespace) -> int:
    state = srv.read_state(expand(cfg.server.state_file))
    running = state is not None and srv.is_managed_process(state.pid, state)

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
            on_event=(None if args.as_json else lambda m: print(f"  {m}")),
        )
    except ValueError as e:
        _eprint(f"error: {e}")
        return EXIT_USAGE

    if args.as_json:
        print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
        return EXIT_OK if summary.requests_ok > 0 else EXIT_GENERIC

    print("")
    print(f"summary     wall              {summary.wall_seconds:.2f}s")
    print(
        f"            requests          {summary.requests_ok}/{summary.requests_total} ok"
    )
    if summary.ttft_p50 is not None:
        print(f"            ttft p50/p95      {summary.ttft_p50:.2f}s / {summary.ttft_p95:.2f}s")
    if summary.decode_tps_p50 is not None:
        print(
            f"            decode p50/p95    "
            f"{summary.decode_tps_p50:.1f} / {summary.decode_tps_p95:.1f} tok/s per stream"
        )
    if summary.total_p50 is not None:
        print(f"            total p50/p95     {summary.total_p50:.2f}s / {summary.total_p95:.2f}s")
    print(
        f"            aggregate         {summary.aggregate_decode_tps:.1f} tok/s "
        f"(sum of all parallel streams)"
    )
    return EXIT_OK if summary.requests_ok > 0 else EXIT_GENERIC


_HANDLERS = {
    "list": _cmd_list,
    "start": _cmd_start,
    "stop": _cmd_stop,
    "restart": _cmd_restart,
    "status": _cmd_status,
    "logs": _cmd_logs,
    "doctor": _cmd_doctor,
    "benchmark": _cmd_benchmark,
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

    if args.cmd == "config":
        if args.config_cmd == "opencode":
            return _cmd_config_opencode(cfg, args)
        if args.config_cmd == "claude-code":
            return _cmd_config_claude_code(cfg, args)
        parser.error(f"unknown config subcommand: {args.config_cmd!r}")
        return EXIT_USAGE

    handler = _HANDLERS.get(args.cmd)
    if handler is None:
        parser.error(f"unknown command: {args.cmd!r}")
        return EXIT_USAGE
    return handler(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
