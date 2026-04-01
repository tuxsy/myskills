"""Tests for remove skill logic (happy path, not installed, dangling symlinks, partial removal) - T028."""

from __future__ import annotations

from pathlib import Path

import pytest

from myskills.agents import SUPPORTED_AGENTS
from myskills.config import CONFIG_VERSION, read_config, write_config
from myskills.models import ProjectContext
from myskills.ui import FakeUI


class TestRemoveSkillHappyPath:
    """Test successful skill removal."""

    def test_remove_skill_single_agent(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """Removing a skill installed for one agent removes primary dir + symlink."""
        # Arrange: Install a skill manually
        from myskills import skill_ops

        skill_name = "test-skill"
        project = ProjectContext(root=tmp_project)

        # Create primary directory
        primary_dir = project.primary_skills_dir / skill_name
        primary_dir.mkdir(parents=True)
        (primary_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Test\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )
        (primary_dir / "instructions.md").write_text("Test content", encoding="utf-8")

        # Create symlink for first agent
        agent = SUPPORTED_AGENTS[0]
        symlink_dir = tmp_project / agent.skills_dir
        symlink_dir.mkdir(parents=True)
        symlink_path = symlink_dir / skill_name
        symlink_path.symlink_to(primary_dir)

        # Create config entry
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {
                skill_name: {
                    "version": "1.0.0",
                    "agents": [agent.id],
                    "installed_at": "2026-03-31T10:00:00Z",
                }
            },
        }
        write_config(project.config_path, config)

        # Configure UI to confirm removal
        fake_ui.set_confirm_responses(True)

        # Act: Remove the skill
        skill_ops.remove_skill(
            skill_name=skill_name,
            project=project,
            ui=fake_ui,
        )

        # Assert: Primary directory removed
        assert not primary_dir.exists()

        # Assert: Symlink removed
        assert not symlink_path.exists()

        # Assert: Config updated (skill entry removed)
        config = read_config(project.config_path)
        assert skill_name not in config.get("installations", {})

        # Assert: Success message displayed
        assert any(
            "removed" in msg[0].lower() or "success" in msg[0].lower() for msg in fake_ui.messages
        )

    def test_remove_skill_multiple_agents(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """Removing a skill installed for multiple agents removes all symlinks."""
        # Arrange: Install for 3 agents
        from myskills import skill_ops

        skill_name = "multi-agent-skill"
        project = ProjectContext(root=tmp_project)

        # Create primary directory
        primary_dir = project.primary_skills_dir / skill_name
        primary_dir.mkdir(parents=True)
        (primary_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Test\nversion: 2.0.0\n---\n",
            encoding="utf-8",
        )

        # Create symlinks for first 3 agents
        agent_ids = []
        for idx in [0, 1, 2]:
            agent = SUPPORTED_AGENTS[idx]
            agent_ids.append(agent.id)
            symlink_dir = tmp_project / agent.skills_dir
            symlink_dir.mkdir(parents=True)
            symlink_path = symlink_dir / skill_name
            symlink_path.symlink_to(primary_dir)

        # Create config entry
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {
                skill_name: {
                    "version": "2.0.0",
                    "agents": agent_ids,
                    "installed_at": "2026-03-31T11:00:00Z",
                }
            },
        }
        write_config(project.config_path, config)

        fake_ui.set_confirm_responses(True)

        # Act
        skill_ops.remove_skill(skill_name, project, fake_ui)

        # Assert: All symlinks removed
        for idx in [0, 1, 2]:
            agent = SUPPORTED_AGENTS[idx]
            symlink = tmp_project / agent.skills_dir / skill_name
            assert not symlink.exists()

        # Assert: Primary directory removed
        assert not primary_dir.exists()

        # Assert: Config updated
        config = read_config(project.config_path)
        assert skill_name not in config.get("installations", {})


class TestRemoveSkillNotInstalled:
    """Test handling when skill is not installed."""

    def test_skill_not_installed(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """Removing a skill that is not installed raises an error."""
        # Arrange: Empty project
        from myskills import skill_ops

        project = ProjectContext(root=tmp_project)

        # Act & Assert
        with pytest.raises(skill_ops.SkillOperationError) as exc_info:
            skill_ops.remove_skill("nonexistent-skill", project, fake_ui)

        assert "not installed" in str(exc_info.value).lower()


class TestRemoveSkillDanglingSymlinks:
    """Test handling of dangling symlinks (primary dir manually deleted)."""

    def test_remove_skill_with_dangling_symlinks(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """If primary directory is gone but symlinks remain, remove should clean up symlinks."""
        # Arrange: Create config and symlinks but NO primary directory
        from myskills import skill_ops

        skill_name = "dangling-skill"
        project = ProjectContext(root=tmp_project)

        # Create symlinks without primary directory (dangling)
        agent = SUPPORTED_AGENTS[0]
        symlink_dir = tmp_project / agent.skills_dir
        symlink_dir.mkdir(parents=True)
        symlink_path = symlink_dir / skill_name

        # Create a fake target that we'll delete to make it dangling
        fake_target = tmp_project / ".agents" / "skills" / skill_name
        fake_target.mkdir(parents=True)
        symlink_path.symlink_to(fake_target)

        # Now delete the target to make it dangling
        import shutil

        shutil.rmtree(fake_target)

        # Create config entry
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {
                skill_name: {
                    "version": "1.0.0",
                    "agents": [agent.id],
                    "installed_at": "2026-03-31T10:00:00Z",
                }
            },
        }
        write_config(project.config_path, config)

        fake_ui.set_confirm_responses(True)

        # Act: Remove should clean up dangling symlinks
        skill_ops.remove_skill(skill_name, project, fake_ui)

        # Assert: Symlink removed even though primary was already gone
        assert not symlink_path.exists()

        # Assert: Config updated
        config = read_config(project.config_path)
        assert skill_name not in config.get("installations", {})


class TestRemoveSkillUserCancellation:
    """Test handling when user cancels removal."""

    def test_user_cancels_removal(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """If user declines confirmation, removal is aborted and nothing is changed."""
        # Arrange
        from myskills import skill_ops

        skill_name = "cancel-test"
        project = ProjectContext(root=tmp_project)

        # Create primary directory
        primary_dir = project.primary_skills_dir / skill_name
        primary_dir.mkdir(parents=True)
        (primary_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Test\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )

        # Create symlink
        agent = SUPPORTED_AGENTS[0]
        symlink_dir = tmp_project / agent.skills_dir
        symlink_dir.mkdir(parents=True)
        symlink_path = symlink_dir / skill_name
        symlink_path.symlink_to(primary_dir)

        # Create config entry
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {
                skill_name: {
                    "version": "1.0.0",
                    "agents": [agent.id],
                    "installed_at": "2026-03-31T10:00:00Z",
                }
            },
        }
        write_config(project.config_path, config)

        # User declines confirmation
        fake_ui.set_confirm_responses(False)

        # Act & Assert: Should raise
        with pytest.raises(skill_ops.SkillOperationError) as exc_info:
            skill_ops.remove_skill(skill_name, project, fake_ui)

        assert "cancel" in str(exc_info.value).lower()

        # Assert: Nothing was changed
        assert primary_dir.exists()
        assert symlink_path.exists()
        config = read_config(project.config_path)
        assert skill_name in config["installations"]
