# MySkills

CLI tool to manage AI agent skills from a private Git repository. Install, uninstall, list, update, and import skills for AI coding assistants (Claude, Cursor, Copilot, Windsurf) using a single self-contained executable.

## Project Status

- **Tests**: 187 passing (100% pass rate)
- **Coverage**: 80.17% code coverage
- **Quality**: All E2E and integration tests passing
- **Status**: Production-ready

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

#### List available skills

```bash
# List all skills in the repository
myskills list

# List with verbose output
myskills -v list
```

**Exit codes:**
- `0` - Success
- `3` - Repository unreachable

**Example:**
```bash
myskills list

# Output:
# Available skills (3 total):
# 
#   find-skills              v1.0.0    Helps discover and install agent skills
#                                      [✓ installed]
# 
#   code-review              v2.1.0    Reviews code for best practices and
#                                      suggests improvements
#                                      [✓ installed]
# 
#   test-generator           v1.3.0    Generates test scaffolds from code
# 
# Installed: 2/3
```

**Note:** The output uses ANSI color codes for better readability:
- Skill names appear in **bold**
- Versions appear in *italic*
- Installed markers appear in green
- Long descriptions automatically wrap and align

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

#### Uninstall a skill

```bash
# Remove a skill from the project
myskills remove <skill-name>

# Remove with verbose output
myskills -v remove <skill-name>

# Example workflow:
# 1. Checks if the skill is installed
# 2. Shows removal summary (primary directory and symlinks)
# 3. Asks for confirmation
# 4. Removes all symlinks from agent directories
# 5. Removes the primary skill directory
# 6. Updates .myskills.json configuration
```

**Exit codes:**
- `0` - Success
- `1` - General error (permission error)
- `2` - Skill not installed
- `130` - User cancelled (declined confirmation or Ctrl+C)

**Example:**
```bash
# Remove a skill
myskills remove find-skills

# Output:
# Removing skill: find-skills (v1.0.0)
#   Primary: .agents/skills/find-skills/
#   Agents: claude, windsurf
# 
# Proceed with removal? [y/N]: y
# Removed find-skills (v1.0.0)
```

**Edge cases handled:**
- Dangling symlinks (primary directory manually deleted) are automatically cleaned up
- Missing primary directory is detected and reported
- All symlinks are removed even if primary directory is gone

#### Update installed skills

```bash
# Check for and apply updates to all installed skills
myskills update

# Update with verbose output
myskills -v update

# Example workflow:
# 1. Syncs the skills repository to get latest versions
# 2. Checks each installed skill against repository versions
# 3. For skills with newer versions:
#    - Backs up the current primary directory
#    - Copies new version files to primary directory
#    - Recreates symlinks (preserves agent selections)
#    - Updates .myskills.json with new version
# 4. Reports summary of updated, current, and failed skills
```

**Exit codes:**
- `0` - Success (all updates applied or all skills current)
- `1` - General error (one or more updates failed)
- `3` - Repository unreachable

**Example:**
```bash
# Update all installed skills
myskills update

# Output:
# Syncing repository...
# Updated code-review: 2.1.0 -> 2.2.0
# find-skills is up-to-date (v1.0.0)
# 
# Summary:
#   Updated: 1
#   Current: 1
#   Failed: 0
```

**Features:**
- Atomic updates with automatic rollback on failure
- Preserves existing agent selections (symlinks)
- Handles existing symlinks gracefully (idempotent)
- Skips skills already at latest version

#### Import a local skill to the repository

```bash
# Publish a local skill directory to the repository
myskills import <path>

# Import with verbose output
myskills -v import <path>

# Example workflow:
# 1. Validates the skill directory has a valid SKILL.md manifest
# 2. Syncs the skills repository
# 3. Checks for name conflicts in the repository
# 4. Prompts for conflict resolution (overwrite/abort) if needed
# 5. Shows import summary with files to be published
# 6. Asks for confirmation
# 7. Copies the skill to the repository clone
# 8. Commits changes with descriptive message
# 9. Pushes to remote repository
```

**Exit codes:**
- `0` - Success (skill imported and pushed)
- `1` - General error (invalid manifest, push failure)
- `2` - Invalid skill directory (missing or invalid SKILL.md)
- `3` - Repository unreachable
- `130` - User cancelled (declined confirmation or Ctrl+C)

