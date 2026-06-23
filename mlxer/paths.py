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
