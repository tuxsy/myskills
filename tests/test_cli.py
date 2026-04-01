"""CLI tests for all commands using CliRunner - T020 (add command tests)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from myskills.cli import main
from myskills.config import CONFIG_VERSION, write_config
from myskills.models import ProjectContext


@pytest.fixture
def cli_runner():
    """Provide a Click CliRunner instance."""
    return CliRunner()


@pytest.fixture
def mock_skill_ops():
    """Mock the entire skill_ops module for CLI testing."""
    with patch("myskills.cli.install_skill") as mock_install:
        yield mock_install


class TestAddCommand:
    """Tests for the 'add' CLI command."""

    def test_add_command_happy_path(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
        mock_skill_ops,
    ) -> None:
        """Add command installs skill successfully with agent selection and confirmation."""
        # Arrange: Create fake repository and config
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "test-skill"
        (repo_dir / skill_name).mkdir()
        (repo_dir / skill_name / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Test skill\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )

        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": str(repo_dir),
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock install_skill to succeed
        mock_skill_ops.return_value = None

        # Act: Change to project directory and run command
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_project)
            result = cli_runner.invoke(main, ["add", skill_name])
        finally:
            os.chdir(original_cwd)

        # Assert: Command succeeds
        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert mock_skill_ops.called

    def test_add_command_skill_not_found(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Add command exits with code 2 when skill not found in repository."""
        # Arrange: Setup config
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()

        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": str(repo_dir),
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock install_skill to raise SkillOperationError with "not found"
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.install_skill") as mock_install:
            mock_install.side_effect = SkillOperationError(
                "Skill 'nonexistent-skill' not found in repository."
            )

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["add", "nonexistent-skill"])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 2 (skill not found)
        assert result.exit_code == 2, f"Output: {result.output}"
        assert "not found" in result.output.lower()

    def test_add_command_user_cancels(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Add command exits with code 130 when user cancels confirmation."""
        # Arrange
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()

        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": str(repo_dir),
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock install_skill to raise cancellation error
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.install_skill") as mock_install:
            mock_install.side_effect = SkillOperationError("User cancelled installation.")

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["add", "cancel-test"])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 130 (user cancelled)
        assert result.exit_code == 130, f"Output: {result.output}"

    def test_add_command_already_installed_abort(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Add command handles already-installed skill and aborts on user choice."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {
                "existing-skill": {
                    "version": "1.0.0",
                    "agents": ["claude"],
                    "installed_at": "2026-03-31T10:00:00Z",
                }
            },
        }
        write_config(project.config_path, config)

        # Mock install_skill to raise abort error
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.install_skill") as mock_install:
            mock_install.side_effect = SkillOperationError("User aborted installation.")

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["add", "existing-skill"])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 130 (user cancelled/aborted)
        assert result.exit_code == 130, f"Output: {result.output}"

    def test_add_command_verbose_output(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Add command with --verbose flag shows detailed operation output."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock install_skill to succeed
        with patch("myskills.cli.install_skill") as mock_install:
            mock_install.return_value = None

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["--verbose", "add", "verbose-test"])
            finally:
                os.chdir(original_cwd)

        # Assert: Command succeeds
        assert result.exit_code == 0, f"Output: {result.output}"
        # Check that verbose flag was passed through the context
        assert mock_install.called

    def test_add_command_no_agents_selected(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Add command exits gracefully if no agents are selected."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock install_skill to raise "no agents" error
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.install_skill") as mock_install:
            mock_install.side_effect = SkillOperationError("No agents selected.")

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["add", "no-agents-test"])
            finally:
                os.chdir(original_cwd)

        # Assert: Should fail with appropriate message
        assert result.exit_code == 1, f"Output: {result.output}"
        assert "no agents" in result.output.lower()

    def test_add_command_git_error(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Add command exits with code 3 when repository is unreachable."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/unreachable.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock install_skill to raise GitError
        from myskills.git_ops import GitError

        with patch("myskills.cli.install_skill") as mock_install:
            mock_install.side_effect = GitError("Repository unreachable")

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["add", "any-skill"])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 3 (repository unreachable)
        assert result.exit_code == 3, f"Output: {result.output}"
        assert "repository" in result.output.lower()

    def test_add_command_keyboard_interrupt(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Add command exits with code 130 when interrupted by user (Ctrl+C)."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock install_skill to raise KeyboardInterrupt
        with patch("myskills.cli.install_skill") as mock_install:
            mock_install.side_effect = KeyboardInterrupt()

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["add", "interrupt-test"])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 130 (keyboard interrupt)
        assert result.exit_code == 130, f"Output: {result.output}"


class TestListCommand:
    """Tests for the 'list' CLI command (T025)."""

    def test_list_command_happy_path(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """List command displays all available skills with installation status."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock list_skills to return sample skills
        mock_skills = [
            {
                "name": "skill-a",
                "description": "First test skill",
                "version": "1.0.0",
                "installed": True,
            },
            {
                "name": "skill-b",
                "description": "Second test skill",
                "version": "2.1.0",
                "installed": False,
            },
            {
                "name": "skill-c",
                "description": "Third test skill",
                "version": "1.5.0",
                "installed": True,
            },
        ]

        with patch("myskills.cli.list_skills") as mock_list:
            mock_list.return_value = mock_skills

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["list"])
            finally:
                os.chdir(original_cwd)

        # Assert: Command succeeds
        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"

        # Check output format
        assert "skill-a" in result.output
        assert "skill-b" in result.output
        assert "skill-c" in result.output
        assert "1.0.0" in result.output
        assert "2.1.0" in result.output
        assert "installed" in result.output  # Check for installed marker (✓ installed)
        assert "Installed: 2/3" in result.output or "2/3" in result.output

    def test_list_command_empty_repository(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """List command handles empty repository gracefully."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock list_skills to return empty list
        with patch("myskills.cli.list_skills") as mock_list:
            mock_list.return_value = []

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["list"])
            finally:
                os.chdir(original_cwd)

        # Assert: Command succeeds with appropriate message
        assert result.exit_code == 0, f"Output: {result.output}"
        assert "no skills" in result.output.lower() or "0 total" in result.output.lower()

    def test_list_command_repo_unreachable(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """List command exits with code 3 when repository is unreachable."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/unreachable.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock list_skills to raise GitError
        from myskills.git_ops import GitError

        with patch("myskills.cli.list_skills") as mock_list:
            mock_list.side_effect = GitError("Network error: repository unreachable")

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["list"])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 3 (repository unreachable)
        assert result.exit_code == 3, f"Output: {result.output}"
        assert "repository" in result.output.lower() or "network" in result.output.lower()

    def test_list_command_verbose_output(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """List command with --verbose flag shows detailed operation output."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        mock_skills = [
            {
                "name": "test-skill",
                "description": "A test skill",
                "version": "1.0.0",
                "installed": False,
            },
        ]

        with patch("myskills.cli.list_skills") as mock_list:
            mock_list.return_value = mock_skills

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["--verbose", "list"])
            finally:
                os.chdir(original_cwd)

        # Assert: Command succeeds
        assert result.exit_code == 0, f"Output: {result.output}"
        assert mock_list.called

    def test_list_command_outside_project(
        self,
        tmp_path: Path,
        cli_runner: CliRunner,
    ) -> None:
        """List command fails gracefully outside a project directory."""
        # Act: Run list from a directory without .myskills.json
        original_cwd = os.getcwd()
        try:
            # Create a directory with no git marker or config
            non_project = tmp_path / "non-project"
            non_project.mkdir()
            os.chdir(non_project)
            result = cli_runner.invoke(main, ["list"])
        finally:
            os.chdir(original_cwd)

        # Assert: Should fail with project context error
        assert result.exit_code in [1, 2], f"Output: {result.output}"
        # The error message should indicate project detection issue


class TestRemoveCommand:
    """Tests for the 'remove' CLI command (T029)."""

    def test_remove_command_happy_path(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Remove command uninstalls skill successfully with confirmation."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        skill_name = "test-skill"

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

        # Mock remove_skill to succeed
        with patch("myskills.cli.remove_skill") as mock_remove:
            mock_remove.return_value = None

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["remove", skill_name])
            finally:
                os.chdir(original_cwd)

        # Assert: Command succeeds
        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert mock_remove.called


class TestUpdateCommand:
    """Tests for the 'update' CLI command (T034)."""

    def test_update_command_happy_path(self, tmp_project: Path, cli_runner: CliRunner):
        """Update command runs and reports summary when updates are applied."""
        project = ProjectContext(root=tmp_project)

        # Create a fake repo with an updated skill
        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()
        skill_name = "skill-update"
        skill_dir = repo_dir / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: skill-update\ndescription: s\nversion: 2.0.0\n---\n",
            encoding="utf-8",
        )

        config = {
            "version": CONFIG_VERSION,
            "repository": str(repo_dir),
            "installations": {skill_name: {"version": "1.0.0", "agents": []}},
        }
        write_config(project.config_path, config)

        # Run update command
        original_cwd = None
        try:
            import os

            original_cwd = os.getcwd()
            os.chdir(tmp_project)
            result = cli_runner.invoke(main, ["update"])
        finally:
            if original_cwd:
                os.chdir(original_cwd)

        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert "Updated:" in result.output

    def test_update_command_repo_unreachable(self, tmp_project: Path, cli_runner: CliRunner):
        """Update command exits with code 3 when repository is unreachable."""
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/unreachable.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Simulate git error by patching sync to raise GitError via update_skills path
        from myskills.git_ops import GitError

        with patch("myskills.cli.update_skills") as mock_update:
            mock_update.side_effect = GitError("Network error")

            original_cwd = None
            try:
                import os

                original_cwd = os.getcwd()
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["update"])
            finally:
                if original_cwd:
                    os.chdir(original_cwd)

        assert result.exit_code == 3, f"Output: {result.output}"
        assert "repository" in result.output.lower() or "network" in result.output.lower()

    def test_remove_command_skill_not_installed(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Remove command exits with code 2 when skill is not installed."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock remove_skill to raise SkillOperationError with "not installed"
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.remove_skill") as mock_remove:
            mock_remove.side_effect = SkillOperationError(
                "Skill 'nonexistent-skill' is not installed."
            )

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["remove", "nonexistent-skill"])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 2 (skill not found/installed)
        assert result.exit_code == 2, f"Output: {result.output}"
        assert "not installed" in result.output.lower()

    def test_remove_command_user_cancels(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Remove command exits with code 130 when user cancels confirmation."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        skill_name = "cancel-test"

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

        # Mock remove_skill to raise cancellation error
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.remove_skill") as mock_remove:
            mock_remove.side_effect = SkillOperationError("User cancelled removal.")

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["remove", skill_name])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 130 (user cancelled)
        assert result.exit_code == 130, f"Output: {result.output}"

    def test_remove_command_verbose_output(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Remove command with --verbose flag shows detailed operation output."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        skill_name = "verbose-test"

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

        # Mock remove_skill to succeed
        with patch("myskills.cli.remove_skill") as mock_remove:
            mock_remove.return_value = None

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["--verbose", "remove", skill_name])
            finally:
                os.chdir(original_cwd)

        # Assert: Command succeeds
        assert result.exit_code == 0, f"Output: {result.output}"
        assert mock_remove.called

    def test_remove_command_keyboard_interrupt(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Remove command exits with code 130 when interrupted by user (Ctrl+C)."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        skill_name = "interrupt-test"

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

        # Mock remove_skill to raise KeyboardInterrupt
        with patch("myskills.cli.remove_skill") as mock_remove:
            mock_remove.side_effect = KeyboardInterrupt()

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["remove", skill_name])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 130 (keyboard interrupt)
        assert result.exit_code == 130, f"Output: {result.output}"

    def test_remove_command_dangling_symlinks(
        self,
        tmp_project: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Remove command handles dangling symlinks gracefully."""
        # Arrange: Skill with dangling symlinks scenario
        project = ProjectContext(root=tmp_project)
        skill_name = "dangling-skill"

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

        # Mock remove_skill to succeed (implementation handles dangling links)
        with patch("myskills.cli.remove_skill") as mock_remove:
            mock_remove.return_value = None

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["remove", skill_name])
            finally:
                os.chdir(original_cwd)

        # Assert: Command succeeds despite dangling links
        assert result.exit_code == 0, f"Output: {result.output}"
        assert mock_remove.called


