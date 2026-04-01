"""Tests for project module."""

from pathlib import Path

import pytest

from myskills.project import ProjectError, get_project_context


def test_get_project_context_with_explicit_root(tmp_path: Path):
    """Test get_project_context with explicitly provided project_root."""
    project = tmp_path / "myproject"
    project.mkdir()

    result = get_project_context(project_root=project)

    assert result.root == project.resolve()


def test_get_project_context_with_nonexistent_root(tmp_path: Path):
    """Test get_project_context raises error when explicit root doesn't exist."""
    nonexistent = tmp_path / "nonexistent"

    with pytest.raises(ProjectError, match="not a directory"):
        get_project_context(project_root=nonexistent)


def test_get_project_context_with_file_as_root(tmp_path: Path):
    """Test get_project_context raises error when explicit root is a file."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("test")

    with pytest.raises(ProjectError, match="not a directory"):
        get_project_context(project_root=file_path)
