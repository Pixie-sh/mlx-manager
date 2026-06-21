# mlx-manager — Technical Knowledge Base

> Maintainer reference. Project version 0.1.0. MIT license. Author: rs. The README and source code are canonical when details differ.

---

## 1. Project Overview

**mlx-manager** is a Python CLI tool (v0.1.0) that wraps `mlx_lm server` to run a local MLX HTTP server headlessly on Apple Silicon Macs. Designed for SSH-only headless machines where you need to manage local LLM inference without a GUI.

| Attribute | Value |
|-----------|-------|
| Language | Python ≥ 3.11 |
| Platform | Darwin / arm64 (Apple Silicon only) |
| License | MIT |
| Author | rs |
| Third-party deps | `tomli-w` directly; `mlx_lm` is required in the selected runtime for server/bot usage |
| Total source | Small focused package across CLI, server, model, provider, benchmark, bot, and shim modules |
| Total tests | Pytest suite under `tests/` with faked external calls |

### Design Philosophy

- **Stdlib-first**: Only `tomli-w` as a third-party dependency. Uses `tomllib` (stdlib since Python 3.11) for TOML reading, `argparse` for CLI, `urllib` for HTTP probes, `fcntl` for file locking.
- **No daemon, no database, no web UI**: Just `argparse`, a single state file, an `fcntl` lock, and `urllib`.
- **No external frameworks**: No `typer`, `click`, `rich`, `pydantic`, `requests`, `httpx`.

---

## 2. Architecture

### Module Map

| Module | Lines | Responsibility |
|--------|-------|---------------|
| `cli.py` | ~1,400 | Main entry point, argparse dispatch, all command handlers |
| `config.py` | ~260 | TOML loading/writing, validation, defaults |
| `models.py` | 149 | Model discovery (filesystem + HF cache + aliases) |
| `paths.py` | 23 | Path expansion (~ and $VAR) |
| `providers.py` | 177 | OpenCode/Claude Code/LiteLLM snippet generation |
| `server.py` | ~850 | Process lifecycle, PID management, locks, log rotation |
| `benchmark.py` | 259 | Performance measurement (TTFT, decode tok/s, throughput) |
| `bot.py` | ~320 | In-process troubleshooting chat with cached local model selection |
| `_server_shim.py` | small | Best-effort shim for truncated tool-call finish reasons |

### Data Flow

```
User command → cli.py dispatch → loads config.py → resolves model via models.py
    → server.py spawns/controls process → providers.py generates snippets
    → benchmark.py measures performance
```

### Key Data Structures

```python
# Config (frozen dataclass)
Config(path, server: ServerCfg, models: ModelsCfg, providers: ProvidersCfg)

# Server state (written to state.json)
State(pid, model_alias, model_path, host, port, base_url, command[], started_at, python_executable, mlx_lm_version)

# Discovered model
Model(id, path: Path, source: Literal["alias", "directory", "hf_cache"])

# Provider context
ProviderContext(base_url, api_key, provider_name, model_id)

# Benchmark result
BenchmarkSummary(endpoint, model, requests_total, requests_ok, concurrency, wall_seconds, aggregate_decode_tps, ...)
```

---

## 3. CLI Commands

| Command | Purpose | Key Flags | Exit Codes |
|---------|---------|-----------|------------|
| `list` | Show discovered models | `--json` | 0, 3 |
| `start` | Launch server | `--model`, `--host`, `--port`, `--replace`, `--bind-all`, `--extra-arg` | 0, 5, 6, 7 |
| `load` | Guided start from discovered models | `--host`, `--port`, `--replace`, `--bind-all`, `--extra-arg` | 0, 2, 3, 5, 6, 7 |
| `stop` | Stop managed server | `--timeout` | 0, 4 |
| `restart` | Stop + start | same as start | 0, 6, 7 |
| `status` | Report current state | `--json` | 0, 4 |
| `logs` | Tail server log | `--tail`, `-f` | 0, 4 |
| `config opencode` | Print provider snippet | `--model`, `--format`, `--apply`, `--overwrite` | 0, 3 |
| `config claude-code` | Print Claude/LiteLLM snippet | `--model` | 0, 3 |
| `config warp` | Print WARP BYOK/custom-provider values | `--model`, `--remote` | 0, 3 |
| `doctor` | Run diagnostics and optional safe fixes | `--json`, `--fix` | 0, 1 |
| `bot` | Chat with a local troubleshooting assistant | `--model`, `--choose`, `--max-tokens`, `--temperature`, `--no-context` | 0, 1, 7 |
| `benchmark` | Measure performance | `--model`, `--endpoint`, `--prompt`, `--max-tokens`, `--requests`, `--concurrency`, `--warmup`, `--json` | 0, 1 |

