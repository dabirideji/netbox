"""Environment and JSON configuration loading for Netbox."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from netbox.paths import project_root

PROJECT_ROOT = project_root()
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"


def load_env_files(root: Path = PROJECT_ROOT) -> None:
    """Load dotenv files without overriding shell-provided values."""

    original_keys = set(os.environ)
    load_env_file(root / ".env", original_keys)
    load_env_file(root / ".env.local", original_keys)
    environment = os.environ.get("NETBOX_ENV", "development").strip() or "development"
    load_env_file(root / f".env.{environment}", original_keys)
    load_env_file(root / f".env.{environment}.local", original_keys)


def load_env_file(path: Path, original_keys: set[str]) -> None:
    """Load one dotenv-style file with simple `KEY=value` entries."""

    if not path.is_file():
        return

    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or key in original_keys:
            continue
        os.environ[key] = clean_env_value(value)


def clean_env_value(value: str) -> str:
    """Strip whitespace and matching quotes from an environment value."""

    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned


def config_dir() -> Path:
    """Return the configured JSON config directory."""

    raw_path = os.environ.get("NETBOX_CONFIG_DIR", str(DEFAULT_CONFIG_DIR))
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_json_config(filename: str) -> dict[str, Any]:
    """Load a JSON config file from `NETBOX_CONFIG_DIR`."""

    path = config_dir() / filename
    if not path.is_file():
        return {}

    with path.open() as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def env_str(name: str, default: str | None = None) -> str | None:
    """Return a string environment override when present."""

    value = os.environ.get(name)
    return default if value is None or value == "" else value


def env_int(name: str, default: int) -> int:
    """Return an integer environment override when present."""

    value = env_str(name)
    return int(value) if value is not None else default


def env_float(name: str, default: float) -> float:
    """Return a float environment override when present."""

    value = env_str(name)
    return float(value) if value is not None else default


def env_bool(name: str, default: bool) -> bool:
    """Return a boolean environment override when present."""

    value = env_str(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def nested(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return a nested JSON value with a default fallback."""

    current: Any = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def resolve_project_path(value: str | None) -> str | None:
    """Resolve relative project paths for config values that point to files."""

    if not value:
        return value
    path = Path(value).expanduser()
    return str(path if path.is_absolute() else PROJECT_ROOT / path)


def target_to_arg(target: dict[str, Any]) -> str:
    """Convert a structured target config object to the CLI target format."""

    host = str(target.get("host", "")).strip()
    label = str(target.get("label", host)).strip()
    scope = str(target.get("scope", "external")).strip()
    return f"{host}:{label}:{scope}"


def load_default_target_args() -> list[str]:
    """Return default external targets from `config/targets.json` or `NETBOX_TARGETS`."""

    env_targets = env_str("NETBOX_TARGETS")
    if env_targets:
        return [target.strip() for target in env_targets.split(",") if target.strip()]

    payload = load_json_config("targets.json")
    targets = payload.get("externalTargets", [])
    if not isinstance(targets, list):
        raise ValueError("config/targets.json externalTargets must be a list")
    return [target_to_arg(target) for target in targets if isinstance(target, dict)]


def load_default_target_seeds() -> list[dict[str, Any]]:
    """Return structured target seeds from `config/targets.json` when available."""

    payload = load_json_config("targets.json")
    targets = payload.get("targets")
    if targets is None:
        targets = payload.get("externalTargets", [])
    if not isinstance(targets, list):
        raise ValueError("config/targets.json targets must be a list")
    return [target for target in targets if isinstance(target, dict)]


def load_security_config() -> dict[str, Any]:
    """Return security-related config with safe defaults."""

    payload = load_json_config("security.json")
    return {
        "allowedBindHosts": payload.get("allowedBindHosts", ["127.0.0.1", "localhost", "0.0.0.0"]),
        "headers": payload.get("headers", {}),
    }


def load_speed_config() -> dict[str, Any]:
    """Return active speed-test policy and provider settings."""

    payload = load_json_config("speed.json")
    return {
        "enabled": bool(payload.get("enabled", True)),
        "provider": str(payload.get("provider", "mlab-ndt7")),
        "providerName": str(payload.get("providerName", "Measurement Lab NDT7")),
        "privacyUrl": str(payload.get("privacyUrl", "https://www.measurementlab.net/privacy/")),
        "dataPolicyUrl": str(payload.get("dataPolicyUrl", "https://www.measurementlab.net/privacy/")),
        "minIntervalMinutes": int(payload.get("minIntervalMinutes", 0)),
        "dailyRunLimit": int(payload.get("dailyRunLimit", 0)),
        "historyLimit": int(payload.get("historyLimit", 20)),
        "metadata": payload.get("metadata", {}),
    }


def load_storage_config() -> dict[str, Any]:
    """Return persisted log storage limits and pruning policy."""

    payload = load_json_config("storage.json")
    limits = payload.get("limits", {}) if isinstance(payload.get("limits"), dict) else {}
    return {
        "autoPrune": bool(payload.get("autoPrune", True)),
        "limits": {
            "maxDatabaseBytes": int(limits.get("maxDatabaseBytes", 52_428_800)),
            "maxIncidents": int(limits.get("maxIncidents", 10_000)),
            "maxPingSamples": int(limits.get("maxPingSamples", 100_000)),
            "maxSpeedTests": int(limits.get("maxSpeedTests", 500)),
        },
    }
