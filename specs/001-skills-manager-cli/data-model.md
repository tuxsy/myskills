# Data Model: MySkills CLI Skills Manager

**Feature Branch**: `001-skills-manager-cli`
**Date**: 2026-03-31

## Entities

### Skill

A self-contained package of files that provides a specific capability to an AI agent.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Unique identifier, must match directory name. Lowercase, alphanumeric + hyphens. |
| `description` | `str` | Yes | Brief human-readable description of the skill's purpose. |
| `version` | `str` | Yes | Semantic version string (e.g., `1.0.0`). |
| `files` | `list[Path]` | Derived | List of files in the skill directory (computed from filesystem). |

**Source**: Parsed from `SKILL.md` YAML front-matter.

**Validation rules**:
- `name` must match regex `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (min 2 chars)
- `name` must match the directory name containing the `SKILL.md`
- `description` must be non-empty string
- `version` must be valid semver (`MAJOR.MINOR.PATCH`)
- `SKILL.md` must exist and have parseable YAML front-matter

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    version: str
    path: Path  # Absolute path to skill directory (in repo or installed)

    @property
    def files(self) -> list[Path]:
        """All files in the skill directory."""
        return sorted(f for f in self.path.rglob("*") if f.is_file())
```

---

### SkillManifest

Represents the parsed content of a `SKILL.md` front-matter.

```python
@dataclass(frozen=True)
class SkillManifest:
    name: str
    description: str
    version: str
    raw_content: str  # Full SKILL.md content (front-matter + body)
```

---

### Agent

A supported AI coding assistant with a designated skill directory path.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `str` | Yes | Unique identifier (e.g., `claude`, `cursor`, `copilot`, `windsurf`). |
| `display_name` | `str` | Yes | Human-readable name (e.g., `Claude`, `Cursor`). |
| `skills_dir` | `str` | Yes | Relative path template for skill directory (e.g., `.claude/skills`). |

**Hardcoded for v1** (FR-014):

```python
@dataclass(frozen=True)
class Agent:
    id: str
    display_name: str
    skills_dir: str  # Relative to project root, e.g., ".claude/skills"

SUPPORTED_AGENTS: list[Agent] = [
    Agent(id="claude", display_name="Claude", skills_dir=".claude/skills"),
    Agent(id="cursor", display_name="Cursor", skills_dir=".cursor/skills"),
    Agent(id="copilot", display_name="Copilot", skills_dir=".github/copilot/skills"),
    Agent(id="windsurf", display_name="Windsurf", skills_dir=".windsurf/skills"),
]
```

---

### SkillInstallation

Tracks the relationship between an installed skill and the project.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill_name` | `str` | Yes | Name of the installed skill. |
| `primary_path` | `Path` | Yes | Absolute path to primary skill directory (`.agents/skills/<name>`). |
| `agent_links` | `dict[str, Path]` | Yes | Map of agent_id → symlink path. |
| `installed_version` | `str` | Yes | Version at time of installation. |

```python
@dataclass
class SkillInstallation:
    skill_name: str
    primary_path: Path
    agent_links: dict[str, Path]  # agent_id -> symlink path
    installed_version: str

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
```

---

### SkillsRepository

Represents the connection to the private Git skills repository.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | `str` | Yes | Git repository URL (SSH or HTTPS). |
| `local_cache` | `Path` | Yes | Local clone path (e.g., `~/.cache/myskills/repo`). |
| `last_synced` | `datetime | None` | No | Timestamp of last fetch/pull. |

```python
from datetime import datetime

@dataclass
class SkillsRepository:
    url: str
    local_cache: Path  # ~/.cache/myskills/repo
    last_synced: datetime | None = None

    @property
    def is_cloned(self) -> bool:
        return self.local_cache.exists() and (self.local_cache / ".git").exists()
```

---

### ProjectContext

Represents the current project where skills are managed.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `root` | `Path` | Yes | Project root directory. |
| `primary_skills_dir` | `Path` | Derived | `.agents/skills/` under project root. |
| `config_path` | `Path` | Derived | `.agents/skills/.myskills.json` (installation tracking). |

```python
@dataclass
class ProjectContext:
    root: Path

    @property
    def primary_skills_dir(self) -> Path:
        return self.root / ".agents" / "skills"

    @property
    def config_path(self) -> Path:
        return self.primary_skills_dir / ".myskills.json"
```

---

## Relationships

```
SkillsRepository 1---* Skill          (repository contains many skills)
Project          1---* SkillInstallation (project has many installations)
SkillInstallation 1---* Agent          (installation links to many agents)
Skill            1---1 SkillManifest   (each skill has one manifest)
```

## State Transitions

### Skill Lifecycle (in a project)

```
                    ┌──────────┐
                    │   NOT    │
                    │INSTALLED │
                    └────┬─────┘
                         │ add
                         ▼
                    ┌──────────┐
              ┌─────│INSTALLED │─────┐
              │     └────┬─────┘     │
              │          │           │
         remove│    update│      dangling
              │          │      detected
              │          ▼           │
              │     ┌──────────┐    │
              │     │ UPDATED  │    ▼
              │     └──────────┘  ┌──────────┐
              │                   │ DEGRADED  │
              │                   └────┬─────┘
              ▼                        │ remove/repair
         ┌──────────┐                  │
         │   NOT    │◄─────────────────┘
         │INSTALLED │
         └──────────┘
```

States:
- **NOT INSTALLED**: Skill exists in repository but not in project
- **INSTALLED**: Primary copy + all symlinks present and valid
- **UPDATED**: After successful update (transitions back to INSTALLED)
- **DEGRADED**: Primary copy or symlinks are broken (dangling links, missing primary)

## Configuration File Format

Installation state tracked in `.agents/skills/.myskills.json`:

```json
{
  "version": 1,
  "repository": "git@github.com:org/skills-repo.git",
  "installations": {
    "find-skills": {
      "version": "1.0.0",
      "agents": ["claude", "cursor"],
      "installed_at": "2026-03-31T10:30:00Z"
    },
    "code-review": {
      "version": "2.1.0",
      "agents": ["claude", "copilot", "windsurf"],
      "installed_at": "2026-03-31T11:00:00Z"
    }
  }
}
```

## Local Cache Structure

```
~/.cache/myskills/
└── repo/                    # Cloned skills repository
    ├── .git/
    ├── find-skills/
    │   ├── SKILL.md
    │   └── ...
    └── code-review/
        ├── SKILL.md
        └── ...
```
