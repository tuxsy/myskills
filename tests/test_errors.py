"""Comprehensive error handling tests (permission errors, network failures, disk full, corrupted config) - T043."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from myskills.config import ConfigError, read_config, write_config
from myskills.git_ops import GitError
from myskills.manifest import ManifestError, parse_manifest
from myskills.models import ProjectContext, SkillsRepository
from myskills.skill_ops import (
    SkillOperationError,
    install_skill,
    sync_repository,
)
from myskills.symlinks import SymlinkError, create_symlink, remove_symlink
from myskills.ui import FakeUI


class TestPermissionErrors:
    """Test scenarios where permission errors prevent operations."""

    def test_cannot_write_to_primary_skills_dir(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
    ) -> None:
        """Installing a skill fails gracefully if primary skills dir is read-only."""
        # Arrange: Create repo with a skill
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "test-skill"
        skill_src = skill_dir_factory(skill_name)
        skill_dst = repo_dir / skill_name
        shutil.copytree(skill_src, skill_dst)

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Create primary skills dir and make it read-only
        project.primary_skills_dir.mkdir(parents=True)
        os.chmod(project.primary_skills_dir, 0o444)  # Read-only

        # Configure UI
        fake_ui.set_multi_select_responses([0])  # Select first agent
        fake_ui.set_confirm_responses(True)  # Confirm installation

        # Mock sync to avoid git operations
        with patch("myskills.skill_ops.sync_repository"):
            # Act & Assert: Should raise SkillOperationError with permission message
            with pytest.raises((SkillOperationError, PermissionError, OSError)):
                install_skill(
                    skill_name=skill_name,
                    project=project,
                    repo=repo,
                    ui=fake_ui,
                )

        # Cleanup: Restore permissions
        os.chmod(project.primary_skills_dir, 0o755)

    def test_cannot_create_symlink_in_agent_dir(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """Creating a symlink fails gracefully if agent dir is read-only."""
        # Arrange: Create primary skill directory
        primary_dir = tmp_project / ".agents" / "skills" / "test-skill"
        primary_dir.mkdir(parents=True)
        (primary_dir / "SKILL.md").write_text("---\nname: test-skill\n---\n")

        # Create agent dir and make it read-only
        agent_dir = tmp_project / ".claude" / "skills"
        agent_dir.mkdir(parents=True)
        os.chmod(agent_dir, 0o444)  # Read-only

        symlink_path = agent_dir / "test-skill"

        # Act & Assert: Should raise PermissionError or OSError
        with pytest.raises((PermissionError, OSError)):
            create_symlink(target=primary_dir, link_path=symlink_path)

        # Cleanup: Restore permissions
        os.chmod(agent_dir, 0o755)

    def test_cannot_write_config_file(
        self,
        tmp_project: Path,
    ) -> None:
        """Writing config fails gracefully if directory is read-only."""
        # Arrange: Create config directory and make it read-only
        config_dir = tmp_project / ".agents" / "skills"
        config_dir.mkdir(parents=True)
        config_path = config_dir / ".myskills.json"

        # Write initial config
        write_config(
            config_path,
            {
                "version": "1.0",
                "repository": "git@github.com:org/repo.git",
                "installations": {},
            },
        )

        # Make directory read-only
        os.chmod(config_dir, 0o444)

        # Act & Assert: Should raise ConfigError or PermissionError
        with pytest.raises((ConfigError, PermissionError, OSError)):
            write_config(
                config_path,
                {
                    "version": "1.0",
                    "repository": "git@github.com:org/repo.git",
                    "installations": {},
                },
            )

        # Cleanup: Restore permissions
        os.chmod(config_dir, 0o755)


class TestNetworkErrors:
    """Test scenarios where network/repository operations fail."""

    def test_repository_clone_fails(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """sync_repository raises GitError when clone fails."""
        # Arrange: Invalid repository URL
        repo = SkillsRepository(
            url="git@invalid-host:nonexistent/repo.git",
            local_cache=tmp_project / ".cache" / "repo",
        )

        # Act & Assert: Should raise GitError
        with pytest.raises(GitError):
            sync_repository(repo, fake_ui)

    def test_repository_pull_fails(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """sync_repository raises GitError when pull fails."""
        # Arrange: Create a "cloned" repo directory (fake .git)
        repo_dir = tmp_project / ".cache" / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / ".git").mkdir()

        repo = SkillsRepository(
            url="git@invalid-host:nonexistent/repo.git",
            local_cache=repo_dir,
        )

        # Act & Assert: Should raise GitError when pull fails
        with pytest.raises(GitError):
            sync_repository(repo, fake_ui)

    def test_install_handles_repo_sync_error(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """install_skill surfaces GitError from sync_repository."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(
            url="git@invalid:repo.git",
            local_cache=tmp_project / ".cache" / "repo",
        )

        # Act & Assert: Should raise GitError from sync attempt
        with pytest.raises(GitError):
            install_skill(
                skill_name="test-skill",
                project=project,
                repo=repo,
                ui=fake_ui,
            )


