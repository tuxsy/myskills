"""Project context detection and validation (FR-012)."""

from __future__ import annotations

from pathlib import Path

from myskills.models import ProjectContext


class ProjectError(Exception):
    """Raised when project context is invalid."""


def detect_project_root(start_dir: Path | None = None) -> Path:
    """Detect the project root by walking up to find a Git repository root.

    Looks for .git directory starting from start_dir (or cwd) and walking up.

    Args:
        start_dir: Directory to start searching from. Defaults to cwd.

    Returns:
        The project root path.

    Raises:
        ProjectError: If no project root is found.
    """
    current = (start_dir or Path.cwd()).resolve()

    # Walk up looking for .git
    for directory in [current, *current.parents]:
        if (directory / ".git").exists():
            return directory

    raise ProjectError(
        "Not inside a project directory. Could not find a .git directory in any parent."
    )


def get_project_context(project_root: Path | None = None) -> ProjectContext:
    """Get the project context, validating the root directory.

    Args:
        project_root: Explicit project root. If None, auto-detect.

    Returns:
        ProjectContext for the validated project.

    Raises:
        ProjectError: If validation fails.
    """
    if project_root is None:
        root = detect_project_root()
    else:
        root = project_root.resolve()
        if not root.is_dir():
            raise ProjectError(f"Project root '{root}' is not a directory.")

    return ProjectContext(root=root)
