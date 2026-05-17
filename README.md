# mlx-manager

A small, stdlib-first Python 3.11+ CLI that wraps `python -m mlx_lm.server` so
you can run a local MLX HTTP server headless on an Apple Silicon Mac — start,
stop, restart, status, logs, doctor, and emit copy/paste-ready provider
snippets for [OpenCode](https://opencode.ai) (primary) and Claude Code /
LiteLLM (secondary).

No daemon. No database. No web UI. Just `argparse`, a single state file, an
fcntl lock, and `urllib`.

---

## Install

Either of:

```bash
uv pip install -e .
pip install -e .
```

Requires Python ≥ 3.11. Dependencies: `tomli-w` (only needed to *write* TOML
on first run — TOML reading uses stdlib `tomllib`). No other runtime deps.

You also need [`mlx_lm`](https://pypi.org/project/mlx-lm/) installed in the
same interpreter `mlx-manager` will use to launch the server (default
`python3`). Run `mlx-manager doctor` if you're unsure.

## Quick start

```bash
mlx-manager doctor              # check Python, mlx_lm, paths, port
mlx-manager list                # see discovered models
mlx-manager start --model <id>  # launch server on 127.0.0.1:8080
mlx-manager status              # see live PID, uptime, endpoint
mlx-manager stop
```

## Config

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
extra_args = []                  # forwarded to mlx_lm.server verbatim
startup_timeout_seconds = 120
stop_timeout_seconds = 15
max_log_bytes = 10485760         # 10 MiB
max_log_files = 5

[models]
directories = [
  "~/models/mlx",
  "~/.cache/huggingface/hub",
  "~/.lmstudio/models",
]
default_model = ""

[models.aliases]
# qwen3-8b-4bit = "~/models/mlx/qwen3-8b-4bit"

[providers]
base_url = ""                    # if empty, derived from server.host:port
api_key = "mlx-local"
provider_name = "mlx-local"
```

Validation: unknown tables or keys → exit 3; port must be in 1024–65535.

Aliases pointing at non-existent paths are tolerated at load (so you can have
a model temporarily unavailable without breaking `mlx-manager`); `doctor`
warns about them.

## Discovery rules

A directory is a model iff it has `config.json` **and** at least one of
`model.safetensors`, `model-*.safetensors` shards, or `weights.safetensors`.
Tokenizer files are not required (some MLX repacks omit them).

Each configured root is walked recursively (capped at 4 levels deep, and
discovery stops descending the moment it finds a model). This handles three
common layouts uniformly:

| Layout | Example | Discovered id |
|--------|---------|---------------|
| Flat | `~/models/mlx/<name>/` | `<name>` |
| Nested by publisher (LM Studio) | `~/.lmstudio/models/<publisher>/<name>/` | `<name>` |
| Hugging Face hub cache | `~/.cache/huggingface/hub/models--<org>--<name>/snapshots/<rev>/` | `<org>/<name>` |

The id you see in `mlx-manager list` is the **same string** the HTTP API
exposes — i.e. the value clients put in the `model` JSON field. For
filesystem models that's the model directory's basename; mlx-manager spawns
`mlx_lm.server` with `cwd=<parent>` and `--model <basename>` so the API id is
the basename, not the absolute path. For HF-cache models the id is the
HF-style `<org>/<name>` and `mlx_lm`'s HF resolver finds the snapshot in the
local cache.

If two filesystem models in different directories share the same basename,
the first one discovered wins; rename one of the directories or set an alias
to disambiguate.

`mlx-manager start --model X` resolves `X` in this order: alias → discovered
display name → absolute path.

## Using with OpenCode

```bash
mlx-manager config opencode --model qwen3-8b-4bit
```

emits a `provider` block ready to merge into `~/.config/opencode/opencode.json`:

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

`--format full` wraps it in a complete `opencode.json` with `$schema` set.
If a server is currently running, the snippet's `baseURL` is taken from the
live state; otherwise it falls back to `[providers].base_url` and finally to
`[server].host:port`.

### Apply directly to `opencode.json`

```bash
mlx-manager config opencode --apply                        # merge into ~/.config/opencode/opencode.json
mlx-manager config opencode --apply --overwrite            # replace the provider block entirely
mlx-manager config opencode --apply --target /path/to/opencode.json
```

`--apply` (merge mode) refreshes the `npm` / `name` / `options` fields and
adds any missing model entries, but **keeps your hand-tuned per-model
fields** (e.g. `"limit": { "context": ..., "output": ... }`). All other
top-level keys in `opencode.json` (`permission`, `mcp`, `plugin`, ...) are
left untouched. `--overwrite` is destructive: it replaces the whole provider
block. A `<file>.bak` is written before each apply.

## Using with Claude Code

**Status (verified 2026-05):** the installed Claude Code CLI (`claude --help`)
documents only Anthropic auth (`ANTHROPIC_API_KEY`) and 3P providers
Bedrock/Vertex/Foundry. There is no documented OpenAI-compatible
base-URL routing. We therefore do **not** emit `ANTHROPIC_BASE_URL`.

`mlx-manager config claude-code` emits two things:

1. **Recommended path — LiteLLM in front of MLX.** Use the printed
   `model_list:` YAML as your `config.yaml` for
   [LiteLLM](https://docs.litellm.ai/), then point Claude Code at LiteLLM's
   own URL/key. LiteLLM speaks the OpenAI surface back to Claude-Code-side
   tools and proxies to MLX on the wire. To run it:
   ```bash
   pip install 'litellm[proxy]'
   litellm --config config.yaml --port 4000
   ```
2. **Experimental — direct env vars.** A small `OPENAI_API_KEY` /
   `OPENAI_BASE_URL` block, labeled experimental, for users who have
   confirmed OpenAI-compatible routing on their Claude Code build.

## Benchmark

```bash
mlx-manager benchmark                                  # default prompt, single stream, 5 requests
mlx-manager benchmark --requests 8 --concurrency 4     # concurrency sweep
mlx-manager benchmark --prompt-file ./prompt.txt --max-tokens 512
mlx-manager benchmark --warmup 2                       # extra non-counted warmups
mlx-manager benchmark --json                           # machine-readable
mlx-manager benchmark --endpoint http://other-host:1235/v1 --model some-id
```

Sends streaming chat-completions, measures **TTFT** (time-to-first-token),
**per-stream decode tok/s** (computed from `usage.completion_tokens` returned
in the final SSE chunk; falls back to chunk count for servers that don't emit
`usage`), and **aggregate throughput** = total completion tokens across all
parallel streams ÷ wall-clock. Sample output:

```
benchmark   endpoint    http://127.0.0.1:1235/v1
            model       GLM-4.7-Flash-MLX-6bit
            requests    4 (concurrency=2, max_tokens=128, warmup=0)
  request 1/4  ttft=0.60s  total=3.43s  completion=128  decode=45.3 tok/s
  ...
summary     wall              6.42s
            requests          4/4 ok
            ttft p50/p95      0.39s / 0.60s
            decode p50/p95    45.4 / 45.5 tok/s per stream
            aggregate         79.7 tok/s
```

Knobs that matter:

| Flag | Default | Notes |
|------|---------|-------|
| `--requests N` | 5 | total requests measured |
| `--concurrency N` | 1 | parallel in-flight streams |
| `--warmup N` | 1 | sequential pre-runs not counted in the measurement (defeats prompt-cache cold-start) |
| `--max-tokens N` | 256 | per request — bump for longer decode windows |
| `--prompt TXT` / `--prompt-file F` | built-in | the built-in prompt is generation-bound (~50 words) |
| `--endpoint URL` | running server's `base_url` | for hitting a different MLX endpoint |

Reasoning-model caveat: GLM-4.7 and similar emit their "thinking" tokens
under `delta.reasoning` rather than `delta.content`. The benchmark treats
both as decode tokens, so the tok/s number reflects the model's total
generation rate, not just the user-visible answer.

## Logs

`mlx-manager logs --tail 100` prints the most recent lines; add `-f` to
follow. Logs are appended to `[server].log_file` and rotated when they
exceed `max_log_bytes` (kept up to `max_log_files`).

## Troubleshooting

- **`mlx_lm not installed`** — run `mlx-manager doctor`. Install with
  `pip install mlx-lm` into the interpreter named by `[server].python_executable`.
- **`port already in use`** — another process is bound. `mlx-manager` reports
  the conflicting PID when it can discover one via `lsof`.
- **`server did not become ready within Ns`** — the launcher prints the last
  40 log lines and exits 6. Check the log file for the real failure.
- **stale state file** — if a previous run was killed hard, the next command
  will detect the dead PID and clean up; `status` will report
  `running: false, stale: false` once cleared.

## Exit codes

| Code | Meaning |
|------|---------|
| 0    | success |
| 1    | generic failure |
| 2    | usage error |
| 3    | config error |
| 4    | not running (status/stop) |
| 5    | already running (start without `--replace`) |
| 6    | startup timeout |
| 7    | `mlx_lm` missing |

## Safety notes

- The default bind is `127.0.0.1`. Binding `0.0.0.0` requires `--bind-all`
  and prints a warning to stderr.
- `stop` never kills a PID without first confirming its `argv` contains
  `mlx_lm.server` *and* the recorded port — so a recycled PID belonging to
  some other program will not be touched.
- `start`/`stop`/`restart` hold an `fcntl` lock on `[server].lock_file`
  while they mutate state. Lock acquisition has a 10 s timeout.

## Stretch: `launchd` (not implemented in v1)

A future `mlx-manager install-launchd` would write a `~/Library/LaunchAgents`
plist invoking `mlx-manager start --model <default>` on user login, with
`StandardErrorPath`/`StandardOutPath` pointing at the configured log. The
install/uninstall pair would `bootstrap`/`bootout` the agent via `launchctl`.
v1 ships without it — use a tmux/screen session, an `at` job, or a systemd-
launched VM tunnel if you need restart-on-login.

## Assumptions

Verified on this machine at build time:

- `python3 --version` reported 3.12.6.
- `python3 -m mlx_lm.server --help` exits 0; the known long flags were
  recorded for `--extra-arg` validation. (Note: mlx-lm warns that the
  hyphenated module form is deprecated in favor of `python -m mlx_lm server` —
  we still use the deprecated form, which keeps backwards compatibility with
  older mlx-lm versions; once mlx-lm drops support, swap the spawn line in
  `mlx_manager/server.py:build_command`.)
- `~/.config/opencode/opencode.json` exists; the emitted provider block
  matches its `provider` table layout.
- `claude --version` reports 2.1.128; OpenAI-compatible base URL support is
  not documented on the help output, so Claude Code support is the
  experimental + LiteLLM path described above.

## Development

```bash
pip install -e '.[dev]'
pytest -q
```

Tests run without `mlx_lm` installed and without starting a real server.
