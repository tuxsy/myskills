"""Tests for models module."""

from pathlib import Path

from myskills.models import Skill, SkillInstallation


def test_skill_files_nonexistent_path(tmp_path: Path):
    """Test Skill.files property when path doesn't exist."""
    nonexistent = tmp_path / "nonexistent"
    skill = Skill(path=nonexistent, name="test", description="test", version="1.0.0")

    assert skill.files == []


def test_skill_files_with_files(tmp_path: Path):
    """Test Skill.files property with actual files."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "file1.txt").write_text("test")
    (skill_dir / "file2.md").write_text("test")

    skill = Skill(path=skill_dir, name="test", description="test", version="1.0.0")

    files = skill.files
    assert len(files) == 2
    assert all(f.is_file() for f in files)


def test_installed_skill_is_valid_when_primary_missing(tmp_path: Path):
    """Test SkillInstallation.is_valid when primary path doesn't exist."""
    primary = tmp_path / "primary"
    installed = SkillInstallation(
        skill_name="test", installed_version="1.0.0", primary_path=primary, agent_links={}
    )

    assert installed.is_valid is False


def test_installed_skill_is_valid_when_primary_exists(tmp_path: Path):
    """Test SkillInstallation.is_valid when primary path exists."""
    primary = tmp_path / "primary"
    primary.mkdir()

    installed = SkillInstallation(
        skill_name="test", installed_version="1.0.0", primary_path=primary, agent_links={}
    )

    assert installed.is_valid is True


def test_installed_skill_is_valid_with_broken_link(tmp_path: Path):
    """Test SkillInstallation.is_valid when a link is broken."""
    primary = tmp_path / "primary"
    primary.mkdir()

    # Create a dangling symlink
    dangling_link = tmp_path / "dangling"
    dangling_target = tmp_path / "missing"
    dangling_link.symlink_to(dangling_target)

    installed = SkillInstallation(
        skill_name="test",
        installed_version="1.0.0",
        primary_path=primary,
        agent_links={"dangling": dangling_link},
    )

    assert installed.is_valid is False


def test_installed_skill_dangling_links(tmp_path: Path):
    """Test SkillInstallation.dangling_links property."""
    # Create primary directory
    primary = tmp_path / "primary"
    primary.mkdir()

    # Create a valid symlink
    valid_link = tmp_path / "valid"
    valid_link.symlink_to(primary)

    # Create a dangling symlink
    dangling_link = tmp_path / "dangling"
    dangling_target = tmp_path / "missing"
    dangling_link.symlink_to(dangling_target)

    installed = SkillInstallation(
        skill_name="test",
        installed_version="1.0.0",
        primary_path=primary,
        agent_links={"valid": valid_link, "dangling": dangling_link},
    )

    dangling = installed.dangling_links
    assert len(dangling) == 1
    assert dangling[0][0] == "dangling"
    assert dangling[0][1] == dangling_link
