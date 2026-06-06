# llmemo Knowledge Base

## How to Read This File

- **Format:** `markdown` (schema v1)
- **Sections:**
  - How to Read This File
  - Metadata
  - Stats
  - Directory Tree
  - Files

This file is a self-describing knowledge base of a code repository, produced by `llmemo`. It is designed as a navigable index, not a payload to ingest top-to-bottom. Recommended access pattern for an LLM agent with search or seek capability: (1) read this preamble and the Directory Tree section to understand the scope and shape of the repository; (2) decide which files you actually need from the tree before reading any file content; (3) seek to each file by its repository-relative path — every file entry is keyed by its path in the syntax of the active format (a `### <path>` heading in markdown/plain, a path field in JSON/YAML/TOML, a `<file path="...">` element in XML/HTML); (4) inspect each file's metadata block (size, language, token count) before reading its content so you can budget context window usage. Sections appear in the order listed under "Sections" below; do not assume any section is present unless it is listed. The directory tree mirrors the final file set after ignore filters and security redaction were applied at pack time.

## Metadata

- **Tool:** llmemo
- **Version:** v0.0.3 (62e9be6)
- **Repo:** mlx-manager

## Stats

- **Files:** 32
- **Total size:** 251.3 KB
- **Languages:**
  - python: 25
  - markdown: 4
  - text: 2
  - toml: 1

## Directory Tree

```
├── mlx_manager/
│   ├── __init__.py
│   ├── __main__.py
│   ├── _server_shim.py
│   ├── benchmark.py
│   ├── bot.py
│   ├── cli.py
│   ├── config.py
│   ├── context.py
│   ├── models.py
│   ├── paths.py
│   ├── providers.py
│   └── server.py
├── tests/
│   ├── conftest.py
│   ├── test_benchmark.py
│   ├── test_bot.py
│   ├── test_cli_json.py
│   ├── test_cli_load.py
│   ├── test_config.py
│   ├── test_context.py
│   ├── test_doctor_fix.py
│   ├── test_health.py
│   ├── test_models.py
│   ├── test_providers.py
│   ├── test_server_safety.py
│   └── test_server_shim.py
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── pyproject.toml
└── technical.md
```

## Files

### .gitignore

- size: 759 B
- language: text

```
# Byte-compiled / cache
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
*.egg
MANIFEST

# Test / coverage
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/
coverage.xml
*.cover
.hypothesis/

# Virtual environments
.venv/
venv/
env/
ENV/

# Editor / OS
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# mlx-manager runtime (in case anyone configures the project dir as state dir)
*.log
*.pid
*.bak
*.tmp
/.opencode
/.env.example
/.nvmrc
/specs
/AGENTS.md
/opencode.json
/tui.json
/.utcp_config.json
/CLAUDE.md
/.mcp.json
/.claude
/.codex
/GEMINI.md
/.agents
/.gemini
/prompt.md
/stakeholder.html
# CocoIndex Code (ccc)
/.cocoindex_code/
```

### CHANGELOG.md

- size: 4.7 KB
- language: markdown

```markdown
# Changelog

All notable changes to `mlx-manager` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `load` command: a guided shortcut for starting from the discovered local model
  list. It prints numbered models, then prompts for host, port, and whether to
  replace an existing managed server. The same stepper is available as
  `start --choose`.
- `~/.models/mlx` is now a default discovery root, matching common local model
  paths such as `~/.models/mlx/Qwopus3.6-27B-v2-MLX-4bit`.
- Managed servers now launch through a thin shim (`_server_shim.py`) that
  patches `mlx_lm.server` in memory so a tool call that fails to parse (usually
  truncated mid-generation) reports `finish_reason="length"` instead of being
  silently dropped while the response still claims `stop`/`tool_calls` — which
  left agentic clients with no error signal. The patch is best-effort (the
  server still starts if `mlx_lm` internals don't match) and never edits the
  installed package, so it survives `mlx_lm` reinstalls. Toggle with the new
  `[server].patch_tool_calls` key (default `true`).
- `LICENSE` (MIT), `CONTRIBUTING.md`, `CHANGELOG.md`, and `.gitignore` for
  open-source housekeeping.
- README rewritten to document every command, flag, and exit code.
- `bot` command: an interactive chat with a small on-device LLM (default
  `mlx-community/gemma-4-e2b-it-4bit`) that auto-injects live server status,
  `doctor` findings, and recent log errors so it can help troubleshoot. The
  model is downloaded once into `~/.mlx-manager/bot` (configurable via
  `[bot].cache_dir`) and reused offline thereafter. Configurable via the new
  `[bot]` table (`model`, `cache_dir`, `max_tokens`, `temperature`);
  overridable with `--model`/`--max-tokens`/`--temperature` and `--no-context`.
  On first run (interactive terminal, no model downloaded yet) it offers a
  curated menu of lightweight, capable models — Gemma 4 E2B/E4B, Qwen3 1.7B,
  Llama 3.2 3B, Ministral 3B — and remembers the choice; re-pick with
  `--choose`.
- `~/.mlx-manager/models` is now the first default model-discovery directory.
- `doctor` now reports a `bot runtime` check: whether `mlx_lm` is importable in
  the interpreter running mlx-manager itself (what the in-process `bot` needs),
  which can differ from `server.python_executable`.
- `doctor --fix` attempts remediation: installs `mlx_lm` into the bot runtime
  (`pipx inject <app> mlx-lm` when mlx-manager is pipx-isolated, else
  `pip install`), creates missing configured model directories, and — when the
  default `server.python_executable` ("python3") can't import `mlx_lm` but the
  current interpreter can — repoints it at the working interpreter so `start`
  works without modifying an externally-managed Python. Fix progress is written
  to stderr so `--json` output stays clean.
- `config.update_value()` helper to set a single config key in place.
- Log-based health detection: `status` and `doctor` now scan a server's log
  for fatal model-load failures (unsupported `model_type`, missing
  `mlx_lm.models` module, OOM, unreadable weights) and report it. Previously a
  server whose model could never load still showed `endpoint ok`, because
  `mlx_lm` loads the model lazily on the first request.

### Changed
- `pyproject.toml` now declares classifiers, keywords, and project URLs.

### Removed
- Internal prompt and stakeholder summary artifacts from the public release file
  set; they remain ignored for local regeneration.

### Fixed
- `benchmark` request table now shows the request index in the `#` column
  (previously it leaked `finish_reason` there).
- Removed a handful of unused imports (`field`, `Iterable`, `Any`, `sys`).
- `mlx-manager list` now reuses `_human_size` for directory sizes instead
  of duplicating the formatting logic.
- `--host 0.0.0.0` now exits with usage error unless `--bind-all` is also
  provided, matching the documented network exposure safety rule.

## [0.1.0] - 2026-05

Initial public release.

### Commands
- `list`, `start`, `stop`, `restart`, `switch`, `status`, `logs`, `info`,
  `doctor`, `benchmark`.
- `config opencode` (with `--apply`, `--format`, `--remote`,
  `--overwrite`).
- `config claude-code` (LiteLLM YAML + experimental env-vars).
- `config show`, `config edit`.

### Highlights
- Discovers MLX models from flat, LM-Studio-style nested, and Hugging Face
  hub-cache layouts.
- `fcntl`-locked lifecycle operations with atomic state-file writes.
- Refuses to kill recycled PIDs whose `argv` doesn't match the recorded
  state.
- Streaming benchmark with TTFT, per-stream decode rate, aggregate
  throughput, and parallelism analysis.
- Stdlib-only runtime path apart from `tomli-w`.
```

### CONTRIBUTING.md

- size: 2.5 KB
- language: markdown

````markdown
# Contributing

Thanks for your interest in `mlx-manager`. The project is intentionally
small and easy to keep in your head — please keep PRs in that spirit.

## Ground rules

- **Stdlib first.** Runtime deps are limited to `tomli-w` (for writing the
  default config). Don't introduce new runtime deps without discussing it
  in an issue first. Test-only deps go under `[project.optional-dependencies]`
  (`dev`).
- **No daemons, no database, no web UI.** mlx-manager is a CLI wrapper.
- **Apple Silicon / macOS is the supported target.** Other platforms might
  work but aren't tested.

## Development setup

```bash
git clone <this-repo>
cd mlx-manager
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

The whole test suite runs without `mlx_lm` installed and without spawning a
real server — every external call (subprocess, sockets, HTTP, filesystem
walks for HF-cache discovery) is faked through `tests/conftest.py`.

## Workflow

1. **Open an issue first** for anything non-trivial — bug repro, feature
   sketch, or design question. Quick fixes can go straight to a PR.
2. **Branch off `main`** with a short descriptive name
   (`fix/stop-rejects-recycled-pid`, `feat/info-command`, …).
3. **Add or update tests** under `tests/` for every behaviour change. A
   PR that touches `mlx_manager/` without a corresponding test change is
   almost certainly missing something.
4. **Run `pytest -q`** locally before pushing. PRs are expected to be green.
5. **Keep commits focused.** Squash trivia (`oops`, `wip`) before review.

## Style

- Python 3.11+ idioms; `from __future__ import annotations` everywhere.
- Type-hint public functions and `@dataclass` boundaries.
- Prefer small free functions over classes; keep modules under ~700 lines.
- Errors that the CLI maps to a non-zero exit should be raised as the
  appropriate exception (`ConfigError`, `ServerError(exit_code=…)`,
  `ApplyError`, `LookupError`) — not printed and `sys.exit`-ed from deep in
  the call stack.
- One-line summary docstrings on public functions; reach for prose when
  it's earning its keep.

## Reporting bugs

Please include:

- macOS version and Apple Silicon chip generation (`uname -srm`).
- Python version (`python3 --version`).
- `mlx_lm` version (`pip show mlx-lm`).
- The output of `mlx-manager --version` and `mlx-manager doctor`.
- A minimal reproducer.

## Security

Please don't open public issues for security-sensitive reports — email the
maintainer instead, or open a private security advisory on the repo if it's
hosted somewhere that supports them.
````

### LICENSE

- size: 1.0 KB
- language: text

```
MIT License

Copyright (c) 2026 rs

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### README.md

- size: 23.1 KB
- language: markdown

````markdown
# mlx-manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

A small, stdlib-first Python 3.11+ CLI that wraps `python -m mlx_lm server` so
you can run a local [MLX](https://github.com/ml-explore/mlx) language-model
HTTP server *headless* on an Apple Silicon Mac — start, stop, restart, switch
models, check status, tail logs, benchmark, run diagnostics, and emit
copy/paste-ready provider snippets for [OpenCode](https://opencode.ai),
[Claude Code](https://www.anthropic.com/claude-code), and
[LiteLLM](https://docs.litellm.ai/).

No daemon. No database. No web UI. Just `argparse`, a single state file, an
`fcntl` lock, and `urllib`.

- Runtime deps: `tomli-w` (only used to *write* the default config on first
  run; reading TOML uses stdlib `tomllib`).
- Tested on macOS / Apple Silicon (`Darwin/arm64`) with Python 3.11+.
- License: [MIT](./LICENSE).

---

## Table of contents

- [Install](#install)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Model discovery](#model-discovery)
- [Commands](#commands)
  - [`list`](#list)
  - [`start`](#start)
  - [`load`](#load)
  - [`stop`](#stop)
  - [`restart`](#restart)
  - [`switch`](#switch)
  - [`status`](#status)
  - [`logs`](#logs)
  - [`info`](#info)
  - [`doctor`](#doctor)
  - [`bot`](#bot)
  - [`benchmark`](#benchmark)
  - [`config opencode`](#config-opencode)
  - [`config claude-code`](#config-claude-code)
  - [`config show`](#config-show)
  - [`config edit`](#config-edit)
- [Exit codes](#exit-codes)
- [Safety notes](#safety-notes)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Install

Requires macOS on Apple Silicon, Python >= 3.11, and
[`mlx_lm`](https://pypi.org/project/mlx-lm/) installed in the same interpreter
`mlx-manager` will use to launch the server (by default `python3`).

Install the runtime dependencies first:

```bash
python3 -m pip install mlx-lm
```

Then install `mlx-manager` from this repository:

```bash
uv pip install -e .
pip install -e .
```

The package install also installs `tomli-w`, the only direct runtime dependency
declared by `mlx-manager` itself.

Then verify your environment:

```bash
mlx-manager doctor
```

If `mlx_lm` is missing, `doctor` will tell you; install it into the interpreter
named by `[server].python_executable` in your config.

## Quick start

```bash
mlx-manager doctor                # check Python, mlx_lm, paths, port
mlx-manager list                  # see discovered models
mlx-manager load                  # guided local model picker and start steps
mlx-manager status                # see live PID, uptime, endpoint
mlx-manager benchmark             # TTFT, decode tok/s, aggregate throughput
mlx-manager stop
```

## Global options

These work with every subcommand:

| Flag | Description |
|------|-------------|
| `--config PATH` | Use a different config file (default `~/.config/mlx-manager/config.toml`). |
| `--verbose` | Emit progress information to stderr. |
| `--version` | Print version and exit. |
| `-h, --help` | Show help (works on every subcommand too). |

## Configuration

First run creates `~/.config/mlx-manager/config.toml` with the defaults below.
All paths expand `~` and `$VAR`.

```toml
[server]
host = "127.0.0.1"
port = 8080
log_file = "~/services/mlx/logs/mlx-lm.server.log"
pid_file = "~/services/mlx/mlx-lm.server.pid"
state_file = "~/.local/state/mlx-manager/state.json"
lock_file = "~/.local/state/mlx-manager/lock"
python_executable = "python3"
extra_args = []                  # forwarded to mlx_lm server verbatim
startup_timeout_seconds = 120
stop_timeout_seconds = 15
max_log_bytes = 10485760         # 10 MiB
max_log_files = 5
patch_tool_calls = true          # best-effort shim for truncated tool calls

[models]
directories = [
  "~/.mlx-manager/models",
  "~/.models/mlx",
  "~/models/mlx",
  "~/.cache/huggingface/hub",
  "~/.lmstudio/models",
]
default_model = ""

[models.aliases]
# qwen3-8b-4bit = "~/models/mlx/qwen3-8b-4bit"

[providers]
base_url = ""                    # if empty, derived from [server].host:port
api_key = "mlx-local"
provider_name = "mlx-local"

