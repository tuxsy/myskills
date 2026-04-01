"""Tests for import skill logic (happy path, duplicate name conflict, invalid manifest, push failure) - T038."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

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


@pytest.fixture
def mock_push():
    """Fixture that patches push operations."""
    with (
        patch("myskills.skill_ops.commit_changes") as mock_commit,
        patch("myskills.skill_ops.push_repository") as mock_push_repo,
    ):
        yield mock_commit, mock_push_repo


class TestImportSkillHappyPath:
    """Test successful skill import to repository."""

    def test_import_new_skill(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
        mock_sync,
        mock_push,
    ) -> None:
        """Importing a new skill copies it to the repository and commits/pushes."""
        # Arrange: Create a local skill to import
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "custom-skill"
        local_skill_path = skill_dir_factory(
            skill_name,
            version="1.0.0",
            description="My custom skill",
            extra_files={"instructions.md": "Custom instructions"},
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Configure UI to confirm import
        fake_ui.set_confirm_responses(True)

        # Act: Import the skill
        skill_ops.import_skill(
            skill_path=local_skill_path,
            project=project,
            repo=repo,
            ui=fake_ui,
        )

        # Assert: Skill copied to repository
        repo_skill_dir = repo_dir / skill_name
        assert repo_skill_dir.exists()
        assert (repo_skill_dir / "SKILL.md").exists()
        assert (repo_skill_dir / "instructions.md").exists()

        # Assert: Files match source
        assert (repo_skill_dir / "SKILL.md").read_text() == (
            local_skill_path / "SKILL.md"
        ).read_text()

        # Assert: Commit was created
        mock_commit, mock_push_repo = mock_push
        mock_commit.assert_called_once()
        assert skill_name in mock_commit.call_args[1]["message"]

        # Assert: Push was executed
        mock_push_repo.assert_called_once_with(repo_dir, verbose=False)

        # Assert: Success message displayed
        assert any(
            "imported" in msg[1].lower() or "success" in msg[0].lower() for msg in fake_ui.messages
        )

    def test_import_skill_with_subdirectories(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
        mock_sync,
        mock_push,
    ) -> None:
        """Importing a skill with subdirectories preserves directory structure."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "complex-skill"
        local_skill_path = skill_dir_factory(
            skill_name,
            version="2.0.0",
            description="Complex skill",
            extra_files={
                "docs/guide.md": "Documentation",
                "scripts/helper.py": "# Helper script",
                "templates/template.txt": "Template content",
            },
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        fake_ui.set_confirm_responses(True)

        # Act
        skill_ops.import_skill(
            skill_path=local_skill_path,
            project=project,
            repo=repo,
            ui=fake_ui,
        )

        # Assert: Directory structure preserved
        repo_skill_dir = repo_dir / skill_name
        assert (repo_skill_dir / "docs" / "guide.md").exists()
        assert (repo_skill_dir / "scripts" / "helper.py").exists()
        assert (repo_skill_dir / "templates" / "template.txt").exists()


class TestImportSkillConflicts:
    """Test handling of duplicate skill names."""

    def test_import_duplicate_name_abort(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
        mock_sync,
        mock_push,
    ) -> None:
        """Import aborts when skill name already exists and user chooses abort."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "existing-skill"

        # Create existing skill in repo
        existing_skill = repo_dir / skill_name
        existing_skill.mkdir()
        (existing_skill / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Existing\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )

        # Create local skill to import
        local_skill_path = skill_dir_factory(
            skill_name,
            version="2.0.0",
            description="New version",
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # User chooses to abort
        fake_ui.set_choice_responses("abort")

        # Act
        with pytest.raises(SystemExit) as exc_info:
            skill_ops.import_skill(
                skill_path=local_skill_path,
                project=project,
                repo=repo,
                ui=fake_ui,
            )

        # Assert: Exit code 130 (user cancelled)
        assert exc_info.value.code == 130

        # Assert: Original skill unchanged
        assert (existing_skill / "SKILL.md").read_text().count("Existing") == 1

        # Assert: No commit/push
        mock_commit, mock_push_repo = mock_push
        mock_commit.assert_not_called()
        mock_push_repo.assert_not_called()

    def test_import_duplicate_name_overwrite(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
        mock_sync,
        mock_push,
    ) -> None:
        """Import overwrites when skill name already exists and user confirms."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "existing-skill"

        # Create existing skill in repo
        existing_skill = repo_dir / skill_name
        existing_skill.mkdir()
        (existing_skill / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Old version\nversion: 1.0.0\n---\n",
            encoding="utf-8",
        )
        (existing_skill / "old_file.txt").write_text("Should be removed", encoding="utf-8")

        # Create local skill to import
        local_skill_path = skill_dir_factory(
            skill_name,
            version="2.0.0",
            description="New version",
            extra_files={"new_file.txt": "New content"},
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # User chooses to overwrite, then confirms
        fake_ui.set_choice_responses("overwrite")
        fake_ui.set_confirm_responses(True)

        # Act
        skill_ops.import_skill(
            skill_path=local_skill_path,
            project=project,
            repo=repo,
            ui=fake_ui,
        )

        # Assert: Skill replaced with new version
        manifest_content = (existing_skill / "SKILL.md").read_text()
        assert "version: 2.0.0" in manifest_content
        assert "description: New version" in manifest_content
        assert (existing_skill / "new_file.txt").exists()
        assert not (existing_skill / "old_file.txt").exists()

        # Assert: Commit/push executed
        mock_commit, mock_push_repo = mock_push
        mock_commit.assert_called_once()
        mock_push_repo.assert_called_once()


class TestImportSkillValidation:
    """Test validation of skill directory before import."""

    def test_import_missing_manifest(
        self,
        tmp_project: Path,
        tmp_path: Path,
        fake_ui: FakeUI,
        mock_sync,
    ) -> None:
        """Import fails when skill directory has no SKILL.md."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        # Create directory without SKILL.md
        bad_skill = tmp_path / "bad-skill"
        bad_skill.mkdir()
        (bad_skill / "readme.txt").write_text("No manifest", encoding="utf-8")

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            skill_ops.import_skill(
                skill_path=bad_skill,
                project=project,
                repo=repo,
                ui=fake_ui,
            )

        # Assert: Exit code 2 (not found / invalid)
        assert exc_info.value.code == 2

        # Assert: Error message mentions missing manifest
        assert any(
            "manifest" in msg[1].lower() or "skill.md" in msg[1].lower()
            for msg in fake_ui.messages
            if msg[0] == "error"
        )

    def test_import_invalid_manifest(
        self,
        tmp_project: Path,
        tmp_path: Path,
        fake_ui: FakeUI,
        mock_sync,
    ) -> None:
        """Import fails when SKILL.md has invalid front-matter."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        # Create skill with invalid manifest
        bad_skill = tmp_path / "invalid-skill"
        bad_skill.mkdir()
        (bad_skill / "SKILL.md").write_text(
            "---\nname: invalid-skill\n---\n# Missing required fields",
            encoding="utf-8",
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            skill_ops.import_skill(
                skill_path=bad_skill,
                project=project,
                repo=repo,
                ui=fake_ui,
            )

        # Assert: Exit code 2 (invalid)
        assert exc_info.value.code == 2

    def test_import_nonexistent_path(
        self,
        tmp_project: Path,
        tmp_path: Path,
        fake_ui: FakeUI,
        mock_sync,
    ) -> None:
        """Import fails when skill path does not exist."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        nonexistent_path = tmp_path / "does-not-exist"

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            skill_ops.import_skill(
                skill_path=nonexistent_path,
                project=project,
                repo=repo,
                ui=fake_ui,
            )

        # Assert: Exit code 2 (not found)
        assert exc_info.value.code == 2


class TestImportSkillPushFailure:
    """Test handling of Git push failures."""

    def test_import_push_fails(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
        mock_sync,
    ) -> None:
        """Import fails gracefully when Git push fails."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "new-skill"
        local_skill_path = skill_dir_factory(
            skill_name,
            version="1.0.0",
            description="Test skill",
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        fake_ui.set_confirm_responses(True)

        # Mock push to fail
        with (
            patch("myskills.git_ops.commit_changes"),
            patch("myskills.git_ops.push_repository", side_effect=Exception("Push failed")),
        ):
            # Act & Assert
            with pytest.raises(SystemExit) as exc_info:
                skill_ops.import_skill(
                    skill_path=local_skill_path,
                    project=project,
                    repo=repo,
                    ui=fake_ui,
                )

            # Assert: Exit code 1 (general error)
            assert exc_info.value.code == 1

            # Assert: Error message displayed
            assert any(msg[0] == "error" for msg in fake_ui.messages)

    def test_import_user_cancels_confirmation(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
        mock_sync,
        mock_push,
    ) -> None:
        """Import aborts when user declines final confirmation."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "new-skill"
        local_skill_path = skill_dir_factory(
            skill_name,
            version="1.0.0",
            description="Test skill",
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        # User declines confirmation
        fake_ui.set_confirm_responses(False)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            skill_ops.import_skill(
                skill_path=local_skill_path,
                project=project,
                repo=repo,
                ui=fake_ui,
            )

        # Assert: Exit code 130 (user cancelled)
        assert exc_info.value.code == 130

        # Assert: Skill not added to repo
        repo_skill_dir = repo_dir / skill_name
        assert not repo_skill_dir.exists()

        # Assert: No commit/push
        mock_commit, mock_push_repo = mock_push
        mock_commit.assert_not_called()
        mock_push_repo.assert_not_called()


class TestImportSkillVersionHandling:
    """Test import adds explicit version field when missing."""

    def test_import_adds_explicit_version_when_missing(
        self,
        tmp_project: Path,
        tmp_path: Path,
        fake_ui: FakeUI,
        mock_sync,
        mock_push,
    ) -> None:
        """Import adds explicit version field to SKILL.md when missing."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "no-version-skill"

        # Create local skill WITHOUT version field
        local_skill = tmp_path / skill_name
        local_skill.mkdir()
        (local_skill / "SKILL.md").write_text(
            f"---\nname: {skill_name}\ndescription: Skill without version\n---\n\n# Body",
            encoding="utf-8",
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        fake_ui.set_confirm_responses(True)

        # Act: Import the skill
        skill_ops.import_skill(
            skill_path=local_skill,
            project=project,
            repo=repo,
            ui=fake_ui,
        )

        # Assert: Local SKILL.md now has explicit version field
        local_manifest_content = (local_skill / "SKILL.md").read_text()
        assert "version: 1.0.0" in local_manifest_content

        # Assert: Field order is name, description, version
        lines = local_manifest_content.split("\n")
        assert lines[0] == "---"
        assert lines[1] == f"name: {skill_name}"
        assert lines[2] == "description: Skill without version"
        assert lines[3] == "version: 1.0.0"
        assert lines[4] == "---"

        # Assert: Body content preserved
        assert "# Body" in local_manifest_content

        # Assert: Repo copy also has explicit version
        repo_manifest_content = (repo_dir / skill_name / "SKILL.md").read_text()
        assert "version: 1.0.0" in repo_manifest_content

    def test_import_preserves_explicit_version(
        self,
        tmp_project: Path,
        skill_dir_factory,
        fake_ui: FakeUI,
        mock_sync,
        mock_push,
    ) -> None:
        """Import preserves existing explicit version field."""
        from myskills import skill_ops

        repo_dir = tmp_project / "repo"
        repo_dir.mkdir()
        (repo_dir / ".git").mkdir()

        skill_name = "with-version-skill"

        # Create local skill WITH explicit version
        local_skill_path = skill_dir_factory(
            skill_name,
            version="2.5.0",
            description="Skill with version",
        )

        project = ProjectContext(root=tmp_project)
        repo = SkillsRepository(url="git@github.com:org/repo.git", local_cache=repo_dir)

        fake_ui.set_confirm_responses(True)

        # Act: Import the skill
        skill_ops.import_skill(
            skill_path=local_skill_path,
            project=project,
            repo=repo,
            ui=fake_ui,
        )

        # Assert: Version preserved (not replaced with 1.0.0)
        local_manifest_content = (local_skill_path / "SKILL.md").read_text()
        assert "version: 2.5.0" in local_manifest_content
        assert "version: 1.0.0" not in local_manifest_content

        # Assert: Repo copy has same version
        repo_manifest_content = (repo_dir / skill_name / "SKILL.md").read_text()
        assert "version: 2.5.0" in repo_manifest_content