class TestCorruptedConfig:
    """Test scenarios where config files are corrupted or invalid."""

    def test_read_config_with_invalid_json(
        self,
        tmp_project: Path,
    ) -> None:
        """read_config raises ConfigError for invalid JSON."""
        # Arrange: Write invalid JSON
        config_path = tmp_project / ".agents" / "skills" / ".myskills.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("{invalid json", encoding="utf-8")

        # Act & Assert: Should raise ConfigError
        with pytest.raises(ConfigError) as exc_info:
            read_config(config_path)

        assert "Failed to read" in str(exc_info.value) or "parse" in str(exc_info.value).lower()

    def test_read_config_with_missing_version(
        self,
        tmp_project: Path,
    ) -> None:
        """read_config raises ConfigError if version field is missing."""
        # Arrange: Write config without version
        config_path = tmp_project / ".agents" / "skills" / ".myskills.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            json.dumps({"repository": "git@github.com:org/repo.git", "installations": {}}),
            encoding="utf-8",
        )

        # Act & Assert: Should raise ConfigError
        with pytest.raises(ConfigError) as exc_info:
            read_config(config_path)

        assert "version" in str(exc_info.value).lower()

    def test_read_config_with_wrong_version(
        self,
        tmp_project: Path,
    ) -> None:
        """read_config raises ConfigError for unsupported schema version."""
        # Arrange: Write config with unsupported version
        config_path = tmp_project / ".agents" / "skills" / ".myskills.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            json.dumps(
                {
                    "version": 999,
                    "repository": "git@github.com:org/repo.git",
                    "installations": {},
                }
            ),
            encoding="utf-8",
        )

        # Act & Assert: Should raise ConfigError
        with pytest.raises(ConfigError) as exc_info:
            read_config(config_path)

        assert (
            "version" in str(exc_info.value).lower()
            or "unsupported" in str(exc_info.value).lower()
        )


