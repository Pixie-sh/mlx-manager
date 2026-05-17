# Build `mlx-manager`: a headless MLX server controller

## Mission

Build a Python 3.11+ CLI named `mlx-manager` that wraps `python -m mlx_lm.server` on a headless Apple Silicon Mac (M3 Max, 128 GB unified memory, SSH-only). It must start/stop/restart the server with a chosen local model, report status, tail logs, run a self-diagnostic, and print copy/paste-ready provider snippets for **OpenCode** (primary) and **Claude Code / LiteLLM** (secondary, only if verifiable).

The brief is **prescriptive** — when a choice is made below, do not relitigate it. When the brief says "verify before deciding," the model **must** run the verification command and use the result, not guess.

---

## Hard constraints

1. Python **3.11+**, stdlib-first. Allowed third-party deps: `tomli-w` (TOML write only — `tomllib` is stdlib for read). No `typer`, no `click`, no `rich`, no `pydantic`. Use `argparse` + plain `print`. Justify any extra dep in the README.
2. Single console script: `mlx-manager`. Packaged via `pyproject.toml`, installable with `pip install -e .` or `uv pip install -e .`.
3. Default bind **`127.0.0.1`**. Binding `0.0.0.0` requires `--bind-all` and prints a warning to stderr.
4. **Never** kill a PID without first confirming its current `argv` contains `mlx_lm.server` *and* matches the managed state file. Reused-PID safety is non-negotiable.
5. All filesystem paths expand `~` and `$VAR`. No hardcoded `/Users/rs` anywhere except README examples that say so.
6. No Docker, no LM Studio, no Ollama, no database, no GUI, no `sudo`, no `launchd` in v1 (stretch goal only).
7. Exit codes: `0` success, `1` generic failure, `2` usage error, `3` config error, `4` not-running (for `status`/`stop`), `5` already-running (for `start` without `--replace`), `6` startup-timeout, `7` `mlx_lm` missing.
8. All commands that mutate state (`start`, `stop`, `restart`) acquire an exclusive lock on `lock_file` (e.g. `fcntl.flock`). Lock timeout: 10 s, then fail with exit 1.

---

## Out of scope (do not build)

Model downloading, auth, multi-tenancy, web UI, supervisor frameworks, model deletion/mutation, GPU monitoring beyond what `mlx-lm.server` already exposes.

---

## Build order

### Phase 1 — MVP (must work end-to-end)

`config` load + default-write, `list`, `list --json`, `start`, `stop`, `restart`, `status`, `status --json`, `logs`, `doctor`, `config opencode`.

### Phase 2 — Stretch

`config claude-code` (with LiteLLM fallback), `install-launchd`/`uninstall-launchd`/`launchd-status`.

Phase 2 may **not** block or destabilize Phase 1. If Claude Code support cannot be verified offline, ship the LiteLLM fallback only and document the gap.

---

## File layout

```
mlx_manager/
  __init__.py        # __version__
  __main__.py        # python -m mlx_manager → cli.main()
  cli.py             # argparse dispatch, exit codes, --json plumbing
  config.py          # TOML load/write, defaults, path expansion
  models.py          # discovery, alias resolution, HF cache parsing
  server.py          # Popen lifecycle, PID/state/lock/log files, readiness probe
  providers.py       # OpenCode, Claude Code, LiteLLM snippet generation
  paths.py           # ~ and $VAR expansion, mkdir -p helpers
tests/
  conftest.py        # tmp_path fixtures with fake model dirs
  test_config.py
  test_models.py
  test_server_safety.py   # PID reuse, stale PID, lock
  test_providers.py
  test_cli_json.py
pyproject.toml
README.md
```

---

## CLI surface (authoritative)

| Command | Purpose | Key flags | Exit on |
|---|---|---|---|
| `mlx-manager list` | Show discovered models | `--json` | 0, 3 |
| `mlx-manager start` | Launch server | `--model <id\|path>`, `--host`, `--port`, `--replace`, `--bind-all`, `--extra-arg KEY=VAL` (repeatable) | 0, 5, 6, 7 |
| `mlx-manager stop` | Stop managed server | `--timeout <s>` | 0, 4 |
| `mlx-manager restart` | Stop + start | same as `start` | 0, 6, 7 |
| `mlx-manager status` | Report current state | `--json` | 0, 4 |
| `mlx-manager logs` | Tail server log | `--tail <n>` (default 100), `-f` | 0, 4 |
| `mlx-manager config opencode` | Print snippet | `--model <id>`, `--format full\|merge` (default `merge`) | 0, 3 |
| `mlx-manager config claude-code` | Print snippet or fallback | `--model <id>` | 0, 3 |
| `mlx-manager doctor` | Diagnostics | `--json` | 0, 1 |

All commands respect `--config <path>` (default `~/.config/mlx-manager/config.toml`) and `--verbose`. Human output goes to stdout; warnings/errors to stderr.

