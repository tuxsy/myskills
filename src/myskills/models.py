"""Data models for MySkills CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    """A self-contained skill package from the repository."""

    name: str
    description: str
    version: str
    path: Path  # Absolute path to skill directory (in repo or installed)

    @property
    def files(self) -> list[Path]:
        """All files in the skill directory."""
        if not self.path.exists():
            return []
        return sorted(f for f in self.path.rglob("*") if f.is_file())


@dataclass(frozen=True)
class SkillManifest:
    """Parsed content of a SKILL.md front-matter."""

    name: str
    description: str
    version: str
    raw_content: str  # Full SKILL.md content (front-matter + body)


@dataclass(frozen=True)
class Agent:
    """A supported AI coding assistant with a designated skills directory."""

    id: str
    display_name: str
    skills_dir: str  # Relative to project root, e.g. ".claude/skills"


@dataclass
class SkillInstallation:
    """Tracks an installed skill and its agent links."""

    skill_name: str
    primary_path: Path
    agent_links: dict[str, Path]  # agent_id -> symlink path
    installed_version: str
    installed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_valid(self) -> bool:
        """Check primary path exists and all symlinks are non-dangling."""
        if not self.primary_path.exists():
            return False
        return all(link.exists() for link in self.agent_links.values())

    @property
    def dangling_links(self) -> list[tuple[str, Path]]:
        """Return agent links that are dangling (target removed)."""
        return [
            (agent_id, link)
            for agent_id, link in self.agent_links.items()
            if link.is_symlink() and not link.exists()
        ]


@dataclass
class SkillsRepository:
    """Connection to the private Git skills repository."""

    url: str
    local_cache: Path  # ~/.cache/myskills/repo
    last_synced: datetime | None = None

    @property
    def is_cloned(self) -> bool:
        """Whether the repository has been cloned locally."""
        return self.local_cache.exists() and (self.local_cache / ".git").exists()


@dataclass
class ProjectContext:
    """The current project where skills are managed."""

    root: Path

    @property
    def primary_skills_dir(self) -> Path:
        """Primary skills directory: .agents/skills/."""
        return self.root / ".agents" / "skills"

    @property
    def config_path(self) -> Path:
        """Configuration file path: .agents/skills/.myskills.json."""
        return self.primary_skills_dir / ".myskills.json"
