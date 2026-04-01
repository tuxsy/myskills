"""Git workflow integration tests with real local bare repos (R-004) - T044."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from myskills.git_ops import (
    GitError,
    clone_repository,
    commit_changes,
    pull_repository,
    push_repository,
    sync_repository,
)
from myskills.models import SkillsRepository


@pytest.fixture
def bare_repo(tmp_path: Path) -> Path:
    """Create a real local bare git repository for testing.

    Returns:
        Path to the bare repository.
    """
    bare = tmp_path / "test-repo.git"
    bare.mkdir()

    # Initialize bare repository using system git
    result = subprocess.run(
        ["git", "init", "--bare", str(bare)],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to create bare repo: {result.stderr}")

    return bare


@pytest.fixture
def working_repo(tmp_path: Path, bare_repo: Path) -> Path:
    """Create a working clone of the bare repository.

    Returns:
        Path to the working repository.
    """
    working = tmp_path / "working-clone"

    # Clone the bare repo using system git
    result = subprocess.run(
        ["git", "clone", str(bare_repo), str(working)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to clone repo: {result.stderr}")

    # Create initial commit to have a branch
    test_file = working / "README.md"
    test_file.write_text("# Test Repository\n")

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
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=working,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=working,
        check=True,
    )
    subprocess.run(
        ["git", "push", "origin", "master"],
        cwd=working,
        check=True,
        timeout=10,
    )

    return working


@pytest.mark.integration
class TestCloneRepository:
    """Integration tests for cloning repositories."""

    def test_clone_local_bare_repo(
        self,
        tmp_path: Path,
        bare_repo: Path,
        working_repo: Path,
    ) -> None:
        """Clone a local bare repository successfully."""
        # Arrange: Target for new clone
        target = tmp_path / "new-clone"

        # Act: Clone using clone_repository
        clone_repository(url=str(bare_repo), target=target, verbose=True)

        # Assert: Repository was cloned
        assert target.exists()
        assert (target / ".git").exists()
        assert (target / "README.md").exists()

    def test_clone_existing_target_fails(
        self,
        tmp_path: Path,
        bare_repo: Path,
        working_repo: Path,
    ) -> None:
        """Cloning to an existing path raises GitError."""
        # Arrange: Create existing directory
        target = tmp_path / "existing"
        target.mkdir()

        # Act & Assert: Should raise GitError
        with pytest.raises(GitError) as exc_info:
            clone_repository(url=str(bare_repo), target=target, verbose=True)

        assert "already exists" in str(exc_info.value).lower()

    def test_clone_invalid_repo_fails(
        self,
        tmp_path: Path,
    ) -> None:
        """Cloning an invalid repository raises GitError."""
        # Arrange: Non-existent repository URL
        target = tmp_path / "clone-target"

        # Act & Assert: Should raise GitError
        with pytest.raises(GitError):
            clone_repository(
                url="/nonexistent/invalid-repo.git",
                target=target,
                verbose=True,
            )


@pytest.mark.integration
class TestPullRepository:
    """Integration tests for pulling changes."""

    def test_pull_with_no_changes(
        self,
        working_repo: Path,
    ) -> None:
        """Pulling when already up-to-date succeeds."""
        # Act: Pull repository
        pull_repository(repo_path=working_repo, verbose=True)

        # Assert: No error, repository state unchanged
        assert (working_repo / "README.md").exists()

    def test_pull_with_new_commits(
        self,
        tmp_path: Path,
        bare_repo: Path,
        working_repo: Path,
    ) -> None:
        """Pulling fetches new commits from remote."""
        # Arrange: Create a second clone and add a commit
        second_clone = tmp_path / "second-clone"

        subprocess.run(
            ["git", "clone", str(bare_repo), str(second_clone)],
            capture_output=True,
            check=True,
            timeout=30,
        )

        # Add a new file in second clone
        new_file = second_clone / "newfile.txt"
        new_file.write_text("New content\n")

        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=second_clone,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=second_clone,
            check=True,
        )
        subprocess.run(
            ["git", "add", "newfile.txt"],
            cwd=second_clone,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add new file"],
            cwd=second_clone,
            check=True,
        )
        subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=second_clone,
            check=True,
            timeout=10,
        )

        # Act: Pull in first clone
        pull_repository(repo_path=working_repo, verbose=True)

        # Assert: New file appears in first clone
        assert (working_repo / "newfile.txt").exists()
        assert (working_repo / "newfile.txt").read_text() == "New content\n"

    def test_pull_nonexistent_repo_fails(
        self,
        tmp_path: Path,
    ) -> None:
        """Pulling from non-existent path raises GitError."""
        # Arrange: Non-existent path
        nonexistent = tmp_path / "nonexistent-repo"

        # Act & Assert: Should raise GitError
        with pytest.raises(GitError) as exc_info:
            pull_repository(repo_path=nonexistent, verbose=True)

        assert "does not exist" in str(exc_info.value).lower()


@pytest.mark.integration
class TestSyncRepository:
    """Integration tests for sync_repository (clone or pull)."""

    def test_sync_clones_if_not_cloned(
        self,
        tmp_path: Path,
        bare_repo: Path,
        working_repo: Path,
    ) -> None:
        """sync_repository clones if local cache doesn't exist."""
        # Arrange: Repository that needs cloning
        cache = tmp_path / "cache"
        repo = SkillsRepository(url=str(bare_repo), local_cache=cache)

        # Act: Sync repository
        sync_repository(repo, verbose=True)

        # Assert: Repository was cloned
        assert cache.exists()
        assert (cache / ".git").exists()
        assert (cache / "README.md").exists()

    def test_sync_pulls_if_already_cloned(
        self,
        tmp_path: Path,
        bare_repo: Path,
        working_repo: Path,
    ) -> None:
        """sync_repository pulls if local cache already exists."""
        # Arrange: Clone repository first
        cache = tmp_path / "cache"
        clone_repository(url=str(bare_repo), target=cache, verbose=True)

        # Add a new commit to the working repo and push
        new_file = working_repo / "another.txt"
        new_file.write_text("Another file\n")

        subprocess.run(
            ["git", "add", "another.txt"],
            cwd=working_repo,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add another file"],
            cwd=working_repo,
            check=True,
        )
        subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=working_repo,
            check=True,
            timeout=10,
        )

        # Act: Sync repository (should pull)
        repo = SkillsRepository(url=str(bare_repo), local_cache=cache)
        sync_repository(repo, verbose=True)

        # Assert: New file appears in cache
        assert (cache / "another.txt").exists()
        assert (cache / "another.txt").read_text() == "Another file\n"