---

## Config schema

Path: `~/.config/mlx-manager/config.toml`. Created on first run if missing.

```toml
[server]
host = "127.0.0.1"
port = 8080
log_file = "~/services/mlx/logs/mlx-lm.server.log"
pid_file = "~/services/mlx/mlx-lm.server.pid"
state_file = "~/.local/state/mlx-manager/state.json"
lock_file = "~/.local/state/mlx-manager/lock"
python_executable = "python3"
extra_args = []                 # forwarded to mlx_lm.server verbatim
startup_timeout_seconds = 120
stop_timeout_seconds = 15
max_log_bytes = 10_485_760      # 10 MiB
max_log_files = 5

[models]
directories = ["~/models/mlx", "~/.cache/huggingface/hub"]
default_model = ""

[models.aliases]
# qwen3-8b-4bit = "~/models/mlx/qwen3-8b-4bit"

[providers]
base_url = ""                   # if empty, derived from server.host:port
api_key = "mlx-local"
provider_name = "mlx-local"
```

Validation rules:
- Unknown top-level table → exit 3 with the offending key.
- `port` outside 1024–65535 → exit 3.
- Alias values must resolve to an existing directory at load time, **or** be tolerated with a warning if discovery later finds them (decide and document one behavior; recommended: tolerate, warn at `doctor`).

---

## State file (authoritative shape)

`state_file` is JSON, written atomically (write-tmp + rename). Schema:

```json
{
  "pid": 12345,
  "model_alias": "qwen3-8b-4bit",
  "model_path": "/Users/rs/models/mlx/qwen3-8b-4bit",
  "host": "127.0.0.1",
  "port": 8080,
  "base_url": "http://127.0.0.1:8080/v1",
  "command": ["python3", "-m", "mlx_lm.server", "--model", "...", "--host", "...", "--port", "..."],
  "started_at": "2026-05-15T09:04:11Z",
  "python_executable": "python3",
  "mlx_lm_version": "0.x.y"
}
```

`status --json` returns this object plus `{"running": bool, "uptime_seconds": int, "endpoint_ok": bool}`. When not running, `running: false` and the rest of the fields are present but may be stale — explicitly mark with `"stale": true` if the PID is dead.

---

## Model discovery

A directory is a candidate model iff it contains **`config.json` AND at least one of**: `model.safetensors`, a `model-*.safetensors` shard, or `weights.safetensors`. Tokenizer files are bonus signals, not requirements (some MLX repacks omit them).

