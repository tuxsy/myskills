# MySkills

CLI tool to manage AI agent skills from a private Git repository. Install, uninstall, list, update, and import skills for AI coding assistants (Claude, Cursor, Copilot, Windsurf) using a single self-contained executable.

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

# Also works as a Python module
python -m myskills --version
python -m myskills --help
```

### Linting and formatting

```bash
ruff check src/ tests/
ruff format src/ tests/
```

### Running tests

```bash
pytest
```
