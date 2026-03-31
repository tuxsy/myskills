"""SKILL.md YAML front-matter parser and validator (R-007, config-contract.md)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from myskills.models import SkillManifest

# Skill name: lowercase alphanumeric + hyphens, min 2 chars
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

# Semantic version: MAJOR.MINOR.PATCH
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


class ManifestError(Exception):
    """Raised when manifest parsing or validation fails."""


def parse_manifest(skill_dir: Path) -> SkillManifest:
    """Parse and validate SKILL.md from a skill directory.

    Args:
        skill_dir: Path to the skill directory containing SKILL.md.

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

    # Validate required fields
    for field_name in ("name", "description", "version"):
        if field_name not in front_matter or not front_matter[field_name]:
            raise ManifestError(f"SKILL.md is missing required field '{field_name}'.")

    name = str(front_matter["name"])
    description = str(front_matter["description"])
    version = str(front_matter["version"])

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