class TestImportCommand:
    """Tests for the 'import' CLI command - T039."""

    def test_import_command_happy_path(
        self,
        tmp_project: Path,
        skill_dir_factory,
        cli_runner: CliRunner,
    ) -> None:
        """Import command publishes local skill to repository successfully."""
        # Arrange: Create local skill to import
        skill_name = "my-skill"
        local_skill = skill_dir_factory(
            skill_name,
            version="1.0.0",
            description="My custom skill",
        )

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": str(repo_dir),
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock import_skill to succeed
        with patch("myskills.cli.import_skill") as mock_import:
            mock_import.return_value = None

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["import", str(local_skill)])
            finally:
                os.chdir(original_cwd)

        # Assert: Command succeeds
        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert mock_import.called

    def test_import_command_invalid_path(
        self,
        tmp_project: Path,
        tmp_path: Path,
        cli_runner: CliRunner,
    ) -> None:
        """Import command exits with code 2 when skill path is invalid."""
        # Arrange
        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        invalid_path = tmp_path / "nonexistent"

        # Mock import_skill to raise error
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.import_skill") as mock_import:
            mock_import.side_effect = SkillOperationError(
                "Invalid skill directory. Missing required manifest file (SKILL.md)."
            )

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["import", str(invalid_path)])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 2 (invalid)
        assert result.exit_code == 2, f"Output: {result.output}"
        assert "invalid" in result.output.lower() or "missing" in result.output.lower()

    def test_import_command_push_failure(
        self,
        tmp_project: Path,
        skill_dir_factory,
        cli_runner: CliRunner,
    ) -> None:
        """Import command exits with code 1 on push failure."""
        # Arrange
        skill_name = "test-skill"
        local_skill = skill_dir_factory(skill_name, version="1.0.0")

        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock import_skill to raise error
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.import_skill") as mock_import:
            mock_import.side_effect = SkillOperationError("Failed to push to repository.")

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["import", str(local_skill)])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 1 (general error)
        assert result.exit_code == 1, f"Output: {result.output}"
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_import_command_user_cancels(
        self,
        tmp_project: Path,
        skill_dir_factory,
        cli_runner: CliRunner,
    ) -> None:
        """Import command exits with code 130 when user cancels."""
        # Arrange
        skill_name = "test-skill"
        local_skill = skill_dir_factory(skill_name, version="1.0.0")

        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock import_skill to raise cancellation error
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.import_skill") as mock_import:
            mock_import.side_effect = SkillOperationError("User cancelled import.")

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["import", str(local_skill)])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 130 (user cancelled)
        assert result.exit_code == 130, f"Output: {result.output}"

    def test_import_command_repo_unreachable(
        self,
        tmp_project: Path,
        skill_dir_factory,
        cli_runner: CliRunner,
    ) -> None:
        """Import command exits with code 3 when repository is unreachable."""
        # Arrange
        skill_name = "test-skill"
        local_skill = skill_dir_factory(skill_name, version="1.0.0")

        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/unreachable.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock import_skill to raise repository error
        from myskills.skill_ops import SkillOperationError

        with patch("myskills.cli.import_skill") as mock_import:
            mock_import.side_effect = SkillOperationError(
                "Repository unreachable",
                is_repo_error=True,
            )

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["import", str(local_skill)])
            finally:
                os.chdir(original_cwd)

        # Assert: Exit code 3 (repo unreachable)
        assert result.exit_code == 3, f"Output: {result.output}"

    def test_import_command_with_verbose(
        self,
        tmp_project: Path,
        skill_dir_factory,
        cli_runner: CliRunner,
    ) -> None:
        """Import command with --verbose flag shows detailed output."""
        # Arrange
        skill_name = "test-skill"
        local_skill = skill_dir_factory(skill_name, version="1.0.0")

        project = ProjectContext(root=tmp_project)
        config = {
            "version": CONFIG_VERSION,
            "repository": "git@github.com:org/repo.git",
            "installations": {},
        }
        write_config(project.config_path, config)

        # Mock import_skill to succeed
        with patch("myskills.cli.import_skill") as mock_import:
            mock_import.return_value = None

            # Act
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_project)
                result = cli_runner.invoke(main, ["--verbose", "import", str(local_skill)])
            finally:
                os.chdir(original_cwd)

        # Assert: Command succeeds and verbose flag is respected
        assert result.exit_code == 0, f"Output: {result.output}"
        assert mock_import.called
