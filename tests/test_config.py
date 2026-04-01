"""Tests for config module."""

from pathlib import Path

import pytest

from myskills.config import (
    CONFIG_VERSION,
    ConfigError,
    add_installation,
    read_config,
    remove_installation,
    write_config,
)


def test_read_config_nonexistent_returns_default(tmp_path: Path):
    """Test reading config when file doesn't exist returns default."""
    config_path = tmp_path / ".myskills.json"
    config = read_config(config_path)
    assert config["version"] == CONFIG_VERSION
    assert config["installations"] == {}
    assert "repository" in config  # Default config has repository key


def test_read_config_invalid_json_raises_error(tmp_path: Path):
    """Test reading invalid JSON raises ConfigError."""
    config_path = tmp_path / ".myskills.json"
    config_path.write_text("invalid json{")

    with pytest.raises(ConfigError):
        read_config(config_path)


def test_read_config_non_dict_raises_error(tmp_path: Path):
    """Test reading non-dict JSON raises ConfigError."""
    config_path = tmp_path / ".myskills.json"
    config_path.write_text("[]")

    with pytest.raises(ConfigError) as exc_info:
        read_config(config_path)

    assert "must be a JSON object" in str(exc_info.value)


def test_read_config_wrong_version_raises_error(tmp_path: Path):
    """Test reading config with wrong version raises ConfigError."""
    config_path = tmp_path / ".myskills.json"
    config_path.write_text('{"version": "99.0", "installations": {}}')

    with pytest.raises(ConfigError) as exc_info:
        read_config(config_path)

    assert "Unsupported config version" in str(exc_info.value)


def test_write_config_creates_file(tmp_path: Path):
    """Test writing config creates file."""
    config_path = tmp_path / ".myskills.json"
    data = {
        "version": CONFIG_VERSION,
        "repository": "git@example.com:org/repo.git",
        "installations": {},
    }

    write_config(config_path, data)

    assert config_path.exists()
    read_data = read_config(config_path)
    assert read_data["version"] == CONFIG_VERSION
    assert read_data["repository"] == "git@example.com:org/repo.git"


def test_add_installation_creates_entry(tmp_path: Path):
    """Test adding an installation."""
    config_path = tmp_path / ".myskills.json"
    write_config(
        config_path,
        {
            "version": CONFIG_VERSION,
            "repository": None,
            "installations": {},
        },
    )

    add_installation(
        config_path=config_path,
        repo_url="git@example.com:org/repo.git",
        skill_name="test-skill",
        version="1.0.0",
        agents=["claude"],
    )

    config = read_config(config_path)
    assert "test-skill" in config["installations"]
    assert config["installations"]["test-skill"]["version"] == "1.0.0"
    assert config["installations"]["test-skill"]["agents"] == ["claude"]


def test_remove_installation_deletes_entry(tmp_path: Path):
    """Test removing an installation."""
    config_path = tmp_path / ".myskills.json"
    write_config(
        config_path,
        {
            "version": CONFIG_VERSION,
            "repository": "git@example.com:org/repo.git",
            "installations": {
                "test-skill": {
                    "version": "1.0.0",
                    "agents": ["claude"],
                }
            },
        },
    )

    remove_installation(config_path, "test-skill")

    config = read_config(config_path)
    assert "test-skill" not in config["installations"]


def test_remove_nonexistent_installation_is_noop(tmp_path: Path):
    """Test removing nonexistent installation is a no-op."""
    config_path = tmp_path / ".myskills.json"
    write_config(
        config_path,
        {
            "version": CONFIG_VERSION,
            "repository": None,
            "installations": {},
        },
    )

    # Should not raise an error
    remove_installation(config_path, "nonexistent")

    config = read_config(config_path)
    assert config["installations"] == {}


def test_get_installation(tmp_path: Path):
    """Test getting an installation."""
    config_path = tmp_path / ".myskills.json"
    write_config(
        config_path,
        {
            "version": CONFIG_VERSION,
            "repository": "git@example.com:org/repo.git",
            "installations": {
                "test-skill": {
                    "version": "1.0.0",
                    "agents": ["claude"],
                }
            },
        },
    )

    from myskills.config import get_installation

    installation = get_installation(config_path, "test-skill")
    assert installation is not None
    assert installation["version"] == "1.0.0"
    assert installation["agents"] == ["claude"]

    # Test nonexistent
    installation = get_installation(config_path, "nonexistent")
    assert installation is None


def test_get_all_installations(tmp_path: Path):
    """Test getting all installations."""
    config_path = tmp_path / ".myskills.json"
    write_config(
        config_path,
        {
            "version": CONFIG_VERSION,
            "repository": "git@example.com:org/repo.git",
            "installations": {
                "skill1": {"version": "1.0.0", "agents": ["claude"]},
                "skill2": {"version": "2.0.0", "agents": ["cursor"]},
            },
        },
    )

    from myskills.config import get_all_installations

    installations = get_all_installations(config_path)
    assert len(installations) == 2
    assert "skill1" in installations
    assert "skill2" in installations