**Example:**
```bash
# Import a local skill
myskills import ./my-custom-skill

# Output:
# Validating skill directory: ./my-custom-skill
# Found: my-custom-skill (v1.0.0) - My custom AI skill
# Syncing repository...
# 
# Import summary:
#   Skill: my-custom-skill (v1.0.0)
#   Files to publish (3):
#     SKILL.md
#     instructions.md
#     README.md
# 
# Publish to repository? [y/N]: y
# Committing changes...
# Pushing to repository...
# Imported my-custom-skill (v1.0.0) to repository.
```

**Conflict handling:**
- If a skill with the same name exists, you'll be prompted to:
  - **Overwrite** - Replace the existing skill with your version
  - **Abort** - Cancel the import operation

**Requirements:**
- The skill directory must contain a valid `SKILL.md` file with YAML front-matter
- Required fields: `name`, `description`, `version` (semver format)
- The `name` in SKILL.md must match the directory name
- You must have push access to the configured repository

> **Status**: All core commands (`add`, `list`, `remove`, `update`, `import`) are fully functional and production-ready.

### Running tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=myskills --cov-report=term-missing

# Run with coverage enforcement (requires 80% minimum)
pytest --cov=myskills --cov-fail-under=80

# Run only unit tests (skip integration)
pytest -m "not integration"

# Run only integration tests
pytest -m integration

# Run a specific test file
pytest tests/test_manifest.py
pytest tests/test_symlinks.py
pytest tests/test_rollback.py
```

**Current test statistics:**
- **Total tests**: 187 (all passing)
- **Coverage**: 80.17%
- **Test types**: Unit tests, integration tests, E2E tests, error handling tests

**Environment variables for testing:**

When writing tests or running tests in CI, you can use these environment variables to control behavior:

- `MYSKILLS_CACHE_DIR` - Override the default cache directory (useful for test isolation)
- `MYSKILLS_AUTO_SELECT_AGENTS` - Comma-separated list of agents to auto-select (bypasses interactive prompt)
- `MYSKILLS_AUTO_CONFIRM` - Set to "yes" to automatically confirm prompts (for non-interactive testing)

Example test setup:
```bash
# Run tests with isolated cache
MYSKILLS_CACHE_DIR=/tmp/test-cache pytest

# Run E2E tests with auto-confirmation
MYSKILLS_AUTO_SELECT_AGENTS=claude,cursor MYSKILLS_AUTO_CONFIRM=yes pytest tests/integration/
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

## Building a Standalone Executable

You can build a standalone executable using PyInstaller for distribution without requiring Python installation:

```bash
# Install PyInstaller (included in dev dependencies)
pip install -e ".[dev]"

# Build the executable
pyinstaller myskills.spec

# The executable will be in dist/myskills
./dist/myskills --version
```

**Build configuration:**
- Single-file executable (`--onefile`)
- Optimized for size (excludes unnecessary modules like tkinter, unittest, http, xml)
- Uses runtime temp directory for unpacking
- All configuration in `myskills.spec`

**Distribution:**
After building, you can distribute the `dist/myskills` executable as a standalone binary. Users won't need Python or pip installed to use it.

## Development

### Project Structure

```
myskills/
├── src/myskills/          # Source code
│   ├── cli.py             # Click CLI commands
│   ├── skill_ops.py       # Core skill operations
│   ├── git_ops.py         # Git repository operations
│   ├── config.py          # Configuration management
│   ├── manifest.py        # SKILL.md parsing
│   ├── symlinks.py        # Symlink management
│   ├── rollback.py        # Atomic operation rollback
│   ├── ui.py              # Terminal UI abstraction
│   ├── models.py          # Data models
│   ├── agents.py          # Supported AI agents
│   └── project.py         # Project context detection
├── tests/                 # Test suite
│   ├── integration/       # Integration and E2E tests
│   └── test_*.py          # Unit tests
├── specs/                 # Design documents
└── myskills.spec          # PyInstaller configuration
```

### Contributing

1. Install in development mode with all dependencies:
   ```bash
   pip install -e ".[dev,test]"
   ```

2. Make your changes

3. Run tests and ensure they pass:
   ```bash
   pytest --cov=myskills --cov-fail-under=80
   ```

4. Format and lint your code:
   ```bash
   ruff format src/ tests/
   ruff check --fix src/ tests/
   ```

5. Commit your changes
