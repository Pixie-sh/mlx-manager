from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomli_w

from mlx_manager.paths import ensure_parent, expand

DEFAULT_CONFIG_PATH = "~/.config/mlx-manager/config.toml"

_DEFAULTS: dict[str, Any] = {
    "server": {
        "host": "127.0.0.1",
        "port": 8080,
        "log_file": "~/services/mlx/logs/mlx-lm.server.log",
        "pid_file": "~/services/mlx/mlx-lm.server.pid",
        "state_file": "~/.local/state/mlx-manager/state.json",
        "lock_file": "~/.local/state/mlx-manager/lock",
        "python_executable": "python3",
        "extra_args": [],
        "startup_timeout_seconds": 120,
        "stop_timeout_seconds": 15,
        "max_log_bytes": 10_485_760,
        "max_log_files": 5,
        "patch_tool_calls": True,
        "max_context_tokens": 0,
        "prompt_cache_fraction": 0.5,
    },
    "models": {
        "directories": [
            "~/.mlx-manager/models",
            "~/.models/mlx",
            "~/models/mlx",
            "~/.cache/huggingface/hub",
            "~/.lmstudio/models",
        ],
        "default_model": "",
        "aliases": {},
    },
    "providers": {
        "base_url": "",
        "api_key": "mlx-local",
        "provider_name": "mlx-local",
    },
    "bot": {
        "model": "mlx-community/gemma-4-e2b-it-4bit",
        "cache_dir": "~/.mlx-manager/bot",
        "max_tokens": 1024,
        "temperature": 0.7,
    },
}

_KNOWN_TABLES = {"server", "models", "providers", "bot"}
_KNOWN_KEYS = {
    "server": set(_DEFAULTS["server"].keys()),
    "models": {"directories", "default_model", "aliases"},
    "providers": set(_DEFAULTS["providers"].keys()),
    "bot": set(_DEFAULTS["bot"].keys()),
}


class ConfigError(Exception):
    """Raised for invalid configuration; CLI maps this to exit code 3."""


@dataclass(frozen=True)
class ServerCfg:
    host: str
    port: int
    log_file: str
    pid_file: str
    state_file: str
    lock_file: str
    python_executable: str
    extra_args: list[str]
    startup_timeout_seconds: int
    stop_timeout_seconds: int
    max_log_bytes: int
    max_log_files: int
    patch_tool_calls: bool = True
    max_context_tokens: int = 0
    prompt_cache_fraction: float = 0.5


@dataclass(frozen=True)
class ModelsCfg:
    directories: list[str]
    default_model: str
    aliases: dict[str, str]


@dataclass(frozen=True)
class ProvidersCfg:
    base_url: str
    api_key: str
    provider_name: str


@dataclass(frozen=True)
class BotCfg:
    model: str
    cache_dir: str
    max_tokens: int
    temperature: float


@dataclass(frozen=True)
class Config:
    path: Path
    server: ServerCfg
    models: ModelsCfg
    providers: ProvidersCfg
    bot: BotCfg

    @property
    def base_url(self) -> str:
        return self.providers.base_url or f"http://{self.server.host}:{self.server.port}/v1"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def write_default(path: Path) -> None:
    """Write the default config TOML to *path* (creating parents)."""
    ensure_parent(path)
    with open(path, "wb") as f:
        tomli_w.dump(_DEFAULTS, f)


def update_value(path: str | Path, table: str, key: str, value: Any) -> None:
    """Set ``[table].key = value`` in the TOML at *path*, preserving other keys.

    Reads the existing file (creating defaults first if absent), sets the one
    value, re-validates, and writes the whole document back. TOML comments are
    not preserved.
    """
    p = expand(path)
    if not p.exists():
        write_default(p)
    with open(p, "rb") as f:
        raw = tomllib.load(f)
    raw.setdefault(table, {})[key] = value
    _validate(raw)
    ensure_parent(p)
    with open(p, "wb") as f:
        tomli_w.dump(raw, f)