class TestManifestErrors:
    """Test scenarios where SKILL.md manifests are invalid."""

    def test_parse_manifest_missing_file(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """parse_manifest raises ManifestError if SKILL.md is missing."""
        # Arrange: Empty skill directory
        skill_dir = tmp_project / "test-skill"
        skill_dir.mkdir()

        # Act & Assert: Should raise ManifestError
        with pytest.raises(ManifestError) as exc_info:
            parse_manifest(skill_dir, ui=fake_ui)

        assert "SKILL.md" in str(exc_info.value)

    def test_parse_manifest_invalid_yaml(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """parse_manifest raises ManifestError for invalid YAML."""
        # Arrange: Create SKILL.md with invalid YAML
        skill_dir = tmp_project / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: [\ninvalid\n---\n",
            encoding="utf-8",
        )

        # Act & Assert: Should raise ManifestError
        with pytest.raises(ManifestError) as exc_info:
            parse_manifest(skill_dir, ui=fake_ui)

        assert "parse" in str(exc_info.value).lower()

    def test_parse_manifest_missing_required_field(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """parse_manifest raises ManifestError if required field is missing."""
        # Arrange: Create SKILL.md without description
        skill_dir = tmp_project / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )

        # Act & Assert: Should raise ManifestError
        with pytest.raises(ManifestError) as exc_info:
            parse_manifest(skill_dir, ui=fake_ui)

        assert "description" in str(exc_info.value).lower()

    def test_parse_manifest_name_mismatch(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """parse_manifest raises ManifestError if name doesn't match directory."""
        # Arrange: Create SKILL.md with mismatched name
        skill_dir = tmp_project / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: different-name\ndescription: Test\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )

        # Act & Assert: Should raise ManifestError
        with pytest.raises(ManifestError) as exc_info:
            parse_manifest(skill_dir, ui=fake_ui)

        assert "does not match" in str(exc_info.value).lower()


class TestSymlinkErrors:
    """Test scenarios where symlink operations fail."""

    def test_remove_nonexistent_symlink(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """remove_symlink raises SymlinkError if symlink doesn't exist."""
        # Arrange
        link_path = tmp_project / ".claude" / "skills" / "nonexistent"

        # Act & Assert: Should raise SymlinkError
        with pytest.raises(SymlinkError):
            remove_symlink(link_path=link_path)

    def test_create_symlink_target_does_not_exist(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """create_symlink creates dangling symlink if target doesn't exist."""
        # Arrange
        target = tmp_project / "nonexistent-target"
        link = tmp_project / ".claude" / "skills" / "test-skill"
        link.parent.mkdir(parents=True)

        # Act: Should create dangling symlink
        create_symlink(target=target, link_path=link)

        # Assert: Symlink created but is dangling
        assert link.is_symlink()
        assert not link.exists()  # Target doesn't exist


class TestFilesystemErrors:
    """Test scenarios where filesystem operations fail."""

    def test_copy_skill_with_disk_full_simulation(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
    ) -> None:
        """Simulate disk full by mocking shutil.copytree to raise OSError."""
        # Arrange: Create repo with a skill
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "test-skill"
        skill_src = skill_dir_factory(skill_name)
        import shutil

        skill_dst = repo_dir / skill_name
        shutil.copytree(skill_src, skill_dst)

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Configure UI
        fake_ui.set_multi_select_responses([0])  # Select first agent
        fake_ui.set_confirm_responses(True)  # Confirm installation

        # Mock sync and copytree
        with patch("myskills.skill_ops.sync_repository"):
            with patch("shutil.copytree", side_effect=OSError("No space left on device")):
                # Act & Assert: Should raise SkillOperationError wrapping OSError
                with pytest.raises(SkillOperationError) as exc_info:
                    install_skill(
                        skill_name=skill_name,
                        project=project,
                        repo=repo,
                        ui=fake_ui,
                    )

                assert "space" in str(exc_info.value).lower()

    def test_project_root_does_not_exist(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """Operations fail if project root doesn't exist."""
        # Arrange: Non-existent project root
        nonexistent = tmp_project / "nonexistent-project"
        project = ProjectContext(root=nonexistent)
        repo = SkillsRepository(
            url="git@github.com:org/repo.git",
            local_cache=tmp_project / "repo",
        )

        # Act & Assert: Should raise SkillOperationError
        with patch("myskills.skill_ops.sync_repository"):
            with pytest.raises(SkillOperationError) as exc_info:
                install_skill(
                    skill_name="test-skill",
                    project=project,
                    repo=repo,
                    ui=fake_ui,
                )

            assert (
                "not found" in str(exc_info.value).lower()
                or "does not exist" in str(exc_info.value).lower()
            )


class TestInterruptionHandling:
    """Test scenarios where operations are interrupted (Ctrl+C, cancellation)."""

    def test_user_cancels_installation(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
    ) -> None:
        """User declining confirmation prevents installation."""
        # Arrange: Create repo with a skill
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "test-skill"
        skill_src = skill_dir_factory(skill_name)
        import shutil

        skill_dst = repo_dir / skill_name
        shutil.copytree(skill_src, skill_dst)

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Configure UI to decline confirmation
        fake_ui.set_multi_select_responses([0])  # Select first agent
        fake_ui.set_confirm_responses(False)  # Decline confirmation

        # Mock sync to avoid git operations
        with patch("myskills.skill_ops.sync_repository"):
            # Act: Should raise SkillOperationError with cancellation message
            with pytest.raises(SkillOperationError) as exc_info:
                install_skill(
                    skill_name=skill_name,
                    project=project,
                    repo=repo,
                    ui=fake_ui,
                )

            assert (
                "cancelled" in str(exc_info.value).lower()
                or "aborted" in str(exc_info.value).lower()
            )

        # Assert: Nothing was installed
        assert not (project.primary_skills_dir / skill_name).exists()

    def test_keyboard_interrupt_during_installation(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
    ) -> None:
        """KeyboardInterrupt during installation is handled gracefully."""
        # Arrange: Create repo with a skill
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "test-skill"
        skill_src = skill_dir_factory(skill_name)
        import shutil

        skill_dst = repo_dir / skill_name
        shutil.copytree(skill_src, skill_dst)

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Configure UI
        fake_ui.set_multi_select_responses([0])  # Select first agent
        fake_ui.set_confirm_responses(True)  # Confirm installation

        # Mock sync and copytree to raise KeyboardInterrupt
        with patch("myskills.skill_ops.sync_repository"):
            with patch("shutil.copytree", side_effect=KeyboardInterrupt):
                # Act & Assert: KeyboardInterrupt should propagate
                with pytest.raises(KeyboardInterrupt):
                    install_skill(
                        skill_name=skill_name,
                        project=project,
                        repo=repo,
                        ui=fake_ui,
                    )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_repository(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """get_skill_from_repo raises error for empty repository."""
        from myskills.skill_ops import get_skill_from_repo

        # Arrange: Empty repository
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Act & Assert: Should raise SkillOperationError
        with pytest.raises(SkillOperationError) as exc_info:
            get_skill_from_repo("nonexistent-skill", repo)

        assert "not found" in str(exc_info.value).lower()

    def test_skill_directory_is_file_not_directory(
        self,
        tmp_project: Path,
        fake_ui: FakeUI,
    ) -> None:
        """Operations fail if skill path is a file, not a directory."""
        from myskills.skill_ops import get_skill_from_repo

        # Arrange: Create a file instead of a directory
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        (repo_dir / "test-skill").write_text("not a directory")

        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Act & Assert: Should raise appropriate error
        with pytest.raises((SkillOperationError, ManifestError)):
            get_skill_from_repo("test-skill", repo)
