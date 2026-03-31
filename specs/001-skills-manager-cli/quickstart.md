# Quickstart: MySkills CLI

**Feature Branch**: `001-skills-manager-cli`
**Date**: 2026-03-31

## Prerequisites

- Python 3.11+
- Git (for development; not required at runtime when using the bundled executable)
- macOS or Linux

## Project Setup (Development)

```bash
# Clone the repository
git clone <repo-url>
cd myskills

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (editable mode)
pip install -e ".[dev,test]"

# Verify installation
myskills --version
myskills --help
```

## Project Structure

```
myskills/
├── pyproject.toml           # Project metadata, dependencies, build config
├── src/
│   └── myskills/
│       ├── __init__.py      # Package init, version
│       ├── __main__.py      # Entry point: python -m myskills
│       ├── cli.py           # Click CLI definition (commands, options)
│       ├── models.py        # Data classes (Skill, Agent, SkillInstallation, etc.)
│       ├── git_ops.py       # Git operations via dulwich (clone, pull, push)
│       ├── skill_ops.py     # Skill operations (install, remove, update, import)
│       ├── manifest.py      # SKILL.md parsing and validation
│       ├── symlinks.py      # Symlink creation, removal, validation
│       ├── config.py        # .myskills.json read/write
│       ├── agents.py        # Supported agent definitions
│       ├── project.py       # Project context detection and validation
│       ├── ui.py            # Terminal UI abstraction (prompts, output)
│       └── rollback.py      # Atomic operation / undo stack
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── test_cli.py          # CliRunner command tests
│   ├── test_add.py          # Add skill logic tests
│   ├── test_remove.py       # Remove skill logic tests
│   ├── test_list.py         # List skills logic tests
│   ├── test_update.py       # Update skill logic tests
│   ├── test_import.py       # Import skill logic tests
│   ├── test_manifest.py     # Manifest parsing tests
│   ├── test_symlinks.py     # Symlink operations tests
│   ├── test_rollback.py     # Atomicity and rollback tests
│   ├── test_errors.py       # Error handling tests
│   └── integration/
│       ├── test_git_workflow.py
│       └── test_end_to_end.py
├── myskills.spec             # PyInstaller build spec
└── PURPOSE.md
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=myskills --cov-report=term-missing

# Run only unit tests (skip integration)
pytest -m "not integration"

# Run only integration tests
pytest -m integration

# Run with verbose output
pytest -v
```

## Building the Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build single-file executable
pyinstaller myskills.spec

# Or build directly
pyinstaller --onefile --name myskills src/myskills/__main__.py

# Test the built executable
./dist/myskills --version
./dist/myskills list
```

## Linting and Formatting

```bash
# Check lint
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/

# Type check
mypy src/myskills/
```

## Key Development Patterns

### 1. All filesystem paths are injectable
Every function accepts a `base_dir` or `project_root` parameter. Never hardcode paths.

### 2. UI is abstracted
Interactive prompts go through `ui.py`, enabling test injection via `FakeUI`.

### 3. Operations use undo stacks
Destructive operations (install, remove, update) use `rollback.py` to ensure atomicity.

### 4. Git operations are isolated
All dulwich interactions live in `git_ops.py` behind a clean interface, enabling subprocess fallback.

## Configuration

The tool needs a Git repository URL on first use. Configure via:

```bash
# Environment variable (highest priority)
export MYSKILLS_REPO_URL="git@github.com:myorg/ai-skills.git"

# Or the tool will prompt on first run
./myskills list
# > No repository configured. Enter repository URL: _
```
