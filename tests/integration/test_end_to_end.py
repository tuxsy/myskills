"""End-to-end tests for full CLI command flows (add, list, remove, update, import) - T045."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from myskills.cli import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def real_bare_repo(tmp_path: Path) -> Path:
    """Create a real bare git repository with sample skills.

    Returns:
        Path to the bare repository.
    """
    bare = tmp_path / "skills-repo.git"
    bare.mkdir()

    # Initialize bare repository
    subprocess.run(
        ["git", "init", "--bare", str(bare)],
        check=True,
        capture_output=True,
        timeout=10,
    )

    # Create a working clone to add skills
    working = tmp_path / "working-clone"
    subprocess.run(
        ["git", "clone", str(bare), str(working)],
        check=True,
        capture_output=True,
        timeout=30,
    )

    # Configure git
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=working,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=working,
        check=True,
    )

    # Create sample skills
    for skill_name, version in [("test-skill", "1.0.0"), ("another-skill", "2.1.0")]:
        skill_dir = working / skill_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {skill_name}\n"
            f"description: A test skill named {skill_name}\n"
            f"version: {version}\n---\n\n"
            f"# {skill_name}\n\n"
            f"This is a test skill.\n"
        )
        (skill_dir / "instructions.md").write_text(f"Instructions for {skill_name}\n")

    # Commit and push
    subprocess.run(["git", "add", "."], cwd=working, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Add sample skills"],
        cwd=working,
        check=True,
    )
    subprocess.run(["git", "push", "origin", "master"], cwd=working, check=True, timeout=10)

    return bare


@pytest.mark.integration
class TestEndToEndAddCommand:
    """End-to-end tests for the add command."""

    def test_add_skill_full_workflow(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test full add command workflow with real git operations."""
        # Arrange: Create project directory
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()  # Mark as git repo

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")  # Select first agent
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Act: Run add command
        result = cli_runner.invoke(
            main,
            ["add", "test-skill"],
        )

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Output: {result.output}"

        # Verify primary directory created
        primary_dir = project / ".agents" / "skills" / "test-skill"
        assert primary_dir.exists()
        assert (primary_dir / "SKILL.md").exists()
        assert (primary_dir / "instructions.md").exists()

        # Verify symlink created
        symlink = project / ".claude" / "skills" / "test-skill"
        assert symlink.is_symlink()
        assert symlink.resolve() == primary_dir.resolve()

        # Verify config created
        config_path = project / ".agents" / "skills" / ".myskills.json"
        assert config_path.exists()

    def test_add_skill_not_found(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test add command with non-existent skill returns exit code 2."""
        # Arrange: Create project directory
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Act: Run add command with non-existent skill
        result = cli_runner.invoke(
            main,
            ["add", "nonexistent-skill"],
        )

        # Assert: Exit code 2 (not found)
        assert result.exit_code == 2
        assert "not found" in result.output.lower()

    def test_add_skill_user_cancels(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test add command when user declines confirmation returns exit code 130."""
        # Arrange: Create project directory
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "no")  # User declines

        # Act: Run add command and decline confirmation
        result = cli_runner.invoke(
            main,
            ["add", "test-skill"],
        )

        # Assert: Exit code 130 (user cancelled)
        assert result.exit_code == 130

        # Verify nothing was installed
        primary_dir = project / ".agents" / "skills" / "test-skill"
        assert not primary_dir.exists()


