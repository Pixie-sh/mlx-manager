from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal, Union

from mlxer.config import ModelsCfg
from mlxer.paths import expand

Source = Literal["alias", "directory", "hf_cache"]

# Discovery walks each configured root recursively up to this many levels.
# 2 covers LM Studio (publisher/model-name), 3 covers the HF cache layout
# (models--org--name/snapshots/rev), 4 gives a little headroom for users with
# slightly deeper trees. Recursion also short-circuits the moment a model
# directory is found, so this only bounds *unproductive* walks.
_MAX_DEPTH = 4

# Reasons surfaced for directories that look like they were *meant* to be model
# dirs but can't be served by mlx_lm. Stable enough to assert on in tests.
_GGUF_REASON = "GGUF format (mlx_lm requires safetensors)"
_NO_SAFETENSORS_REASON = "config.json present but no safetensors weights"
_NO_CONFIG_REASON = "safetensors present but missing config.json"
_NO_HF_SNAPSHOT_REASON = "no usable snapshot in HF cache repo"


@dataclass(frozen=True)
class Model:
    id: str
    path: Path
    source: Source

    def to_dict(self) -> dict:
        return {"id": self.id, "path": str(self.path), "source": self.source}


@dataclass(frozen=True)
class SkippedDir:
    """A directory that looked model-shaped but can't be served by mlx_lm."""

    path: Path
    reason: str

    def to_dict(self) -> dict:
        return {"path": str(self.path), "reason": self.reason}


_Classification = Literal["model", "skipped", "container"]


def _classify_dir(path: Path) -> tuple[_Classification, str | None]:
    """Decide whether *path* is a model dir, a known-bad model dir, or neither.

    A "model" needs both ``config.json`` and at least one safetensors weights
    file (single, sharded, or ``weights.safetensors``). A "skipped" record is
    emitted when the directory clearly *intended* to hold a model — has GGUF
    weights, or one half of the (config + safetensors) pair — so the user can
    see *why* it didn't show up. Everything else is a plain "container" we keep
    walking into.
    """
    if not path.is_dir():
        return "container", None

    has_config = (path / "config.json").is_file()
    has_safetensors = False
    has_gguf = False
    try:
        for child in path.iterdir():
            if not child.is_file():
                continue
            name = child.name
            if name in ("model.safetensors", "weights.safetensors"):
                has_safetensors = True
            elif name.startswith("model-") and name.endswith(".safetensors"):
                has_safetensors = True
            elif name.endswith(".gguf"):
                has_gguf = True
    except (PermissionError, OSError):
        return "container", None

    if has_config and has_safetensors:
        return "model", None
    if has_gguf:
        return "skipped", _GGUF_REASON
    if has_config and not has_safetensors:
        return "skipped", _NO_SAFETENSORS_REASON
    if has_safetensors and not has_config:
        return "skipped", _NO_CONFIG_REASON
    return "container", None


def _is_model_dir(path: Path) -> bool:
    """A directory is a candidate model iff it contains ``config.json`` and at
    least one safetensors weights file (single, sharded, or ``weights.safetensors``)."""
    return _classify_dir(path)[0] == "model"


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


def _scan(root: Path, *, _depth: int = 0) -> Iterator[Union[Model, SkippedDir]]:
    """Recursively walk *root* yielding Models or SkippedDirs.

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
            else:
                snaps_dir = root / "snapshots"
                try:
                    has_any_snap = snaps_dir.is_dir() and any(
                        s.is_dir() for s in snaps_dir.iterdir()
                    )
                except (PermissionError, OSError):
                    has_any_snap = False
                if has_any_snap:
                    yield SkippedDir(
                        path=root.resolve(), reason=_NO_HF_SNAPSHOT_REASON
                    )
        return

    if _depth > 0:
        kind, reason = _classify_dir(root)
        if kind == "model":
            yield Model(id=root.name, path=root.resolve(), source="directory")
            return
        if kind == "skipped":
            yield SkippedDir(path=root.resolve(), reason=reason or "unknown reason")
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


def _discover_internal(cfg: ModelsCfg) -> tuple[list[Model], list[SkippedDir]]:
    """Walk every configured root once, partitioning into models and skipped dirs.

    Alias > directory > hf_cache precedence applies to models; skipped dirs are
    de-duplicated by resolved path.
    """
    found: dict[str, Model] = {}
    skipped_by_path: dict[Path, SkippedDir] = {}

    for alias, raw in cfg.aliases.items():
        target = expand(raw)
        found[alias] = Model(id=alias, path=target, source="alias")

    for raw_dir in cfg.directories:
        root = expand(raw_dir)
        for entry in _scan(root):
            if isinstance(entry, Model):
                if entry.id in found:
                    continue
                found[entry.id] = entry
            else:
                skipped_by_path.setdefault(entry.path, entry)

    skipped = sorted(skipped_by_path.values(), key=lambda s: str(s.path))
    return list(found.values()), skipped


def discover(cfg: ModelsCfg) -> list[Model]:
    """Return the de-duplicated model list, alias > directory > hf_cache priority."""
    models, _ = _discover_internal(cfg)
    return models


def discover_with_skipped(cfg: ModelsCfg) -> tuple[list[Model], list[SkippedDir]]:
    """Like :func:`discover` but also returns directories that looked
    model-shaped (had GGUF weights, or one of {config.json, safetensors} but
    not both) so callers can explain *why* they aren't selectable."""
    return _discover_internal(cfg)


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
        f"model {requested!r} not found; try `mlxer list` to see available IDs"
    )