### Exit Code Reference

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic failure |
| 2 | Usage error |
| 3 | Config error |
| 4 | Not running (status/stop) |
| 5 | Already running (start without --replace) |
| 6 | Startup timeout |
| 7 | mlx_lm missing |

---

## 4. Configuration System

### Config File Location

Default: `~/.config/mlx-manager/config.toml` (auto-created on first run)

### TOML Schema

```toml
[server]
host = "127.0.0.1"              # Default bind address
port = 8080                      # Default port (1024-65535 validated)
log_file = "~/services/mlx/logs/mlx-lm.server.log"
pid_file = "~/services/mlx/mlx-lm.server.pid"
state_file = "~/.local/state/mlx-manager/state.json"
lock_file = "~/.local/state/mlx-manager/lock"
python_executable = "python3"    # Which Python to use
extra_args = []                  # Forwarded to mlx_lm.server verbatim
startup_timeout_seconds = 120    # Max wait for server readiness
stop_timeout_seconds = 15        # SIGTERM wait before SIGKILL
max_log_bytes = 10485760         # 10 MiB rotation threshold
max_log_files = 5                # Kept rotated log files
patch_tool_calls = true          # Best-effort shim for truncated tool calls

[models]
directories = [                  # Roots to scan for models
  "~/.mlx-manager/models",
  "~/.models/mlx",
  "~/models/mlx",
  "~/.cache/huggingface/hub",
  "~/.lmstudio/models",
]
default_model = ""               # Auto-select on start without --model

[models.aliases]
# qwen3-8b-4bit = "~/models/mlx/qwen3-8b-4bit"

[providers]
base_url = ""                    # Empty → derived from server.host:port
api_key = "mlx-local"            # Dummy key for local provider
provider_name = "mlx-local"      # Provider label

[bot]
model = "mlx-community/gemma-4-e2b-it-4bit"
cache_dir = "~/.mlx-manager/bot"
max_tokens = 1024
temperature = 0.7
```

### Validation Rules

- Unknown top-level tables → exit 3 with error
- Unknown keys within known tables → exit 3 with error
- Port must be integer in range 1024–65535
- `extra_args` must be list of strings
- `directories` must be list of strings
- `aliases` must be a table (dict)
- Aliases pointing at non-existent paths are tolerated (warned in `doctor`)

### Config Loading

1. If config file doesn't exist, write defaults automatically
2. Read existing TOML with `tomllib` (stdlib)
3. Validate against known schema
4. Deep-merge user values over defaults
5. Construct frozen dataclasses

---

## 5. Model Discovery

### Discovery Rules

A directory is a candidate model iff it contains **`config.json`** AND at least one of:
- `model.safetensors` (single weights file)
- `model-*.safetensors` (sharded weights)
- `weights.safetensors` (alternative naming)

Tokenizer files are bonus signals, not requirements.

### Supported Layouts

| Layout | Example Path | Discovered ID | Source Tag |
|--------|--------------|---------------|------------|
| Flat | `~/models/mlx/<name>/` | `<name>` | `directory` |
| Nested (LM Studio) | `~/.lmstudio/models/<publisher>/<name>/` | `<name>` | `directory` |
| HF Cache | `~/.cache/huggingface/hub/models--<org>--<name>/snapshots/<rev>/` | `<org>/<name>` | `hf_cache` |

### Discovery Algorithm

1. Walk each configured root recursively (max depth 4)
2. Skip hidden directories (prefixed with `.`)
3. Special-case HF cache repos (`models--<org>--<name>`)
4. For HF cache: pick the newest snapshot with valid weights
5. Short-circuit recursion when a model is found
6. Deduplicate by ID (alias > directory > hf_cache priority)

### Alias Resolution Order

When `start --model X` is called, resolve `X` in this order:
1. Check `[models.aliases]` — if found, use alias target
2. Check discovered model IDs — if found, use discovered path
3. Treat as absolute filesystem path — validate it's a model dir

---

## 6. Server Lifecycle

### Start Sequence

```
1. Acquire fcntl exclusive lock (10s timeout)
2. Check if server already running (PID alive + argv match)
   → If running and no --replace: exit 5
   → If running and --replace: stop existing first
3. Check port availability (socket bind test + lsof)
4. Rotate log file if over max_log_bytes
5. Build command: python -m mlx_lm server --model <id> --host <h> --port <p> [+ extra args]
6. Spawn via subprocess.Popen (detached with start_new_session=True)
7. Write state.json atomically (write-tmp + rename)
8. Write pid_file
9. Poll GET http://host:port/v1/models every 500ms up to startup_timeout
   → Ready: print summary, exit 0
   → Timeout: kill child, print last 40 log lines, exit 6
10. Release lock
```

### Stop Sequence

