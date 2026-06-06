# Changelog

All notable changes to `mlx-manager` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `load` command: a guided shortcut for starting from the discovered local model
  list. It prints numbered models, then prompts for host, port, whether to
  replace an existing managed server, and whether to apply the OpenCode
  provider config in one go (defaults to no). If you opt in, three follow-up
  prompts let you pick the OpenCode config path, choose merge vs overwrite
  (i.e. reset the whole provider block), and optionally also print a Claude
  Code (LiteLLM) snippet to stdout. The same stepper is available as
  `start --choose`. Pass `--update-opencode` (and optionally `--opencode-target
  /path/to/opencode.json` / `--overwrite`) on the CLI to skip the prompts and
  apply silently.
- `config opencode --choose`: same set of interactive prompts (target,
  merge/overwrite, Claude Code snippet) for users who already have a server
  running and just want to apply or reset the provider config. Implies
  `--apply` so a single command goes from "I have a server" to "OpenCode is
  configured" without remembering the flag combinations.
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
- OpenCode provider keys emitted by `config opencode` are now prefixed with
  `mlx-manager:` and suffixed with the port (e.g. `mlx-manager:mlx-local:8080`)
  so every mlx-manager-managed block is identifiable. `--apply` opportunistically
  migrates a legacy bare key (e.g. `mlx-local`) when its `options.baseURL`
  matches the new block's `baseURL`, so existing setups upgrade without
  duplicate provider entries; user-curated bare keys pointing at a different
  backend are left untouched. Use `config opencode --reset` to wipe and
  re-apply if you want a fully fresh install.

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
  provided, matching the documented network exposure safety rule. The same
  guard applies when `[server].host = "0.0.0.0"` is set in `config.toml`:
  starting a server now requires explicit `--bind-all` each invocation so
  network exposure is never inherited from a stale config edit. To restore
  the previous behavior, switch the config back to `127.0.0.1` and pass
  `--bind-all` on the runs that should be reachable.

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
