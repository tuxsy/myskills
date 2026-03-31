"""Tests for list skill logic (T024)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from myskills.config import write_config
from myskills.git_ops import GitError
from myskills.models import ProjectContext, SkillsRepository
from myskills.skill_ops import list_skills
from myskills.ui import FakeUI


def test_list_skills_with_available_skills(
    tmp_project: Path,
    tmp_path: Path,
    fake_ui: FakeUI,
    fake_git_repo,
):
    """List should show all repository skills with correct metadata."""
    # Create a fake repository with multiple skills
    repo_path = fake_git_repo(skills=["skill-a", "skill-b", "skill-c"])

    # Add more details to one skill
    (repo_path / "skill-a" / "instructions.md").write_text("Detailed instructions")

    project = ProjectContext(root=tmp_project)
    repo = SkillsRepository(url="git@github.com:test/repo.git", local_cache=repo_path)

    # Mock that the repo is already cloned
    assert repo.is_cloned

    # Mock sync_repository to avoid actual git operations
    with patch("myskills.skill_ops.sync_repository"):
        result = list_skills(project, repo, fake_ui)

    assert len(result) == 3
    assert result[0]["name"] == "skill-a"
    assert result[0]["description"] == "A test skill named skill-a"
    assert result[0]["version"] == "1.0.0"
    assert result[0]["installed"] is False

    assert result[1]["name"] == "skill-b"
    assert result[2]["name"] == "skill-c"


def test_list_skills_with_some_installed(
    tmp_project: Path,
    fake_ui: FakeUI,
    fake_git_repo,
):
    """List should mark installed skills correctly."""
    # Create a fake repository
    repo_path = fake_git_repo(skills=["skill-a", "skill-b", "skill-c"])

    project = ProjectContext(root=tmp_project)
    repo = SkillsRepository(url="git@github.com:test/repo.git", local_cache=repo_path)

    # Mark skill-a and skill-c as installed in config
    config = {
        "version": 1,
        "repository": repo.url,
        "installations": {
            "skill-a": {
                "version": "1.0.0",
                "agents": ["claude"],
                "installed_at": "2026-03-31T10:00:00Z",
            },
            "skill-c": {
                "version": "1.0.0",
                "agents": ["cursor", "copilot"],
                "installed_at": "2026-03-31T11:00:00Z",
            },
        },
    }

    project.primary_skills_dir.mkdir(parents=True, exist_ok=True)
    write_config(project.config_path, config)

    # Mock sync_repository to avoid actual git operations
    with patch("myskills.skill_ops.sync_repository"):
        result = list_skills(project, repo, fake_ui)

    assert len(result) == 3
    assert result[0]["name"] == "skill-a"
    assert result[0]["installed"] is True

    assert result[1]["name"] == "skill-b"
    assert result[1]["installed"] is False

    assert result[2]["name"] == "skill-c"
    assert result[2]["installed"] is True


def test_list_skills_empty_repo(
    tmp_project: Path,
    tmp_path: Path,
    fake_ui: FakeUI,
):
    """List should handle empty repository gracefully."""
    # Create empty repository
    repo_path = tmp_path / "empty-repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    project = ProjectContext(root=tmp_project)
    repo = SkillsRepository(url="git@github.com:test/repo.git", local_cache=repo_path)

    # Mock sync_repository to avoid actual git operations
    with patch("myskills.skill_ops.sync_repository"):
        result = list_skills(project, repo, fake_ui)

    assert len(result) == 0


def test_list_skills_repo_unreachable(
    tmp_project: Path,
    tmp_path: Path,
    fake_ui: FakeUI,
    monkeypatch,
):
    """List should raise GitError when repository sync fails."""
    from myskills import skill_ops

    # Mock sync_repository to raise GitError
    def mock_sync_error(repo, ui):
        raise GitError("Network error: could not reach repository")

    monkeypatch.setattr(skill_ops, "sync_repository", mock_sync_error)

    project = ProjectContext(root=tmp_project)
    repo = SkillsRepository(
        url="git@github.com:test/repo.git",
        local_cache=tmp_path / "nonexistent",
    )

    with pytest.raises(GitError, match="Network error"):
        list_skills(project, repo, fake_ui)


def test_list_skills_with_invalid_manifest(
    tmp_project: Path,
    tmp_path: Path,
    fake_ui: FakeUI,
):
    """List should skip skills with invalid manifests and log warning."""
    # Create repository with one valid and one invalid skill
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()

    # Valid skill
    skill_a = repo_path / "skill-a"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text(
        "---\nname: skill-a\ndescription: Valid skill\nversion: 1.0.0\n---\n"
    )

    # Invalid skill (missing required fields)
    skill_b = repo_path / "skill-b"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text("---\nname: skill-b\n---\n")

    project = ProjectContext(root=tmp_project)
    repo = SkillsRepository(url="git@github.com:test/repo.git", local_cache=repo_path)

    # Mock sync_repository to avoid actual git operations
    with patch("myskills.skill_ops.sync_repository"):
        result = list_skills(project, repo, fake_ui)

    # Only valid skill should be returned
    assert len(result) == 1
    assert result[0]["name"] == "skill-a"

    # UI should have logged a warning about invalid skill
    # FakeUI stores messages as (level, message) tuples
    warning_msgs = [msg for level, msg in fake_ui.messages if "skill-b" in msg.lower()]
    assert len(warning_msgs) > 0, (
        f"Expected warning about skill-b, got messages: {fake_ui.messages}"
    )


def test_list_skills_sorted_by_name(
    tmp_project: Path,
    fake_ui: FakeUI,
    fake_git_repo,
):
    """List should return skills sorted alphabetically by name."""
    # Create repository with skills in random order
    repo_path = fake_git_repo(skills=["zebra", "alpha", "middle"])

    project = ProjectContext(root=tmp_project)
    repo = SkillsRepository(url="git@github.com:test/repo.git", local_cache=repo_path)

    # Mock sync_repository to avoid actual git operations
    with patch("myskills.skill_ops.sync_repository"):
        result = list_skills(project, repo, fake_ui)

    assert len(result) == 3
    assert result[0]["name"] == "alpha"
    assert result[1]["name"] == "middle"
    assert result[2]["name"] == "zebra"
