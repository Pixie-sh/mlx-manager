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
  `doctor` findings, and recent log errors so it can help troubleshoot.
  Configurable via the new `[bot]` table (`model`, `max_tokens`,
  `temperature`); overridable with `--model`/`--max-tokens`/`--temperature`
  and `--no-context`.
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
