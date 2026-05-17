# mlx-manager — Technical Knowledge Base

> Generated 2026-05-15. Project version 0.1.0. MIT license. Author: rs.

---

## 1. Project Overview

**mlx-manager** is a Python CLI tool (v0.1.0) that wraps `python -m mlx_lm.server` to run a local MLX HTTP server headlessly on Apple Silicon Macs. Designed for SSH-only headless machines where you need to manage local LLM inference without a GUI.

| Attribute | Value |
|-----------|-------|
| Language | Python ≥ 3.11 |
| Platform | Darwin / arm64 (Apple Silicon only) |
| License | MIT |
| Author | rs |
| Third-party deps | tomli-w only (TOML writing) |
| Total source | ~1,959 lines across 8 modules |
| Total tests | ~72 tests across 7 files |

### Design Philosophy

- **Stdlib-first**: Only `tomli-w` as a third-party dependency. Uses `tomllib` (stdlib since Python 3.11) for TOML reading, `argparse` for CLI, `urllib` for HTTP probes, `fcntl` for file locking.
- **No daemon, no database, no web UI**: Just `argparse`, a single state file, an `fcntl` lock, and `urllib`.
- **No external frameworks**: No `typer`, `click`, `rich`, `pydantic`, `requests`, `httpx`.

---

## 2. Architecture

### Module Map

| Module | Lines | Responsibility |
|--------|-------|---------------|
| `cli.py` | 621 | Main entry point, argparse dispatch, all command handlers |
| `config.py` | 196 | TOML loading/writing, validation, defaults |
| `models.py` | 149 | Model discovery (filesystem + HF cache + aliases) |
| `paths.py` | 23 | Path expansion (~ and $VAR) |
| `providers.py` | 177 | OpenCode/Claude Code/LiteLLM snippet generation |
| `server.py` | 634 | Process lifecycle, PID management, locks, log rotation |
| `benchmark.py` | 259 | Performance measurement (TTFT, decode tok/s, throughput) |

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
| `stop` | Stop managed server | `--timeout` | 0, 4 |
| `restart` | Stop + start | same as start | 0, 6, 7 |
| `status` | Report current state | `--json` | 0, 4 |
| `logs` | Tail server log | `--tail`, `-f` | 0, 4 |
| `config opencode` | Print provider snippet | `--model`, `--format`, `--apply`, `--overwrite` | 0, 3 |
| `config claude-code` | Print Claude/LiteLLM snippet | `--model` | 0, 3 |
| `doctor` | Run diagnostics | `--json` | 0, 1 |
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

[models]
directories = [                  # Roots to scan for models
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
5. Build command: python -m mlx_lm.server --model <id> --host <h> --port <p> [+ extra args]
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
3. Verify PID argv contains mlx_lm.server AND recorded port
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

---

## 7. Safety Mechanisms

### PID Reuse Protection

The system **never kills a PID without verifying**:
1. PID is alive (`os.kill(pid, 0)`)
2. PID's argv contains `mlx_lm.server` (via `ps -p <pid>`)
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

2. **mlx_lm module name change**
   - Currently uses deprecated `python -m mlx_lm.server` form
   - Future mlx-lm may drop hyphenated module form
   - Will need to swap to `python -m mlx_lm server` in `server.py:build_command`

### Out of Scope (Explicitly Not Built)

- Model downloading
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

### Verified at Build Time

- `python3 --version` reported 3.12.6
- `python3 -m mlx_lm.server --help` exits 0; known long flags recorded
- `~/.config/opencode/opencode.json` exists; emitted provider block matches its schema
- `claude --version` reports 2.1.128; OpenAI-compatible base URL support not documented

### Design Assumptions

- Target platform is Darwin/arm64 (Apple Silicon)
- `mlx_lm` is installed in the same interpreter mlx-manager uses
- SSH-only headless access pattern
- Single-user scenario (no multi-tenancy)
- Models are pre-loaded locally (no downloading)

---

## Appendix: File Inventory

```
mlx-manager/
├── pyproject.toml          # Build config, dependencies, entry point
├── README.md               # User documentation
├── prompt.md               # Original design brief (323 lines)
├── mlx_manager/
│   ├── __init__.py         # Version string
│   ├── __main__.py         # python -m mlx_manager entry
│   ├── cli.py              # CLI dispatch, all command handlers (621 lines)
│   ├── config.py           # TOML config loading/writing (196 lines)
│   ├── models.py           # Model discovery + resolution (149 lines)
│   ├── paths.py            # Path expansion utilities (23 lines)
│   ├── providers.py        # Provider snippet generation (177 lines)
│   ├── server.py           # Process lifecycle management (634 lines)
│   └── benchmark.py        # Performance benchmarking (259 lines)
├── tests/
│   ├── conftest.py         # Shared fixtures (137 lines)
│   ├── test_config.py      # Config tests (61 lines)
│   ├── test_models.py      # Discovery tests (109 lines)
│   ├── test_server_safety.py # Safety tests (249 lines)
│   ├── test_providers.py   # Provider tests (172 lines)
│   ├── test_cli_json.py    # CLI JSON tests (106 lines)
│   └── test_benchmark.py   # Benchmark tests (155 lines)
└── mlx_manager.egg-info/   # setuptools build artifacts
```