```
1. Acquire fcntl exclusive lock
2. Load state file
   → No state or dead PID: clean up files, exit 4
3. Verify PID argv contains mlx_lm AND recorded port
   → Mismatch: refuse to kill, exit 1
4. Send SIGTERM, wait up to stop_timeout_seconds
5. If still alive: send SIGKILL
6. Remove state + pid files
7. Release lock
```

### Readiness Probe

- Polls `GET http://host:port/v1/models` every 500ms
- Uses stdlib `urllib.request` with 2s per-attempt timeout
- Returns True on 2xx/3xx/4xx status codes


### Serving Invocation (`serving_invocation()`)

The `serving_invocation(model)` function in `server.py` determines how to pass the model to `mlx_lm server` so the HTTP API exposes the same id string that `mlx-manager list` shows and that clients use in the `model` JSON field.

- **Filesystem models** (`directory`/`alias` source): passes the directory basename as `--model <basename>` and sets `cwd` to the parent directory. `Path(basename)` then resolves locally within that cwd, so `mlx_lm` loads the model without contacting HuggingFace — and the API id becomes the basename.
- **HF-cache models** (`hf_cache` source): passes `<org>/<name>` directly as `--model <org>/<name>` with no cwd change. `mlx_lm`'s built-in HF resolver locates the snapshot in the local cache.

This is the load-bearing detail that makes a bare `"GLM-4.7-Flash-MLX-6bit"` work as the model field in an OpenCode config, even though the actual model files live deep in `~/.lmstudio/models/publisher/GLM-4.7-Flash-MLX-6bit/`.

### Module Invocation Form

The server is spawned with `python -m mlx_lm server` (space-separated, not dotted `mlx_lm.server`). The dotted form is deprecated in newer mlx-lm releases. `is_managed_process()` checks for `mlx_lm server`, `mlx_lm.server`, or bare `mlx_lm` in the live argv to cover both forms during transition.

---

## 7. Safety Mechanisms

### PID Reuse Protection

The system **never kills a PID without verifying**:
1. PID is alive (`os.kill(pid, 0)`)
2. PID's argv contains `mlx_lm` (via `ps -p <pid>`)
3. PID's argv contains the recorded port number
4. PID's argv contains the model alias/path/basename

If any check fails, the operation is refused. This prevents killing unrelated processes that happen to have recycled PIDs.

### Lock Mechanism

- Uses `fcntl.flock()` for exclusive file locking
- Lock file at `~/.local/state/mlx-manager/lock`
- 10-second acquisition timeout
- Automatically released on completion or error
- Prevents concurrent `start`/`stop`/`restart` from corrupting state

### Atomic Writes

All state file writes use the write-tmp-then-rename pattern:
```python
tmp = path.with_suffix(path.suffix + ".tmp")
# write to tmp
os.replace(tmp, path)  # atomic on POSIX
```

### Log Rotation

- Appends stdout/stderr to configured log file
- Rotates when file exceeds `max_log_bytes` (default 10 MiB)
- Keeps up to `max_log_files` rotated copies (default 5)
- Oldest rotated file is deleted when limit exceeded

---

## 8. Provider Integration

### OpenCode (Primary)