**Hugging Face cache** (`~/.cache/huggingface/hub/models--<org>--<name>/snapshots/<rev>/`): resolve to the snapshot directory. Display name: `<org>/<name>` (or just `<name>` if `<org>` is `mlx-community`, since that's the common case). Never display the bare snapshot hash.

**Aliases** in `[models.aliases]` take precedence over discovered names — they are the canonical user-facing IDs. `start --model X` resolves in this order: alias → discovered display name → absolute path.

`list` output (human):
```
ALIAS                   PATH
qwen3-8b-4bit           /Users/rs/models/mlx/qwen3-8b-4bit
mlx-community/Llama-3.2-3B-Instruct-4bit
                        /Users/rs/.cache/huggingface/hub/.../snapshots/abc123
```

`list --json`:
```json
[
  {"id": "qwen3-8b-4bit", "path": "/Users/rs/models/mlx/qwen3-8b-4bit", "source": "alias"},
  {"id": "mlx-community/Llama-3.2-3B-Instruct-4bit", "path": "...", "source": "hf_cache"}
]
```

---

## Server lifecycle contract

**Before constructing the start command**, run `python3 -m mlx_lm.server --help` once and parse its supported flags. Only forward flags the installed version accepts. Unknown flags from `[server.extra_args]` or `--extra-arg` pass through verbatim (user's responsibility).

**Start sequence**:
1. Acquire lock.
2. If state file says running and PID is alive and `argv` matches → exit 5 unless `--replace`.
3. If port is bound by an unrelated process → exit 1 with the conflicting PID if discoverable.
4. `Popen` with `stdout`/`stderr` appended to `log_file` (rotate first if over `max_log_bytes`; keep `max_log_files`).
5. Detach so the child survives the parent. Use `start_new_session=True`.
6. Write PID file and state file atomically.
7. Poll `GET http://host:port/v1/models` every 500 ms up to `startup_timeout_seconds`. On success → print summary, exit 0. On timeout → kill the child, print last 40 log lines, exit 6.
8. Release lock.

**Stop sequence**:
1. Acquire lock.
2. Load state. If no PID or PID dead → clean up files, exit 4.
3. Verify `/proc`-equivalent on macOS (`ps -p <pid> -o command=`) contains `mlx_lm.server`. If not → refuse to kill, exit 1 with diagnostic.
4. `SIGTERM`, wait up to `stop_timeout_seconds`, then `SIGKILL`.
5. Remove PID + state files. Release lock.

**Readiness probe** uses stdlib `urllib.request` with a 2 s per-attempt timeout — do not pull in `requests` or `httpx`.

---

## `doctor` checks

Each check prints `OK` / `WARN` / `FAIL` with a one-line reason. Exit 0 if no FAILs.

- Python executable resolves and reports version.
- `import mlx_lm` succeeds (run in a subprocess to avoid polluting the manager's interpreter).
- `python -m mlx_lm.server --help` exits 0; report parsed flag count.
- Each `[models.directories]` exists and is readable; report model count per dir.
- Parents of `log_file`, `pid_file`, `state_file`, `lock_file` are writable (create them if missing).
- Port reachable: if state says running, the endpoint answers; else port is bindable.
- Platform: `platform.machine() == "arm64"` and `platform.system() == "Darwin"` — WARN otherwise.

---

## Provider snippets

### OpenCode (primary, default format `merge`)

```json
{
  "provider": {
    "mlx-local": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "MLX Local",
      "options": {
        "baseURL": "http://127.0.0.1:8080/v1",
        "apiKey": "mlx-local"
      },
      "models": {
        "<model-id>": { "name": "<model-id>" }
      }
    }
  }
}
```

`--format full` wraps the above inside a complete `opencode.json`-shaped document. Use the running server's `host:port` if a server is running; otherwise use `[providers].base_url` or fall back to `[server].host:port`.

### Claude Code (secondary, verification-dependent)

If Claude Code documentation or local installation confirms support for OpenAI-compatible base URLs at the time of build, emit that config. Otherwise emit:

1. An `env`-style snippet **labeled "experimental — verify against your Claude Code version"**:
   ```bash
   export OPENAI_API_KEY="mlx-local"
   export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
   ```
   Do **not** emit `ANTHROPIC_BASE_URL` unless verified.
2. A LiteLLM fallback marked as the recommended path:
   ```yaml
   model_list:
     - model_name: mlx-local/<model-id>
       litellm_params:
         model: openai/<model-id>
         api_base: http://127.0.0.1:8080/v1
         api_key: mlx-local
   ```
   With a one-paragraph README pointer explaining how to run LiteLLM in front of MLX.

---

## Testing

Tests must run **without** `mlx_lm` installed and **without** starting a real server. Strategy:

- Fixture model dirs under `tmp_path` with synthetic `config.json` + zero-byte `model.safetensors`.
- Fake HF cache layout in `tmp_path` to exercise snapshot resolution.
- Server lifecycle tests use a dummy long-running subprocess (e.g. `python -c "import time; time.sleep(300)"`) as a stand-in; assert PID-match safety logic against this stand-in.
- Lock tests: spawn two manager invocations concurrently, assert one wins.
- JSON output tests assert the documented schemas (`list --json`, `status --json`, `doctor --json`).
- Snippet tests pin exact JSON output for OpenCode and exact YAML for LiteLLM.

CI-friendly: `pytest -q` from repo root, no network, no real models.

---

## Definition of Done

This script must run clean on the target Mac (assuming `mlx_lm` is installed and at least one model is available):

```bash
pip install -e .
mlx-manager --help
mlx-manager doctor
mlx-manager list
mlx-manager list --json | python -m json.tool
mlx-manager config opencode --model <discovered-id>
mlx-manager config claude-code --model <discovered-id>
mlx-manager start --model <discovered-id>
mlx-manager status
mlx-manager status --json | python -m json.tool
curl -s http://127.0.0.1:8080/v1/models | python -m json.tool
mlx-manager logs --tail 20
mlx-manager restart --model <other-id>      # if a second model exists
mlx-manager stop
mlx-manager status        # should report not running, exit 4
pytest -q
```

Every line either exits 0 or with the documented intentional non-zero code. The README documents how to run each.

---

## README requirements

- Install (one block: `uv pip install -e .` and `pip install -e .`).
- Quick start (5-line example).
- Full config reference (copy of the TOML above with comments).
- Discovery rules (1 paragraph).
- "Using with OpenCode" — drop-in snippet.
- "Using with Claude Code" — what's verified, what's experimental, and the LiteLLM recipe.
- Troubleshooting (`doctor`, common failures, log file location).
- Optional launchd (design sketch even if not implemented).

---

## What to verify before writing code

1. `python3 --version` (need ≥ 3.11 for `tomllib`).
2. `python3 -m mlx_lm.server --help` if `mlx_lm` is installed — record the supported flags and reference them in `server.py`. If not installed, code defensively and surface install instructions via `doctor`.
3. Check whether any OpenCode config already lives under `~/.config/opencode/` and mirror its real schema if so.
4. Check installed Claude Code CLI (`claude --version` / config under `~/.claude/`) to confirm or deny OpenAI-compatible support before emitting Claude Code snippets.

If any of (2)–(4) cannot be verified, document the assumption you made in the README under "Assumptions".
