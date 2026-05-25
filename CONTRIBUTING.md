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
