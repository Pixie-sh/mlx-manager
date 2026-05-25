from __future__ import annotations

import contextlib
import difflib
import errno
import fcntl
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from mlx_manager.config import Config
from mlx_manager.models import Model
from mlx_manager.paths import ensure_parent, expand

LOCK_ACQUIRE_TIMEOUT_S = 10.0
READINESS_PROBE_INTERVAL_S = 0.5
READINESS_PROBE_HTTP_TIMEOUT_S = 2.0


class ServerError(Exception):
    """Operational error during a server lifecycle action."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class State:
    pid: int
    model_alias: str
    model_path: str
    host: str
    port: int
    base_url: str
    command: list[str]
    started_at: str
    python_executable: str
    mlx_lm_version: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def acquire_lock(lock_path: Path, timeout: float = LOCK_ACQUIRE_TIMEOUT_S):
    """Acquire an exclusive fcntl flock on *lock_path*. Raises ServerError on timeout."""
    ensure_parent(lock_path)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ServerError(
                        f"could not acquire lock {lock_path} within {timeout:.0f}s",
                        exit_code=1,
                    )
                time.sleep(0.1)
        yield
    finally:
        with contextlib.suppress(Exception):
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------


def write_state(state_path: Path, state: State) -> None:
    """Atomically write *state* to *state_path* (write-tmp + rename)."""
    p = ensure_parent(state_path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, p)


def read_state(state_path: Path) -> State | None:
    p = expand(state_path)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    try:
        return State(
            pid=int(raw["pid"]),
            model_alias=str(raw["model_alias"]),
            model_path=str(raw["model_path"]),
            host=str(raw["host"]),
            port=int(raw["port"]),
            base_url=str(raw["base_url"]),
            command=[str(c) for c in raw["command"]],
            started_at=str(raw["started_at"]),
            python_executable=str(raw["python_executable"]),
            mlx_lm_version=str(raw.get("mlx_lm_version", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def clear_state(cfg: Config) -> None:
    for path in (cfg.server.state_file, cfg.server.pid_file):
        p = expand(path)
        with contextlib.suppress(FileNotFoundError):
            p.unlink()


# ---------------------------------------------------------------------------
# Process inspection
# ---------------------------------------------------------------------------


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def pid_command(pid: int) -> str:
    """Return the full command line for *pid* via ``ps``. Empty string if unavailable."""
    try:
        out = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if out.returncode != 0:
        return ""
    return out.stdout.strip()


def is_managed_process(pid: int, state: State | None = None) -> bool:
    """True if *pid* is alive and its argv looks like a managed mlx_lm server.

    If *state* is given, also requires its recorded port to be present in the
    live argv, plus at least one of: the recorded model alias (== the serving
    id we passed via ``--model``), the model path, or the path's basename.
    """
    if not pid_alive(pid):
        return False
    cmd = pid_command(pid)
    if "mlx_lm server" not in cmd and "mlx_lm.server" not in cmd and "mlx_lm" not in cmd:
        return False
    if state is not None:
        if str(state.port) not in cmd:
            return False
        bn = Path(state.model_path).name
        if (
            state.model_alias not in cmd
            and state.model_path not in cmd
            and bn not in cmd
        ):
            return False
    return True


def port_listener_pid(port: int) -> int | None:
    """Return the PID listening on TCP *port* on localhost, or None."""
    try:
        out = subprocess.run(
            ["lsof", "-nP", "-iTCP:%d" % port, "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    first = out.stdout.strip().splitlines()
    if not first:
        return None
    try:
        return int(first[0])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# mlx_lm introspection
# ---------------------------------------------------------------------------


def supported_server_flags(python_executable: str) -> set[str]:
    """Run ``python -m mlx_lm server --help`` and parse the long flags it accepts.

    Returns an empty set if mlx_lm isn't installed or help can't be parsed.
    """
    try:
        out = subprocess.run(
            [python_executable, "-m", "mlx_lm", "server", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return set()
    text = (out.stdout or "") + "\n" + (out.stderr or "")
    if "usage" not in text.lower():
        return set()
    flags = set(re.findall(r"(--[a-zA-Z][a-zA-Z0-9\-]*)", text))
    return flags


def mlx_lm_installed(python_executable: str) -> bool:
    try:
        out = subprocess.run(
            [python_executable, "-c", "import mlx_lm"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return out.returncode == 0


def mlx_lm_version(python_executable: str) -> str:
    try:
        out = subprocess.run(
            [
                python_executable,
                "-c",
                "import mlx_lm, sys; print(getattr(mlx_lm, '__version__', ''))",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    return (out.stdout or "").strip()


# ---------------------------------------------------------------------------
# Log rotation
# ---------------------------------------------------------------------------


def rotate_log_if_needed(log_path: Path, max_bytes: int, max_files: int) -> None:
    p = expand(log_path)
    if not p.exists() or max_bytes <= 0:
        return
    try:
        size = p.stat().st_size
    except OSError:
        return
    if size < max_bytes:
        return
    # log -> log.1, log.1 -> log.2, ..., drop the oldest.
    for i in range(max(1, max_files - 1), 0, -1):
        src = p.with_name(p.name + f".{i}")
        dst = p.with_name(p.name + f".{i + 1}")
        if src.exists():
            if i + 1 > max_files:
                with contextlib.suppress(FileNotFoundError):
                    src.unlink()
            else:
                with contextlib.suppress(FileNotFoundError):
                    shutil.move(str(src), str(dst))
    with contextlib.suppress(FileNotFoundError):
        shutil.move(str(p), str(p.with_name(p.name + ".1")))


def tail_lines(log_path: Path, n: int) -> list[str]:
    p = expand(log_path)
    if not p.exists():
        return []
    try:
        with open(p, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            chunk = min(size, max(8192, n * 256))
            f.seek(size - chunk)
            data = f.read()
    except OSError:
        return []
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return lines[-n:] if n > 0 else lines


# ---------------------------------------------------------------------------
# Readiness probe
# ---------------------------------------------------------------------------


def endpoint_ok(host: str, port: int) -> bool:
    url = f"http://{host}:{port}/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=READINESS_PROBE_HTTP_TIMEOUT_S) as resp:
            return 200 <= resp.status < 500
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
        return False


def wait_ready(host: str, port: int, timeout: float, *, on_verbose=None) -> bool:
    deadline = time.monotonic() + timeout
    t0 = time.monotonic()
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        if on_verbose:
            elapsed = time.monotonic() - t0
            on_verbose(f"readiness probe attempt {attempt} ({host}:{port}, {elapsed:.1f}s)")
        if endpoint_ok(host, port):
            if on_verbose:
                on_verbose(f"server is ready ({time.monotonic() - t0:.1f}s)")
            return True
        time.sleep(READINESS_PROBE_INTERVAL_S)
    if on_verbose:
        on_verbose(f"server not ready after {attempt} attempts ({time.monotonic() - t0:.1f}s)")
    return False


# ---------------------------------------------------------------------------
# Build start command
# ---------------------------------------------------------------------------

# Flags that mlx_lm.server takes as `--flag VALUE` rather than booleans, used
# only when forwarding [server.extra_args] / --extra-arg KEY=VAL pairs.
_BOOL_FLAGS = {"--trust-remote-code", "--use-default-chat-template", "--pipeline"}


def _normalize_extra_args(
    pairs: Iterable[str],
    extra_list: Iterable[str],
    supported: set[str],
) -> tuple[list[str], list[str]]:
    """Return (forwarded_args, warnings).

    *pairs* are ``KEY=VAL`` strings from ``--extra-arg``.
    *extra_list* is the raw list from ``[server.extra_args]`` (passed verbatim).
    Flags not in *supported* (when *supported* is non-empty) produce a warning.
    """
    args: list[str] = []
    warnings: list[str] = []

    for kv in pairs:
        if "=" not in kv:
            raise ServerError(
                f"--extra-arg must be KEY=VAL (got {kv!r})", exit_code=2
            )
        k, _, v = kv.partition("=")
        flag = k if k.startswith("--") else f"--{k.lstrip('-')}"
        if supported and flag not in supported:
            similar = difflib.get_close_matches(flag, supported, n=1, cutoff=0.6)
            msg = f"flag {flag} not recognized by installed mlx_lm server"
            if similar:
                msg += f" (did you mean {similar[0]}?)"
            warnings.append(msg)
        if flag in _BOOL_FLAGS:
            if v.lower() in ("1", "true", "yes", "y", "on"):
                args.append(flag)
        else:
            args.extend([flag, v])

    args.extend(list(extra_list))
    return args, warnings


def serving_invocation(model: Model) -> tuple[str, Path | None]:
    """Return ``(--model arg, cwd)`` such that ``mlx_lm server`` loads *model*
    and exposes it on the wire under the same string the client uses in the
    ``model`` JSON field.

    - Filesystem models (``directory``/``alias``): pass the directory basename
      and set ``cwd`` to its parent. ``Path(basename)`` then resolves locally,
      so ``mlx_lm`` loads it without going through Hugging Face — and the API
      id becomes the basename (matches ``mlx-manager list`` output).
    - HF-cache models: pass ``<org>/<name>`` directly and let ``mlx_lm``'s HF
      resolver locate it in the local cache. No ``cwd`` needed.
    """
    if model.source == "hf_cache":
        return model.id, None
    return model.path.name, model.path.parent


def build_command(
    cfg: Config,
    model: Model,
    host: str,
    port: int,
    extra_arg_pairs: list[str],
    supported_flags: set[str],
) -> tuple[list[str], Path | None, list[str]]:
    """Return ``(argv, cwd, warnings)`` for the mlx_lm server invocation."""
    serving_id, cwd = serving_invocation(model)
    cmd = [
        cfg.server.python_executable,
        "-m",
        "mlx_lm",
        "server",
        "--model",
        serving_id,
        "--host",
        host,
        "--port",
        str(port),
    ]
    extra, warnings = _normalize_extra_args(
        extra_arg_pairs, cfg.server.extra_args, supported_flags
    )
    cmd.extend(extra)
    return cmd, cwd, warnings


# ---------------------------------------------------------------------------
# Start / Stop
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        try:
            s.bind((host, port))
        except OSError as e:
            if e.errno in (errno.EADDRINUSE, errno.EACCES):
                return True
            return False
    return False


def start(
    cfg: Config,
    model: Model,
    *,
    host: str,
    port: int,
    extra_arg_pairs: list[str],
    replace: bool,
    on_warning=None,
    on_verbose=None,
) -> State:
    """Start the server. Returns the live State or raises ServerError."""
    state_path = expand(cfg.server.state_file)
    pid_path = expand(cfg.server.pid_file)
    log_path = expand(cfg.server.log_file)

    if not mlx_lm_installed(cfg.server.python_executable):
        raise ServerError(
            "mlx_lm is not importable from "
            f"{cfg.server.python_executable!r}; install with `pip install mlx-lm`",
            exit_code=7,
        )

    supported = supported_server_flags(cfg.server.python_executable)
    cmd, cwd, warnings = build_command(
        cfg, model, host, port, extra_arg_pairs, supported
    )
    if on_warning:
        for w in warnings:
            on_warning(w)
    if on_verbose:
        on_verbose(f"command: {' '.join(cmd)}")
        if cwd:
            on_verbose(f"cwd: {cwd}")

    existing = read_state(state_path)
    if existing is not None and is_managed_process(existing.pid, existing):
        if not replace:
            raise ServerError(
                f"server already running (pid {existing.pid}, model "
                f"{existing.model_alias!r}); use --replace to swap",
                exit_code=5,
            )
        if on_verbose:
            on_verbose(f"stopping existing server (pid {existing.pid})")
        # Stop existing before starting new.
        stop(cfg, timeout=cfg.server.stop_timeout_seconds)

    if _is_port_in_use(host, port):
        owner = port_listener_pid(port)
        owner_msg = f" (pid {owner})" if owner else ""
        raise ServerError(
            f"port {host}:{port} is already in use{owner_msg}", exit_code=1
        )

    rotate_log_if_needed(log_path, cfg.server.max_log_bytes, cfg.server.max_log_files)
    ensure_parent(log_path)
    ensure_parent(pid_path)
    ensure_parent(state_path)

    log_fd = open(log_path, "ab", buffering=0)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=str(cwd) if cwd is not None else None,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        log_fd.close()

    if on_verbose:
        on_verbose(f"spawned pid {proc.pid}")

    state = State(
        pid=proc.pid,
        model_alias=model.id,
        model_path=str(model.path),
        host=host,
        port=port,
        base_url=f"http://{host}:{port}/v1",
        command=cmd,
        started_at=_utc_now(),
        python_executable=cfg.server.python_executable,
        mlx_lm_version=mlx_lm_version(cfg.server.python_executable),
    )
    write_state(state_path, state)
    pid_path.write_text(f"{proc.pid}\n", encoding="utf-8")

    if not wait_ready(host, port, cfg.server.startup_timeout_seconds, on_verbose=on_verbose):
        # Kill the failed child; surface tail of log.
        with contextlib.suppress(ProcessLookupError):
            os.kill(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.kill(proc.pid, signal.SIGKILL)
        clear_state(cfg)
        tail = "\n".join(tail_lines(log_path, 40))
        raise ServerError(
            f"server did not become ready within "
            f"{cfg.server.startup_timeout_seconds}s\n\n--- last 40 log lines ---\n{tail}",
            exit_code=6,
        )

    return state


def stop(cfg: Config, *, timeout: int | None = None) -> State:
    """Stop the managed server. Returns the killed State or raises ServerError(4)."""
    state_path = expand(cfg.server.state_file)
    state = read_state(state_path)
    if state is None or not pid_alive(state.pid):
        clear_state(cfg)
        raise ServerError("no managed server is running", exit_code=4)

    cmd = pid_command(state.pid)
    if "mlx_lm" not in cmd:
        raise ServerError(
            f"pid {state.pid} is alive but does not look like mlx_lm server "
            f"(command: {cmd!r}); refusing to kill",
            exit_code=1,
        )
    if str(state.port) not in cmd:
        raise ServerError(
            f"pid {state.pid} command does not match recorded state "
            f"(expected port {state.port} in argv); refusing to kill",
            exit_code=1,
        )

    t = int(timeout if timeout is not None else cfg.server.stop_timeout_seconds)
    try:
        os.kill(state.pid, signal.SIGTERM)
    except ProcessLookupError:
        clear_state(cfg)
        raise ServerError("process disappeared before SIGTERM", exit_code=4)

    deadline = time.monotonic() + t
    while time.monotonic() < deadline:
        if not pid_alive(state.pid):
            break
        time.sleep(0.2)
    else:
        with contextlib.suppress(ProcessLookupError):
            os.kill(state.pid, signal.SIGKILL)

    clear_state(cfg)
    return state


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def status_dict(cfg: Config) -> dict[str, Any]:
    state_path = expand(cfg.server.state_file)
    state = read_state(state_path)
    if state is None:
        return {
            "running": False,
            "pid": None,
            "model_alias": None,
            "model_path": None,
            "host": None,
            "port": None,
            "base_url": None,
            "command": [],
            "started_at": None,
            "python_executable": None,
            "mlx_lm_version": "",
            "uptime_seconds": 0,
            "endpoint_ok": False,
            "stale": False,
        }
    managed = is_managed_process(state.pid, state)
    uptime = 0
    if state.started_at:
        try:
            t0 = datetime.strptime(state.started_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            uptime = int((datetime.now(timezone.utc) - t0).total_seconds())
        except ValueError:
            uptime = 0
    return {
        **state.to_dict(),
        "running": managed,
        "uptime_seconds": uptime if managed else 0,
        "endpoint_ok": endpoint_ok(state.host, state.port) if managed else False,
        "stale": (not managed),
    }
