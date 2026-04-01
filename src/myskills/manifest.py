"""SKILL.md YAML front-matter parser and validator (R-007, config-contract.md)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from myskills.models import SkillManifest

if TYPE_CHECKING:
    from myskills.ui import UIProvider

# Skill name: lowercase alphanumeric + hyphens, min 2 chars
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

# Semantic version: MAJOR.MINOR.PATCH
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class ManifestError(Exception):
    """Raised when manifest parsing or validation fails."""


def parse_manifest(skill_dir: Path, ui: UIProvider | None = None) -> SkillManifest:
    """Parse and validate SKILL.md from a skill directory.

    Args:
        skill_dir: Path to the skill directory containing SKILL.md.
        ui: Optional UI provider for verbose warnings.

    Returns:
        Validated SkillManifest instance.

    Raises:
        ManifestError: If parsing or validation fails.
    """
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        raise ManifestError(f"Missing required manifest file (SKILL.md) in '{skill_dir}'.")

    raw_content = skill_md.read_text(encoding="utf-8")

    if not raw_content.startswith("---"):
        raise ManifestError("SKILL.md must start with YAML front-matter (---).")

    # Split front-matter from body
    parts = raw_content.split("---", 2)
    if len(parts) < 3:
        raise ManifestError("SKILL.md must start with YAML front-matter (---).")

    front_matter_str = parts[1].strip()

    try:
        front_matter = yaml.safe_load(front_matter_str)
    except yaml.YAMLError as e:
        raise ManifestError(f"Failed to parse YAML front-matter in SKILL.md: {e}") from e

    if not isinstance(front_matter, dict):
        raise ManifestError("SKILL.md front-matter must be a YAML mapping.")

    # Validate required fields (only name and description are required)
    for field_name in ("name", "description"):
        if field_name not in front_matter or not front_matter[field_name]:
            raise ManifestError(f"SKILL.md is missing required field '{field_name}'.")

    name = str(front_matter["name"])
    description = str(front_matter["description"])

    # Version is optional, default to "1.0.0" if missing or empty
    version_raw = front_matter.get("version")
    if not version_raw:  # None, empty string, or missing
        version = "1.0.0"
        if ui:
            ui.warning(f"No version specified in SKILL.md for '{name}', assuming 1.0.0")
    else:
        version = str(version_raw)

    # Validate name format
    if not NAME_PATTERN.match(name):
        raise ManifestError(
            f"Invalid skill name '{name}'. Must be lowercase alphanumeric + hyphens, min 2 chars."
        )

    # Validate name matches directory
    if name != skill_dir.name:
        raise ManifestError(
            f"Skill name '{name}' in manifest does not match directory name '{skill_dir.name}'."
        )

    # Validate version format
    if not SEMVER_PATTERN.match(version):
        raise ManifestError(
            f"Invalid version '{version}' in SKILL.md. Expected format: MAJOR.MINOR.PATCH"
        )

    return SkillManifest(
        name=name,
        description=description,
        version=version,
        raw_content=raw_content,
    )


def was_version_missing(skill_path: Path) -> bool:
    """Check if SKILL.md originally lacked version field.

    Args:
        skill_path: Path to the skill directory containing SKILL.md.

    Returns:
        True if version field was missing or empty in the original SKILL.md.
    """
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False

    try:
        content = skill_md.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) < 3:
            return False

        front_matter_str = parts[1].strip()
        front_matter = yaml.safe_load(front_matter_str)

        if not isinstance(front_matter, dict):
            return False

        # Check if version is missing or empty
        return "version" not in front_matter or not front_matter.get("version")
    except Exception:
        return False


def update_manifest_with_version(skill_path: Path, version: str) -> None:
    """Add/update version field in SKILL.md YAML front-matter.

    This function preserves the order of existing fields and adds version
    in the appropriate position (after description if possible).

    Args:
        skill_path: Path to the skill directory containing SKILL.md.
        version: Version string to set (e.g., "1.0.0").

    Raises:
        ManifestError: If SKILL.md cannot be updated.
    """
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise ManifestError(f"SKILL.md not found in {skill_path}")

    try:
        content = skill_md.read_text(encoding="utf-8")
        parts = content.split("---", 2)

        if len(parts) < 3:
            raise ManifestError("Invalid SKILL.md format")

        front_matter_str = parts[1].strip()
        front_matter = yaml.safe_load(front_matter_str)

        if not isinstance(front_matter, dict):
            raise ManifestError("Invalid front-matter format")

        # Add/update version field
        front_matter["version"] = version

        # Rebuild YAML with preserved order: name, description, version
        ordered_keys = []
        if "name" in front_matter:
            ordered_keys.append("name")
        if "description" in front_matter:
            ordered_keys.append("description")
        if "version" in front_matter:
            ordered_keys.append("version")

        # Add any remaining keys
        for key in front_matter:
            if key not in ordered_keys:
                ordered_keys.append(key)

        # Build YAML string manually to preserve order
        yaml_lines = []
        for key in ordered_keys:
            value = front_matter[key]
            # Properly escape strings with special characters
            if isinstance(value, str) and ("\n" in value or ":" in value):
                yaml_lines.append(f"{key}: |")
                for line in value.split("\n"):
                    yaml_lines.append(f"  {line}")
            else:
                yaml_lines.append(f"{key}: {value}")

        new_front_matter = "\n".join(yaml_lines)
        new_content = f"---\n{new_front_matter}\n---{parts[2]}"

        skill_md.write_text(new_content, encoding="utf-8")
    except Exception as e:
        raise ManifestError(f"Failed to update SKILL.md: {e}") from e
