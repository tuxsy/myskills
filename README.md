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

> Subcommands (`add`, `list`, `remove`, `update`, `import`) are not yet wired -- the foundational modules are in place and ready for integration.

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
