# MySkills

CLI tool to manage AI agent skills from a private Git repository. Install, uninstall, list, update, and import skills for AI coding assistants (Claude, Cursor, Copilot, Windsurf) using a single self-contained executable.

## Requirements

- **Python 3.11+**
- **pip** (included with Python)
- **Git** (for cloning the repository)

## Quick Start

```bash
# Clone and enter the project
git clone <repo-url>
cd myskills

# Create a virtual environment and activate it
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev and test dependencies
pip install -e ".[dev,test]"
```

### Available commands

```bash
# Show version
myskills --version

# Show help
myskills --help

# Enable verbose output (applies to any subcommand)
myskills -v <command>

# Also works as a Python module
python -m myskills --version
python -m myskills --help
```

### Skill Management Commands

#### Install a skill from the repository

```bash
# Install a skill (interactive agent selection)
myskills add <skill-name>

# Install with verbose output
myskills -v add <skill-name>

# Example workflow:
# 1. Syncs the skills repository
# 2. Validates the skill exists
# 3. Prompts to select target agents (Claude, Cursor, Copilot, Windsurf)
# 4. Shows installation summary
# 5. Asks for confirmation
# 6. Creates primary copy in .agents/skills/<skill-name>/
# 7. Creates symlinks in selected agent directories
# 8. Updates .myskills.json configuration
```

**Exit codes:**
- `0` - Success
- `1` - General error (invalid manifest, permission error)
- `2` - Skill not found in repository
- `3` - Repository unreachable
- `130` - User cancelled (declined confirmation or Ctrl+C)

**Prerequisites:**
- Must be run from within a Git repository (project root)
- First run requires `MYSKILLS_REPO_URL` environment variable or existing `.myskills.json` configuration

**Example:**
```bash
# Set your skills repository URL (first time only)
export MYSKILLS_REPO_URL="git@github.com:your-org/skills-repo.git"

# Install a skill
myskills add find-skills

# Output:
# Syncing repository...
# Found skill: find-skills (v1.0.0) - Helps discover and install agent skills
# 
# Select agents to install 'find-skills' for:
#  [x] Claude
#  [ ] Cursor
#  [x] Windsurf
#  [ ] Copilot
# 
# Installation summary:
#   Primary: .agents/skills/find-skills/
#     Files: 3
#   Symlinks:
#     .claude/skills/find-skills -> .agents/skills/find-skills
#     .windsurf/skills/find-skills -> .agents/skills/find-skills
# 
# Proceed with installation? [y/N]: y
# Installed find-skills (v1.0.0) for claude, windsurf
```

> **Status**: `add` command is fully functional (MVP). Additional commands (`list`, `remove`, `update`, `import`) are planned for future releases.

### Running tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=myskills --cov-report=term-missing

# Run only unit tests (skip integration)
pytest -m "not integration"

# Run only integration tests
pytest -m integration

# Run a specific test file
pytest tests/test_manifest.py
pytest tests/test_symlinks.py
pytest tests/test_rollback.py
```

### Linting and formatting

```bash
# Check for lint errors
ruff check src/ tests/

# Auto-fix lint errors
ruff check --fix src/ tests/

# Check formatting
ruff format --check src/ tests/

# Apply formatting
ruff format src/ tests/
```
