"""Shared test fixtures for MySkills tests (R-004)."""

from __future__ import annotations

from pathlib import Path

import pytest

from myskills.ui import FakeUI


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with .git marker."""
    project = tmp_path / "test-project"
    project.mkdir()
    (project / ".git").mkdir()  # Fake git repo marker
    return project


@pytest.fixture
def skills_dir(tmp_project: Path) -> Path:
    """Create .agents/skills/ directory in the temp project."""
    d = tmp_project / ".agents" / "skills"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def fake_ui() -> FakeUI:
    """Provide a FakeUI instance for testing."""
    return FakeUI()


@pytest.fixture
def skill_dir_factory(tmp_path: Path):
    """Factory fixture to create skill directories with SKILL.md manifests.

    Usage:
        skill_dir = skill_dir_factory("my-skill", version="1.0.0", description="A test skill")
    """

    def _create(
        name: str,
        version: str = "1.0.0",
        description: str = "A test skill",
        extra_files: dict[str, str] | None = None,
        front_matter: str | None = None,
    ) -> Path:
        skill = tmp_path / name
        skill.mkdir(parents=True, exist_ok=True)

        if front_matter is not None:
            content = front_matter
        else:
            content = (
                f"---\n"
                f"name: {name}\n"
                f"description: {description}\n"
                f"version: {version}\n"
                f"---\n\n"
                f"# {name}\n\n"
                f"{description}\n"
            )

        (skill / "SKILL.md").write_text(content, encoding="utf-8")

        if extra_files:
            for fname, fcontent in extra_files.items():
                fpath = skill / fname
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(fcontent, encoding="utf-8")

        return skill

    return _create


@pytest.fixture
def fake_git_repo(tmp_path: Path):
    """Factory fixture to create a fake bare git repo with skill directories.

    Usage:
        repo_path = fake_git_repo(skills=["skill-a", "skill-b"])
    """

    def _create(
        skills: list[str] | None = None,
        repo_name: str = "skills-repo",
    ) -> Path:
        repo = tmp_path / repo_name
        repo.mkdir(parents=True, exist_ok=True)
        (repo / ".git").mkdir()

        for skill_name in skills or []:
            skill_dir = repo / skill_name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\n"
                f"name: {skill_name}\n"
                f"description: A test skill named {skill_name}\n"
                f"version: 1.0.0\n"
                f"---\n\n"
                f"# {skill_name}\n",
                encoding="utf-8",
            )

        return repo

    return _create
