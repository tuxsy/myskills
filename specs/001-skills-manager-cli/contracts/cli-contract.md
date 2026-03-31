# CLI Contract: MySkills

**Feature Branch**: `001-skills-manager-cli`
**Date**: 2026-03-31

This document defines the command-line interface contract for the `myskills` CLI tool. All commands, arguments, options, and expected outputs are specified here.

## Global Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--verbose` | `-v` | flag | `false` | Enable detailed operation output (FR-017) |
| `--help` | `-h` | flag | - | Show help message and exit |
| `--version` | | flag | - | Show version and exit |

## Commands

### `myskills add <skill_name>`

Install a skill from the repository into the current project.

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `skill_name` | Yes | Name of the skill to install |

**Flow**:
1. Validate project context (FR-012)
2. Sync repository (clone or pull)
3. Validate skill exists in repository and has valid manifest (FR-015)
4. Check if skill is already installed (FR-011)
   - If installed: prompt to reinstall/update or abort
5. Present multi-select list of supported AI agents (FR-003)
6. Display installation summary (files to be added) (FR-016)
7. Require user confirmation (FR-016)
8. Copy skill to `.agents/skills/<skill_name>/` (FR-004)
9. Create symlinks in each selected agent directory (FR-004)
10. Update `.myskills.json` configuration
11. Display success message

**Exit codes**:
| Code | Meaning |
|------|---------|
| 0 | Skill installed successfully |
| 1 | General error (invalid manifest, permission error, etc.) |
| 2 | Skill not found in repository |
| 3 | Repository unreachable |
| 130 | User cancelled (Ctrl+C or declined confirmation) |

**Output examples**:

```
$ ./myskills add find-skills
Syncing repository...
Found skill: find-skills (v1.0.0) - Helps discover and install agent skills

Select agents to install for:
 [x] Claude
 [ ] Cursor
 [x] Windsurf
 [ ] Copilot

Installation summary:
  Primary: .agents/skills/find-skills/
    SKILL.md (1.2 KB)
    instructions.md (3.4 KB)
  Symlinks:
    .claude/skills/find-skills -> .agents/skills/find-skills
    .windsurf/skills/find-skills -> .agents/skills/find-skills

Proceed? [y/N]: y
Installed find-skills (v1.0.0) for claude, windsurf
```

```
$ ./myskills add nonexistent
Error: Skill 'nonexistent' not found in repository.
Use 'myskills list' to see available skills.
```

```
$ ./myskills add find-skills  # already installed
Skill 'find-skills' is already installed (v1.0.0).
  [R]einstall  [U]pdate  [A]bort: a
Aborted.
```

---

### `myskills list`

Display all available skills and their installation status.

**Arguments**: None

**Flow**:
1. Validate project context (FR-012)
2. Sync repository (clone or pull)
3. Read all skills from repository
4. Check installation status for each skill
5. Display formatted list

**Exit codes**:
| Code | Meaning |
|------|---------|
| 0 | Success |
| 3 | Repository unreachable |

**Output examples**:

```
$ ./myskills list
Available skills (3 total):

  find-skills      v1.0.0  [installed]  Helps discover and install agent skills
  code-review      v2.1.0  [installed]  Reviews code for best practices
  test-generator   v1.3.0              Generates test scaffolds from code

Installed: 2/3
```

```
$ ./myskills list
Available skills (0 total):

  No skills available in repository.
```

---

### `myskills remove <skill_name>`

Uninstall a skill by removing primary directory and all symlinks.

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `skill_name` | Yes | Name of the skill to remove |

**Flow**:
1. Validate project context (FR-012)
2. Check if skill is installed (FR-011)
3. Display removal summary (files and symlinks to be removed)
4. Require user confirmation
5. Remove all agent symlinks (FR-006)
6. Remove primary skill directory (FR-006)
7. Update `.myskills.json` configuration
8. Display success message

**Exit codes**:
| Code | Meaning |
|------|---------|
| 0 | Skill removed successfully |
| 1 | General error |
| 2 | Skill not installed |
| 130 | User cancelled |

**Output examples**:

```
$ ./myskills remove find-skills
Removal summary:
  Primary: .agents/skills/find-skills/ (2 files)
  Symlinks:
    .claude/skills/find-skills (symlink)
    .windsurf/skills/find-skills (symlink)

Remove skill and all links? [y/N]: y
Removed find-skills
```

```
$ ./myskills remove nonexistent
Error: Skill 'nonexistent' is not installed.
```

---

### `myskills update`

Check for and apply skill updates from the repository.

**Arguments**: None (updates all installed skills)

**Flow**:
1. Validate project context (FR-012)
2. Sync repository (clone or pull)
3. Compare installed skill versions against repository versions
4. List skills with available updates (FR-007)
5. If no updates: display message and exit
6. Display update summary (files to be changed per skill)
7. Require user confirmation (FR-016)
8. For each skill: replace primary directory files, verify symlinks intact (FR-007)
9. Update `.myskills.json` configuration
10. Display success message

**Exit codes**:
| Code | Meaning |
|------|---------|
| 0 | Success (updates applied or already up to date) |
| 1 | General error |
| 3 | Repository unreachable |
| 130 | User cancelled |

**Output examples**:

```
$ ./myskills update
Syncing repository...
Checking for updates...

Updates available:
  find-skills    1.0.0 -> 1.1.0
  code-review    2.1.0 -> 2.2.0

Apply updates? [y/N]: y
Updated find-skills to v1.1.0
Updated code-review to v2.2.0

All skills up to date.
```

```
$ ./myskills update
Syncing repository...
Checking for updates...

All installed skills are up to date.
```

---

### `myskills import <path>`

Import a local skill directory into the private repository.

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `path` | Yes | Path to the local skill directory to import |

**Flow**:
1. Validate project context (FR-012)
2. Validate skill directory has valid manifest (FR-015)
3. Sync repository (clone or pull)
4. Check if skill name already exists in repository (FR-008)
   - If exists: warn and prompt for overwrite/rename/abort
5. Display import summary
6. Copy skill to repository clone
7. Commit and push to repository
8. Display success message

**Exit codes**:
| Code | Meaning |
|------|---------|
| 0 | Skill imported successfully |
| 1 | General error (invalid manifest, push failure) |
| 2 | Invalid skill directory |
| 3 | Repository unreachable |
| 130 | User cancelled |

**Output examples**:

```
$ ./myskills import ./my-custom-skill
Validating skill...
Found: my-custom-skill (v1.0.0) - My custom AI skill

Import summary:
  Files to publish:
    SKILL.md (1.2 KB)
    instructions.md (2.1 KB)

Publish to repository? [y/N]: y
Imported my-custom-skill (v1.0.0) to repository.
```

```
$ ./myskills import ./bad-directory
Error: Invalid skill directory. Missing required manifest file (SKILL.md).
Expected a SKILL.md file with YAML front-matter containing: name, description, version.
```

---

## Error Message Conventions

All error messages follow this format:
```
Error: <clear description of what went wrong>
<optional: actionable suggestion for resolution>
```

Warning messages:
```
Warning: <description of non-fatal issue>
```

Verbose mode (`--verbose`) adds:
```
[verbose] <operation detail>
```

Example:
```
[verbose] Cloning repository git@github.com:org/skills.git
[verbose] Clone completed in 2.3s
[verbose] Found 15 skills in repository
[verbose] Creating symlink: .claude/skills/find-skills -> .agents/skills/find-skills
```
