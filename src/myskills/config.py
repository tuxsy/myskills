""".myskills.json config read/write with atomic file operations (config-contract.md)."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Raised when config operations fail."""


# Schema version
CONFIG_VERSION = 1


def read_config(config_path: Path) -> dict[str, Any]:
    """Read and validate .myskills.json.

    Args:
        config_path: Path to .myskills.json.

    Returns:
        Parsed config dict. Returns empty default if file doesn't exist.
    """
    if not config_path.exists():
        return _default_config()

    try:
        raw = config_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError) as e:
        raise ConfigError(f"Failed to read config: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError("Config file must be a JSON object.")

    if data.get("version") != CONFIG_VERSION:
        raise ConfigError(
            f"Unsupported config version: {data.get('version')}. Expected {CONFIG_VERSION}."
        )

    return data


def write_config(config_path: Path, data: dict[str, Any]) -> None:
    """Write config atomically (write-to-temp-then-rename).

    Args:
        config_path: Path to .myskills.json.
        data: Config data to write.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Write to a temp file in the same directory, then rename
        fd, tmp_path = tempfile.mkstemp(
            dir=config_path.parent,
            prefix=".myskills_",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
                f.write("\n")
            os.replace(tmp_path, config_path)
        except BaseException:
            # Clean up temp file on any error
            import contextlib

            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise
    except OSError as e:
        raise ConfigError(f"Failed to write config: {e}") from e


def add_installation(
    config_path: Path,
    repo_url: str,
    skill_name: str,
    version: str,
    agents: list[str],
) -> None:
    """Add or update a skill installation in the config.

    Args:
        config_path: Path to .myskills.json.
        repo_url: Repository URL.
        skill_name: Name of the skill.
        version: Installed version.
        agents: List of agent IDs.
    """
    data = read_config(config_path)
    data["repository"] = repo_url
    data["installations"][skill_name] = {
        "version": version,
        "agents": agents,
        "installed_at": datetime.utcnow().isoformat() + "Z",
    }
    write_config(config_path, data)


def remove_installation(config_path: Path, skill_name: str) -> None:
    """Remove a skill installation from the config.

    Args:
        config_path: Path to .myskills.json.
        skill_name: Name of the skill to remove.
    """
    data = read_config(config_path)
    data["installations"].pop(skill_name, None)
    write_config(config_path, data)


def get_installation(config_path: Path, skill_name: str) -> dict[str, Any] | None:
    """Get installation details for a specific skill.

    Args:
        config_path: Path to .myskills.json.
        skill_name: Name of the skill.

    Returns:
        Installation dict or None if not installed.
    """
    data = read_config(config_path)
    return data["installations"].get(skill_name)


def get_all_installations(config_path: Path) -> dict[str, dict[str, Any]]:
    """Get all installed skills from config.

    Args:
        config_path: Path to .myskills.json.

    Returns:
        Dict of skill_name -> installation details.
    """
    data = read_config(config_path)
    return data["installations"]


def _default_config() -> dict[str, Any]:
    """Return a default empty config."""
    return {
        "version": CONFIG_VERSION,
        "repository": "",
        "installations": {},
    }
