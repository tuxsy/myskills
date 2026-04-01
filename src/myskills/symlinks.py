"""Symlink creation, removal, and dangling symlink detection (FR-004, FR-006, FR-013)."""

from __future__ import annotations

import os
from pathlib import Path


class SymlinkError(Exception):
    """Raised when symlink operations fail."""


def create_symlink(target: Path, link_path: Path) -> None:
    """Create a symbolic link pointing to target (idempotent).

    If a symlink already exists at link_path:
    - If it points to the same target: no-op (idempotent)
    - If it points elsewhere or is dangling: replace it

    Args:
        target: The directory the symlink should point to (primary skill dir).
        link_path: Where to create the symlink.

    Raises:
        SymlinkError: If symlink creation fails or a non-symlink file/dir exists at link_path.
    """
    # Ensure parent directory exists
    link_path.parent.mkdir(parents=True, exist_ok=True)

    # If an existing symlink is present
    if link_path.is_symlink():
        # Compare resolved targets without raising for dangling symlinks
        existing = link_path.resolve(strict=False)
        desired = target.resolve(strict=False)
        if existing == desired:
            # Already correct, nothing to do
            return
        # Remove existing symlink (either pointing elsewhere or dangling)
        try:
            link_path.unlink()
        except OSError as e:
            raise SymlinkError(f"Failed to remove existing symlink '{link_path}': {e}") from e

    # If a real file/dir exists at link_path, error (don't overwrite)
    if link_path.exists():
        raise SymlinkError(f"Link path already exists and is not a symlink: '{link_path}'.")

    try:
        # Use relative path for portability
        rel_target = os.path.relpath(target, link_path.parent)
        link_path.symlink_to(rel_target)
    except OSError as e:
        raise SymlinkError(f"Failed to create symlink '{link_path}' -> '{target}': {e}") from e


def remove_symlink(link_path: Path) -> None:
    """Remove a symbolic link.

    Args:
        link_path: Path to the symlink to remove.

    Raises:
        SymlinkError: If removal fails or path is not a symlink.
    """
    if not link_path.is_symlink():
        raise SymlinkError(f"Path is not a symlink: '{link_path}'.")

    try:
        link_path.unlink()
    except OSError as e:
        raise SymlinkError(f"Failed to remove symlink '{link_path}': {e}") from e


def is_dangling(link_path: Path) -> bool:
    """Check if a symlink is dangling (target does not exist).

    Args:
        link_path: Path to check.

    Returns:
        True if the path is a symlink whose target doesn't exist.
    """
    return link_path.is_symlink() and not link_path.exists()


def find_dangling_symlinks(directory: Path) -> list[Path]:
    """Find all dangling symlinks in a directory tree.

    Args:
        directory: Root directory to search.

    Returns:
        List of paths to dangling symlinks.
    """
    dangling: list[Path] = []

    if not directory.exists():
        return dangling

    for entry in directory.rglob("*"):
        if is_dangling(entry):
            dangling.append(entry)

    return sorted(dangling)


def create_skill_symlinks(
    primary_dir: Path,
    project_root: Path,
    agent_skills_dirs: list[str],
    skill_name: str,
) -> list[Path]:
    """Create symlinks for a skill in multiple agent directories.

    Args:
        primary_dir: Primary skill directory (.agents/skills/<name>).
        project_root: Project root directory.
        agent_skills_dirs: List of relative agent skill dirs (e.g., ".claude/skills").
        skill_name: Name of the skill.

    Returns:
        List of created symlink paths.

    Raises:
        SymlinkError: If any symlink creation fails.
    """
    created: list[Path] = []

    for agent_dir in agent_skills_dirs:
        link_path = project_root / agent_dir / skill_name
        create_symlink(primary_dir, link_path)
        created.append(link_path)

    return created


def remove_skill_symlinks(
    project_root: Path,
    agent_skills_dirs: list[str],
    skill_name: str,
) -> list[Path]:
    """Remove symlinks for a skill from agent directories.

    Args:
        project_root: Project root directory.
        agent_skills_dirs: List of relative agent skill dirs.
        skill_name: Name of the skill.

    Returns:
        List of removed symlink paths.
    """
    removed: list[Path] = []

    for agent_dir in agent_skills_dirs:
        link_path = project_root / agent_dir / skill_name
        if link_path.is_symlink():
            remove_symlink(link_path)
            removed.append(link_path)

    return removed
