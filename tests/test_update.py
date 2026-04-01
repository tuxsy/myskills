"""Unit tests for update logic (T033).

These tests exercise the update_skills function behavior in-memory by
creating a fake repo layout and project config.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from myskills.config import CONFIG_VERSION, write_config
from myskills.models import ProjectContext, SkillsRepository
from myskills.skill_ops import update_skills


def test_update_no_repo(tmp_project: Path, tmp_path: Path):
    """If the repo is unreachable, update_skills should raise GitError (propagated).

    We simulate by pointing repo to a non-existent path; the sync_repository will
    raise GitError via pull/clone. Here we assert that an exception is raised.
    """
    project = ProjectContext(root=tmp_project)
    config = {
        "version": CONFIG_VERSION,
        "repository": str(tmp_path / "missing-repo"),
        "installations": {},
    }
    write_config(project.config_path, config)

    repo = SkillsRepository(url=config["repository"], local_cache=Path(config["repository"]))
    from myskills.git_ops import GitError

    with pytest.raises(GitError):
        update_skills(
            project=project,
            repo=repo,
            ui=type(
                "U",
                (),
                {
                    "verbose": lambda *_: None,
                    "verbose_mode": False,
                    "info": lambda *_: None,
                    "warning": lambda *_: None,
                    "error": lambda *_: None,
                    "success": lambda *_: None,
                },
            )(),
        )


def test_update_skips_current_versions(tmp_project: Path):
    """If installed version equals repo version, skill is reported current."""
    # Setup a fake repo with a skill
    repo_dir = tmp_project / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    skill_name = "skill-update"
    skill_dir = repo_dir / skill_name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: skill-update\ndescription: s\nversion: 1.0.0\n---\n", encoding="utf-8"
    )

    project = ProjectContext(root=tmp_project)
    config = {
        "version": CONFIG_VERSION,
        "repository": str(repo_dir),
        "installations": {skill_name: {"version": "1.0.0", "agents": []}},
    }
    write_config(project.config_path, config)

    repo = SkillsRepository(url=str(repo_dir), local_cache=repo_dir)

    class DummyUI:
        verbose_mode = False

        def verbose(self, *a, **k):
            pass

        def info(self, *a, **k):
            pass

        def warning(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

        def success(self, *a, **k):
            pass

    # Patch out repository syncing to avoid invoking real git in tests
    from unittest.mock import patch

    with patch("myskills.skill_ops.sync_repository", lambda *_: None):
        summary = update_skills(project=project, repo=repo, ui=DummyUI())
    assert "current" in summary and skill_name in summary["current"]


def test_update_with_existing_symlinks(tmp_project: Path):
    """Update should handle existing symlinks gracefully (replace them if needed).

    This test reproduces the scenario where symlinks already exist and update
    needs to recreate them. The idempotent create_symlink should handle this.
    """
    # Setup a fake repo with a skill at version 1.0.0
    repo_dir = tmp_project / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    skill_name = "skill-update-symlinks"
    skill_dir = repo_dir / skill_name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: skill-update-symlinks\ndescription: test\nversion: 1.0.0\n---\nOld content",
        encoding="utf-8",
    )

    # Setup project with installed skill at 1.0.0
    project = ProjectContext(root=tmp_project)
    primary_dir = project.primary_skills_dir / skill_name
    primary_dir.mkdir(parents=True)
    (primary_dir / "SKILL.md").write_text(
        "---\nname: skill-update-symlinks\ndescription: test\nversion: 1.0.0\n---\nOld content",
        encoding="utf-8",
    )

    # Create existing symlinks for claude agent
    from myskills.agents import SUPPORTED_AGENTS

    claude_agent = next(a for a in SUPPORTED_AGENTS if a.id == "claude")
    symlink_path = project.root / claude_agent.skills_dir / skill_name
    symlink_path.parent.mkdir(parents=True, exist_ok=True)
    symlink_path.symlink_to(primary_dir)

    config = {
        "version": CONFIG_VERSION,
        "repository": str(repo_dir),
        "installations": {skill_name: {"version": "1.0.0", "agents": ["claude"]}},
    }
    write_config(project.config_path, config)

    # Update repo to version 2.0.0
    (skill_dir / "SKILL.md").write_text(
        "---\nname: skill-update-symlinks\ndescription: test\nversion: 2.0.0\n---\nNew content",
        encoding="utf-8",
    )

    repo = SkillsRepository(url=str(repo_dir), local_cache=repo_dir)

    class DummyUI:
        verbose_mode = False

        def verbose(self, *a, **k):
            pass

        def info(self, *a, **k):
            pass

        def warning(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

        def success(self, *a, **k):
            pass

    # Execute update with existing symlinks
    with patch("myskills.skill_ops.sync_repository", lambda *_: None):
        summary = update_skills(project=project, repo=repo, ui=DummyUI())

    # Should successfully update without errors
    assert skill_name in summary["updated"]
    assert (primary_dir / "SKILL.md").read_text().endswith("New content")
    # Symlink should still exist and point to updated primary
    assert symlink_path.is_symlink()
    assert symlink_path.resolve() == primary_dir.resolve()
