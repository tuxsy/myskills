# Configuration Contract: MySkills

**Feature Branch**: `001-skills-manager-cli`
**Date**: 2026-03-31

This document defines the configuration file formats used by the `myskills` tool.

## Installation Tracking: `.myskills.json`

**Location**: `.agents/skills/.myskills.json` (relative to project root)

**Purpose**: Tracks which skills are installed, their versions, and which agents they are linked to.

### Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "repository", "installations"],
  "properties": {
    "version": {
      "type": "integer",
      "description": "Schema version number",
      "const": 1
    },
    "repository": {
      "type": "string",
      "description": "Git repository URL (SSH or HTTPS)"
    },
    "installations": {
      "type": "object",
      "description": "Map of skill_name -> installation details",
      "additionalProperties": {
        "type": "object",
        "required": ["version", "agents", "installed_at"],
        "properties": {
          "version": {
            "type": "string",
            "description": "Installed version (semver)",
            "pattern": "^\\d+\\.\\d+\\.\\d+$"
          },
          "agents": {
            "type": "array",
            "description": "List of agent IDs this skill is linked to",
            "items": {
              "type": "string",
              "enum": ["claude", "cursor", "copilot", "windsurf"]
            },
            "minItems": 1
          },
          "installed_at": {
            "type": "string",
            "description": "ISO 8601 timestamp of installation",
            "format": "date-time"
          }
        }
      }
    }
  }
}
```

### Example

```json
{
  "version": 1,
  "repository": "git@github.com:myorg/ai-skills.git",
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

### Behavior

- File is created on first `add` command if it doesn't exist
- File is updated atomically (write to temp file, then rename) to prevent corruption
- If file is missing but skills are installed on disk, the tool can reconstruct state from filesystem
- File uses JSON for simplicity and stdlib support (no additional dependencies)

---

## Skill Manifest: `SKILL.md`

**Location**: `<skill_directory>/SKILL.md`

**Purpose**: Declares skill metadata in YAML front-matter, with human-readable documentation in the markdown body.

### Format

```markdown
---
name: skill-name
description: Brief description of what the skill does
version: 1.0.0
---

# Skill Name

Detailed documentation for the skill...
```

### Front-matter Fields

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `name` | string | Yes | Must match `^[a-z0-9][a-z0-9-]*[a-z0-9]$`, min 2 chars, must match directory name |
| `description` | string | Yes | Non-empty string |
| `version` | string | Yes | Valid semver: `MAJOR.MINOR.PATCH` |

### Validation Rules

1. `SKILL.md` must exist in the skill root directory
2. File must start with `---` (YAML front-matter delimiter)
3. All required fields must be present and non-empty
4. `name` must match the containing directory name
5. `version` must be a valid semantic version string

### Error Messages for Validation Failures

| Failure | Error Message |
|---------|---------------|
| No SKILL.md | `Error: Missing required manifest file (SKILL.md) in '<path>'.` |
| No front-matter | `Error: SKILL.md must start with YAML front-matter (---).` |
| Invalid YAML | `Error: Failed to parse YAML front-matter in SKILL.md: <parse_error>` |
| Missing field | `Error: SKILL.md is missing required field '<field>'.` |
| Name mismatch | `Error: Skill name '<name>' in manifest does not match directory name '<dir>'.` |
| Invalid version | `Error: Invalid version '<version>' in SKILL.md. Expected format: MAJOR.MINOR.PATCH` |

---

## Repository URL Configuration

The repository URL is configured on first use and stored in `.myskills.json`. If no configuration exists, the tool prompts for the repository URL.

**Supported URL formats**:
- SSH: `git@github.com:org/repo.git`
- HTTPS: `https://github.com/org/repo.git`

**Environment variable override**: `MYSKILLS_REPO_URL` takes precedence over the stored configuration.
