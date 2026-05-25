# Changelog

All notable changes to `mlx-manager` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `LICENSE` (MIT), `CONTRIBUTING.md`, `CHANGELOG.md`, and `.gitignore` for
  open-source housekeeping.
- README rewritten to document every command, flag, and exit code.

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