@pytest.mark.integration
class TestCommitChanges:
    """Integration tests for committing changes."""

    def test_commit_new_files(
        self,
        working_repo: Path,
    ) -> None:
        """Committing new files creates a commit."""
        # Arrange: Add a new file
        new_file = working_repo / "test-skill" / "SKILL.md"
        new_file.parent.mkdir(parents=True)
        new_file.write_text("---\nname: test-skill\ndescription: Test\n---\n")

        # Act: Commit changes
        commit_changes(
            repo_path=working_repo,
            message="Add test-skill",
            author="myskills <myskills@local>",
            verbose=True,
        )

        # Assert: Verify commit was created using git log
        result = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=working_repo,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Add test-skill" in result.stdout

    def test_commit_modified_files(
        self,
        working_repo: Path,
    ) -> None:
        """Committing modified files creates a commit."""
        # Arrange: Modify existing file
        readme = working_repo / "README.md"
        readme.write_text("# Updated Repository\n\nNew content\n")

        # Act: Commit changes
        commit_changes(
            repo_path=working_repo,
            message="Update README",
            verbose=True,
        )

        # Assert: Verify commit was created
        result = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            cwd=working_repo,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Update README" in result.stdout

    def test_commit_nonexistent_repo_fails(
        self,
        tmp_path: Path,
    ) -> None:
        """Committing to non-existent repo raises GitError."""
        # Arrange: Non-existent path
        nonexistent = tmp_path / "nonexistent-repo"

        # Act & Assert: Should raise GitError
        with pytest.raises(GitError):
            commit_changes(
                repo_path=nonexistent,
                message="Test commit",
                verbose=True,
            )


