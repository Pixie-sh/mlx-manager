# mlxer — Headless MLX Local LLM Server Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![PyPI version](https://badge.fury.io/py/mlxer.svg)](https://pypi.org/project/mlxer/)
[![Python version](https://img.shields.io/pypi/pyversions/mlxer.svg)](https://pypi.org/project/mlxer/)
[![Downloads](https://img.shields.io/pypi/dm/mlxer.svg)](https://pypi.org/project/mlxer/)
[![Test](https://github.com/Pixie-sh/mlxer/actions/workflows/test.yml/badge.svg)](https://github.com/Pixie-sh/mlxer/actions)

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
- Available on [PyPI](https://pypi.org/project/mlxer/).

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
  - [`config warp`](#config-warp)
  - [`config show`](#config-show)
  - [`config edit`](#config-edit)
- [Exit codes](#exit-codes)
- [Safety notes](#safety-notes)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Install

Requires macOS on Apple Silicon, Python >= 3.11, and
[`mlx_lm`](https://pypi.org/project/mlx-lm/) installed in the same interpreter
`mlxer` will use to launch the server (by default `python3`).

### Recommended: pipx or pip

Install the CLI from PyPI:

```bash
pipx install mlxer
```

Or install into the active Python environment:

```bash
python3 -m pip install mlxer
```

Then verify the runtime. If `mlx_lm` is missing, let `doctor --fix` install it
into a managed runtime or into the appropriate pipx environment:

```bash
mlxer doctor --fix
```

### Standalone binary: curl installer

For macOS Apple Silicon, install the latest GitHub Release binary with:

```bash
curl -fsSL https://github.com/Pixie-sh/mlxer/releases/latest/download/install.sh | sh
```

The installer downloads `mlxer-darwin-arm64.tar.gz`, verifies it against
`checksums.txt`, and writes the binary to `~/.local/bin` by default. Override
the target directory or version when needed:

```bash
curl -fsSL https://github.com/Pixie-sh/mlxer/releases/latest/download/install.sh \
  | MLXER_BIN_DIR=/usr/local/bin sh

curl -fsSL https://github.com/Pixie-sh/mlxer/releases/download/v0.1.0/install.sh \
  | MLXER_VERSION=v0.1.0 sh
```

The standalone binary manages `mlx_lm` through your configured Python
interpreter; it does not bundle model runtimes or `mlx_lm` itself. Run
`mlxer doctor --fix` after installation to create a private runtime venv when
your system Python is externally managed.

### Install from this repository

Install the runtime dependencies first. In a virtual environment, use:

```bash
python3 -m pip install mlx-lm
```

Then install `mlxer` from this repository for local development:

```bash
uv pip install -e .
pip install -e .
```

The package install also installs `tomli-w`, the only direct runtime dependency
declared by `mlxer` itself.

Then verify your environment:

```bash
mlxer doctor
```

If `mlx_lm` is missing, `doctor` will tell you; install it into the interpreter
named by `[server].python_executable` in your config.

## Quick start

```bash
mlxer doctor                # check Python, mlx_lm, paths, port
mlxer list                  # see discovered models
mlxer load                  # guided local model picker and start steps
mlxer status                # see live PID, uptime, endpoint
mlxer benchmark             # TTFT, decode tok/s, aggregate throughput
mlxer stop
```

## Global options

These work with every subcommand:

| Flag | Description |
|------|-------------|
| `--config PATH` | Use a different config file (default `~/.config/mlxer/config.toml`). |
| `--verbose` | Emit progress information to stderr. |
| `--version` | Print version and exit. |
| `-h, --help` | Show help (works on every subcommand too). |

## Configuration

First run creates `~/.config/mlxer/config.toml` with the defaults below.
All paths expand `~` and `$VAR`.

```toml
[server]
host = "127.0.0.1"
port = 8080
log_file = "~/services/mlx/logs/mlx-lm.server.log"
pid_file = "~/services/mlx/mlx-lm.server.pid"
state_file = "~/.local/state/mlxer/state.json"
lock_file = "~/.local/state/mlxer/lock"
python_executable = "python3"
extra_args = []                  # forwarded to mlx_lm server verbatim
startup_timeout_seconds = 120
stop_timeout_seconds = 15
max_log_bytes = 10485760         # 10 MiB
max_log_files = 5
patch_tool_calls = true          # best-effort shim for truncated tool calls

[models]
directories = [
  "~/.mlxer/models",
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
cache_dir = "~/.mlxer/bot"
max_tokens = 1024
temperature = 0.7
```

Validation: unknown tables or keys → exit code 3; `port` must be in
`1024–65535`; `extra_args`, `directories`, `aliases`, `patch_tool_calls`,
and `[bot]` values are type-checked.

Aliases pointing at non-existent paths are tolerated at load time (so a model
can be temporarily unavailable without breaking `mlxer`); `doctor`
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

The id printed by `mlxer list` is the **same string** the HTTP API
exposes — i.e. the value clients put in the `model` JSON field. For
filesystem models that's the model directory's basename; mlxer spawns
`mlx_lm server` with `cwd=<parent>` and `--model <basename>` so the API id
ends up as the basename, not the absolute path. For HF-cache models the id
is the HF-style `<org>/<name>` and mlx_lm's HF resolver finds the snapshot
in the local cache.

If two filesystem models in different directories share the same basename,
the first one discovered wins; rename one of the directories or set an alias
to disambiguate.

`mlxer start --model X` resolves `X` in this order: alias → discovered
display name → absolute filesystem path.

`mlxer load` is the guided shortcut form for local models. It prints the
current discovered model list, asks which model to start, then steps through
host, port, and whether to replace an existing managed server on that port.

---

## Commands

### `list`

Show discovered models.

```bash
mlxer list
mlxer list --json
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
mlxer start --model qwen3-8b-4bit
mlxer start --model qwen3-8b-4bit --port 1234
mlxer start --model /abs/path/to/model --replace
mlxer start --model qwen3-8b-4bit --extra-arg trust-remote-code=true
mlxer start --model qwen3-8b-4bit --bind-all     # bind on 0.0.0.0
mlxer start --choose                             # guided model picker
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
mlxer load
mlxer load --port 1237 --bind-all
mlxer load --bind-all --replace
```

| Flag | Description |
|------|-------------|
| `--host`, `--port`, `--replace`, `--bind-all`, `--extra-arg` | Same as [`start`](#start). If omitted, `load` prompts for host, port, and replace behavior. |

### `stop`

Stop the managed server.

```bash
mlxer stop
mlxer stop --timeout 30
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
mlxer restart
mlxer restart --port 1234
```

### `switch`

Convenience for swapping the running server to a different model. Takes
the model id as a positional argument.

```bash
mlxer switch qwen3-8b-4bit
mlxer switch /abs/path/to/other-model --extra-arg max-tokens=8192
```

| Flag | Description |
|------|-------------|
| `model` (positional) | New model id, alias, or absolute path. |
| `--host`, `--port`, `--bind-all`, `--extra-arg` | Same as [`start`](#start). |

### `status`

Report live server state.

```bash
mlxer status
mlxer status --json
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
mlxer logs                  # last 100 lines
mlxer logs --tail 500
mlxer logs -f               # follow (Ctrl-C to exit)
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
mlxer info qwen3-8b-4bit
mlxer info qwen3-8b-4bit --json
```

| Flag | Description |
|------|-------------|
| `model` (positional) | Model id, alias, or absolute path. |
| `--json` | Emit metadata as JSON. |

### `doctor`

Run diagnostics. Useful as the first thing you run after install, and
whenever something looks off.

```bash
mlxer doctor
mlxer doctor --json
mlxer doctor --fix
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
- The current `mlxer` runtime can import `mlx_lm` for the in-process
  [`bot`](#bot) command.

Exits `1` if any check is `FAIL`, otherwise `0`.

With `--fix`, `doctor` attempts only local, reversible setup work: install
`mlx_lm` into the bot runtime, create missing configured model directories,
and repair the default `server.python_executable`. For Python/pipx installs it
can repoint the server to the current working interpreter; for the standalone
binary it creates a private venv under `~/.local/share/mlxer/venv` and points
the server there. Fix progress is printed to stderr so `--json` output stays
parseable.

### `bot`

Chat with a small on-device troubleshooting assistant. The bot runs `mlx_lm`
in the current `mlxer` Python process, injects live `status`, `doctor`,
and recent-log context by default, and downloads its model once into
`[bot].cache_dir` for later reuse.

```bash
mlxer bot
mlxer bot --choose
mlxer bot --model mlx-community/Qwen3-1.7B-4bit
mlxer bot --no-context
```

| Flag | Description |
|------|-------------|
| `--model ID_OR_PATH` | Override `[bot].model` for this run. |
| `--choose` | Re-pick from the built-in lightweight model menu. |
| `--max-tokens N` | Override `[bot].max_tokens`. |
| `--temperature N` | Override `[bot].temperature`. |
| `--no-context` | Do not inject live server, doctor, or log context. |

If `mlx_lm` is not importable in the current interpreter, `bot` exits `7` and
suggests `mlxer doctor --fix`.

### `benchmark`

Measure **TTFT** (time-to-first-token), **per-stream decode tok/s** (computed
from `usage.completion_tokens` returned in the final SSE chunk; falls back to
chunk count for servers that don't emit `usage`), and **aggregate throughput**
= total completion tokens across all parallel streams ÷ wall-clock.

```bash
mlxer benchmark                                  # default prompt, 5 requests
mlxer benchmark --requests 8 --concurrency 4     # concurrency sweep
mlxer benchmark --prompt-file ./prompt.txt --max-tokens 512
mlxer benchmark --warmup 2                       # extra non-counted warmups
mlxer benchmark --json                           # machine-readable
mlxer benchmark --endpoint http://host:1235/v1 --model some-id
mlxer benchmark --save results.json
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
mlxer config opencode                            # print snippet to stdout
mlxer config opencode --model qwen3-8b-4bit
mlxer config opencode --format full              # full opencode.json shape
mlxer config opencode --apply                    # merge into ~/.config/opencode/opencode.json
mlxer config opencode --apply --overwrite        # replace the provider block
mlxer config opencode --reset                    # remove mlxer-managed provider blocks
mlxer config opencode --apply --target /path/to/opencode.json
mlxer config opencode --remote                   # use LAN IP, suffix provider name with @hostname
```

| Flag | Description |
|------|-------------|
| `--model ID` | Model id for the snippet (default: running server, then first discovered, then `[models].default_model`). |
| `--format merge\|full` | `merge` (default) emits just the `provider` map; `full` wraps it in a complete `opencode.json` with `$schema`. |
| `--apply` | Write into the file instead of stdout. A `<file>.bak` is created. |
| `--target PATH` | OpenCode config path (default `~/.config/opencode/opencode.json`). Used with `--apply` or `--reset`. |
| `--overwrite` | Replace the entire provider block. Without it, `--apply` *merges*: `npm`/`name`/`options` are refreshed and missing model entries added, but hand-tuned per-model fields (e.g. `"limit": { "context": ..., "output": ... }`) are preserved. Other top-level keys in `opencode.json` (`permission`, `mcp`, `plugin`, ...) are untouched. |
| `--reset` | Remove only provider keys marked with the `mlxer:` prefix from the target OpenCode config. User-managed providers are preserved. |
| `--remote` | Use this machine's LAN IP instead of `127.0.0.1`/`0.0.0.0` in the emitted URL and suffix the provider name with `@<hostname>`. Useful when generating a config for clients on the same network. |

Sample snippet (`merge` form):

```json
{
  "provider": {
    "mlxer:mlx-local:8080": {
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
`[server].host:port`. OpenCode provider keys are marked with `mlxer:`
and always include the port, such as `mlxer:mlx-local:8080`, so reset can
identify every mlxer-managed entry consistently.

**Migrating from an earlier version.** Older releases wrote either a bare
`mlx-local` provider block or an older managed key. On `--apply`, mlxer
opportunistically removes any legacy key whose `options.baseURL` matches the new
block's `baseURL`, so a previously-managed provider migrates cleanly to the new
`mlxer:` key without leaving a stale duplicate. A bare `mlx-local` block that
points at a different backend (e.g. LiteLLM on a different port) is treated as
user-curated and left in place. If you'd rather start fresh, run
`config opencode --reset` before `--apply`.

### `config claude-code`

Emit guidance and a LiteLLM `model_list` YAML for Claude Code.

```bash
mlxer config claude-code
mlxer config claude-code --model qwen3-8b-4bit
mlxer config claude-code --remote
```

| Flag | Description |
|------|-------------|
| `--model ID` | Model id for the snippet (same fallback chain as `config opencode`). |
| `--remote` | Use LAN IP in the emitted base URL. |

Why a snippet rather than direct config? At the time of writing, the Claude
Code CLI (`claude --help`) documents only Anthropic auth and third-party
providers Bedrock / Vertex / Foundry — there is no documented
OpenAI-compatible base-URL routing. mlxer therefore does **not** emit
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

### `config warp`

Emit WARP Terminal BYOK/custom-provider setup values for the local MLX
OpenAI-compatible endpoint.

```bash
mlxer config warp
mlxer config warp --model qwen3-8b-4bit
mlxer config warp --remote
```

| Flag | Description |
|------|-------------|
| `--model ID` | Model id for the snippet (same fallback chain as `config claude-code`). |
| `--remote` | Use LAN IP in the emitted base URL. |

Sample output:

```text
# WARP Terminal custom AI provider
# Paste these values into WARP's BYOK/custom provider settings.
Provider type: OpenAI-compatible
Provider name: mlx-local
Base URL: http://127.0.0.1:8080/v1
API key: mlx-local
Model: qwen3-8b-4bit
```

Use these values in WARP's custom AI provider or BYOK settings. `mlxer`
does not currently modify WARP files directly because WARP's local AI provider
configuration file schema is not verified here; this keeps user-managed WARP
settings safe while still providing copy/paste-ready endpoint details.

### `config show`

Display the current effective configuration (merged defaults + your file).

```bash
mlxer config show
mlxer config show --json
```

| Flag | Description |
|------|-------------|
| `--json` | Emit the config as JSON. |

### `config edit`

Open `config.toml` in `$EDITOR` and reload it on save (validates after).

```bash
mlxer config edit
mlxer config edit --editor code
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

- **`mlx_lm not installed`** — run `mlxer doctor --fix`. Avoid plain global
  `pip install` on Homebrew Python because PEP 668 may block it; `doctor --fix`
  uses pipx injection or a private venv instead.
- **`port already in use`** — another process is bound. `mlxer`
  reports the conflicting PID when it can discover one via `lsof`.
- **`server did not become ready within Ns`** — the launcher prints the
  last 40 log lines and exits 6. Check the log file for the real failure.
- **Stale state file** — if a previous run was killed hard, the next
  command detects the dead PID and clears it; `status` will then report
  `not running` cleanly.

## Development

```bash
git clone https://github.com/Pixie-sh/mlxer.git
cd mlxer
pip install -e '.[dev]'
pytest -q
```

Tests run without `mlx_lm` installed and without starting a real server
(every external call is faked through `tests/conftest.py`).

To build the local standalone binary for manual testing:

```bash
pip install -e '.[release]'
pyinstaller --onefile --name mlxer --add-data "mlxer/_server_shim.py:mlxer" mlxer/__main__.py
```

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

## FAQ

**What is mlxer?**
mlxer is a lightweight Python CLI that manages a local MLX language-model HTTP
server on Apple Silicon Macs. It lets you start, stop, restart, and switch
models without a GUI — ideal for SSH-only headless machines.

**How does mlxer differ from other LLM tools?**
mlxer is stdlib-first with only one runtime dependency (`tomli-w`). It has no
daemon, no database, no web UI — just `argparse`, a state file, an `fcntl`
lock, and `urllib`. Unlike Ollama or LM Studio, mlxer wraps the native
`mlx_lm` server directly.

**What models are supported?**
Any MLX-compatible model. mlxer discovers models from flat directories,
LM Studio nested layouts, and the Hugging Face hub cache. It also supports
model aliases for custom naming.

**How do I install mlxer?**
```bash
pipx install mlxer
mlxer doctor
```
Or use the standalone binary:
```bash
curl -fsSL https://github.com/Pixie-sh/mlxer/releases/latest/download/install.sh | sh
```

**How do I use mlxer with OpenCode?**
```bash
mlxer start --model qwen3-8b-4bit
mlxer config opencode --apply
```

**How do I use mlxer with Claude Code?**
mlxer provides two paths: a LiteLLM proxy (recommended) or experimental
OpenAI-compatible env vars. See the [`config claude-code`](#config-claude-code)
section above.

**What is the OpenAI-compatible endpoint?**
mlxer wraps `mlx_lm server` which exposes an OpenAI-compatible API at
`http://127.0.0.1:8080/v1`. Any tool that supports OpenAI-compatible
endpoints can connect to mlxer.

---

```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "mlxer",
  "description": "Headless CLI for managing local MLX language-model HTTP servers on Apple Silicon Macs. Supports model discovery, server lifecycle management, performance benchmarking, and provider integration with OpenCode, Claude Code, and LiteLLM.",
  "applicationCategory": "Developer Tool",
  "operatingSystem": "macOS (Apple Silicon)",
  "programmingLanguage": "Python",
  "license": "MIT",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  },
  "applicationSuite": "MLX",
  "keywords": "local llm, mlx, mlx-lm, headless server, apple silicon, openai-compatible",
  "releaseNotes": "https://github.com/Pixie-sh/mlxer/blob/main/CHANGELOG.md",
  "feature": {
    "@type": "CreativeWork",
    "name": "Server Lifecycle",
    "description": "Start, stop, restart, and switch MLX models with fcntl-locked atomic operations"
  },
  "knowsAbout": ["Large Language Models", "MLX Framework", "OpenAI Compatible API", "Local Inference"]
}
```