def _validate(raw: dict[str, Any]) -> None:
    for key in raw.keys():
        if key not in _KNOWN_TABLES:
            raise ConfigError(f"unknown top-level table: [{key}]")
    for table in _KNOWN_TABLES:
        sub = raw.get(table, {})
        if not isinstance(sub, dict):
            raise ConfigError(f"[{table}] must be a table")
        for k in sub.keys():
            if k not in _KNOWN_KEYS[table]:
                raise ConfigError(f"unknown key: [{table}].{k}")

    server = raw.get("server", {})
    if "port" in server:
        port = server["port"]
        if not isinstance(port, int) or not (1024 <= port <= 65535):
            raise ConfigError(f"server.port must be int in 1024–65535 (got {port!r})")
    if "extra_args" in server and not isinstance(server["extra_args"], list):
        raise ConfigError("server.extra_args must be a list of strings")
    if "extra_args" in server:
        for a in server["extra_args"]:
            if not isinstance(a, str):
                raise ConfigError("server.extra_args entries must be strings")
    if "patch_tool_calls" in server and not isinstance(server["patch_tool_calls"], bool):
        raise ConfigError("server.patch_tool_calls must be a boolean")
    if "max_context_tokens" in server:
        mct = server["max_context_tokens"]
        if not isinstance(mct, int) or mct < 0:
            raise ConfigError("server.max_context_tokens must be a non-negative int (0 = auto)")
    if "prompt_cache_fraction" in server:
        pcf = server["prompt_cache_fraction"]
        if not isinstance(pcf, (int, float)) or not (0.0 < float(pcf) <= 1.0):
            raise ConfigError("server.prompt_cache_fraction must be a number in (0.0, 1.0]")

    models = raw.get("models", {})
    if "directories" in models:
        if not isinstance(models["directories"], list):
            raise ConfigError("models.directories must be a list of strings")
        for d in models["directories"]:
            if not isinstance(d, str):
                raise ConfigError("models.directories entries must be strings")
    if "aliases" in models and not isinstance(models["aliases"], dict):
        raise ConfigError("[models.aliases] must be a table")

    bot = raw.get("bot", {})
    if "model" in bot and not isinstance(bot["model"], str):
        raise ConfigError("bot.model must be a string")
    if "cache_dir" in bot and not isinstance(bot["cache_dir"], str):
        raise ConfigError("bot.cache_dir must be a string")
    if "max_tokens" in bot and (
        not isinstance(bot["max_tokens"], int) or bot["max_tokens"] <= 0
    ):
        raise ConfigError("bot.max_tokens must be a positive int")
    if "temperature" in bot and not isinstance(bot["temperature"], (int, float)):
        raise ConfigError("bot.temperature must be a number")


def load(path: str | Path | None = None) -> Config:
    """Load config from *path* (default ``~/.config/mlx-manager/config.toml``).

    Creates a default config on first use. Unknown tables/keys raise ConfigError.
    """
    cfg_path = expand(path or DEFAULT_CONFIG_PATH)
    if not cfg_path.exists():
        write_default(cfg_path)

    with open(cfg_path, "rb") as f:
        raw = tomllib.load(f)

    _validate(raw)

    merged = _deep_merge(_DEFAULTS, raw)
    server = merged["server"]
    models = merged["models"]
    providers = merged["providers"]
    bot = merged["bot"]

    return Config(
        path=cfg_path,
        server=ServerCfg(
            host=str(server["host"]),
            port=int(server["port"]),
            log_file=str(server["log_file"]),
            pid_file=str(server["pid_file"]),
            state_file=str(server["state_file"]),
            lock_file=str(server["lock_file"]),
            python_executable=str(server["python_executable"]),
            extra_args=list(server["extra_args"]),
            startup_timeout_seconds=int(server["startup_timeout_seconds"]),
            stop_timeout_seconds=int(server["stop_timeout_seconds"]),
            max_log_bytes=int(server["max_log_bytes"]),
            max_log_files=int(server["max_log_files"]),
            patch_tool_calls=bool(server["patch_tool_calls"]),
            max_context_tokens=int(server["max_context_tokens"]),
            prompt_cache_fraction=float(server["prompt_cache_fraction"]),
        ),
        models=ModelsCfg(
            directories=[str(d) for d in models["directories"]],
            default_model=str(models["default_model"]),
            aliases={str(k): str(v) for k, v in models["aliases"].items()},
        ),
        providers=ProvidersCfg(
            base_url=str(providers["base_url"]),
            api_key=str(providers["api_key"]),
            provider_name=str(providers["provider_name"]),
        ),
        bot=BotCfg(
            model=str(bot["model"]),
            cache_dir=str(bot["cache_dir"]),
            max_tokens=int(bot["max_tokens"]),
            temperature=float(bot["temperature"]),
        ),
    )
