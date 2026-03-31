"""Unit tests for symlink operations (T017)."""

from __future__ import annotations

from pathlib import Path

import pytest

from myskills.symlinks import (
    SymlinkError,
    create_skill_symlinks,
    create_symlink,
    find_dangling_symlinks,
    is_dangling,
    remove_skill_symlinks,
    remove_symlink,
)


class TestCreateSymlink:
    """Tests for individual symlink creation."""

    def test_create_symlink_success(self, tmp_path: Path):
        """Create a symlink that points to an existing directory."""
        target = tmp_path / "target-dir"
        target.mkdir()
        (target / "file.txt").write_text("hello")
        link = tmp_path / "link-dir"

        create_symlink(target, link)

        assert link.is_symlink()
        assert (link / "file.txt").read_text() == "hello"

    def test_create_symlink_creates_parent_dirs(self, tmp_path: Path):
        """Parent directories of the link should be created automatically."""
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "deep" / "nested" / "link"

        create_symlink(target, link)

        assert link.is_symlink()

    def test_create_symlink_existing_path_raises_error(self, tmp_path: Path):
        """Creating a symlink where a file/dir already exists should fail."""
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "existing"
        link.mkdir()

        with pytest.raises(SymlinkError, match="already exists"):
            create_symlink(target, link)

    def test_create_symlink_existing_symlink_raises_error(self, tmp_path: Path):
        """Creating a symlink where a symlink already exists should fail."""
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target)

        with pytest.raises(SymlinkError, match="already exists"):
            create_symlink(target, link)

    def test_create_symlink_uses_relative_path(self, tmp_path: Path):
        """Symlinks should use relative paths for portability."""
        target = tmp_path / "a" / "b" / "target"
        target.mkdir(parents=True)
        link = tmp_path / "c" / "d" / "link"

        create_symlink(target, link)

        assert link.is_symlink()
        # The raw symlink target should be relative, not absolute
        raw_target = link.readlink()
        assert not raw_target.is_absolute()


class TestRemoveSymlink:
    """Tests for symlink removal."""

    def test_remove_symlink_success(self, tmp_path: Path):
        """Remove an existing symlink."""
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target)

        remove_symlink(link)

        assert not link.exists()
        assert not link.is_symlink()

    def test_remove_non_symlink_raises_error(self, tmp_path: Path):
        """Trying to remove a regular file/dir as symlink should fail."""
        regular = tmp_path / "regular"
        regular.mkdir()

        with pytest.raises(SymlinkError, match="not a symlink"):
            remove_symlink(regular)

    def test_remove_nonexistent_raises_error(self, tmp_path: Path):
        """Trying to remove a nonexistent path should fail."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(SymlinkError, match="not a symlink"):
            remove_symlink(nonexistent)


class TestIsDangling:
    """Tests for dangling symlink detection."""

    def test_dangling_symlink(self, tmp_path: Path):
        """A symlink whose target is removed should be dangling."""
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target)
        target.rmdir()  # Remove target to make it dangling

        assert is_dangling(link) is True

    def test_valid_symlink_is_not_dangling(self, tmp_path: Path):
        """A symlink with valid target should not be dangling."""
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target)

        assert is_dangling(link) is False

    def test_regular_file_is_not_dangling(self, tmp_path: Path):
        """A regular file should not be detected as dangling."""
        regular = tmp_path / "file.txt"
        regular.write_text("content")

        assert is_dangling(regular) is False

    def test_nonexistent_path_is_not_dangling(self, tmp_path: Path):
        """A nonexistent path is not a dangling symlink."""
        nonexistent = tmp_path / "nope"

        assert is_dangling(nonexistent) is False


class TestFindDanglingSymlinks:
    """Tests for finding dangling symlinks in a directory tree."""

    def test_find_dangling_in_directory(self, tmp_path: Path):
        """Should find dangling symlinks in the directory tree."""
        target = tmp_path / "target"
        target.mkdir()
        link1 = tmp_path / "link1"
        link1.symlink_to(target)
        link2 = tmp_path / "sub" / "link2"
        link2.parent.mkdir()
        link2.symlink_to(target)

        # Make both dangling
        target.rmdir()

        result = find_dangling_symlinks(tmp_path)

        assert len(result) == 2
        assert link1 in result
        assert link2 in result

    def test_no_dangling_returns_empty(self, tmp_path: Path):
        """Directory with no dangling symlinks should return empty list."""
        target = tmp_path / "target"
        target.mkdir()
        link = tmp_path / "link"
        link.symlink_to(target)

        result = find_dangling_symlinks(tmp_path)

        assert result == []

    def test_nonexistent_directory_returns_empty(self, tmp_path: Path):
        """Nonexistent directory should return empty list."""
        result = find_dangling_symlinks(tmp_path / "nonexistent")

        assert result == []


class TestCreateSkillSymlinks:
    """Tests for creating symlinks across multiple agent directories."""

    def test_create_symlinks_for_multiple_agents(self, tmp_project: Path):
        """Should create symlinks in all specified agent directories."""
        primary = tmp_project / ".agents" / "skills" / "test-skill"
        primary.mkdir(parents=True)
        (primary / "SKILL.md").write_text("test")

        agents = [".claude/skills", ".cursor/skills"]

        created = create_skill_symlinks(primary, tmp_project, agents, "test-skill")

        assert len(created) == 2
        for link in created:
            assert link.is_symlink()
            assert (link / "SKILL.md").read_text() == "test"

    def test_created_symlinks_point_to_primary(self, tmp_project: Path):
        """All symlinks should resolve to the primary skill directory."""
        primary = tmp_project / ".agents" / "skills" / "test-skill"
        primary.mkdir(parents=True)

        agents = [".claude/skills"]
        created = create_skill_symlinks(primary, tmp_project, agents, "test-skill")

        assert created[0].resolve() == primary.resolve()


class TestRemoveSkillSymlinks:
    """Tests for removing skill symlinks from agent directories."""

    def test_remove_existing_symlinks(self, tmp_project: Path):
        """Should remove existing symlinks from agent directories."""
        primary = tmp_project / ".agents" / "skills" / "test-skill"
        primary.mkdir(parents=True)

        agents = [".claude/skills", ".cursor/skills"]
        create_skill_symlinks(primary, tmp_project, agents, "test-skill")

        removed = remove_skill_symlinks(tmp_project, agents, "test-skill")

        assert len(removed) == 2
        for link in removed:
            assert not link.exists()

    def test_remove_nonexistent_symlinks_is_noop(self, tmp_project: Path):
        """Removing symlinks that don't exist should return empty list."""
        agents = [".claude/skills"]

        removed = remove_skill_symlinks(tmp_project, agents, "test-skill")

        assert removed == []