[bot]
model = "mlx-community/gemma-4-e2b-it-4bit"
cache_dir = "~/.mlx-manager/bot"
max_tokens = 1024
temperature = 0.7
```

Validation: unknown tables or keys → exit code 3; `port` must be in
`1024–65535`; `extra_args`, `directories`, `aliases`, `patch_tool_calls`,
and `[bot]` values are type-checked.

Aliases pointing at non-existent paths are tolerated at load time (so a model
can be temporarily unavailable without breaking `mlx-manager`); `doctor`
warns about them.

## Model discovery

A directory is treated as a model iff it contains `config.json` **and** at
least one of: `model.safetensors`, `model-*.safetensors` shards, or
`weights.safetensors`. Tokenizer files are not required (some MLX repacks
omit them).

Each configured root in `[models].directories` is walked recursively (capped
at four levels deep, and discovery stops descending as soon as a model is
identified). This handles three common on-disk layouts uniformly:

| Layout | Example | Discovered id |
|--------|---------|---------------|
| Flat | `~/models/mlx/<name>/` | `<name>` |
| Nested by publisher (LM Studio) | `~/.lmstudio/models/<publisher>/<name>/` | `<name>` |
| Hugging Face hub cache | `~/.cache/huggingface/hub/models--<org>--<name>/snapshots/<rev>/` | `<org>/<name>` |

The id printed by `mlx-manager list` is the **same string** the HTTP API
exposes — i.e. the value clients put in the `model` JSON field. For
filesystem models that's the model directory's basename; mlx-manager spawns
`mlx_lm server` with `cwd=<parent>` and `--model <basename>` so the API id
ends up as the basename, not the absolute path. For HF-cache models the id
is the HF-style `<org>/<name>` and mlx_lm's HF resolver finds the snapshot
in the local cache.

If two filesystem models in different directories share the same basename,
the first one discovered wins; rename one of the directories or set an alias
to disambiguate.

`mlx-manager start --model X` resolves `X` in this order: alias → discovered
display name → absolute filesystem path.

`mlx-manager load` is the guided shortcut form for local models. It prints the
current discovered model list, asks which model to start, then steps through
host, port, and whether to replace an existing managed server on that port.

---

## Commands

### `list`

Show discovered models.

```bash
mlx-manager list
mlx-manager list --json
```

| Flag | Description |
|------|-------------|
| `--json` | Emit a JSON array of `{id, path, source}` records. |

Sample output:

```
ID                SOURCE    WEIGHTS  SIZE   PATH
qwen3-8b-4bit     directory 1        4.5GB  ~/models/mlx/qwen3-8b-4bit
mlx-community/... hf_cache  1        7.2GB  ~/.cache/huggingface/hub/...
```

### `start`

Launch the MLX server.

```bash
mlx-manager start --model qwen3-8b-4bit
mlx-manager start --model qwen3-8b-4bit --port 1234
mlx-manager start --model /abs/path/to/model --replace
mlx-manager start --model qwen3-8b-4bit --extra-arg trust-remote-code=true
mlx-manager start --model qwen3-8b-4bit --bind-all     # bind on 0.0.0.0
mlx-manager start --choose                             # guided model picker
```

| Flag | Description |
|------|-------------|
| `--model ID` | Model id, alias, or absolute path. Falls back to `[models].default_model` if omitted. |
| `--host HOST` | Override `[server].host`. |
| `--port N` | Override `[server].port`. |
| `--replace` | Stop a running managed server first instead of erroring. |
| `--choose` | Pick from the discovered model list and prompt for missing start options. |
| `--bind-all` | Bind on `0.0.0.0` (prints a warning). |
| `--extra-arg KEY=VAL` | Forward an extra flag to `mlx_lm server`. Repeatable. Boolean flags accept `true/yes/1/on`. Unknown flags are warned about based on the locally-installed `mlx_lm server --help` output. |

On success prints the PID, model id/path, base URL, and log file path. On
startup-timeout the launcher prints the tail of the log and exits 6.

### `load`

Guided shortcut for launching one discovered local model. It uses the same
server start path as `start`, but instead of making you type the full command,
it shows the current model list and prompts for the missing choices.

```bash
mlx-manager load
mlx-manager load --port 1237 --bind-all
mlx-manager load --bind-all --replace
```

| Flag | Description |
|------|-------------|
| `--host`, `--port`, `--replace`, `--bind-all`, `--extra-arg` | Same as [`start`](#start). If omitted, `load` prompts for host, port, and replace behavior. |

### `stop`

Stop the managed server.

```bash
mlx-manager stop
mlx-manager stop --timeout 30
```

| Flag | Description |
|------|-------------|
| `--timeout N` | Seconds to wait for SIGTERM before sending SIGKILL (default `[server].stop_timeout_seconds`). |

Refuses to kill a PID whose `argv` doesn't contain both `mlx_lm` and the
recorded port — protects against killing an unrelated process if the PID was
recycled.

### `restart`

Equivalent to `start --replace`. Accepts the same `--model / --host / --port
/ --bind-all / --extra-arg` flags as `start`.

```bash
mlx-manager restart
mlx-manager restart --port 1234
```

### `switch`

Convenience for swapping the running server to a different model. Takes
the model id as a positional argument.

```bash
mlx-manager switch qwen3-8b-4bit
mlx-manager switch /abs/path/to/other-model --extra-arg max-tokens=8192
```

| Flag | Description |
|------|-------------|
| `model` (positional) | New model id, alias, or absolute path. |
| `--host`, `--port`, `--bind-all`, `--extra-arg` | Same as [`start`](#start). |

### `status`

Report live server state.

```bash
mlx-manager status
mlx-manager status --json
```

| Flag | Description |
|------|-------------|
| `--json` | Machine-readable status dictionary. |

Exit code is `0` if running, `4` if not. Text output includes PID, model,
host:port, base URL, start time, human-readable uptime, mlx_lm version, RSS
memory, and an HTTP reachability check (`endpoint  ok | unreachable`).

If a previous run was killed hard, the next `status` call detects the dead
PID, clears the stale state file, and reports `not running`.

### `logs`

Tail (and optionally follow) the server log.

```bash
mlx-manager logs                  # last 100 lines
mlx-manager logs --tail 500
mlx-manager logs -f               # follow (Ctrl-C to exit)
```

| Flag | Description |
|------|-------------|
| `--tail N` | Number of trailing lines (default 100). |
| `-f, --follow` | Stream new lines as they're appended. |

Logs are appended to `[server].log_file` and rotated when they exceed
`max_log_bytes` (kept up to `max_log_files`).

### `info`

Show metadata for a single model: id, source, weight files, total size,
selected `config.json` fields.

```bash
mlx-manager info qwen3-8b-4bit
mlx-manager info qwen3-8b-4bit --json
```

| Flag | Description |
|------|-------------|
| `model` (positional) | Model id, alias, or absolute path. |
| `--json` | Emit metadata as JSON. |

### `doctor`

Run diagnostics. Useful as the first thing you run after install, and
whenever something looks off.

```bash
mlx-manager doctor
mlx-manager doctor --json
mlx-manager doctor --fix
```

| Flag | Description |
|------|-------------|
| `--json` | Emit results as a JSON array. |
| `--fix` | Attempt safe remediations and write progress to stderr. |

Checks performed:

- `[server].python_executable` is on `PATH` and runs.
- `import mlx_lm` succeeds; `mlx_lm server --help` parses.
- Each `[models].directories` entry exists and is readable, and how many
  models it contains.
- Each `[models.aliases]` target exists.
- Parents of `log_file`, `pid_file`, `state_file`, `lock_file` are writable.
- `[server].host:port` is reachable (if running) or bindable (if not).
- Platform is `Darwin/arm64`.
- Total physical memory (via `sysctl hw.memsize`).
- `pf` firewall state.
- The current `mlx-manager` runtime can import `mlx_lm` for the in-process
  [`bot`](#bot) command.

Exits `1` if any check is `FAIL`, otherwise `0`.

With `--fix`, `doctor` attempts only local, reversible setup work: install
`mlx_lm` into the bot runtime, create missing configured model directories,
and repoint the default `server.python_executable` to the current interpreter
when that interpreter can import `mlx_lm` but `python3` cannot. Fix progress is
printed to stderr so `--json` output stays parseable.

### `bot`

Chat with a small on-device troubleshooting assistant. The bot runs `mlx_lm`
in the current `mlx-manager` Python process, injects live `status`, `doctor`,
and recent-log context by default, and downloads its model once into
`[bot].cache_dir` for later reuse.

```bash
mlx-manager bot
mlx-manager bot --choose
mlx-manager bot --model mlx-community/Qwen3-1.7B-4bit
mlx-manager bot --no-context
```

| Flag | Description |
|------|-------------|
| `--model ID_OR_PATH` | Override `[bot].model` for this run. |
| `--choose` | Re-pick from the built-in lightweight model menu. |
| `--max-tokens N` | Override `[bot].max_tokens`. |
| `--temperature N` | Override `[bot].temperature`. |
| `--no-context` | Do not inject live server, doctor, or log context. |

If `mlx_lm` is not importable in the current interpreter, `bot` exits `7` and
suggests `mlx-manager doctor --fix`.

### `benchmark`

Measure **TTFT** (time-to-first-token), **per-stream decode tok/s** (computed
from `usage.completion_tokens` returned in the final SSE chunk; falls back to
chunk count for servers that don't emit `usage`), and **aggregate throughput**
= total completion tokens across all parallel streams ÷ wall-clock.

```bash
mlx-manager benchmark                                  # default prompt, 5 requests
mlx-manager benchmark --requests 8 --concurrency 4     # concurrency sweep
mlx-manager benchmark --prompt-file ./prompt.txt --max-tokens 512
mlx-manager benchmark --warmup 2                       # extra non-counted warmups
mlx-manager benchmark --json                           # machine-readable
mlx-manager benchmark --endpoint http://host:1235/v1 --model some-id
mlx-manager benchmark --save results.json
```

| Flag | Default | Description |
|------|---------|-------------|
| `--model ID` | running server's model, then `[models].default_model` | model id for the request body |
| `--endpoint URL` | running server's base URL, else `[providers].base_url` | hit a different MLX-compatible endpoint |
| `--prompt TEXT` / `--prompt-file FILE` | built-in generation-bound prompt (~50 words) | prompt to send |
| `--max-tokens N` | 256 | per request — bump for longer decode windows |
| `--requests N` | 5 | total requests measured |
| `--concurrency N` | 1 | parallel in-flight streams |
| `--warmup N` | 1 | sequential pre-runs not counted in the measurement (defeats prompt-cache cold-start) |
| `--save FILE` | (none) | write summary JSON to `FILE` |
| `--json` | off | emit summary as JSON instead of the table |

Sample output:

```
benchmark   endpoint    http://127.0.0.1:8080/v1
            model       qwen3-8b-4bit
            requests    4 (concurrency=2, max_tokens=128, warmup=1, prompt_chars=180)

  #   TTFT     Total    Tokens   Decode       Bar
  1   0.39s    3.21s    128      45.4 tok/s   ████████████░░░░
  2   0.41s    3.25s    128      45.3 tok/s   ████████████░░░░
  ...

─── Summary ──────────────────────────────────────────────────────
  wall time:        6.42s
  requests:         4/4 succeeded
  ttft:             p50=0.39s  p95=0.60s  ░░░░░░░░░░░░░░░░
  decode rate:      p50=45.4 tok/s  p95=45.5 tok/s  ████████████████ (per stream)
  total time:       p50=3.23s  p95=3.40s  ████████████████
  aggregate rate:   79.7 tok/s  ████████░░░░░░░░
  parallelism gain: 1.76×
  per-stream delta: +12.1% (vs single-stream)
