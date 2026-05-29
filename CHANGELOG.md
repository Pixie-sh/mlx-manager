# Changelog

All notable changes to `mlx-manager` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
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

### Fixed
- `benchmark` request table now shows the request index in the `#` column
  (previously it leaked `finish_reason` there).
- Removed a handful of unused imports (`field`, `Iterable`, `Any`, `sys`).
- `mlx-manager list` now reuses `_human_size` for directory sizes instead
  of duplicating the formatting logic.

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
