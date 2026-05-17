from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Literal

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