Generates JSON provider blocks for `~/.config/opencode/opencode.json`:

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
        "qwen3-8b-4bit": { "name": "qwen3-8b-4bit" }
      }
    }
  }
}
```

**Apply modes:**
- **Merge** (default): Refreshes npm/name/options, adds missing models, preserves user-tuned per-model fields (limits, custom names)
- **Overwrite**: Replaces entire provider block
- Always writes `.bak` backup before modifying

### Claude Code / LiteLLM (Secondary)

Claude Code doesn't document OpenAI-compatible base-URL routing (verified May 2026). Two paths offered:

1. **Experimental env vars** (labeled as such):
   ```bash
   export OPENAI_API_KEY="mlx-local"
   export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
   ```

2. **Recommended: LiteLLM proxy** — runs LiteLLM in front of MLX:
   ```yaml
   model_list:
     - model_name: mlx-local/qwen3-8b-4bit
       litellm_params:
         model: openai/qwen3-8b-4bit
         api_base: http://127.0.0.1:8080/v1
         api_key: mlx-local
   ```

### WARP Terminal (Manual BYOK)

WARP setup emits deterministic OpenAI-compatible fields for the WARP custom
provider/BYOK settings UI:

```text
# WARP Terminal custom AI provider
# Paste these values into WARP's BYOK/custom provider settings.
Provider type: OpenAI-compatible
Provider name: mlx-local
Base URL: http://127.0.0.1:8080/v1
API key: mlx-local
Model: qwen3-8b-4bit
```

The implementation intentionally does not write WARP config files. The local AI
provider file schema is not verified, so snippet output is the safe integration
surface until a stable schema and ownership marker strategy are available.

---

## 9. Benchmark System

### What It Measures

| Metric | Description |
|--------|-------------|
| TTFT | Time-to-first-token (latency from request to first token) |
| Decode tok/s | Per-stream decoding throughput |
| Total time | End-to-end request duration |
| Aggregate tok/s | Total completion tokens across all parallel streams ÷ wall-clock |

### How It Works

1. Sends warmup requests sequentially (not counted in measurement)
2. Fires `requests` total at `concurrency` parallel streams
3. Each request uses streaming chat-completions (`stream: true`)
4. Parses SSE chunks to extract:
   - TTFT (time from request to first content chunk)
   - Completion tokens (from `usage` field or chunk count fallback)
   - Finish reason
5. Computes percentiles (p50, p95) for TTFT, decode tok/s, total time

### Key Implementation Details

- Uses `concurrent.futures.ThreadPoolExecutor` for parallelism
- Uses stdlib `urllib.request` (no external HTTP libraries)
- Handles reasoning models (GLM-4.7 etc.) where tokens appear in `delta.reasoning`
- Falls back to chunk counting when server doesn't emit `usage`
- Default prompt is a generation-bound technical explanation (~50 words)

---

## 10. Testing Strategy

### Principles

- Tests run **without** `mlx_lm` installed
- Tests run **without** starting a real server
- All model directories are synthetic (fake `config.json` + zero-byte weights)
- Server lifecycle tests use dummy subprocesses (`python -c "sleep 3600"`)

### Test Suite

| File | Tests | Coverage |
|------|-------|----------|
| `test_config.py` | 7 | TOML loading, validation, defaults, port range |
| `test_models.py` | 7 | Discovery (flat/nested/HF cache), aliases, deduplication |
| `test_server_safety.py` | 11 | Lock serialization, PID verification, reused-PID refusal, log rotation |
| `test_providers.py` | 11 | OpenCode snippets, merge/overwrite, Claude Code/LiteLLM |
| `test_cli_json.py` | 7 | CLI JSON output shapes, exit codes |
| `test_benchmark.py` | 5 | TTFT measurement, concurrency, summary stats, validation |

### Fixtures

- `fake_models_root`: Plain directory with two model subdirs + decoy
- `fake_hf_cache`: Synthetic HF cache with valid/invalid repos
- `fake_lmstudio_root`: LM Studio nested layout (publisher/model)
- `cfg_factory`: Builds test Config objects rooted in `tmp_path`
- `fake_server`: In-process ThreadingHTTPServer with configurable SSE responses

---

## 11. Future Work

### Documented Stretch Goals

1. **launchd integration** (`install-launchd`/`uninstall-launchd`/`launchd-status`)
   - Would write `~/Library/LaunchAgents` plist
   - Auto-start on user login
   - `bootstrap`/`bootout` via `launchctl`

### Out of Scope (Explicitly Not Built)

- Serving-model downloading (the bot may download its own assistant model once)
- Authentication
- Multi-tenancy
- Web UI
- Supervisor frameworks
- Model deletion/mutation
- GPU monitoring beyond what mlx-lm.server exposes
- Docker support
- Non-Apple-Silicon platforms

---

## 12. Assumptions & Verified Facts

### Historical Build-Time Notes

- Initial development verified Python and `mlx_lm server --help` locally.
- Claude Code OpenAI-compatible base URL routing was not documented at initial
  release time; README documents the LiteLLM fallback path.

### Design Assumptions

- Target platform is Darwin/arm64 (Apple Silicon)
- `mlx_lm` is installed in the same interpreter mlx-manager uses
- SSH-only headless access pattern
- Single-user scenario (no multi-tenancy)
- Serving models are pre-loaded locally; the bot assistant model may download once
  into `[bot].cache_dir`.

---

## Appendix: File Inventory

```
mlx-manager/
├── pyproject.toml          # Build config, dependencies, entry point
├── README.md               # User documentation
├── mlx_manager/
│   ├── __init__.py         # Version string
│   ├── __main__.py         # python -m mlx_manager entry
│   ├── cli.py              # CLI dispatch and command handlers
│   ├── config.py           # TOML config loading/writing
│   ├── models.py           # Model discovery + resolution
│   ├── paths.py            # Path expansion utilities
│   ├── providers.py        # Provider snippet generation
│   ├── server.py           # Process lifecycle management
│   ├── benchmark.py        # Performance benchmarking
│   ├── bot.py              # Local troubleshooting assistant
│   └── _server_shim.py     # Tool-call finish-reason shim
├── tests/
│   ├── conftest.py         # Shared fixtures
│   └── test_*.py           # Config, model, server, provider, CLI, bot, health, shim, and benchmark tests
└── CHANGELOG.md            # Release notes
```