───
```

> **Reasoning-model caveat:** some models (e.g. GLM-4.x) emit "thinking"
> tokens under `delta.reasoning` rather than `delta.content`. The benchmark
> treats both as decode tokens, so the tok/s number reflects total
> generation rate, not just the user-visible answer.

### `config opencode`

Emit a `provider` block ready to paste into
`~/.config/opencode/opencode.json`, or apply it in place.

```bash
mlx-manager config opencode                            # print snippet to stdout
mlx-manager config opencode --model qwen3-8b-4bit
mlx-manager config opencode --format full              # full opencode.json shape
mlx-manager config opencode --apply                    # merge into ~/.config/opencode/opencode.json
mlx-manager config opencode --apply --overwrite        # replace the provider block
mlx-manager config opencode --reset                    # remove mlx-manager-managed provider blocks
mlx-manager config opencode --apply --target /path/to/opencode.json
mlx-manager config opencode --remote                   # use LAN IP, suffix provider name with @hostname
```

| Flag | Description |
|------|-------------|
| `--model ID` | Model id for the snippet (default: running server, then first discovered, then `[models].default_model`). |
| `--format merge\|full` | `merge` (default) emits just the `provider` map; `full` wraps it in a complete `opencode.json` with `$schema`. |
| `--apply` | Write into the file instead of stdout. A `<file>.bak` is created. |
| `--target PATH` | OpenCode config path (default `~/.config/opencode/opencode.json`). Used with `--apply` or `--reset`. |
| `--overwrite` | Replace the entire provider block. Without it, `--apply` *merges*: `npm`/`name`/`options` are refreshed and missing model entries added, but hand-tuned per-model fields (e.g. `"limit": { "context": ..., "output": ... }`) are preserved. Other top-level keys in `opencode.json` (`permission`, `mcp`, `plugin`, ...) are untouched. |
| `--reset` | Remove only provider keys marked with the `mlx-manager:` prefix from the target OpenCode config. User-managed providers are preserved. |
| `--remote` | Use this machine's LAN IP instead of `127.0.0.1`/`0.0.0.0` in the emitted URL and suffix the provider name with `@<hostname>`. Useful when generating a config for clients on the same network. |

Sample snippet (`merge` form):

```json
{
  "provider": {
    "mlx-manager:mlx-local:8080": {
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

If a server is currently running, the snippet's `baseURL` is taken from the
live state; otherwise it falls back to `[providers].base_url` and finally to
`[server].host:port`. OpenCode provider keys are marked with `mlx-manager:`
and always include the port, such as `mlx-manager:mlx-local:8080`, so reset can
identify every mlx-manager-managed entry consistently.

### `config claude-code`

Emit guidance and a LiteLLM `model_list` YAML for Claude Code.

```bash
mlx-manager config claude-code
mlx-manager config claude-code --model qwen3-8b-4bit
mlx-manager config claude-code --remote
```

| Flag | Description |
|------|-------------|
| `--model ID` | Model id for the snippet (same fallback chain as `config opencode`). |
| `--remote` | Use LAN IP in the emitted base URL. |

Why a snippet rather than direct config? At the time of writing, the Claude
Code CLI (`claude --help`) documents only Anthropic auth and third-party
providers Bedrock / Vertex / Foundry — there is no documented
OpenAI-compatible base-URL routing. mlx-manager therefore does **not** emit
`ANTHROPIC_BASE_URL`. Instead the output gives two paths:

1. **Recommended — LiteLLM in front of MLX.** Use the printed `model_list:`
   YAML as your `config.yaml` for [LiteLLM](https://docs.litellm.ai/), then
   point Claude Code at LiteLLM's own URL/key:
   ```bash
   pip install 'litellm[proxy]'
   litellm --config config.yaml --port 4000
   ```
2. **Experimental — direct env vars.** A small `OPENAI_API_KEY` /
   `OPENAI_BASE_URL` block, labelled experimental, for users who have
   verified OpenAI-compatible routing on their Claude Code build.

### `config show`

Display the current effective configuration (merged defaults + your file).

```bash
mlx-manager config show
mlx-manager config show --json
```

| Flag | Description |
|------|-------------|
| `--json` | Emit the config as JSON. |

### `config edit`

Open `config.toml` in `$EDITOR` and reload it on save (validates after).

```bash
mlx-manager config edit
mlx-manager config edit --editor code
```

| Flag | Description |
|------|-------------|
| `--editor CMD` | Editor command. Defaults to `$EDITOR`, then `vim`. |

If the file is invalid after editing, exits `3` and prints the validation
error.

---

## Exit codes

| Code | Meaning |
|------|---------|
| 0    | success |
| 1    | generic failure |
| 2    | usage error |
| 3    | config error |
| 4    | not running (used by `status` / `stop`) |
| 5    | already running (`start` without `--replace`) |
| 6    | startup timeout |
| 7    | `mlx_lm` missing |

## Safety notes

- The default bind is `127.0.0.1`. Binding `0.0.0.0` requires `--bind-all`
  and prints a warning to stderr. Passing `--host 0.0.0.0` without
  `--bind-all` exits with usage error `2`.
- `stop` never kills a PID without first confirming its `argv` contains
  `mlx_lm` *and* the recorded port — so a recycled PID belonging to some
  other program will not be touched.
- `start`/`stop`/`restart` hold an `fcntl` lock on `[server].lock_file`
  while they mutate state. Lock acquisition has a 10-second timeout.
- State and PID files are written atomically (write-tmp + rename). The
  OpenCode `--apply` path writes a `.bak` of the previous file before
  replacing it, and also writes atomically.

## Troubleshooting

- **`mlx_lm not installed`** — run `mlx-manager doctor`. Install with
  `pip install mlx-lm` into the interpreter named by
  `[server].python_executable`.
- **`port already in use`** — another process is bound. `mlx-manager`
  reports the conflicting PID when it can discover one via `lsof`.
- **`server did not become ready within Ns`** — the launcher prints the
  last 40 log lines and exits 6. Check the log file for the real failure.
- **Stale state file** — if a previous run was killed hard, the next
  command detects the dead PID and clears it; `status` will then report
  `not running` cleanly.

## Development

```bash
git clone https://github.com/Pixie-sh/mlx-manager.git
cd mlx-manager
pip install -e '.[dev]'
pytest -q
```

Tests run without `mlx_lm` installed and without starting a real server
(every external call is faked through `tests/conftest.py`).

The codebase is intentionally small and stdlib-only on the runtime path; if
you find a place where a tiny helper is more readable than another
dependency, prefer the helper.

## Contributing

Contributions are welcome. Please:

1. Open an issue describing the change first if it's non-trivial.
2. Keep runtime dependencies to a minimum (stdlib + `tomli-w` is the goal).
3. Add or update tests under `tests/` for any behaviour change.
4. Run `pytest -q` before submitting a PR.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

## License

[MIT](./LICENSE) © 2026 rs

`mlx_lm` is a separate project; see
[ml-explore/mlx-lm](https://github.com/ml-explore/mlx-lm) for its license.
````

### mlx_manager/__init__.py

- size: 22 B
- language: python

```python
__version__ = "0.1.0"
```

### mlx_manager/__main__.py

- size: 90 B
- language: python

```python
from mlx_manager.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

### mlx_manager/_server_shim.py

- size: 4.5 KB
- language: python

```python
"""Launch shim: run mlx_lm's server with mlx-manager's tool-call patch applied.

mlx-manager invokes this exactly as it would invoke ``python -m mlx_lm server``,
i.e. ``python <this file> server --model ... --host ... --port ...``. The shim
patches ``mlx_lm.server`` in memory, then hands off to ``mlx_lm.cli.main()`` so
the server behaves identically apart from the patch.

The patch: when a tool call fails to parse (it gets dropped — typically because
the model was cut off mid-call and the JSON is incomplete), force the response's
``finish_reason`` to ``"length"``. Stock mlx_lm logs a warning and silently
drops the call while still reporting ``finish_reason: "stop"``/``"tool_calls"``,
so an API client sees a clean turn with no tool call and no error signal. With
the patch the client gets ``length``, the standard OpenAI marker for a cut-off
generation, and can react instead of flying blind.

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


def _apply_patch() -> None:
    import mlx_lm.server as server_mod

    formatter_cls = getattr(server_mod, "ToolCallFormatter", None)
    handler_cls = getattr(server_mod, "APIHandler", None)
    if formatter_cls is None or handler_cls is None:
        raise AttributeError("mlx_lm.server lacks ToolCallFormatter/APIHandler")
    if getattr(formatter_cls, "_mlxmgr_patched", False):
        return

    orig_init = formatter_cls.__init__
    orig_generate_response = handler_cls.generate_response

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

    formatter_cls.__init__ = patched_init
    handler_cls.generate_response = patched_generate_response
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
            "mlx-manager: tool-call patch active "
            "(unparseable tool calls report finish_reason=length)"
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
```

### mlx_manager/benchmark.py

- size: 10.8 KB
- language: python

```python
"""Minimal streaming benchmark for the MLX HTTP server.

Hits ``/v1/chat/completions`` with ``stream: true`` so we can record
*time-to-first-token* in addition to total wall-clock and decode throughput.
Pure stdlib — ``urllib`` for HTTP, ``concurrent.futures`` for fan-out.
"""
from __future__ import annotations

import concurrent.futures
import json
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Callable


DEFAULT_PROMPT = (
    "Write a five-paragraph technical explanation of how unified memory on "
    "Apple Silicon differs from traditional discrete-GPU memory hierarchies. "
    "Cover bandwidth, latency, and what it means for ML inference workloads."
)

REQUEST_READ_TIMEOUT_S = 600.0  # generous; slow models on long completions.


def _ascii_bar(value: float, max_value: float, width: int = 20) -> str:
    """Return an ASCII bar of *width* cells proportional to *value* / *max_value*.

    Uses full/half/empty block characters for sub-cell resolution.
    """
    if max_value <= 0:
        return " " * width
    ratio = value / max_value
    filled = ratio * width
    int_filled = int(filled)
    remainder = filled - int_filled

    parts: list[str] = []
    if int_filled > 0:
        parts.append("█" * int_filled)
    if remainder > 0.75:
        parts.append("█")
    elif remainder > 0.25:
        parts.append("▓")
    if int_filled + (1 if remainder > 0.25 else 0) < width:
        parts.append("░" * (width - int_filled - (1 if remainder > 0.25 else 0)))
    return "".join(parts)


@dataclass
class RequestResult:
    ok: bool
    ttft_s: float | None
    total_s: float
    prompt_tokens: int
    completion_tokens: int
    decode_tps: float
    finish_reason: str
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkSummary:
    endpoint: str
    model: str
    requests_total: int
    requests_ok: int
    concurrency: int
    warmup: int
    max_tokens: int
    prompt_chars: int
    wall_seconds: float
    aggregate_decode_tps: float  # tokens/s across all parallel streams
    per_request: list[RequestResult] = field(default_factory=list)
    ttft_p50: float | None = None
    ttft_p95: float | None = None
    decode_tps_p50: float | None = None
    decode_tps_p95: float | None = None
    total_p50: float | None = None
    total_p95: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["per_request"] = [r.to_dict() for r in self.per_request]
        return d

    @property
    def single_stream_tps(self) -> float | None:
        """Median per-stream decode rate (useful for parallelism comparison)."""
        vals = [r.decode_tps for r in self.per_request if r.ok and r.decode_tps > 0]
        if not vals:
            return None
        return statistics.median(vals) if len(vals) > 1 else vals[0]

    @property
    def parallelism_ratio(self) -> float | None:
        """Ratio of aggregate throughput to single-stream median. >1 means parallelism helps."""
        single = self.single_stream_tps
        if single is None or single <= 0:
            return None
        return self.aggregate_decode_tps / single

    @property
    def degradation_pct(self) -> float | None:
        """Per-stream degradation percentage when running concurrently. Negative = improvement."""
        single = self.single_stream_tps
        agg_per_stream = self.aggregate_decode_tps / max(self.concurrency, 1)
        if single is None or single <= 0:
            return None
        return ((single - agg_per_stream) / single) * 100


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    # ``statistics.quantiles`` with n=100 gives 99 cut points; index q-1.
    qs = statistics.quantiles(sorted(values), n=100, method="inclusive")
    idx = max(0, min(98, int(round(q)) - 1))
    return qs[idx]


def stream_one(
    endpoint: str,
    model: str,
    prompt: str,
    *,
    max_tokens: int,
    api_key: str = "",
    temperature: float = 0.0,
    timeout: float = REQUEST_READ_TIMEOUT_S,
) -> RequestResult:
    """Send one streaming chat-completions request; return measured stats."""
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": True,
            "temperature": temperature,
            # OpenAI-compat opt-in for the final usage chunk on streamed
            # responses. mlx_lm.server honors this; servers that don't will
            # just ignore the field and we fall back to chunk-counting below.
            "stream_options": {"include_usage": True},
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = endpoint.rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    t0 = time.monotonic()
    ttft: float | None = None
    completion_tokens = 0
    prompt_tokens = 0
    finish_reason = ""
    content_chunks = 0  # fallback when the server doesn't return `usage`
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                delta = choices[0].get("delta", {}) if choices else {}
                if delta.get("content") or delta.get("reasoning"):
                    content_chunks += 1
                    if ttft is None:
                        ttft = time.monotonic() - t0
                if choices and choices[0].get("finish_reason"):
                    finish_reason = choices[0]["finish_reason"]
                usage = chunk.get("usage")
                if isinstance(usage, dict):
                    completion_tokens = int(
                        usage.get("completion_tokens", completion_tokens) or 0
                    )
                    prompt_tokens = int(
                        usage.get("prompt_tokens", prompt_tokens) or 0
                    )
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        return RequestResult(
            ok=False,
            ttft_s=ttft,
            total_s=time.monotonic() - t0,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            decode_tps=0.0,
            finish_reason=finish_reason,
            error=str(e),
        )

    total = time.monotonic() - t0
    # Fall back to chunk count when the server didn't report usage.
    if completion_tokens == 0 and content_chunks > 0:
        completion_tokens = content_chunks
    decode_window = max(total - (ttft or 0.0), 1e-6)
    decode_tps = completion_tokens / decode_window if completion_tokens else 0.0
    return RequestResult(
        ok=True,
        ttft_s=ttft,
        total_s=total,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        decode_tps=decode_tps,
        finish_reason=finish_reason,
    )


def run(
    endpoint: str,
    model: str,
    prompt: str,
    *,
    requests: int,
    concurrency: int,
    max_tokens: int,
    warmup: int = 0,
    api_key: str = "",
    on_event: Callable[[str], None] | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    results: list[RequestResult] | None = None,
) -> BenchmarkSummary:
    """Run *requests* total at *concurrency*, after *warmup* sequential calls.

    *on_progress* is called with ``(completed, total)`` as each request finishes,
    enabling a progress indicator in the caller.

    If *results* is given, completed RequestResult objects are appended to it
    as they finish, so the caller can inspect them before ``run()`` returns.
    """
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    if requests < 1:
        raise ValueError("requests must be >= 1")
    if warmup < 0:
        raise ValueError("warmup must be >= 0")

    def emit(msg: str) -> None:
        if on_event:
            on_event(msg)

    # Warmup runs are sequential and not part of the measurement.
    for i in range(warmup):
        emit(f"warmup {i + 1}/{warmup}")
        stream_one(
            endpoint, model, prompt, max_tokens=max_tokens, api_key=api_key
        )

    internal_results: list[RequestResult] = results if results is not None else []
    completed = 0
    t_start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [
            ex.submit(
                stream_one,
                endpoint,
                model,
                prompt,
                max_tokens=max_tokens,
                api_key=api_key,
            )
            for _ in range(requests)
        ]
        for i, fut in enumerate(concurrent.futures.as_completed(futures), start=1):
            r = fut.result()
            internal_results.append(r)
            completed += 1
            if on_progress:
                on_progress(completed, requests)
            emit(
                f"request {i}/{requests}  "
                f"ttft={'-' if r.ttft_s is None else f'{r.ttft_s:.2f}s'}  "
                f"total={r.total_s:.2f}s  "
                f"completion={r.completion_tokens}  "
                f"decode={r.decode_tps:.1f} tok/s"
                + (f"  ERR {r.error}" if not r.ok else "")
            )
    wall = time.monotonic() - t_start

    ok = [r for r in internal_results if r.ok]
    completion_total = sum(r.completion_tokens for r in ok)
    aggregate_tps = completion_total / wall if wall > 0 else 0.0

    ttft_vals = [r.ttft_s for r in ok if r.ttft_s is not None]
    decode_vals = [r.decode_tps for r in ok if r.completion_tokens > 0]
    total_vals = [r.total_s for r in ok]

    return BenchmarkSummary(
        endpoint=endpoint,
        model=model,
        requests_total=requests,
        requests_ok=len(ok),
        concurrency=concurrency,
        warmup=warmup,
        max_tokens=max_tokens,
        prompt_chars=len(prompt),
        wall_seconds=wall,
        aggregate_decode_tps=aggregate_tps,
        per_request=internal_results,
        ttft_p50=_percentile(ttft_vals, 50),
        ttft_p95=_percentile(ttft_vals, 95),
        decode_tps_p50=_percentile(decode_vals, 50),
        decode_tps_p95=_percentile(decode_vals, 95),
        total_p50=_percentile(total_vals, 50),
        total_p95=_percentile(total_vals, 95),
    )
```

### mlx_manager/bot.py

- size: 10.3 KB
- language: python

```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from mlx_manager.paths import ensure_dir, expand

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
            "it in-process). Run `mlx-manager doctor --fix` to install it here."
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
```

### mlx_manager/cli.py

- size: 56.6 KB
- language: python

```python
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
from mlx_manager.context import model_memory_plan
from mlx_manager.models import Model, discover, resolve
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
    sp.add_argument("--port", type=int, help="override server port")
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
    sp.add_argument("--update-opencode", action="store_true", help="apply OpenCode provider config after start")
    sp.add_argument("--overwrite", action="store_true", help="replace provider block instead of merging (with --update-opencode)")

    sp = sub.add_parser("load", help="guided start from the discovered local model list")
    sp.add_argument("--host", help="override server host")
    sp.add_argument("--port", type=int, help="override server port")
    sp.add_argument("--replace", action="store_true", help="stop running server first")
    sp.add_argument("--bind-all", action="store_true", help="bind on 0.0.0.0 (insecure)")
    sp.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        metavar="KEY=VAL",
        help="forward extra flag to mlx_lm server (repeatable)",
    )
    sp.add_argument("--update-opencode", action="store_true", help="apply OpenCode provider config after start")
    sp.add_argument("--overwrite", action="store_true", help="replace provider block instead of merging (with --update-opencode)")

    sp = sub.add_parser("stop", help="stop the managed server")
    sp.add_argument("--port", type=int, help="port of server to stop (required when multiple are running)")
    sp.add_argument("--timeout", type=int, help="seconds to wait for SIGTERM before SIGKILL")

    sp = sub.add_parser("restart", help="stop then start the server")
    sp.add_argument("--model", help="model id, alias, or absolute path")
    sp.add_argument("--host")
    sp.add_argument("--port", type=int)
    sp.add_argument("--bind-all", action="store_true")
    sp.add_argument("--extra-arg", action="append", default=[], metavar="KEY=VAL")
    sp.add_argument("--update-opencode", action="store_true", help="apply OpenCode provider config after start")
    sp.add_argument("--overwrite", action="store_true", help="replace provider block instead of merging (with --update-opencode)")

    sp = sub.add_parser("switch", help="swap running server to a different model")
    sp.add_argument("model", help="new model id, alias, or absolute path")
    sp.add_argument("--host", help="override server host")
    sp.add_argument("--port", type=int, help="override server port")
    sp.add_argument("--bind-all", action="store_true", help="bind on 0.0.0.0 (insecure)")
    sp.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        metavar="KEY=VAL",
        help="forward extra flag to mlx_lm server (repeatable)",
    )
    sp.add_argument("--update-opencode", action="store_true", help="apply OpenCode provider config after start")
    sp.add_argument("--overwrite", action="store_true", help="replace provider block instead of merging (with --update-opencode)")

    sp = sub.add_parser("status", help="report server state")
    sp.add_argument("--port", type=int, help="show status for a specific port only")
    sp.add_argument("--json", action="store_true", dest="as_json")

    sp = sub.add_parser("logs", help="tail server log")
    sp.add_argument("--port", type=int, help="port of server whose log to tail (required when multiple are running)")
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
        default="~/.config/opencode/opencode.json",
        help="OpenCode config path (used with --apply or --reset)",
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
    models = discover(cfg.models)
    if args.as_json:
        print(json.dumps([m.to_dict() for m in models], indent=2))
        return EXIT_OK
    if not models:
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
        out_fn(f"  {idx:>2}. {model.id:<{id_w}}  {model.source:<9} {model.path}")

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
    elif answer.lower() in {"all", "any", "*", "0", "0.0.0.0"}:
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
        if 1024 <= port <= 65535:
            return port
        out_fn("Enter a port between 1024 and 65535.")


def _choose_replace(
    *,
    input_fn: Callable[[str], str] | None = None,
) -> bool:
    input_fn = input if input_fn is None else input_fn
    answer = _prompt(input_fn, "replace existing managed server on this port if needed? [y/N]: ")
    return answer.lower() in {"y", "yes"}


def _cmd_start(cfg: Config, args: argparse.Namespace) -> int:
    if getattr(args, "choose", False):
        return _cmd_start_guided(cfg, args)

    rc, m_or_err = _resolve_model_for_action(cfg, args.model)
    if rc != EXIT_OK:
        _eprint(f"error: {m_or_err}")
        return rc
    model = m_or_err  # type: ignore[assignment]

    return _start_model(cfg, args, model)


def _extra_arg_has_flag(pairs: list[str], raw_extra: list[str], flag: str) -> bool:
    """Return True if *flag* (without leading dashes) already appears in either list."""
    norm = flag.lstrip("-")
    for kv in pairs:
        if kv.partition("=")[0].lstrip("-") == norm:
            return True
    for item in raw_extra:
        item_norm = item.lstrip("-")
        if item_norm == norm or item_norm.startswith(norm + "="):
            return True
    return False


def _start_model(cfg: Config, args: argparse.Namespace, model: object) -> int:
    """Start the server for an already resolved model."""

    host = args.host or cfg.server.host
    if host == "0.0.0.0" and not args.bind_all:
        _eprint("error: binding on 0.0.0.0 requires --bind-all")
        return EXIT_USAGE
    if args.bind_all:
        host = "0.0.0.0"
        _eprint("warning: binding on 0.0.0.0 — server is reachable from the network")
    port = args.port or cfg.server.port

    m = model  # type: ignore[assignment]
    plan = model_memory_plan(m.path)

    extra_arg_pairs: list[str] = list(args.extra_arg)
    if not _extra_arg_has_flag(extra_arg_pairs, cfg.server.extra_args, "prompt-cache-bytes"):
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

    if getattr(args, "update_opencode", False):
        ctx_len = plan[0] if plan else None
        ctx = ProviderContext(
            base_url=state.base_url,
            api_key=cfg.providers.api_key,
            provider_name=managed_provider_name(f"{cfg.providers.provider_name}:{port}"),
            model_id=state.model_alias,
            context_length=ctx_len,
        )
        target = expand("~/.config/opencode/opencode.json")
        overwrite = getattr(args, "overwrite", False)
        try:
            summary = apply_opencode(ctx, target, overwrite=overwrite)
            print(f"  opencode:   {summary}")
        except (ApplyError, OSError) as e:
            _eprint(f"warning: opencode config not updated: {e}")

    return EXIT_OK


def _cmd_load(cfg: Config, args: argparse.Namespace) -> int:
    return _cmd_start_guided(cfg, args)


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
        update_opencode=getattr(args, "update_opencode", False),
        overwrite=getattr(args, "overwrite", False),
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
    )
    return _cmd_start(cfg, start_args)


def _cmd_switch(cfg: Config, args: argparse.Namespace) -> int:
    """Swap running server to a different model (convenience alias for restart --replace)."""
    start_args = argparse.Namespace(
        model=args.model,
        host=args.host or cfg.server.host,
        port=args.port or cfg.server.port,
        replace=True,
        bind_all=args.bind_all,
        extra_arg=args.extra_arg,
        verbose=args.verbose,
        update_opencode=getattr(args, "update_opencode", False),
        overwrite=getattr(args, "overwrite", False),
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
                plan = model_memory_plan(m.path)
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
        plan = model_memory_plan(Path(state.model_path))
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
            summary = reset_opencode(target)
        except (ApplyError, OSError) as e:
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
    if args.apply:
        target = expand(args.target)
        try:
            summary = apply_opencode(contexts, target, overwrite=args.overwrite)
        except (ApplyError, OSError) as e:
            _eprint(f"error: {e}")
            return EXIT_CONFIG
        print(summary)
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
    "load": _cmd_load,
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
```

### mlx_manager/config.py

- size: 8.0 KB
- language: python

```python
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli_w

from mlx_manager.paths import ensure_parent, expand

DEFAULT_CONFIG_PATH = "~/.config/mlx-manager/config.toml"

_DEFAULTS: dict[str, Any] = {
    "server": {
        "host": "127.0.0.1",
        "port": 8080,
        "log_file": "~/services/mlx/logs/mlx-lm.server.log",
        "pid_file": "~/services/mlx/mlx-lm.server.pid",
        "state_file": "~/.local/state/mlx-manager/state.json",
        "lock_file": "~/.local/state/mlx-manager/lock",
        "python_executable": "python3",
        "extra_args": [],
        "startup_timeout_seconds": 120,
        "stop_timeout_seconds": 15,
        "max_log_bytes": 10_485_760,
        "max_log_files": 5,
        "patch_tool_calls": True,
    },
    "models": {
        "directories": [
            "~/.mlx-manager/models",
            "~/.models/mlx",
            "~/models/mlx",
            "~/.cache/huggingface/hub",
            "~/.lmstudio/models",
        ],
        "default_model": "",
        "aliases": {},
    },
    "providers": {
        "base_url": "",
        "api_key": "mlx-local",
        "provider_name": "mlx-local",
    },
    "bot": {
        "model": "mlx-community/gemma-4-e2b-it-4bit",
        "cache_dir": "~/.mlx-manager/bot",
        "max_tokens": 1024,
        "temperature": 0.7,
    },
}

_KNOWN_TABLES = {"server", "models", "providers", "bot"}
_KNOWN_KEYS = {
    "server": set(_DEFAULTS["server"].keys()),
    "models": {"directories", "default_model", "aliases"},
    "providers": set(_DEFAULTS["providers"].keys()),
    "bot": set(_DEFAULTS["bot"].keys()),
}


class ConfigError(Exception):
    """Raised for invalid configuration; CLI maps this to exit code 3."""


@dataclass(frozen=True)
class ServerCfg:
    host: str
    port: int
    log_file: str
    pid_file: str
    state_file: str
    lock_file: str
    python_executable: str
    extra_args: list[str]
    startup_timeout_seconds: int
    stop_timeout_seconds: int
    max_log_bytes: int
    max_log_files: int
    patch_tool_calls: bool = True


@dataclass(frozen=True)
class ModelsCfg:
    directories: list[str]
    default_model: str
    aliases: dict[str, str]


@dataclass(frozen=True)
class ProvidersCfg:
    base_url: str
    api_key: str
    provider_name: str


@dataclass(frozen=True)
class BotCfg:
    model: str
    cache_dir: str
    max_tokens: int
    temperature: float


@dataclass(frozen=True)
class Config:
    path: Path
    server: ServerCfg
    models: ModelsCfg
    providers: ProvidersCfg
    bot: BotCfg

    @property
    def base_url(self) -> str:
        return self.providers.base_url or f"http://{self.server.host}:{self.server.port}/v1"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def write_default(path: Path) -> None:
    """Write the default config TOML to *path* (creating parents)."""
    ensure_parent(path)
    with open(path, "wb") as f:
        tomli_w.dump(_DEFAULTS, f)


def update_value(path: str | Path, table: str, key: str, value: Any) -> None:
    """Set ``[table].key = value`` in the TOML at *path*, preserving other keys.

    Reads the existing file (creating defaults first if absent), sets the one
    value, re-validates, and writes the whole document back. TOML comments are
    not preserved.
    """
    p = expand(path)
    if not p.exists():
        write_default(p)
    with open(p, "rb") as f:
        raw = tomllib.load(f)
    raw.setdefault(table, {})[key] = value
    _validate(raw)
    ensure_parent(p)
    with open(p, "wb") as f:
        tomli_w.dump(raw, f)


def _validate(raw: dict[str, Any]) -> None:
    for key in raw.keys():
        if key not in _KNOWN_TABLES:
            raise ConfigError(f"unknown top-level table: [{key}]")
    for table in _KNOWN_TABLES:
        sub = raw.get(table, {})
        if not isinstance(sub, dict):
            raise ConfigError(f"[{table}] must be a table")
        for k in sub.keys():
            if k not in _KNOWN_KEYS[table]:
                raise ConfigError(f"unknown key: [{table}].{k}")

    server = raw.get("server", {})
    if "port" in server:
        port = server["port"]
        if not isinstance(port, int) or not (1024 <= port <= 65535):
            raise ConfigError(f"server.port must be int in 1024–65535 (got {port!r})")
    if "extra_args" in server and not isinstance(server["extra_args"], list):
        raise ConfigError("server.extra_args must be a list of strings")
    if "extra_args" in server:
        for a in server["extra_args"]:
            if not isinstance(a, str):
                raise ConfigError("server.extra_args entries must be strings")
    if "patch_tool_calls" in server and not isinstance(server["patch_tool_calls"], bool):
        raise ConfigError("server.patch_tool_calls must be a boolean")

    models = raw.get("models", {})
    if "directories" in models:
        if not isinstance(models["directories"], list):
            raise ConfigError("models.directories must be a list of strings")
        for d in models["directories"]:
            if not isinstance(d, str):
                raise ConfigError("models.directories entries must be strings")
    if "aliases" in models and not isinstance(models["aliases"], dict):
        raise ConfigError("[models.aliases] must be a table")

    bot = raw.get("bot", {})
    if "model" in bot and not isinstance(bot["model"], str):
        raise ConfigError("bot.model must be a string")
    if "cache_dir" in bot and not isinstance(bot["cache_dir"], str):
        raise ConfigError("bot.cache_dir must be a string")
    if "max_tokens" in bot and (
        not isinstance(bot["max_tokens"], int) or bot["max_tokens"] <= 0
    ):
        raise ConfigError("bot.max_tokens must be a positive int")
    if "temperature" in bot and not isinstance(bot["temperature"], (int, float)):
        raise ConfigError("bot.temperature must be a number")


def load(path: str | Path | None = None) -> Config:
    """Load config from *path* (default ``~/.config/mlx-manager/config.toml``).

    Creates a default config on first use. Unknown tables/keys raise ConfigError.
    """
    cfg_path = expand(path or DEFAULT_CONFIG_PATH)
    if not cfg_path.exists():
        write_default(cfg_path)

    with open(cfg_path, "rb") as f:
        raw = tomllib.load(f)

    _validate(raw)

    merged = _deep_merge(_DEFAULTS, raw)
    server = merged["server"]
    models = merged["models"]
    providers = merged["providers"]
    bot = merged["bot"]

    return Config(
        path=cfg_path,
        server=ServerCfg(
            host=str(server["host"]),
            port=int(server["port"]),
            log_file=str(server["log_file"]),
            pid_file=str(server["pid_file"]),
            state_file=str(server["state_file"]),
            lock_file=str(server["lock_file"]),
            python_executable=str(server["python_executable"]),
            extra_args=list(server["extra_args"]),
            startup_timeout_seconds=int(server["startup_timeout_seconds"]),
            stop_timeout_seconds=int(server["stop_timeout_seconds"]),
            max_log_bytes=int(server["max_log_bytes"]),
            max_log_files=int(server["max_log_files"]),
            patch_tool_calls=bool(server["patch_tool_calls"]),
        ),
        models=ModelsCfg(
            directories=[str(d) for d in models["directories"]],
            default_model=str(models["default_model"]),
            aliases={str(k): str(v) for k, v in models["aliases"].items()},
        ),
        providers=ProvidersCfg(
            base_url=str(providers["base_url"]),
            api_key=str(providers["api_key"]),
            provider_name=str(providers["provider_name"]),
        ),
        bot=BotCfg(
            model=str(bot["model"]),
            cache_dir=str(bot["cache_dir"]),
            max_tokens=int(bot["max_tokens"]),
            temperature=float(bot["temperature"]),
        ),
    )
```

### mlx_manager/context.py

- size: 3.4 KB
- language: python

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def system_ram_bytes() -> int:
    """Return total unified memory in bytes (macOS sysctl). Returns 0 on failure."""
    try:
        out = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return int(out.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return 0


def model_weight_bytes(model_path: Path) -> int:
    """Sum of safetensors weight file sizes under *model_path*."""
    total = 0
    try:
        for c in model_path.iterdir():
            if c.is_file() and (
                c.name in ("model.safetensors", "weights.safetensors")
                or (c.name.startswith("model-") and c.name.endswith(".safetensors"))
            ):
                total += c.stat().st_size
    except OSError:
        pass
    return total


def safe_context_tokens(total_ram: int, model_bytes: int, cfg_json: dict) -> int:
    """Return the largest context (in tokens) that fits in unified memory.

    Derives KV cache bytes-per-token from the model config, subtracts model
    weights and a 3 GB system headroom from available RAM, then caps at the
    model's architectural maximum.  Returns 0 when inputs are insufficient.
    """
    layers = cfg_json.get("num_hidden_layers", 32)
    kv_heads = cfg_json.get("num_key_value_heads") or cfg_json.get("num_attention_heads", 8)
    head_dim = cfg_json.get("head_dim") or (
        cfg_json.get("hidden_size", 4096) // max(int(cfg_json.get("num_attention_heads", 32)), 1)
    )
    bytes_per_token = 2 * int(layers) * int(kv_heads) * int(head_dim) * 2  # K+V, fp16
    if not bytes_per_token:
        return 0
    # Scale headroom with machine size: Metal on Apple Silicon tops out at ~75% of
    # unified RAM; generation buffers add to weights. 30% reservation is empirically
    # safe across 16–128 GB machines; floor at 8 GB for small machines.
    headroom = max(8 * 1024 ** 3, int(total_ram * 0.30))
    usable = max(0, total_ram - model_bytes - headroom)
    arch_max = int(cfg_json.get("max_position_embeddings", 32768))
    return min(usable // bytes_per_token, arch_max)


def model_memory_plan(model_path: Path) -> tuple[int, int] | None:
    """Return ``(context_tokens, kv_cache_bytes)`` for this model on this machine.

    Reads the model's ``config.json``, queries system RAM, and runs the safe
    context calculation.  Returns ``None`` when any input is unavailable or the
    result is zero.
    """
    try:
        with open(model_path / "config.json", encoding="utf-8") as f:
            cfg_json: dict = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    total_ram = system_ram_bytes()
    if not total_ram:
        return None

    m_bytes = model_weight_bytes(model_path)
    tokens = safe_context_tokens(total_ram, m_bytes, cfg_json)
    if tokens <= 0:
        return None

    layers = cfg_json.get("num_hidden_layers", 32)
    kv_heads = cfg_json.get("num_key_value_heads") or cfg_json.get("num_attention_heads", 8)
    head_dim = cfg_json.get("head_dim") or (
        cfg_json.get("hidden_size", 4096) // max(int(cfg_json.get("num_attention_heads", 32)), 1)
    )
    bytes_per_token = 2 * int(layers) * int(kv_heads) * int(head_dim) * 2
    return tokens, tokens * bytes_per_token
```

### mlx_manager/models.py

- size: 4.7 KB
- language: python

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal

from mlx_manager.config import ModelsCfg
from mlx_manager.paths import expand

Source = Literal["alias", "directory", "hf_cache"]

# Discovery walks each configured root recursively up to this many levels.
# 2 covers LM Studio (publisher/model-name), 3 covers the HF cache layout
# (models--org--name/snapshots/rev), 4 gives a little headroom for users with
# slightly deeper trees. Recursion also short-circuits the moment a model
# directory is found, so this only bounds *unproductive* walks.
_MAX_DEPTH = 4


@dataclass(frozen=True)
class Model:
    id: str
    path: Path
    source: Source

    def to_dict(self) -> dict:
        return {"id": self.id, "path": str(self.path), "source": self.source}


def _is_model_dir(path: Path) -> bool:
    """A directory is a candidate model iff it contains ``config.json`` and at
    least one safetensors weights file (single, sharded, or ``weights.safetensors``)."""
    if not path.is_dir():
        return False
    if not (path / "config.json").is_file():
        return False
    if (path / "model.safetensors").is_file():
        return True
    if (path / "weights.safetensors").is_file():
        return True
    for child in path.iterdir():
        name = child.name
        if name.startswith("model-") and name.endswith(".safetensors"):
            return True
    return False


def _pick_hf_snapshot(snapshots_dir: Path) -> Path | None:
    if not snapshots_dir.is_dir():
        return None
    candidates = sorted(
        (s for s in snapshots_dir.iterdir() if s.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for snap in candidates:
        if _is_model_dir(snap):
            return snap
    return None


def _scan(root: Path, *, _depth: int = 0) -> Iterator[Model]:
    """Recursively walk *root* yielding Models.

    Handles three layouts uniformly:

    - flat ``<root>/<model-name>``
    - nested ``<root>/<publisher>/<model-name>`` (LM Studio)
    - HF cache ``<root>/models--<org>--<name>/snapshots/<rev>/``

    Walk stops descending the moment it identifies a model (or an HF repo dir);
    hidden directories beneath the root are skipped. The yielded ``id`` is the
    string that will be passed to ``mlx_lm.server --model`` and thus also the
    string the HTTP API exposes — for filesystem models that's the model
    directory's basename, for HF-cache models it's ``<org>/<name>``.
    """
    if not root.is_dir() or _depth > _MAX_DEPTH:
        return

    # Special-case HF cache repos: emit the newest snapshot directly.
    if _depth > 0 and root.name.startswith("models--"):
        parts = root.name.split("--", 2)
        if len(parts) == 3:
            _, org, name = parts
            snap = _pick_hf_snapshot(root / "snapshots")
            if snap is not None:
                yield Model(
                    id=f"{org}/{name}", path=snap.resolve(), source="hf_cache"
                )
        return

    if _depth > 0 and _is_model_dir(root):
        yield Model(id=root.name, path=root.resolve(), source="directory")
        return

    try:
        children = sorted(root.iterdir())
    except (PermissionError, OSError):
        return
    for child in children:
        if not child.is_dir():
            continue
        if _depth > 0 and child.name.startswith("."):
            continue
        yield from _scan(child, _depth=_depth + 1)


def discover(cfg: ModelsCfg) -> list[Model]:
    """Return the de-duplicated model list, alias > directory > hf_cache priority."""
    found: dict[str, Model] = {}

    for alias, raw in cfg.aliases.items():
        target = expand(raw)
        found[alias] = Model(id=alias, path=target, source="alias")

    for raw_dir in cfg.directories:
        root = expand(raw_dir)
        for m in _scan(root):
            if m.id in found:
                continue
            found[m.id] = m

    return list(found.values())


def resolve(cfg: ModelsCfg, requested: str) -> Model:
    """Resolve *requested* to a Model.

    Order: alias → discovered display name → absolute filesystem path.
    Raises LookupError if nothing resolves.
    """
    if not requested:
        raise LookupError("no model specified and [models].default_model is empty")

    if requested in cfg.aliases:
        return Model(id=requested, path=expand(cfg.aliases[requested]), source="alias")

    models = discover(cfg)
    for m in models:
        if m.id == requested:
            return m

    p = expand(requested)
    if p.is_absolute() and _is_model_dir(p):
        return Model(id=p.name, path=p.resolve(), source="directory")

    raise LookupError(
        f"model {requested!r} not found; try `mlx-manager list` to see available IDs"
    )
```

### mlx_manager/paths.py

- size: 702 B
- language: python

```python
from __future__ import annotations

import os
from pathlib import Path


def expand(path: str | os.PathLike) -> Path:
    """Expand ``~`` and ``$VAR``/``${VAR}`` in *path* and return an absolute Path."""
    return Path(os.path.expandvars(os.path.expanduser(str(path)))).expanduser()


def ensure_parent(path: str | os.PathLike) -> Path:
    """Ensure the parent directory of *path* exists. Returns the expanded path."""
    p = expand(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def ensure_dir(path: str | os.PathLike) -> Path:
    """Ensure *path* (a directory) exists. Returns the expanded path."""
    p = expand(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
```

### mlx_manager/providers.py

- size: 8.5 KB
- language: python

```python
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
```

### mlx_manager/server.py

- size: 27.3 KB
- language: python

```python
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
# Port-keyed path helpers
# ---------------------------------------------------------------------------


def _servers_dir(cfg: "Config") -> Path:
    return expand(cfg.server.state_file).parent / "servers"


def port_state_path(cfg: "Config", port: int) -> Path:
    return _servers_dir(cfg) / f"{port}.json"


def port_pid_path(cfg: "Config", port: int) -> Path:
    p = expand(cfg.server.pid_file)
    return p.parent / f"{p.stem}.{port}{p.suffix}"


def port_lock_path(cfg: "Config", port: int) -> Path:
    p = expand(cfg.server.lock_file)
    return Path(f"{p}.{port}")


def port_log_path(cfg: "Config", port: int) -> Path:
    p = expand(cfg.server.log_file)
    return p.parent / f"{p.stem}.{port}{p.suffix}"


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


def list_running_states(cfg: Config) -> list[State]:
    """Return all currently-running managed server states, sorted by port."""
    d = _servers_dir(cfg)
    if not d.exists():
        return []
    states = []
    for f in sorted(d.glob("*.json")):
        state = read_state(f)
        if state is not None and is_managed_process(state.pid, state):
            states.append(state)
    return states


def primary_state(cfg: Config) -> State | None:
    """Return the 'primary' running state for single-server commands.

    Prefers the configured default port; falls back to the first running server.
    """
    running = list_running_states(cfg)
    if not running:
        return None
    for s in running:
        if s.port == cfg.server.port:
            return s
    return running[0]


def clear_state(cfg: Config, port: int) -> None:
    for path in (port_state_path(cfg, port), port_pid_path(cfg, port)):
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


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


def _looks_like_mlx_lm_server_command(cmd: str) -> bool:
    return (
        "mlx_lm server" in cmd
        or "mlx_lm.server" in cmd
        or "mlx_lm" in cmd
        or _SERVER_SHIM.name in cmd
    )


def is_managed_process(pid: int, state: State | None = None) -> bool:
    """True if *pid* is alive and its argv looks like a managed mlx_lm server.

    If *state* is given, also requires its recorded port to be present in the
    live argv, plus at least one of: the recorded model alias (== the serving
    id we passed via ``--model``), the model path, or the path's basename.
    """
    if not pid_alive(pid):
        return False
    cmd = pid_command(pid)
    if not _looks_like_mlx_lm_server_command(cmd):
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
# Log-based health
# ---------------------------------------------------------------------------

# mlx_lm logs this when its HTTP listener comes up; the model is loaded lazily
# on the first request, so /v1/models can answer 200 while the model itself
# never loads. We bound the health scan to the current session by anchoring on
# the most recent occurrence of this marker.
_HTTPD_START_MARKER = "Starting httpd"

# Patterns whose presence in the current session's log means the process is up
# but cannot actually serve the model. Each maps a regex to a human message.
_FATAL_LOG_PATTERNS: list[tuple[re.Pattern[str], Any]] = [
    (
        re.compile(r"Model type (\S+?) not supported"),
        lambda m: f"model architecture '{m.group(1)}' is not supported by the installed mlx_lm",
    ),
    (
        re.compile(r"No module named ['\"]mlx_lm\.models\.([\w.]+)['\"]"),
        lambda m: f"installed mlx_lm has no module for architecture '{m.group(1)}'",
    ),
    (
        re.compile(r"(?:metal::|Metal).{0,80}?out of memory|out of memory", re.IGNORECASE),
        lambda m: "ran out of memory while loading the model",
    ),
    (
        re.compile(
            r"\[METAL\].{0,160}?(?:Insufficient Memory|OutOfMemory|kIOGPUCommandBufferCallbackErrorOutOfMemory)",
            re.IGNORECASE,
        ),
        lambda m: "ran out of Metal/unified memory; reduce prompt cache, concurrency, or context size and restart",
    ),
    (
        re.compile(r"SafetensorError|HeaderTooLarge|Error while deserializing header"),
        lambda m: "failed to read model weights (safetensors error)",
    ),
    (
        re.compile(r"(?:OSError|FileNotFoundError).{0,120}?(?:config\.json|safetensors|tokenizer)"),
        lambda m: "model files appear to be missing or unreadable",
    ),
]


def log_health(log_path: Path, scan_lines: int = 600) -> tuple[str, str]:
    """Inspect the current session's log tail for a fatal model-load error.

    Returns ``("ok", "")`` when nothing fatal is found, otherwise
    ``("error", human_readable_detail)``. The scan is bounded to lines after
    the most recent ``Starting httpd`` marker so errors from a previous run of
    the same (appended) log file are ignored.
    """
    lines = tail_lines(log_path, scan_lines)
    if not lines:
        return "ok", ""
    start_idx = 0
    for i in range(len(lines) - 1, -1, -1):
        if _HTTPD_START_MARKER in lines[i]:
            start_idx = i
            break
    text = "\n".join(lines[start_idx:])
    for pattern, fmt in _FATAL_LOG_PATTERNS:
        m = pattern.search(text)
        if m:
            return "error", fmt(m)
    return "ok", ""


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

# Launch shim that patches mlx_lm.server (so unparseable tool calls report
# finish_reason=length) before handing off to mlx_lm's own CLI. Used in place of
# `-m mlx_lm` when server.patch_tool_calls is enabled. See _server_shim.py.
_SERVER_SHIM = Path(__file__).with_name("_server_shim.py")


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
    if cfg.server.patch_tool_calls:
        launcher = [cfg.server.python_executable, str(_SERVER_SHIM), "server"]
    else:
        launcher = [cfg.server.python_executable, "-m", "mlx_lm", "server"]
    cmd = [
        *launcher,
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
    state_path = port_state_path(cfg, port)
    pid_path = port_pid_path(cfg, port)
    log_path = port_log_path(cfg, port)

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
                f"server already running on port {port} (pid {existing.pid}, model "
                f"{existing.model_alias!r}); use --replace to swap",
                exit_code=5,
            )
        if on_verbose:
            on_verbose(f"stopping existing server (pid {existing.pid})")
        stop(cfg, port=port, timeout=cfg.server.stop_timeout_seconds)

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
        clear_state(cfg, port)
        tail = "\n".join(tail_lines(log_path, 40))
        raise ServerError(
            f"server did not become ready within "
            f"{cfg.server.startup_timeout_seconds}s\n\n--- last 40 log lines ---\n{tail}",
            exit_code=6,
        )

    return state


def stop(cfg: Config, *, port: int | None = None, timeout: int | None = None) -> State:
    """Stop the managed server. Returns the killed State or raises ServerError(4).

    If *port* is None and exactly one server is running, it is stopped.
    If multiple servers are running, raises ServerError listing them.
    """
    if port is None:
        running = list_running_states(cfg)
        if not running:
            raise ServerError("no managed server is running", exit_code=4)
        if len(running) > 1:
            summary = ", ".join(f":{s.port} ({s.model_alias})" for s in running)
            raise ServerError(
                f"multiple servers running ({summary}); use --port to specify which to stop",
                exit_code=1,
            )
        port = running[0].port

    state_path = port_state_path(cfg, port)
    state = read_state(state_path)
    if state is None or not pid_alive(state.pid):
        clear_state(cfg, port)
        raise ServerError("no managed server is running", exit_code=4)

    cmd = pid_command(state.pid)
    if not _looks_like_mlx_lm_server_command(cmd):
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
        clear_state(cfg, port)
        raise ServerError("process disappeared before SIGTERM", exit_code=4)

    deadline = time.monotonic() + t
    while time.monotonic() < deadline:
        if not pid_alive(state.pid):
            break
        time.sleep(0.2)
    else:
        with contextlib.suppress(ProcessLookupError):
            os.kill(state.pid, signal.SIGKILL)

    clear_state(cfg, port)
    return state


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def status_dict(cfg: Config, port: int | None = None) -> dict[str, Any]:
    if port is None:
        port = cfg.server.port
    state_path = port_state_path(cfg, port)
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
            "health": "ok",
            "health_detail": "",
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
    health, health_detail = log_health(port_log_path(cfg, state.port))
    return {
        **state.to_dict(),
        "running": managed,
        "uptime_seconds": uptime if managed else 0,
        "endpoint_ok": endpoint_ok(state.host, state.port) if managed else False,
        "health": health,
        "health_detail": health_detail,
        "stale": (not managed),
    }


def all_status_dicts(cfg: Config) -> list[dict[str, Any]]:
    """Return a status dict for every managed server (running or stale)."""
    d = _servers_dir(cfg)
    if not d.exists():
        return []
    results = []
    for f in sorted(d.glob("*.json")):
        state = read_state(f)
        if state is None:
            continue
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
        health, health_detail = log_health(port_log_path(cfg, state.port))
        results.append({
            **state.to_dict(),
            "running": managed,
            "uptime_seconds": uptime if managed else 0,
            "endpoint_ok": endpoint_ok(state.host, state.port) if managed else False,
            "health": health,
            "health_detail": health_detail,
            "stale": not managed,
        })
    return results
```

### pyproject.toml

- size: 1.6 KB
- language: toml

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mlx-manager"
version = "0.1.0"
description = "Headless controller for the MLX language-model HTTP server on Apple Silicon."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "rs" }]
keywords = ["mlx", "mlx-lm", "apple-silicon", "llm", "local-llm", "cli", "opencode"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: MacOS :: MacOS X",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Systems Administration",
]

dependencies = [
    "tomli-w>=1.0",
]

[project.urls]
Homepage = "https://github.com/Pixie-sh/mlx-manager"
Repository = "https://github.com/Pixie-sh/mlx-manager"
Issues = "https://github.com/Pixie-sh/mlx-manager/issues"
Changelog = "https://github.com/Pixie-sh/mlx-manager/blob/main/CHANGELOG.md"

[project.optional-dependencies]
dev = ["pytest>=7", "huggingface-hub>=0.20"]

[project.scripts]
mlx-manager = "mlx_manager.cli:main"

[tool.setuptools.packages.find]
include = ["mlx_manager*"]
exclude = ["tests*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

### technical.md

- size: 17.3 KB
- language: markdown

````markdown
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
````

### tests/conftest.py

- size: 5.1 KB
- language: python

```python
"""Shared fixtures.

The whole suite must run without ``mlx_lm`` installed and without ever
starting a real MLX server, so all model layouts and processes here are
synthetic.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from mlx_manager.config import BotCfg, Config, ModelsCfg, ProvidersCfg, ServerCfg


def _make_model_dir(root: Path, name: str, *, sharded: bool = False) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "config.json").write_text(json.dumps({"model_type": "synthetic"}))
    if sharded:
        (d / "model-00001-of-00002.safetensors").write_bytes(b"")
        (d / "model-00002-of-00002.safetensors").write_bytes(b"")
    else:
        (d / "model.safetensors").write_bytes(b"")
    (d / "tokenizer.json").write_text("{}")
    return d


@pytest.fixture()
def fake_models_root(tmp_path: Path) -> Path:
    """A plain models directory with two model subdirs."""
    root = tmp_path / "models"
    _make_model_dir(root, "qwen3-8b-4bit")
    _make_model_dir(root, "llama-3-8b-4bit", sharded=True)
    # Decoy: looks like a model dir but lacks weights.
    decoy = root / "no-weights"
    decoy.mkdir()
    (decoy / "config.json").write_text("{}")
    return root


@pytest.fixture()
def fake_hf_cache(tmp_path: Path) -> Path:
    """A fake Hugging Face hub cache with one resolvable snapshot."""
    cache = tmp_path / "hf" / "hub"
    cache.mkdir(parents=True)

    repo = cache / "models--mlx-community--Llama-3.2-3B-Instruct-4bit"
    blobs = repo / "blobs"
    snapshots = repo / "snapshots"
    snap = snapshots / "abc123"
    blobs.mkdir(parents=True)
    snap.mkdir(parents=True)
    (snap / "config.json").write_text("{}")
    (snap / "model.safetensors").write_bytes(b"")

    # A second repo whose snapshot has no weights — must be skipped.
    bad_repo = cache / "models--someorg--no-weights"
    (bad_repo / "snapshots" / "deadbeef").mkdir(parents=True)
    (bad_repo / "snapshots" / "deadbeef" / "config.json").write_text("{}")

    return cache


@pytest.fixture()
def fake_lmstudio_root(tmp_path: Path) -> Path:
    """A fake LM Studio models tree: ``<root>/<publisher>/<model-name>/``."""
    root = tmp_path / "lmstudio" / "models"
    _make_model_dir(
        root / "lmstudio-community", "gemma-test-MLX-4bit", sharded=True
    )
    _make_model_dir(root / "someuser", "exotic-model-3bit")
    # Decoy: publisher with no real model dirs underneath.
    (root / "empty-publisher").mkdir(parents=True)
    return root


@pytest.fixture()
def cfg_factory(tmp_path: Path):
    """Build a Config rooted in *tmp_path* with the given knobs overridden."""

    def make(**overrides):
        defaults = {
            "host": "127.0.0.1",
            "port": 18080,
            "log_file": str(tmp_path / "mlx.log"),
            "pid_file": str(tmp_path / "mlx.pid"),
            "state_file": str(tmp_path / "state.json"),
            "lock_file": str(tmp_path / "mlx.lock"),
            "python_executable": "python3",
            "extra_args": [],
            "startup_timeout_seconds": 5,
            "stop_timeout_seconds": 2,
            "max_log_bytes": 1024,
            "max_log_files": 3,
            "patch_tool_calls": True,
            "directories": [],
            "default_model": "",
            "aliases": {},
            "base_url": "",
            "api_key": "mlx-local",
            "provider_name": "mlx-local",
            "bot_model": "mlx-community/gemma-4-e2b-it-4bit",
            "bot_cache_dir": str(tmp_path / "bot"),
            "bot_max_tokens": 1024,
            "bot_temperature": 0.7,
        }
        defaults.update(overrides)
        server = ServerCfg(
            host=defaults["host"],
            port=defaults["port"],
            log_file=defaults["log_file"],
            pid_file=defaults["pid_file"],
            state_file=defaults["state_file"],
            lock_file=defaults["lock_file"],
            python_executable=defaults["python_executable"],
            extra_args=list(defaults["extra_args"]),
            startup_timeout_seconds=defaults["startup_timeout_seconds"],
            stop_timeout_seconds=defaults["stop_timeout_seconds"],
            max_log_bytes=defaults["max_log_bytes"],
            max_log_files=defaults["max_log_files"],
            patch_tool_calls=defaults["patch_tool_calls"],
        )
        models = ModelsCfg(
            directories=list(defaults["directories"]),
            default_model=defaults["default_model"],
            aliases=dict(defaults["aliases"]),
        )
        providers = ProvidersCfg(
            base_url=defaults["base_url"],
            api_key=defaults["api_key"],
            provider_name=defaults["provider_name"],
        )
        bot = BotCfg(
            model=defaults["bot_model"],
            cache_dir=defaults["bot_cache_dir"],
            max_tokens=defaults["bot_max_tokens"],
            temperature=defaults["bot_temperature"],
        )
        return Config(
            path=tmp_path / "config.toml",
            server=server,
            models=models,
            providers=providers,
            bot=bot,
        )

    return make
```

### tests/test_benchmark.py

- size: 5.2 KB
- language: python

```python
"""Benchmark tests use an in-process fake SSE server so no real model is needed."""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest

from mlx_manager.benchmark import run, stream_one


def _make_handler(
    *,
    completion_tokens: int = 10,
    prompt_tokens: int = 4,
    first_chunk_delay_s: float = 0.0,
    inter_chunk_delay_s: float = 0.0,
    finish_reason: str = "stop",
):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *a, **kw):  # silence test output
            return

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            _ = self.rfile.read(length)  # discard body
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            def write_chunk(obj: dict) -> None:
                self.wfile.write(b"data: " + json.dumps(obj).encode() + b"\n\n")
                self.wfile.flush()

            # initial "role" delta with no content — must NOT mark TTFT.
            write_chunk({"choices": [{"delta": {"role": "assistant"}}]})
            if first_chunk_delay_s:
                time.sleep(first_chunk_delay_s)
            # content chunks — first one marks TTFT.
            for i in range(completion_tokens):
                write_chunk(
                    {"choices": [{"delta": {"content": f"tok{i} "}}]}
                )
                if inter_chunk_delay_s:
                    time.sleep(inter_chunk_delay_s)
            # final chunk with finish_reason + usage
            write_chunk(
                {
                    "choices": [{"delta": {}, "finish_reason": finish_reason}],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                    },
                }
            )
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    return _Handler


@pytest.fixture()
def fake_server():
    """Start a ThreadingHTTPServer on a random port. Yields its base URL."""
    server: dict[str, object] = {}

    def start(handler_cls):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        port = srv.server_address[1]
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        server["srv"] = srv
        server["thread"] = thread
        return f"http://127.0.0.1:{port}/v1"

    yield start

    s = server.get("srv")
    if s is not None:
        s.shutdown()
        s.server_close()


def test_stream_one_parses_ttft_and_tokens(fake_server):
    endpoint = fake_server(
        _make_handler(
            completion_tokens=8,
            prompt_tokens=3,
            first_chunk_delay_s=0.05,
        )
    )
    r = stream_one(endpoint, "test-model", "hi", max_tokens=16)
    assert r.ok
    assert r.completion_tokens == 8
    assert r.prompt_tokens == 3
    assert r.finish_reason == "stop"
    # TTFT must be set, and must reflect the artificial delay (not zero).
    assert r.ttft_s is not None and r.ttft_s >= 0.04
    # decode_tps is positive.
    assert r.decode_tps > 0


def test_stream_one_returns_error_on_connection_failure():
    # Port 1 is reserved; should fail to connect.
    r = stream_one("http://127.0.0.1:1/v1", "any", "hi", max_tokens=4)
    assert not r.ok
    assert r.completion_tokens == 0
    assert "error" not in r.error.lower() or r.error  # any message is fine


def test_run_concurrency_and_summary(fake_server):
    endpoint = fake_server(
        _make_handler(completion_tokens=5, prompt_tokens=2, inter_chunk_delay_s=0.01)
    )
    summary = run(
        endpoint,
        "test-model",
        "hello",
        requests=4,
        concurrency=2,
        max_tokens=16,
        warmup=0,
    )
    assert summary.requests_total == 4
    assert summary.requests_ok == 4
    assert summary.concurrency == 2
    # Sum of completion tokens / wall time.
    assert summary.aggregate_decode_tps > 0
    # Per-stream stats populated.
    assert summary.ttft_p50 is not None
    assert summary.decode_tps_p50 is not None
    assert summary.total_p50 is not None
    # Each request reported.
    assert len(summary.per_request) == 4
    assert all(r.ok and r.completion_tokens == 5 for r in summary.per_request)


def test_run_validates_arguments():
    with pytest.raises(ValueError, match="concurrency"):
        run("http://x/v1", "m", "p", requests=1, concurrency=0, max_tokens=4)
    with pytest.raises(ValueError, match="requests"):
        run("http://x/v1", "m", "p", requests=0, concurrency=1, max_tokens=4)
    with pytest.raises(ValueError, match="warmup"):
        run("http://x/v1", "m", "p", requests=1, concurrency=1, warmup=-1, max_tokens=4)


def test_run_summary_to_dict_is_json_serializable(fake_server):
    endpoint = fake_server(_make_handler())
    summary = run(endpoint, "test-model", "hi", requests=2, concurrency=1, max_tokens=8)
    # If this doesn't raise, the shape is fine for `--json` output.
    json.dumps(summary.to_dict())
```

### tests/test_bot.py

- size: 4.3 KB
- language: python

```python
from __future__ import annotations

import json

import pytest

from mlx_manager import bot as bot_mod


def _make_model(path):
    path.mkdir(parents=True)
    (path / "config.json").write_text(json.dumps({"model_type": "gemma"}))
    (path / "model.safetensors").write_bytes(b"")


def test_resolve_model_uses_existing_local_dir(tmp_path):
    local = tmp_path / "my-model"
    _make_model(local)
    # An absolute, complete local dir is returned as-is, no download attempted.
    assert bot_mod.resolve_model(str(local), str(tmp_path / "bot")) == str(local)


def test_resolve_model_reuses_cached_repo_without_network(tmp_path):
    cache = tmp_path / "bot"
    # Pre-seed the cache as if a prior run already downloaded it.
    cached = cache / "mlx-community--gemma-4-e2b-it-4bit"
    _make_model(cached)
    # snapshot_download must NOT be called when the model is already present.
    result = bot_mod.resolve_model("mlx-community/gemma-4-e2b-it-4bit", str(cache))
    assert result == str(cached)


def test_resolve_model_downloads_once_when_missing(tmp_path, monkeypatch):
    cache = tmp_path / "bot"
    calls = []

    def fake_snapshot_download(repo_id, local_dir):
        calls.append((repo_id, local_dir))
        from pathlib import Path

        _make_model(Path(local_dir))
        return local_dir

    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_snapshot_download)

    result = bot_mod.resolve_model(
        "mlx-community/gemma-4-e2b-it-4bit", str(cache), on_status=lambda _m: None
    )
    expected = cache / "mlx-community--gemma-4-e2b-it-4bit"
    assert result == str(expected)
    assert calls == [("mlx-community/gemma-4-e2b-it-4bit", str(expected))]


def test_build_system_prompt_with_and_without_context():
    status = [{"running": True, "port": 1235, "model_alias": "qwen", "endpoint_ok": True, "health": "ok"}]
    doctor = [{"name": "python", "status": "OK", "detail": "ok"}]
    full = bot_mod.build_system_prompt(status, doctor)
    assert "port 1235" in full and "Running servers" in full
    bare = bot_mod.build_system_prompt(status, doctor, with_context=False)
    assert "Running servers" not in bare


def test_select_model_override_wins(tmp_path):
    bot_mod.save_selection(str(tmp_path), "saved/model")
    assert bot_mod.select_model("cli/override", "default/model", str(tmp_path)) == "cli/override"


def test_select_model_uses_saved_selection(tmp_path):
    bot_mod.save_selection(str(tmp_path), "saved/model")
    assert bot_mod.select_model(None, "default/model", str(tmp_path)) == "saved/model"


def test_select_model_uses_default_if_already_downloaded(tmp_path):
    _make_model(tmp_path / "default--model")
    assert bot_mod.select_model(None, "default/model", str(tmp_path)) == "default/model"


def test_select_model_returns_none_for_first_run(tmp_path):
    assert bot_mod.select_model(None, "default/model", str(tmp_path)) is None


def test_choose_model_empty_picks_default():
    chosen = bot_mod.choose_model(
        "mlx-community/Qwen3-1.7B-4bit",
        input_fn=lambda _p: "",
        out_fn=lambda _m: None,
    )
    assert chosen == "mlx-community/Qwen3-1.7B-4bit"


def test_choose_model_numeric_pick():
    chosen = bot_mod.choose_model(
        bot_mod.BOT_MODELS[0]["id"],
        input_fn=lambda _p: "2",
        out_fn=lambda _m: None,
    )
    assert chosen == bot_mod.BOT_MODELS[1]["id"]


def test_choose_model_custom_repo_id():
    chosen = bot_mod.choose_model(
        bot_mod.BOT_MODELS[0]["id"],
        input_fn=lambda _p: "some-org/custom-model",
        out_fn=lambda _m: None,
    )
    assert chosen == "some-org/custom-model"


def test_choose_model_menu_lists_all_options():
    lines = []
    bot_mod.choose_model(
        bot_mod.BOT_MODELS[0]["id"],
        input_fn=lambda _p: "1",
        out_fn=lines.append,
    )
    rendered = "\n".join(lines)
    for m in bot_mod.BOT_MODELS:
        assert m["label"] in rendered
    assert "(default)" in rendered


def test_build_system_prompt_flags_unhealthy_server():
    status = [{
        "running": True, "port": 1236, "model_alias": "deepseek",
        "endpoint_ok": True, "health": "error",
        "health_detail": "model architecture 'deepseek_v4' is not supported",
    }]
    prompt = bot_mod.build_system_prompt(status, [])
    assert "deepseek_v4" in prompt and "ERROR" in prompt
```

### tests/test_cli_json.py

- size: 6.0 KB
- language: python

```python
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from mlx_manager import cli


def _run(monkeypatch, capsys, args, *, config_path: Path) -> tuple[int, str, str]:
    rc = cli.main(["--config", str(config_path), *args])
    out, err = capsys.readouterr()
    return rc, out, err


def test_list_json_empty_when_no_models(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[models]\ndirectories = []\n\n[server]\nlog_file = "{0}/mlx.log"\n'
        'pid_file = "{0}/mlx.pid"\nstate_file = "{0}/state.json"\n'
        'lock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    rc, out, _ = _run(monkeypatch, capsys, ["list", "--json"], config_path=cfg)
    assert rc == 0
    assert json.loads(out) == []


def test_list_json_shape(tmp_path, monkeypatch, capsys, fake_models_root):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[models]\ndirectories = ["{r}"]\n\n[server]\n'
        'log_file = "{t}/mlx.log"\npid_file = "{t}/mlx.pid"\n'
        'state_file = "{t}/state.json"\nlock_file = "{t}/mlx.lock"\n'.format(
            r=fake_models_root, t=tmp_path
        )
    )
    rc, out, _ = _run(monkeypatch, capsys, ["list", "--json"], config_path=cfg)
    assert rc == 0
    items = json.loads(out)
    assert isinstance(items, list)
    assert all({"id", "path", "source"} <= set(item.keys()) for item in items)
    ids = {i["id"] for i in items}
    assert "qwen3-8b-4bit" in ids


def test_status_json_when_not_running(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    # Without --port: returns a list (empty when nothing is running).
    rc, out, _ = _run(monkeypatch, capsys, ["status", "--json"], config_path=cfg)
    assert rc == 4
    items = json.loads(out)
    assert isinstance(items, list)
    assert items == []

    # With --port: returns a single status dict.
    rc, out, _ = _run(monkeypatch, capsys, ["status", "--port", "8080", "--json"], config_path=cfg)
    assert rc == 4
    d = json.loads(out)
    assert d["running"] is False
    assert d["stale"] is False
    assert d["uptime_seconds"] == 0


def test_doctor_json_emits_check_array(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    rc, out, _ = _run(monkeypatch, capsys, ["doctor", "--json"], config_path=cfg)
    # Doctor exits 0 or 1 depending on system state, but JSON must always parse.
    assert rc in (0, 1)
    items = json.loads(out)
    assert isinstance(items, list)
    assert all({"name", "status", "detail"} <= set(i.keys()) for i in items)
    for i in items:
        assert i["status"] in ("OK", "WARN", "FAIL")


def test_config_opencode_emits_json(tmp_path, monkeypatch, capsys, fake_models_root):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[models]\ndirectories = ["{r}"]\ndefault_model = "qwen3-8b-4bit"\n\n'
        '[server]\nlog_file = "{t}/mlx.log"\npid_file = "{t}/mlx.pid"\n'
        'state_file = "{t}/state.json"\nlock_file = "{t}/mlx.lock"\n'.format(
            r=fake_models_root, t=tmp_path
        )
    )
    rc, out, _ = _run(
        monkeypatch,
        capsys,
        ["config", "opencode", "--model", "qwen3-8b-4bit"],
        config_path=cfg,
    )
    assert rc == 0
    doc = json.loads(out)
    assert "provider" in doc
    assert "mlx-manager:mlx-local:8080" in doc["provider"]


def test_config_opencode_running_single_server_name_includes_port(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    monkeypatch.setattr(
        cli.srv,
        "list_running_states",
        lambda cfg_obj: [
            cli.srv.State(
                pid=123,
                model_alias="qwen3-8b-4bit",
                model_path="/tmp/qwen3-8b-4bit",
                host="127.0.0.1",
                port=18081,
                base_url="http://127.0.0.1:18081/v1",
                command=["python3", "-m", "mlx_lm", "server"],
                started_at="2026-01-01T00:00:00Z",
                python_executable=cfg_obj.server.python_executable,
            )
        ],
    )
    rc, out, _ = _run(monkeypatch, capsys, ["config", "opencode"], config_path=cfg)
    assert rc == 0
    doc = json.loads(out)
    assert "mlx-manager:mlx-local:18081" in doc["provider"]


def test_config_opencode_reset_clears_managed_providers(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    target = tmp_path / "opencode.json"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    target.write_text(
        json.dumps(
            {
                "provider": {
                    "mlx-manager:mlx-local:8080": {"npm": "remove"},
                    "anthropic": {"npm": "keep"},
                }
            }
        )
    )
    rc, out, err = _run(
        monkeypatch,
        capsys,
        ["config", "opencode", "--reset", "--target", str(target)],
        config_path=cfg,
    )
    assert rc == 0
    assert err == ""
    assert "1 mlx-manager provider(s) removed" in out
    assert json.loads(target.read_text())["provider"] == {"anthropic": {"npm": "keep"}}


def test_stop_when_nothing_running_exits_4(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    cfg.write_text(
        '[server]\nlog_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'.format(tmp_path)
    )
    rc, _, err = _run(monkeypatch, capsys, ["stop"], config_path=cfg)
    assert rc == 4
    assert "no managed server" in err
```

### tests/test_cli_load.py

- size: 5.0 KB
- language: python

```python
from __future__ import annotations

from pathlib import Path

from mlx_manager import cli


def _write_cfg(path: Path, tmp_path: Path, models_root: Path | None) -> None:
    directories = "[]" if models_root is None else f'["{models_root}"]'
    path.write_text(
        '[models]\ndirectories = {dirs}\n\n[server]\nport = 18080\n'
        'log_file = "{t}/mlx.log"\npid_file = "{t}/mlx.pid"\n'
        'state_file = "{t}/state.json"\nlock_file = "{t}/mlx.lock"\n'.format(
            dirs=directories, t=tmp_path
        )
    )


def _fake_start(captured):
    def fake_start(
        cfg_obj,
        model,
        *,
        host,
        port,
        extra_arg_pairs,
        replace,
        on_warning,
        on_verbose,
    ):
        captured.update(
            model_id=model.id,
            host=host,
            port=port,
            extra_arg_pairs=extra_arg_pairs,
            replace=replace,
        )
        return cli.srv.State(
            pid=123,
            model_alias=model.id,
            model_path=str(model.path),
            host=host,
            port=port,
            base_url=f"http://{host}:{port}/v1",
            command=["python3", "-m", "mlx_lm", "server"],
            started_at="2026-01-01T00:00:00Z",
            python_executable=cfg_obj.server.python_executable,
        )

    return fake_start


def _inputs(values):
    items = iter(values)

    def fake_input(prompt):
        return next(items)

    return fake_input


def test_load_guides_model_host_port_and_replace(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    monkeypatch.setattr(
        "builtins.input",
        _inputs(["qwen3-8b-4bit", "all", "1237", "y"]),
    )
    rc = cli.main(["--config", str(cfg), "load"])
    out, err = capsys.readouterr()

    assert rc == 0
    assert captured["model_id"] == "qwen3-8b-4bit"
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 1237
    assert captured["replace"] is True
    # --prompt-cache-bytes is auto-injected when not already set.
    assert len(captured["extra_arg_pairs"]) == 1
    assert captured["extra_arg_pairs"][0].startswith("--prompt-cache-bytes=")
    assert "Discovered models:" in out
    assert "started mlx_lm server" in out
    assert "binding on 0.0.0.0" in err


def test_start_choose_uses_flags_and_prompts_for_model_only(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    monkeypatch.setattr("builtins.input", _inputs(["qwen3-8b-4bit"]))
    rc = cli.main([
        "--config",
        str(cfg),
        "start",
        "--choose",
        "--host",
        "0.0.0.0",
        "--bind-all",
        "--port",
        "1237",
        "--replace",
    ])
    out, err = capsys.readouterr()

    assert rc == 0
    assert captured["model_id"] == "qwen3-8b-4bit"
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 1237
    assert captured["replace"] is True
    assert "Discovered models:" in out
    assert "binding on 0.0.0.0" in err


def test_start_rejects_wildcard_host_without_bind_all(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)

    def fake_start(*args, **kwargs):
        raise AssertionError("start should reject wildcard host before server start")

    monkeypatch.setattr(cli.srv, "start", fake_start)
    rc = cli.main([
        "--config",
        str(cfg),
        "start",
        "--model",
        "qwen3-8b-4bit",
        "--host",
        "0.0.0.0",
    ])
    out, err = capsys.readouterr()

    assert rc == 2
    assert out == ""
    assert "requires --bind-all" in err


def test_start_accepts_localhost_without_bind_all(
    tmp_path, monkeypatch, capsys, fake_models_root
):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, fake_models_root)
    captured = {}

    monkeypatch.setattr(cli.srv, "start", _fake_start(captured))
    rc = cli.main([
        "--config",
        str(cfg),
        "start",
        "--model",
        "qwen3-8b-4bit",
        "--host",
        "127.0.0.1",
    ])
    out, err = capsys.readouterr()

    assert rc == 0
    assert captured["host"] == "127.0.0.1"
    assert "started mlx_lm server" in out
    assert "binding on 0.0.0.0" not in err


def test_load_without_discovered_models_does_not_start(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / "cfg.toml"
    _write_cfg(cfg, tmp_path, None)

    def fake_start(*args, **kwargs):
        raise AssertionError("load should not start without a selected model")

    monkeypatch.setattr(cli.srv, "start", fake_start)
    rc = cli.main(["--config", str(cfg), "load"])
    out, err = capsys.readouterr()

    assert rc == 3
    assert out == ""
    assert "no models discovered" in err
```

### tests/test_config.py

- size: 2.4 KB
- language: python

```python
from __future__ import annotations

import pytest

from mlx_manager.config import ConfigError, load, write_default


def test_first_run_writes_defaults(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg = load(cfg_path)
    assert cfg_path.exists()
    assert cfg.server.host == "127.0.0.1"
    assert cfg.server.port == 8080
    assert "~/.models/mlx" in cfg.models.directories
    assert cfg.providers.api_key == "mlx-local"


def test_load_preserves_user_values(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        """
[server]
host = "0.0.0.0"
port = 9000

[providers]
api_key = "secret"
"""
    )
    cfg = load(cfg_path)
    assert cfg.server.host == "0.0.0.0"
    assert cfg.server.port == 9000
    # Defaults still fill in.
    assert cfg.server.startup_timeout_seconds == 120
    assert cfg.providers.api_key == "secret"


def test_base_url_derives_from_host_port(tmp_path):
    cfg = load(tmp_path / "config.toml")
    assert cfg.base_url == "http://127.0.0.1:8080/v1"


def test_unknown_top_level_table_rejected(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text('[wat]\nfoo = 1\n')
    with pytest.raises(ConfigError, match=r"unknown top-level table: \[wat\]"):
        load(cfg_path)


def test_unknown_key_rejected(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text('[server]\nhost = "127.0.0.1"\nfunky = 1\n')
    with pytest.raises(ConfigError, match=r"server\]\.funky"):
        load(cfg_path)


@pytest.mark.parametrize("bad_port", [80, 99, 1023, 65536, 100000])
def test_invalid_port_rejected(tmp_path, bad_port):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(f'[server]\nport = {bad_port}\n')
    with pytest.raises(ConfigError, match=r"port"):
        load(cfg_path)


def test_patch_tool_calls_defaults_true(tmp_path):
    cfg = load(tmp_path / "config.toml")
    assert cfg.server.patch_tool_calls is True


def test_patch_tool_calls_user_override(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("[server]\npatch_tool_calls = false\n")
    assert load(cfg_path).server.patch_tool_calls is False


def test_patch_tool_calls_must_be_bool(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text('[server]\npatch_tool_calls = "yes"\n')
    with pytest.raises(ConfigError, match=r"patch_tool_calls must be a boolean"):
        load(cfg_path)
```

### tests/test_context.py

- size: 4.0 KB
- language: python

```python
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mlx_manager.context import (
    model_memory_plan,
    model_weight_bytes,
    safe_context_tokens,
    system_ram_bytes,
)


# ---------------------------------------------------------------------------
# safe_context_tokens
# ---------------------------------------------------------------------------

_QWEN3_4B = {
    "num_hidden_layers": 36,
    "num_attention_heads": 16,
    "num_key_value_heads": 8,
    "hidden_size": 2048,
    "max_position_embeddings": 32768,
}


def test_safe_context_respects_arch_max():
    # Give it unlimited RAM — result must not exceed max_position_embeddings.
    tokens = safe_context_tokens(256 * 1024**3, 0, _QWEN3_4B)
    assert tokens == _QWEN3_4B["max_position_embeddings"]


def test_safe_context_constrained_by_ram():
    # 16 GB total, 4 GB model → headroom=8 GB, usable=4 GB → RAM-constrained.
    tokens = safe_context_tokens(16 * 1024**3, 4 * 1024**3, _QWEN3_4B)
    assert 0 < tokens < _QWEN3_4B["max_position_embeddings"]


def test_safe_context_returns_zero_when_no_headroom():
    tokens = safe_context_tokens(3 * 1024**3, 0, _QWEN3_4B)
    assert tokens == 0


def test_safe_context_uses_kv_heads_over_attention_heads():
    cfg_with_gqa = {**_QWEN3_4B, "num_key_value_heads": 2}
    cfg_mha = {k: v for k, v in _QWEN3_4B.items() if k != "num_key_value_heads"}

    # 16 GB total, 4 GB model → headroom=8 GB, usable=4 GB; MHA is RAM-constrained
    # while GQA still hits arch_max, proving the KV-head count drives the calculation.
    tokens_gqa = safe_context_tokens(16 * 1024**3, 4 * 1024**3, cfg_with_gqa)
    tokens_mha = safe_context_tokens(16 * 1024**3, 4 * 1024**3, cfg_mha)
    assert tokens_gqa > tokens_mha


def test_safe_context_falls_back_to_hidden_size_for_head_dim():
    cfg = {
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "hidden_size": 4096,
        "max_position_embeddings": 8192,
    }
    tokens = safe_context_tokens(32 * 1024**3, 3 * 1024**3, cfg)
    assert tokens > 0


# ---------------------------------------------------------------------------
# model_weight_bytes
# ---------------------------------------------------------------------------

def test_model_weight_bytes_sums_safetensors(tmp_path):
    (tmp_path / "model.safetensors").write_bytes(b"x" * 1000)
    (tmp_path / "model-00001-of-00002.safetensors").write_bytes(b"x" * 2000)
    (tmp_path / "tokenizer.json").write_bytes(b"x" * 500)
    assert model_weight_bytes(tmp_path) == 3000


def test_model_weight_bytes_handles_missing_dir():
    assert model_weight_bytes(Path("/nonexistent/path")) == 0


# ---------------------------------------------------------------------------
# system_ram_bytes
# ---------------------------------------------------------------------------

def test_system_ram_bytes_returns_int():
    ram = system_ram_bytes()
    assert isinstance(ram, int)
    assert ram >= 0


# ---------------------------------------------------------------------------
# model_memory_plan
# ---------------------------------------------------------------------------

def test_model_memory_plan_returns_plan(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps(_QWEN3_4B))
    (tmp_path / "model.safetensors").write_bytes(b"x" * (2 * 1024**3 // 100))

    with patch("mlx_manager.context.system_ram_bytes", return_value=16 * 1024**3):
        plan = model_memory_plan(tmp_path)

    assert plan is not None
    tokens, cache_bytes = plan
    assert tokens > 0
    assert cache_bytes > 0
    assert cache_bytes == pytest.approx(tokens * 2 * 36 * 8 * 128 * 2, rel=0.01)


def test_model_memory_plan_none_on_missing_config(tmp_path):
    assert model_memory_plan(tmp_path) is None


def test_model_memory_plan_none_when_ram_unavailable(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps(_QWEN3_4B))
    with patch("mlx_manager.context.system_ram_bytes", return_value=0):
        assert model_memory_plan(tmp_path) is None
```

### tests/test_doctor_fix.py

- size: 4.0 KB
- language: python

```python
from __future__ import annotations

import sys

from mlx_manager import cli


def test_pipx_app_name_detects_venv(monkeypatch):
    monkeypatch.setattr(sys, "prefix", "pipx/venvs/mlx-manager")
    assert cli._pipx_app_name() == "mlx-manager"


def test_pipx_app_name_none_for_regular_venv(monkeypatch):
    monkeypatch.setattr(sys, "prefix", "/Library/Frameworks/Python.framework/Versions/3.12")
    assert cli._pipx_app_name() is None


def test_install_cmd_uses_pipx_inject_when_isolated(monkeypatch):
    monkeypatch.setattr(cli, "_pipx_app_name", lambda: "mlx-manager")
    monkeypatch.setattr(cli.shutil, "which", lambda _name: "/opt/homebrew/bin/pipx")
    assert cli._mlx_lm_install_cmd() == ["pipx", "inject", "mlx-manager", "mlx-lm"]


def test_install_cmd_falls_back_to_pip(monkeypatch):
    monkeypatch.setattr(cli, "_pipx_app_name", lambda: None)
    assert cli._mlx_lm_install_cmd() == [sys.executable, "-m", "pip", "install", "mlx-lm"]


def test_install_cmd_pip_when_pipx_missing(monkeypatch):
    monkeypatch.setattr(cli, "_pipx_app_name", lambda: "mlx-manager")
    monkeypatch.setattr(cli.shutil, "which", lambda _name: None)
    assert cli._mlx_lm_install_cmd() == [sys.executable, "-m", "pip", "install", "mlx-lm"]


def test_doctor_fix_creates_missing_model_dirs(monkeypatch, tmp_path, capsys, cfg_factory):
    missing = tmp_path / "new-models"
    cfg = cfg_factory(directories=[str(missing)])
    # Pretend mlx_lm is already importable so the fixer only handles dirs.
    monkeypatch.setattr(cli, "_mlx_lm_importable_here", lambda: True)
    cli._doctor_fix(cfg)
    assert missing.is_dir()


def test_doctor_fix_installs_when_bot_runtime_missing(monkeypatch, capsys, cfg_factory):
    cfg = cfg_factory(directories=[])
    states = iter([False, True])  # missing before, present after install
    monkeypatch.setattr(cli, "_mlx_lm_importable_here", lambda: next(states))
    ran = []
    monkeypatch.setattr(cli, "_mlx_lm_install_cmd", lambda: ["echo", "install"])
    monkeypatch.setattr(cli, "_run_fix_cmd", lambda cmd: ran.append(cmd) or 0)
    # Server python already has mlx_lm, so no repoint.
    monkeypatch.setattr(cli.srv, "mlx_lm_installed", lambda _py: True)
    cli._doctor_fix(cfg)
    assert ran == [["echo", "install"]]
    err = capsys.readouterr().err
    assert "ok" in err


def test_doctor_fix_repoints_server_python_when_default_lacks_mlx_lm(
    monkeypatch, tmp_path, capsys
):
    from mlx_manager.config import load

    cfg_path = tmp_path / "cfg.toml"
    cfg_path.write_text(
        '[server]\npython_executable = "python3"\n'
        'log_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'
        "[models]\ndirectories = []\n".format(tmp_path)
    )
    cfg = load(cfg_path)
    monkeypatch.setattr(cli, "_mlx_lm_importable_here", lambda: True)
    monkeypatch.setattr(cli.srv, "mlx_lm_installed", lambda _py: False)
    monkeypatch.setattr(cli.sys, "executable", "/venv/bin/python")
    cli._doctor_fix(cfg)
    # Config file updated to the working interpreter.
    assert load(cfg_path).server.python_executable == "/venv/bin/python"
    assert "set server.python_executable" in capsys.readouterr().err


def test_doctor_fix_advises_when_custom_server_python_lacks_mlx_lm(
    monkeypatch, tmp_path, capsys
):
    from mlx_manager.config import load

    cfg_path = tmp_path / "cfg.toml"
    cfg_path.write_text(
        '[server]\npython_executable = "/custom/python"\n'
        'log_file = "{0}/mlx.log"\npid_file = "{0}/mlx.pid"\n'
        'state_file = "{0}/state.json"\nlock_file = "{0}/mlx.lock"\n'
        "[models]\ndirectories = []\n".format(tmp_path)
    )
    cfg = load(cfg_path)
    monkeypatch.setattr(cli, "_mlx_lm_importable_here", lambda: True)
    monkeypatch.setattr(cli.srv, "mlx_lm_installed", lambda _py: False)
    cli._doctor_fix(cfg)
    # Custom value is NOT overwritten; user is advised instead.
    assert load(cfg_path).server.python_executable == "/custom/python"
    assert "cannot import mlx_lm" in capsys.readouterr().err
```

### tests/test_health.py

- size: 2.8 KB
- language: python

```python
from __future__ import annotations

from mlx_manager import server as srv

_DEEPSEEK_LOG = """\
2026-05-28 10:56:11,064 - INFO - Starting httpd at 0.0.0.0 on port 1236...
Exception in thread Thread-1 (_generate):
Traceback (most recent call last):
ModuleNotFoundError: No module named 'mlx_lm.models.deepseek_v4'
ValueError: Model type deepseek_v4 not supported.
127.0.0.1 - - [28/May/2026 10:56:11] "GET /v1/models HTTP/1.1" 200 -
"""

_CLEAN_LOG = """\
2026-05-28 09:55:05,000 - INFO - Starting httpd at 0.0.0.0 on port 1235...
127.0.0.1 - - [28/May/2026 09:55:30] "POST /v1/chat/completions HTTP/1.1" 200 -
"""

_METAL_OOM_LOG = """\
2026-06-03 23:36:01,909 - INFO - Starting httpd at 0.0.0.0 on port 1236...
libc++abi: terminating due to uncaught exception of type std::runtime_error: [METAL] Command buffer execution failed: Insufficient Memory (00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)
"""


def test_log_health_detects_unsupported_model_type(tmp_path):
    log = tmp_path / "mlx.1236.log"
    log.write_text(_DEEPSEEK_LOG)
    status, detail = srv.log_health(log)
    assert status == "error"
    assert "deepseek_v4" in detail


def test_log_health_detects_metal_oom(tmp_path):
    log = tmp_path / "mlx.1236.log"
    log.write_text(_METAL_OOM_LOG)
    status, detail = srv.log_health(log)
    assert status == "error"
    assert "Metal" in detail
    assert "reduce prompt cache" in detail


def test_log_health_ok_for_clean_log(tmp_path):
    log = tmp_path / "mlx.1235.log"
    log.write_text(_CLEAN_LOG)
    assert srv.log_health(log) == ("ok", "")


def test_log_health_missing_file_is_ok(tmp_path):
    assert srv.log_health(tmp_path / "nope.log") == ("ok", "")


def test_log_health_ignores_error_before_latest_restart(tmp_path):
    """An error before the most recent 'Starting httpd' marker is from a prior
    run of the same appended log and must not flag the current session."""
    log = tmp_path / "mlx.log"
    log.write_text(_DEEPSEEK_LOG + _CLEAN_LOG)
    assert srv.log_health(log) == ("ok", "")


def test_status_reports_log_health_for_stale_state(tmp_path, cfg_factory):
    cfg = cfg_factory()
    srv.write_state(
        srv.port_state_path(cfg, cfg.server.port),
        srv.State(
            pid=999999,
            model_alias="oom-model",
            model_path="/models/oom-model",
            host="127.0.0.1",
            port=cfg.server.port,
            base_url=f"http://127.0.0.1:{cfg.server.port}/v1",
            command=[],
            started_at="2026-01-01T00:00:00Z",
            python_executable="python3",
        ),
    )
    srv.port_log_path(cfg, cfg.server.port).write_text(_METAL_OOM_LOG)

    status = srv.status_dict(cfg, cfg.server.port)

    assert status["running"] is False
    assert status["stale"] is True
    assert status["health"] == "error"
    assert "Metal" in status["health_detail"]
```

### tests/test_models.py

- size: 3.8 KB
- language: python

```python
from __future__ import annotations

import pytest

from mlx_manager.config import ModelsCfg
from mlx_manager.models import discover, resolve


def test_discover_plain_directory(fake_models_root):
    cfg = ModelsCfg(directories=[str(fake_models_root)], default_model="", aliases={})
    found = discover(cfg)
    ids = {m.id for m in found}
    assert "qwen3-8b-4bit" in ids
    assert "llama-3-8b-4bit" in ids  # sharded
    assert "no-weights" not in ids
    for m in found:
        assert m.source == "directory"


def test_discover_hf_cache_keeps_org_prefix(fake_hf_cache):
    cfg = ModelsCfg(directories=[str(fake_hf_cache)], default_model="", aliases={})
    found = discover(cfg)
    ids = {m.id for m in found}
    # Full HF-style id is preserved so the API can serve it under the same name.
    assert "mlx-community/Llama-3.2-3B-Instruct-4bit" in ids
    # Repo with no usable snapshot is skipped.
    assert all("no-weights" not in i for i in ids)
    # Resolved path is the snapshot dir, not the bare hash.
    m = next(m for m in found if m.id == "mlx-community/Llama-3.2-3B-Instruct-4bit")
    assert m.source == "hf_cache"
    assert m.path.name == "abc123"
    assert m.path.parent.name == "snapshots"


def test_alias_takes_precedence(fake_models_root):
    cfg = ModelsCfg(
        directories=[str(fake_models_root)],
        default_model="",
        aliases={"qwen3-8b-4bit": str(fake_models_root / "qwen3-8b-4bit")},
    )
    found = discover(cfg)
    alias_entry = next(m for m in found if m.id == "qwen3-8b-4bit")
    assert alias_entry.source == "alias"


def test_resolve_alias_then_id_then_path(fake_models_root, tmp_path):
    alias_target = fake_models_root / "qwen3-8b-4bit"
    cfg = ModelsCfg(
        directories=[str(fake_models_root)],
        default_model="",
        aliases={"speedy": str(alias_target)},
    )
    # By alias
    assert resolve(cfg, "speedy").path == alias_target.resolve()
    # By discovered id
    assert resolve(cfg, "llama-3-8b-4bit").id == "llama-3-8b-4bit"
    # By absolute path
    extra = fake_models_root / "other-model"
    extra.mkdir()
    (extra / "config.json").write_text("{}")
    (extra / "model.safetensors").write_bytes(b"")
    assert resolve(cfg, str(extra)).path == extra.resolve()


def test_discover_lmstudio_nested_layout(fake_lmstudio_root):
    """LM Studio uses ``<root>/<publisher>/<model-name>/``.

    The id is the model directory's basename (no publisher prefix) so the
    spawned ``mlx_lm.server --model <basename>`` exposes that exact id on the
    wire — matching what users naturally type in OpenCode-style configs.
    """
    cfg = ModelsCfg(
        directories=[str(fake_lmstudio_root)], default_model="", aliases={}
    )
    found = discover(cfg)
    ids = {m.id for m in found}
    assert "gemma-test-MLX-4bit" in ids
    assert "exotic-model-3bit" in ids
    for m in found:
        assert m.source == "directory"
        # Display id is always the deepest path segment.
        assert m.id == m.path.name


def test_discover_mixed_roots_dedupes_by_id(
    tmp_path, fake_models_root, fake_lmstudio_root, fake_hf_cache
):
    """All three layouts coexist; ids are unique in the output."""
    cfg = ModelsCfg(
        directories=[
            str(fake_models_root),
            str(fake_lmstudio_root),
            str(fake_hf_cache),
        ],
        default_model="",
        aliases={},
    )
    found = discover(cfg)
    ids = [m.id for m in found]
    assert len(ids) == len(set(ids))
    # At least one entry from each layout is present.
    sources = {m.source for m in found}
    assert {"directory", "hf_cache"} <= sources


def test_resolve_unknown_raises(tmp_path):
    cfg = ModelsCfg(directories=[str(tmp_path)], default_model="", aliases={})
    with pytest.raises(LookupError):
        resolve(cfg, "ghost-model")
```

### tests/test_providers.py

- size: 8.4 KB
- language: python

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mlx_manager.providers import (
    ApplyError,
    MANAGED_PROVIDER_PREFIX,
    ProviderContext,
    apply_opencode,
    claude_code_snippet,
    managed_provider_name,
    litellm_yaml,
    opencode_snippet,
    reset_opencode,
)


def _ctx() -> ProviderContext:
    return ProviderContext(
        base_url="http://127.0.0.1:8080/v1",
        api_key="mlx-local",
        provider_name="mlx-manager:mlx-local:8080",
        model_id="qwen3-8b-4bit",
    )


def test_opencode_merge_snippet_exact_shape():
    out = opencode_snippet(_ctx(), format="merge")
    doc = json.loads(out)
    assert doc == {
        "provider": {
            "mlx-manager:mlx-local:8080": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "MLX Local",
                "options": {
                    "baseURL": "http://127.0.0.1:8080/v1",
                    "apiKey": "mlx-local",
                },
                "models": {"qwen3-8b-4bit": {"name": "qwen3-8b-4bit"}},
            }
        }
    }


def test_opencode_snippet_omits_context_length_when_none():
    out = opencode_snippet(_ctx(), format="merge")
    doc = json.loads(out)
    model_def = doc["provider"]["mlx-manager:mlx-local:8080"]["models"]["qwen3-8b-4bit"]
    assert "contextLength" not in model_def


def test_opencode_snippet_includes_context_length_when_set():
    ctx = ProviderContext(
        base_url="http://127.0.0.1:8080/v1",
        api_key="mlx-local",
        provider_name="mlx-manager:mlx-local:8080",
        model_id="qwen3-8b-4bit",
        context_length=32768,
    )
    out = opencode_snippet(ctx, format="merge")
    doc = json.loads(out)
    model_def = doc["provider"]["mlx-manager:mlx-local:8080"]["models"]["qwen3-8b-4bit"]
    assert model_def["contextLength"] == 32768


def test_managed_provider_name_marks_mlx_manager_entries():
    assert MANAGED_PROVIDER_PREFIX == "mlx-manager:"
    assert managed_provider_name("mlx-local") == "mlx-manager:mlx-local"
    assert managed_provider_name("mlx-manager:mlx-local") == "mlx-manager:mlx-local"


def test_opencode_full_snippet_includes_schema():
    out = opencode_snippet(_ctx(), format="full")
    doc = json.loads(out)
    assert doc["$schema"] == "https://opencode.ai/config.json"
    assert "provider" in doc


def test_litellm_yaml_pins_format():
    out = litellm_yaml(
        ProviderContext(
            base_url="http://127.0.0.1:8080/v1",
            api_key="mlx-local",
            provider_name="mlx-local",
            model_id="qwen3-8b-4bit",
        )
    )
    assert out == (
        "model_list:\n"
        "  - model_name: mlx-local/qwen3-8b-4bit\n"
        "    litellm_params:\n"
        "      model: openai/qwen3-8b-4bit\n"
        "      api_base: http://127.0.0.1:8080/v1\n"
        "      api_key: mlx-local\n"
    )


def test_apply_creates_file_with_schema(tmp_path):
    target = tmp_path / "opencode.json"
    summary = apply_opencode(_ctx(), target)
    assert "added" in summary
    doc = json.loads(target.read_text())
    assert doc["$schema"] == "https://opencode.ai/config.json"
    assert doc["provider"]["mlx-manager:mlx-local:8080"]["options"]["baseURL"] == "http://127.0.0.1:8080/v1"
    assert "qwen3-8b-4bit" in doc["provider"]["mlx-manager:mlx-local:8080"]["models"]


def test_apply_merge_preserves_user_per_model_tuning(tmp_path):
    """Without --overwrite, existing model fields like `limit` must survive."""
    target = tmp_path / "opencode.json"
    target.write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "permission": {"edit": "ask"},
                "provider": {
                    "mlx-manager:mlx-local:8080": {
                        "npm": "old-package",
                        "name": "stale display",
                        "options": {"baseURL": "http://old:1234/v1", "apiKey": "x"},
                        "models": {
                            "qwen3-8b-4bit": {
                                "name": "Hand tuned name",
                                "limit": {"context": 250000, "output": 8192},
                            }
                        },
                    }
                },
            },
            indent=2,
        )
    )
    summary = apply_opencode(_ctx(), target)
    assert "merged" in summary
    doc = json.loads(target.read_text())
    # Outer keys untouched.
    assert doc["permission"] == {"edit": "ask"}
    prov = doc["provider"]["mlx-manager:mlx-local:8080"]
    # mlx-manager-owned fields are refreshed.
    assert prov["npm"] == "@ai-sdk/openai-compatible"
    assert prov["options"]["baseURL"] == "http://127.0.0.1:8080/v1"
    # User-tuned per-model fields survive.
    assert prov["models"]["qwen3-8b-4bit"]["name"] == "Hand tuned name"
    assert prov["models"]["qwen3-8b-4bit"]["limit"] == {"context": 250000, "output": 8192}


def test_apply_overwrite_replaces_provider_block(tmp_path):
    target = tmp_path / "opencode.json"
    target.write_text(
        json.dumps(
            {
                "provider": {
                    "mlx-manager:mlx-local:8080": {
                        "npm": "old",
                        "name": "stale",
                        "options": {"baseURL": "http://old", "apiKey": "x"},
                        "models": {"old-model": {"name": "old", "limit": {"output": 1}}},
                    },
                    "other": {"npm": "keep me"},
                }
            }
        )
    )
    summary = apply_opencode(_ctx(), target, overwrite=True)
    assert "overwritten" in summary
    doc = json.loads(target.read_text())
    # Other providers are untouched.
    assert doc["provider"]["other"] == {"npm": "keep me"}
    # Our provider is reset — old-model and its limit are gone.
    assert "old-model" not in doc["provider"]["mlx-manager:mlx-local:8080"]["models"]
    assert "qwen3-8b-4bit" in doc["provider"]["mlx-manager:mlx-local:8080"]["models"]


def test_apply_writes_backup(tmp_path):
    target = tmp_path / "opencode.json"
    original = {"existing": True, "provider": {}}
    target.write_text(json.dumps(original))
    apply_opencode(_ctx(), target)
    backup = target.with_name(target.name + ".bak")
    assert backup.exists()
    assert json.loads(backup.read_text()) == original


def test_reset_removes_only_mlx_manager_providers(tmp_path):
    target = tmp_path / "opencode.json"
    target.write_text(
        json.dumps(
            {
                "provider": {
                    "mlx-manager:mlx-local:8080": {"npm": "remove"},
                    "mlx-manager:mlx-local@studio:8081": {"npm": "remove too"},
                    "mlx-local": {"npm": "keep"},
                    "anthropic": {"npm": "keep"},
                },
                "permission": {"edit": "ask"},
            }
        )
    )
    summary = reset_opencode(target)
    assert "2 mlx-manager provider(s) removed" in summary
    doc = json.loads(target.read_text())
    assert doc["provider"] == {
        "mlx-local": {"npm": "keep"},
        "anthropic": {"npm": "keep"},
    }
    assert doc["permission"] == {"edit": "ask"}


def test_reset_is_idempotent_and_writes_backup(tmp_path):
    target = tmp_path / "opencode.json"
    original = {"provider": {"anthropic": {"npm": "keep"}}}
    target.write_text(json.dumps(original))
    summary = reset_opencode(target)
    assert "0 mlx-manager provider(s) removed" in summary
    assert json.loads(target.read_text()) == original
    assert json.loads(target.with_name(target.name + ".bak").read_text()) == original


def test_apply_rejects_non_object_top_level(tmp_path):
    target = tmp_path / "opencode.json"
    target.write_text(json.dumps(["not", "an", "object"]))
    with pytest.raises(ApplyError, match="top-level"):
        apply_opencode(_ctx(), target)


def test_apply_rejects_invalid_json(tmp_path):
    target = tmp_path / "opencode.json"
    target.write_text("{ not json")
    with pytest.raises(ApplyError, match="not valid JSON"):
        apply_opencode(_ctx(), target)


def test_claude_code_snippet_marks_experimental_and_recommends_litellm():
    out = claude_code_snippet(_ctx())
    # Experimental label must be present in the env-var section.
    assert "experimental" in out.lower()
    # No ANTHROPIC_BASE_URL leaked (unverified — explicitly forbidden by brief).
    assert "ANTHROPIC_BASE_URL" not in out
    # LiteLLM block must be there and recommended.
    assert "model_list:" in out
    assert "openai/qwen3-8b-4bit" in out
```

### tests/test_server_safety.py

- size: 11.4 KB
- language: python

```python
from __future__ import annotations

import multiprocessing as mp
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from mlx_manager import server as srv
from mlx_manager.config import ModelsCfg
from mlx_manager.models import Model, discover
from mlx_manager.paths import expand


def _spawn_idle(tag: str = "mlx-test-idle") -> subprocess.Popen:
    """Launch a long-running python process whose argv contains *tag*.

    The script just sleeps forever and reacts to SIGTERM normally.
    """
    code = f"import sys, time, signal\nsys.argv.append({tag!r})\ntime.sleep(3600)\n"
    return subprocess.Popen(
        [sys.executable, "-c", code, tag],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_lock_serializes_two_callers(tmp_path):
    """Two acquirers cannot hold the same lock at once; the second times out."""
    lock_path = tmp_path / "lock"

    def hold_lock_then_signal(release_evt, holding_evt):
        with srv.acquire_lock(lock_path, timeout=5):
            holding_evt.set()
            release_evt.wait(timeout=10)

    ctx = mp.get_context("fork")
    release = ctx.Event()
    holding = ctx.Event()
    holder = ctx.Process(target=hold_lock_then_signal, args=(release, holding))
    holder.start()
    try:
        assert holding.wait(timeout=5)
        t0 = time.monotonic()
        with pytest.raises(srv.ServerError, match=r"could not acquire lock"):
            with srv.acquire_lock(lock_path, timeout=0.5):
                pass
        assert time.monotonic() - t0 >= 0.4
    finally:
        release.set()
        holder.join(timeout=5)


def test_pid_alive_and_command_match(tmp_path):
    p = _spawn_idle("mlx_lm.server-test-tag")
    try:
        assert srv.pid_alive(p.pid)
        cmd = srv.pid_command(p.pid)
        assert "mlx_lm.server-test-tag" in cmd
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=5)
    assert not srv.pid_alive(p.pid)


def test_is_managed_process_requires_argv_match(tmp_path):
    p = _spawn_idle("mlx_lm.server")
    try:
        # State whose port appears in the synthetic argv → managed.
        good_state = srv.State(
            pid=p.pid,
            model_alias="m",
            model_path="/x/y/m",
            host="127.0.0.1",
            port=18080,  # must appear in argv — it doesn't, by design.
            base_url="http://127.0.0.1:18080/v1",
            command=[],
            started_at="2026-01-01T00:00:00Z",
            python_executable=sys.executable,
        )
        assert srv.is_managed_process(p.pid, good_state) is False  # port absent
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=5)


def test_reused_pid_with_wrong_argv_is_not_managed(tmp_path):
    """A live PID whose argv doesn't contain mlx_lm must NOT be considered managed."""
    p = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert srv.pid_alive(p.pid)
        assert srv.is_managed_process(p.pid, None) is False
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=5)


def test_stop_refuses_when_state_pid_argv_unrelated(tmp_path, cfg_factory):
    """Reused-PID safety: stop must refuse to kill an unrelated process."""
    cfg = cfg_factory()
    state_path = srv.port_state_path(cfg, cfg.server.port)

    p = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        # State claims the unrelated PID is "ours". stop() must refuse.
        srv.write_state(
            state_path,
            srv.State(
                pid=p.pid,
                model_alias="ghost",
                model_path="/nope",
                host="127.0.0.1",
                port=cfg.server.port,
                base_url=f"http://127.0.0.1:{cfg.server.port}/v1",
                command=[sys.executable, "-c", "..."],
                started_at="2026-01-01T00:00:00Z",
                python_executable=sys.executable,
            ),
        )
        with pytest.raises(srv.ServerError) as ei:
            srv.stop(cfg, port=cfg.server.port)
        assert ei.value.exit_code == 1
        # And the unrelated process is still alive.
        assert srv.pid_alive(p.pid)
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=5)


def test_stop_accepts_shim_argv(tmp_path, cfg_factory, monkeypatch):
    cfg = cfg_factory()
    state_path = srv.port_state_path(cfg, cfg.server.port)
    pid = 424242
    alive = True

    srv.write_state(
        state_path,
        srv.State(
            pid=pid,
            model_alias="ghost",
            model_path="/models/ghost",
            host="127.0.0.1",
            port=cfg.server.port,
            base_url=f"http://127.0.0.1:{cfg.server.port}/v1",
            command=[
                sys.executable,
                str(srv._SERVER_SHIM),
                "server",
                "--model",
                "ghost",
                "--port",
                str(cfg.server.port),
            ],
            started_at="2026-01-01T00:00:00Z",
            python_executable=sys.executable,
        ),
    )

    def fake_pid_alive(pid_arg):
        assert pid_arg == pid
        return alive

    def fake_kill(pid_arg, sig):
        nonlocal alive
        assert pid_arg == pid
        assert sig == signal.SIGTERM
        alive = False

    monkeypatch.setattr(srv, "pid_alive", fake_pid_alive)
    monkeypatch.setattr(
        srv,
        "pid_command",
        lambda pid_arg: (
            f"{sys.executable} {srv._SERVER_SHIM} server --model ghost "
            f"--host 127.0.0.1 --port {cfg.server.port}"
        ),
    )
    monkeypatch.setattr(srv.os, "kill", fake_kill)

    state = srv.stop(cfg, port=cfg.server.port)

    assert state.pid == pid
    assert not state_path.exists()


def test_stop_reports_not_running_for_dead_pid(tmp_path, cfg_factory):
    cfg = cfg_factory()
    state_path = srv.port_state_path(cfg, cfg.server.port)
    srv.write_state(
        state_path,
        srv.State(
            pid=999999,  # unlikely to exist
            model_alias="x",
            model_path="/x",
            host="127.0.0.1",
            port=cfg.server.port,
            base_url=f"http://127.0.0.1:{cfg.server.port}/v1",
            command=[],
            started_at="2026-01-01T00:00:00Z",
            python_executable=sys.executable,
        ),
    )
    with pytest.raises(srv.ServerError) as ei:
        srv.stop(cfg, port=cfg.server.port)
    assert ei.value.exit_code == 4
    # State file cleaned up.
    assert not state_path.exists()


def test_state_write_is_atomic(tmp_path):
    """Atomic write: no .tmp residue, file contains valid JSON."""
    state_path = tmp_path / "state.json"
    s = srv.State(
        pid=1,
        model_alias="m",
        model_path="/m",
        host="127.0.0.1",
        port=8080,
        base_url="http://127.0.0.1:8080/v1",
        command=["py"],
        started_at="2026-01-01T00:00:00Z",
        python_executable="python3",
    )
    srv.write_state(state_path, s)
    assert state_path.is_file()
    assert not (state_path.parent / "state.json.tmp").exists()
    # Roundtrip parses.
    s2 = srv.read_state(state_path)
    assert s2 is not None
    assert s2.pid == 1


def test_serving_invocation_filesystem_uses_basename_and_parent_cwd(
    fake_lmstudio_root,
):
    """Filesystem models spawn with ``cwd=<parent>`` and ``--model <basename>``
    so the API exposes the same id ``mlx-manager list`` shows."""
    cfg = ModelsCfg(
        directories=[str(fake_lmstudio_root)], default_model="", aliases={}
    )
    m = next(x for x in discover(cfg) if x.id == "gemma-test-MLX-4bit")
    serving_id, cwd = srv.serving_invocation(m)
    assert serving_id == "gemma-test-MLX-4bit"
    assert cwd == m.path.parent
    # And the path is *resolvable* from that cwd as the bare id.
    assert (cwd / serving_id).is_dir()


def test_serving_invocation_hf_cache_uses_org_name(fake_hf_cache):
    """HF-cache models are passed as ``<org>/<name>``; mlx_lm's HF resolver
    finds them locally without needing a specific cwd."""
    cfg = ModelsCfg(directories=[str(fake_hf_cache)], default_model="", aliases={})
    m = next(
        x for x in discover(cfg) if x.id == "mlx-community/Llama-3.2-3B-Instruct-4bit"
    )
    serving_id, cwd = srv.serving_invocation(m)
    assert serving_id == "mlx-community/Llama-3.2-3B-Instruct-4bit"
    assert cwd is None


def test_build_command_returns_cwd_and_serving_id(cfg_factory, fake_lmstudio_root):
    cfg = cfg_factory()
    mcfg = ModelsCfg(
        directories=[str(fake_lmstudio_root)], default_model="", aliases={}
    )
    m = next(x for x in discover(mcfg) if x.id == "gemma-test-MLX-4bit")
    cmd, cwd, _warnings = srv.build_command(
        cfg, m, host="127.0.0.1", port=12345, extra_arg_pairs=[], supported_flags=set()
    )
    # `--model <serving_id>` is present and the absolute path is NOT.
    assert "--model" in cmd
    model_idx = cmd.index("--model")
    assert cmd[model_idx + 1] == "gemma-test-MLX-4bit"
    assert str(m.path) not in cmd
    assert cwd == m.path.parent


def test_build_command_routes_through_shim_when_patch_enabled(
    cfg_factory, fake_lmstudio_root
):
    cfg = cfg_factory(patch_tool_calls=True)
    mcfg = ModelsCfg(
        directories=[str(fake_lmstudio_root)], default_model="", aliases={}
    )
    m = next(x for x in discover(mcfg) if x.id == "gemma-test-MLX-4bit")
    cmd, _cwd, _warnings = srv.build_command(
        cfg, m, host="127.0.0.1", port=12345, extra_arg_pairs=[], supported_flags=set()
    )
    # Launches the shim (not `-m mlx_lm`) but still passes the `server` subcommand.
    assert str(srv._SERVER_SHIM) in cmd
    assert "-m" not in cmd
    assert cmd[cmd.index(str(srv._SERVER_SHIM)) + 1] == "server"


def test_build_command_uses_mlx_lm_when_patch_disabled(
    cfg_factory, fake_lmstudio_root
):
    cfg = cfg_factory(patch_tool_calls=False)
    mcfg = ModelsCfg(
        directories=[str(fake_lmstudio_root)], default_model="", aliases={}
    )
    m = next(x for x in discover(mcfg) if x.id == "gemma-test-MLX-4bit")
    cmd, _cwd, _warnings = srv.build_command(
        cfg, m, host="127.0.0.1", port=12345, extra_arg_pairs=[], supported_flags=set()
    )
    assert "-m" in cmd and "mlx_lm" in cmd
    assert str(srv._SERVER_SHIM) not in cmd


def test_is_managed_process_recognizes_shim_argv(tmp_path):
    """A process launched via the patch shim (argv has no literal `mlx_lm`) must
    still be recognized as managed."""
    p = _spawn_idle(srv._SERVER_SHIM.name)
    try:
        assert srv.pid_alive(p.pid)
        assert srv.is_managed_process(p.pid, None) is True
    finally:
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=5)


def test_log_rotation_caps_max_files(tmp_path):
    log = tmp_path / "x.log"
    log.write_bytes(b"0" * 4096)
    srv.rotate_log_if_needed(log, max_bytes=1024, max_files=3)
    # After rotation the original is moved to .1 and main is gone.
    assert not log.exists()
    assert (tmp_path / "x.log.1").exists()
    # Trigger again with a fresh oversize main.
    log.write_bytes(b"0" * 4096)
    srv.rotate_log_if_needed(log, max_bytes=1024, max_files=3)
    assert (tmp_path / "x.log.1").exists()
    assert (tmp_path / "x.log.2").exists()
    # Third rotation drops the oldest.
    log.write_bytes(b"0" * 4096)
    srv.rotate_log_if_needed(log, max_bytes=1024, max_files=3)
    assert not (tmp_path / "x.log.4").exists()
```

### tests/test_server_shim.py

- size: 3.0 KB
- language: python

```python
"""Tests for the launch shim that patches mlx_lm.server's tool-call handling.

The patch behavior tests need a real ``mlx_lm`` to patch, so they skip when it
isn't installed (the rest of the suite must run without it).
"""
from __future__ import annotations

import sys

import pytest

from mlx_manager import _server_shim as shim

mlx_server = pytest.importorskip("mlx_lm.server")


@pytest.fixture(autouse=True)
def _patched():
    shim._apply_patch()  # idempotent; mutates mlx_lm.server classes in-process


def _make_handler(*, object_type="chat.completion.chunk", stream=True):
    h = mlx_server.APIHandler.__new__(mlx_server.APIHandler)
    h.request_id = "req-1"
    h.system_fingerprint = "fp"
    h.object_type = object_type
    h.requested_model = "m"
    h.created = 0
    h.stream = stream
    return h


def test_formatter_flags_parse_failure_and_drops_call():
    def raising_parser(text, tools):
        raise ValueError("truncated")

    f = mlx_server.ToolCallFormatter(raising_parser, [], streaming=False)
    assert shim._state.tool_parse_failed is False  # reset on construction
    assert f(["{half-a-tool"]) == []  # dropped, as stock mlx_lm does
    assert shim._state.tool_parse_failed is True  # ...but now flagged


def test_formatter_leaves_flag_clear_on_success():
    def ok_parser(text, tools):
        return {"name": "get_weather", "arguments": {"city": "NYC"}}

    f = mlx_server.ToolCallFormatter(ok_parser, [], streaming=False)
    assert shim._state.tool_parse_failed is False
    out = f(['{"name": "get_weather"}'])
    assert shim._state.tool_parse_failed is False
    assert len(out) == 1 and out[0]["type"] == "function"


def test_generate_response_forces_length_after_parse_failure():
    h = _make_handler()
    shim._state.tool_parse_failed = True
    resp = h.generate_response("hi", "tool_calls")
    assert resp["choices"][0]["finish_reason"] == "length"


def test_generate_response_untouched_when_no_failure():
    h = _make_handler()
    shim._state.tool_parse_failed = False
    resp = h.generate_response("hi", "tool_calls")
    assert resp["choices"][0]["finish_reason"] == "tool_calls"


def test_generate_response_ignores_streaming_delta_packets():
    """Intermediate stream packets carry finish_reason=None and must stay None
    even if a parse failure has been flagged."""
    h = _make_handler()
    shim._state.tool_parse_failed = True
    resp = h.generate_response("hi", None)
    assert resp["choices"][0]["finish_reason"] is None


def test_main_rebuilds_argv_and_dispatches_to_mlx_cli(monkeypatch):
    import mlx_lm.cli as cli

    captured = {}
    monkeypatch.setattr(cli, "main", lambda: captured.setdefault("argv", list(sys.argv)))
    monkeypatch.setattr(shim, "_apply_patch", lambda: None)
    monkeypatch.setattr(shim, "_announce_when_logging_ready", lambda msg: None)

    shim.main(["/abs/_server_shim.py", "server", "--model", "foo", "--port", "9001"])

    # Reconstructs exactly what `python -m mlx_lm server ...` would hand the CLI.
    assert captured["argv"] == ["mlx_lm", "server", "--model", "foo", "--port", "9001"]
```

