"""Tests for add skill logic (happy path, already installed, skill not found, repo unreachable) - T019."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from myskills.agents import SUPPORTED_AGENTS
from myskills.config import CONFIG_VERSION, read_config, write_config
from myskills.models import ProjectContext, SkillsRepository
from myskills.ui import FakeUI


# Helper to mock sync_repository for unit tests
def mock_sync_repository(repo, ui):
    """Mock sync that does nothing - assumes repo is already synced."""
    ui.verbose(f"Mock sync: {repo.url}")


@pytest.fixture
def mock_sync():
    """Fixture that patches sync_repository for all tests."""
    with patch("myskills.skill_ops.sync_repository", mock_sync_repository):
        yield


class TestInstallSkillHappyPath:
    """Test successful skill installation."""

    def test_install_new_skill_single_agent(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
        mock_sync,
    ) -> None:
        """Installing a new skill for a single agent creates primary dir + symlink."""
        # Arrange: Create a fake repository with a skill
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "test-skill"
        skill_dir_factory(skill_name, version="1.0.0", description="A test skill")
        (repo_dir / skill_name).mkdir()
        (repo_dir / skill_name / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: A test skill\nversion: 1.0.0\n---\n\nTest content",
            encoding="utf-8",
        )
        (repo_dir / skill_name / "instructions.md").write_text(
            "Test instructions", encoding="utf-8"
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Configure UI to select first agent (claude) and confirm installation
        fake_ui.set_multi_select_responses([0])  # Select first agent
        fake_ui.set_confirm_responses(True)  # Confirm installation

        # Act: Install the skill
        skill_ops.install_skill(
            skill_name=skill_name,
            project=project,
            repo=repo,
            ui=fake_ui,
        )

        # Assert: Primary directory created
        primary_dir = project.primary_skills_dir / skill_name
        assert primary_dir.exists()
        assert (primary_dir / "SKILL.md").exists()
        assert (primary_dir / "instructions.md").exists()

        # Assert: Symlink created for selected agent
        agent = SUPPORTED_AGENTS[0]
        symlink_path = tmp_project / agent.skills_dir / skill_name
        assert symlink_path.is_symlink()
        assert symlink_path.resolve() == primary_dir.resolve()

        # Assert: Config updated
        config = read_config(project.config_path)
        assert skill_name in config["installations"]
        assert config["installations"][skill_name]["version"] == "1.0.0"
        assert config["installations"][skill_name]["agents"] == [agent.id]

        # Assert: Success message displayed
        assert any(
            "success" in msg[0].lower() or "installed" in msg[1].lower()
            for msg in fake_ui.messages
        )

    def test_install_skill_multiple_agents(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
        mock_sync,
    ) -> None:
        """Installing a skill for multiple agents creates symlinks for each."""
        # Arrange
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "multi-agent-skill"
        (repo_dir / skill_name).mkdir()
        (repo_dir / skill_name / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Multi-agent skill\nversion: 2.0.0\n---\n",
            encoding="utf-8",
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Select first 3 agents (claude, cursor, copilot)
        fake_ui.set_multi_select_responses([0, 1, 2])
        fake_ui.set_confirm_responses(True)

        # Act
        skill_ops.install_skill(skill_name, project, repo, fake_ui)

        # Assert: Symlinks created for all 3 selected agents
        for idx in [0, 1, 2]:
            agent = SUPPORTED_AGENTS[idx]
            symlink = tmp_project / agent.skills_dir / skill_name
            assert symlink.is_symlink()

        # Assert: Config tracks all agents
        config = read_config(project.config_path)
        assert set(config["installations"][skill_name]["agents"]) == {
            "claude",
            "cursor",
            "copilot",
        }


class TestInstallSkillAlreadyInstalled:
    """Test handling of already-installed skills."""

    def test_skill_already_installed_abort(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
        mock_sync,
    ) -> None:
        """If skill is already installed, prompt for action; abort should exit cleanly."""
        # Arrange: Pre-install a skill
        from myskills import skill_ops

        skill_name = "existing-skill"
        project = ProjectContext(root=tmp_project)

        # Create primary directory
        primary_dir = project.primary_skills_dir / skill_name
        primary_dir.mkdir(parents=True)
        (primary_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Existing\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )

        # Create config entry
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {
                skill_name: {
                    "version": "1.0.0",
                    "agents": ["claude"],
                    "installed_at": "2026-03-31T10:00:00Z",
                }
            },
        }
        write_config(project.config_path, config)

        # Create fake repo
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        (repo_dir / skill_name).mkdir()
        (repo_dir / skill_name / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Existing\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )

        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # User chooses to abort (action index 2 = Abort)
        fake_ui.set_select_action_responses(2)

        # Act & Assert: Should raise
        with pytest.raises(skill_ops.SkillOperationError):
            skill_ops.install_skill(skill_name, project, repo, fake_ui)


class TestInstallSkillNotFound:
    """Test handling when skill doesn't exist in repository."""

    def test_skill_not_in_repository(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
        mock_sync,
    ) -> None:
        """Installing a nonexistent skill raises an error."""
        # Arrange: Empty repository
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Act & Assert
        with pytest.raises(skill_ops.SkillOperationError) as exc_info:
            skill_ops.install_skill("nonexistent-skill", project, repo, fake_ui)

        assert "not found" in str(exc_info.value).lower()


class TestInstallSkillRepoUnreachable:
    """Test handling when repository is unreachable."""

    def test_repo_not_cloned_and_unreachable(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """If repository is not cloned and git operations fail, raise GitError."""
        from myskills import skill_ops
        from myskills.git_ops import GitError

        project = ProjectContext(root=tmp_project)
        repo_cache = tmp_project / "nonexistent-repo"
        repo = SkillsRepository(url="git@github.com:org/unreachable.git", local_cache=repo_cache)

        # Mock sync to fail
        def mock_sync_fail(repo, ui):
            raise GitError("Repository unreachable")

        # Act & Assert
        with patch("myskills.skill_ops.sync_repository", mock_sync_fail):
            with pytest.raises(GitError) as exc_info:
                skill_ops.install_skill("any-skill", project, repo, fake_ui)

            assert "unreachable" in str(exc_info.value).lower()


class TestInstallSkillRollback:
    """Test that rollback works on partial failures."""

    def test_rollback_on_symlink_failure(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
        mock_sync,
    ) -> None:
        """If symlink creation fails, primary directory should be rolled back."""
        # Arrange
        from myskills import skill_ops
        from myskills.symlinks import SymlinkError

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "rollback-test"
        (repo_dir / skill_name).mkdir()
        (repo_dir / skill_name / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Test\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        fake_ui.set_multi_select_responses([0])
        fake_ui.set_confirm_responses(True)

        # Mock symlink creation to fail
        def mock_create_symlinks_fail(*args, **kwargs):
            raise SymlinkError("Simulated symlink failure")

        # Act & Assert: Installation should fail
        with (
            patch("myskills.skill_ops.create_skill_symlinks", mock_create_symlinks_fail),
            pytest.raises(skill_ops.SkillOperationError),
        ):
            skill_ops.install_skill(skill_name, project, repo, fake_ui)

        # Assert: Primary directory should NOT exist (rolled back)
        primary_dir = project.primary_skills_dir / skill_name
        assert not primary_dir.exists()

        # Assert: Config should not have the skill entry
        if project.config_path.exists():
            config = read_config(project.config_path)
            assert skill_name not in config.get("installations", {})