@pytest.mark.integration
class TestPushRepository:
    """Integration tests for pushing changes."""

    def test_push_new_commits(
        self,
        tmp_path: Path,
        bare_repo: Path,
        working_repo: Path,
    ) -> None:
        """Pushing commits updates the remote."""
        # Arrange: Add a new file and commit
        new_file = working_repo / "pushed-file.txt"
        new_file.write_text("Pushed content\n")

        commit_changes(
            repo_path=working_repo,
            message="Add pushed file",
            verbose=True,
        )

        # Act: Push changes
        push_repository(repo_path=working_repo, verbose=True)

        # Assert: Create a new clone and verify the file exists
        verify_clone = tmp_path / "verify-clone"
        subprocess.run(
            ["git", "clone", str(bare_repo), str(verify_clone)],
            capture_output=True,
            check=True,
            timeout=30,
        )

        assert (verify_clone / "pushed-file.txt").exists()
        assert (verify_clone / "pushed-file.txt").read_text() == "Pushed content\n"

    def test_push_nonexistent_repo_fails(
        self,
        tmp_path: Path,
    ) -> None:
        """Pushing from non-existent repo raises GitError."""
        # Arrange: Non-existent path
        nonexistent = tmp_path / "nonexistent-repo"

        # Act & Assert: Should raise GitError
        with pytest.raises(GitError) as exc_info:
            push_repository(repo_path=nonexistent, verbose=True)

        assert "does not exist" in str(exc_info.value).lower()


@pytest.mark.integration
class TestFullWorkflow:
    """Integration tests for complete git workflows."""

    def test_clone_commit_push_pull_workflow(
        self,
        tmp_path: Path,
        bare_repo: Path,
        working_repo: Path,
    ) -> None:
        """Test complete workflow: clone, commit, push, pull from another clone."""
        # 1. Clone a second working copy
        clone2 = tmp_path / "clone2"
        clone_repository(url=str(bare_repo), target=clone2, verbose=True)

        assert (clone2 / "README.md").exists()

        # 2. Add a file in first clone and commit
        skill_dir = working_repo / "new-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: new-skill\ndescription: A new skill\nversion: 1.0.0\n---\n"
        )

        commit_changes(
            repo_path=working_repo,
            message="Add new-skill",
            verbose=True,
        )

        # 3. Push from first clone
        push_repository(repo_path=working_repo, verbose=True)

        # 4. Pull in second clone
        pull_repository(repo_path=clone2, verbose=True)

        # 5. Verify file appears in second clone
        assert (clone2 / "new-skill" / "SKILL.md").exists()
        content = (clone2 / "new-skill" / "SKILL.md").read_text()
        assert "new-skill" in content

    def test_multiple_clones_can_push_independently(
        self,
        tmp_path: Path,
        bare_repo: Path,
        working_repo: Path,
    ) -> None:
        """Multiple clones can push commits independently."""
        # 1. Create second clone
        clone2 = tmp_path / "clone2"
        clone_repository(url=str(bare_repo), target=clone2, verbose=True)

        # 2. Add file in first clone
        (working_repo / "file1.txt").write_text("From clone 1\n")
        commit_changes(working_repo, "Add file1", verbose=True)
        push_repository(working_repo, verbose=True)

        # 3. Pull in second clone
        pull_repository(clone2, verbose=True)

        # 4. Add file in second clone
        (clone2 / "file2.txt").write_text("From clone 2\n")
        commit_changes(clone2, "Add file2", verbose=True)
        push_repository(clone2, verbose=True)

        # 5. Pull in first clone
        pull_repository(working_repo, verbose=True)

        # 6. Verify both files exist in both clones
        assert (working_repo / "file1.txt").exists()
        assert (working_repo / "file2.txt").exists()
        assert (clone2 / "file1.txt").exists()
        assert (clone2 / "file2.txt").exists()
