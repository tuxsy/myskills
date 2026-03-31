"""CLI tests for all commands using CliRunner - T020 (add command tests)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

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