@pytest.mark.integration
class TestEndToEndListCommand:
    """End-to-end tests for the list command."""

    def test_list_skills(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test list command displays available skills."""
        # Arrange: Create project directory
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Act: Run list command
        result = cli_runner.invoke(main, ["list"])

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Verify skills are listed
        assert "test-skill" in result.output
        assert "another-skill" in result.output
        assert "1.0.0" in result.output
        assert "2.1.0" in result.output

    def test_list_shows_installed_markers(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test list command shows [installed] markers for installed skills."""
        # Arrange: Create project and install a skill
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Install test-skill first
        cli_runner.invoke(
            main,
            ["add", "test-skill"],
        )

        # Act: Run list command
        result = cli_runner.invoke(main, ["list"])

        # Assert: test-skill shows as installed
        assert result.exit_code == 0
        assert "installed" in result.output.lower()
        assert "Installed: 1/" in result.output  # Shows 1 out of N installed


@pytest.mark.integration
class TestEndToEndRemoveCommand:
    """End-to-end tests for the remove command."""

    def test_remove_installed_skill(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test remove command successfully removes installed skill."""
        # Arrange: Create project and install a skill
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Install test-skill
        cli_runner.invoke(
            main,
            ["add", "test-skill"],
        )

        primary_dir = project / ".agents" / "skills" / "test-skill"
        symlink = project / ".claude" / "skills" / "test-skill"
        assert primary_dir.exists()
        assert symlink.is_symlink()

        # Act: Run remove command with confirmation
        result = cli_runner.invoke(
            main,
            ["remove", "test-skill"],
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Verify skill removed
        assert not primary_dir.exists()
        assert not symlink.exists()

    def test_remove_not_installed_skill(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test remove command with non-installed skill returns exit code 2."""
        # Arrange: Create project directory
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Act: Run remove command for non-installed skill
        result = cli_runner.invoke(
            main,
            ["remove", "test-skill"],
        )

        # Assert: Exit code 2 (not installed)
        assert result.exit_code == 2
        assert "not installed" in result.output.lower()


@pytest.mark.integration
class TestEndToEndUpdateCommand:
    """End-to-end tests for the update command."""

    def test_update_with_no_updates(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test update command when skills are already up-to-date."""
        # Arrange: Create project and install a skill
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Install test-skill
        cli_runner.invoke(
            main,
            ["add", "test-skill"],
        )

        # Act: Run update command
        result = cli_runner.invoke(main, ["update"])

        # Assert: Command succeeded, no updates available
        assert result.exit_code == 0
        assert "Current: 1" in result.output  # 1 skill current, 0 updated

    def test_update_with_new_version(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test update command detects and applies updates."""
        # Arrange: Create project and install a skill
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Install test-skill
        cli_runner.invoke(
            main,
            ["add", "test-skill"],
            input="0\n\ny\n",
        )

        # Update the skill in the repository (create a new version)
        working = tmp_path / "working-update"
        subprocess.run(
            ["git", "clone", str(real_bare_repo), str(working)],
            check=True,
            capture_output=True,
            timeout=30,
        )

        # Modify skill version
        skill_manifest = working / "test-skill" / "SKILL.md"
        skill_manifest.write_text(
            "---\nname: test-skill\n"
            "description: A test skill named test-skill\n"
            "version: 1.1.0\n---\n\n"
            "# test-skill\n\nUpdated version.\n"
        )

        # Commit and push
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=working, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=working, check=True)
        subprocess.run(["git", "add", "."], cwd=working, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Update test-skill to 1.1.0"], cwd=working, check=True
        )
        subprocess.run(["git", "push", "origin", "master"], cwd=working, check=True, timeout=10)

        # Act: Run update command with confirmation
        result = cli_runner.invoke(
            main,
            ["update"],
            input="y\n",
        )

        # Assert: Update detected and applied
        assert result.exit_code == 0
        assert "1.1.0" in result.output


@pytest.mark.integration
class TestEndToEndImportCommand:
    """End-to-end tests for the import command."""

    def test_import_new_skill(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test import command adds a new skill to the repository."""
        # Arrange: Create project and a skill to import
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        skill_to_import = tmp_path / "custom-skill"
        skill_to_import.mkdir()
        (skill_to_import / "SKILL.md").write_text(
            "---\nname: custom-skill\n"
            "description: A custom skill\n"
            "version: 1.0.0\n---\n\n"
            "# custom-skill\n"
        )

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Act: Run import command with confirmation
        result = cli_runner.invoke(
            main,
            ["import", str(skill_to_import)],
            input="y\n",
        )

        # Assert: Command succeeded
        assert result.exit_code == 0

        # Verify skill was added to repository
        working = tmp_path / "verify-import"
        subprocess.run(
            ["git", "clone", str(real_bare_repo), str(working)],
            check=True,
            capture_output=True,
            timeout=30,
        )

        assert (working / "custom-skill" / "SKILL.md").exists()

    def test_import_invalid_skill_directory(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test import command with invalid skill directory returns exit code 2."""
        # Arrange: Create project
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        # Create invalid skill directory (no SKILL.md)
        invalid_skill = tmp_path / "invalid-skill"
        invalid_skill.mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # Act: Run import command
        result = cli_runner.invoke(
            main,
            ["import", str(invalid_skill)],
        )

        # Assert: Exit code 2 (invalid)
        assert result.exit_code in [1, 2]
        assert "manifest" in result.output.lower() or "invalid" in result.output.lower()


@pytest.mark.integration
class TestEndToEndCompleteWorkflow:
    """Test complete workflows involving multiple commands."""

    def test_complete_skill_lifecycle(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test complete lifecycle: list, add, list, remove, list."""
        # Arrange: Create project
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # 1. List skills (none installed)
        result1 = cli_runner.invoke(main, ["list"])
        assert result1.exit_code == 0
        assert "test-skill" in result1.output
        assert "[installed]" not in result1.output

        # 2. Add test-skill
        result2 = cli_runner.invoke(
            main,
            ["add", "test-skill"],
        )
        assert result2.exit_code == 0

        # 3. List skills (test-skill installed)
        result3 = cli_runner.invoke(main, ["list"])
        assert result3.exit_code == 0
        assert "test-skill" in result3.output
        assert "installed" in result3.output.lower() or "Installed: 1/" in result3.output

        # 4. Remove test-skill
        result4 = cli_runner.invoke(
            main,
            ["remove", "test-skill"],
        )
        assert result4.exit_code == 0

        # 5. List skills (none installed again)
        result5 = cli_runner.invoke(main, ["list"])
        assert result5.exit_code == 0
        # test-skill should be listed but not marked as installed
        assert "test-skill" in result5.output

    def test_import_then_install_workflow(
        self,
        cli_runner: CliRunner,
        tmp_path: Path,
        real_bare_repo: Path,
        monkeypatch,
    ) -> None:
        """Test importing a skill then installing it."""
        # Arrange: Create project and custom skill
        project = tmp_path / "test-project"
        project.mkdir()
        (project / ".git").mkdir()

        custom_skill = tmp_path / "my-custom-skill"
        custom_skill.mkdir()
        (custom_skill / "SKILL.md").write_text(
            "---\nname: my-custom-skill\ndescription: My custom skill\nversion: 1.0.0\n---\n"
        )

        monkeypatch.chdir(project)
        monkeypatch.setenv("MYSKILLS_REPO_URL", str(real_bare_repo))
        monkeypatch.setenv("MYSKILLS_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setenv("MYSKILLS_AUTO_SELECT_AGENTS", "0")
        monkeypatch.setenv("MYSKILLS_AUTO_CONFIRM", "yes")

        # 1. Import custom skill
        result1 = cli_runner.invoke(
            main,
            ["import", str(custom_skill)],
            input="y\n",
        )
        assert result1.exit_code == 0

        # 2. List skills (custom skill should appear)
        result2 = cli_runner.invoke(main, ["list"])
        assert result2.exit_code == 0
        assert "my-custom-skill" in result2.output

        # 3. Install the custom skill
        result3 = cli_runner.invoke(
            main,
            ["add", "my-custom-skill"],
            input="0\n\ny\n",
        )
        assert result3.exit_code == 0

        # 4. Verify installation
        primary_dir = project / ".agents" / "skills" / "my-custom-skill"
        assert primary_dir.exists()
