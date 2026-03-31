# Research: MySkills CLI Skills Manager

**Feature Branch**: `001-skills-manager-cli`
**Date**: 2026-03-31

## R-001: CLI Framework

**Decision**: click (v8.x)

**Rationale**: click is the best choice for a PyInstaller-bundled CLI tool. It is pure Python (108 KB wheel), has an official PyInstaller hook, and provides clean decorator-based subcommand support. Production/Stable status on PyPI, maintained by Pallets (Flask maintainers), BSD-3 license, 10+ year track record. AWS CLI is built on click and ships as bundled executables -- battle-tested path.

**Alternatives considered**:
- **argparse (stdlib)**: Zero dependencies and perfect PyInstaller compatibility, but verbose boilerplate (~3x more code for 5+ subcommands). Help formatting is plain. Rejected because the code savings and cleaner API from click justify the single lightweight dependency.
- **typer**: Least boilerplate via type hints, but transitive dependency chain (click + rich + shellingham + pygments + markdown-it-py) creates PyInstaller friction. Still classified as Beta on PyPI. Bundle size penalty is significant (~2-5 MB added vs ~108 KB for click). Rejected due to bundling complexity and Beta status.

---

## R-002: Git Interaction

**Decision**: dulwich (pure Python mode)

**Rationale**: dulwich is a pure Python Git implementation that requires no external `git` binary, making the PyInstaller bundle truly self-contained. The `porcelain` module provides high-level `clone()`, `pull()`, `push()`, and direct repo object access that maps directly to requirements. Active maintenance (v1.1.0 released Feb 2026), supports Python 3.10-3.14. Pure Python mode adds ~2-3 MB to the bundle with zero native dependencies.

**Credential handling**: dulwich doesn't automatically use system git credential helpers. For SSH, install with `dulwich[paramiko]` for SSH agent support. For HTTPS, pass username/password (token) directly. A fallback to system `git` via subprocess can be provided when dulwich's credential handling is insufficient and `git` is available on the PATH.

**Alternatives considered**:
- **GitPython**: Wraps the system `git` binary via subprocess. Requires `git` installed on the user's system at runtime -- defeats the purpose of PyInstaller bundling for self-containment. Rejected.
- **subprocess calls to git**: Same fundamental problem as GitPython (requires system `git`). However, kept as a fallback strategy for edge cases.
- **pygit2**: Python bindings to libgit2 (C library). Requires bundling libgit2 + OpenSSL + libssh2 shared libraries. No PyInstaller hook exists. Cross-platform builds become complex. Rejected due to native dependency complexity.

**Important note**: While dulwich handles most operations, the spec states (FR-009, Assumptions) that the repository uses the user's existing Git credentials. A credential resolution strategy is needed:
1. SSH: paramiko integration discovers SSH agent keys automatically
2. HTTPS: detect credentials from environment variables, `.netrc`, or git credential helper output
3. Fallback: if dulwich fails authentication, attempt the operation via system `git` if available

---

## R-003: Terminal User Interaction

**Decision**: click built-in prompts + simple-term-menu for multi-select

**Rationale**: Minimizing dependency weight for PyInstaller bundling. click provides `click.confirm()` and `click.secho()` (colored output) at zero additional cost (already the CLI framework). simple-term-menu adds multi-select checkbox capability with zero dependencies (28 KB, single file), and the project itself ships PyInstaller binaries -- proven compatibility. Total added weight: ~136 KB, zero transitive dependencies beyond click.

**Alternatives considered**:
- **questionary + rich**: Best API polish (questionary for input, rich for output). However, questionary depends on prompt_toolkit (~700 KB), and rich adds ~590 KB + pygments (~4.5 MB). Too heavy for a self-contained CLI tool where colored `click.secho()` is sufficient.
- **inquirer (python-inquirer)**: `blessed` dependency causes real PyInstaller issues (curses/terminfo database lookups). Multiple open GitHub issues about PyInstaller. Rejected.
- **rich alone**: Output-only library, no multi-select capability. Would still need another library for interactive selection.

---

## R-004: Testing Strategy

**Decision**: pytest with click.testing.CliRunner, pytest-subprocess, real local bare repos for integration

**Rationale**: pytest is the standard Python testing framework. click's CliRunner enables in-process command testing with prompt simulation via `input=`. pytest-subprocess fakes git subprocess calls for fast unit tests. Real local bare git repos provide full-fidelity integration testing without network access.

**Key architectural decisions for testability**:
1. **Injectable filesystem root**: Every function accepts a `base_dir` or `skills_dir` parameter so `tmp_path` can be passed in tests.
2. **Prompt abstraction layer**: Wrap simple-term-menu in a thin interface so tests can inject a FakePromptUI that returns predetermined selections.
3. **Rollback as undo stack**: Implement operations as steps with corresponding undo actions, making it trivially testable by injecting failures at each step.
4. **Marker-based test separation**: `@pytest.mark.integration` for real git operations, enabling fast feedback with `pytest -m "not integration"`.

**Test dependencies**: pytest, pytest-cov (coverage, fail_under=80), pytest-subprocess (git mocking), pytest-mock (internal function mocking)

**Test organization**:
```
tests/
    conftest.py              # Shared fixtures: git_repo, skill_dir, fake_ui
    test_cli.py              # CliRunner-based tests for each subcommand
    test_add.py              # Unit tests for add logic
    test_remove.py           # Unit tests for remove logic
    test_list.py             # Unit tests for list logic
    test_update.py           # Unit tests for update/pull logic
    test_import.py           # Unit tests for import logic
    test_rollback.py         # Atomicity and rollback scenarios
    test_errors.py           # Permission, network, disk-full error paths
    integration/
        test_git_workflow.py # Real local bare repo tests
        test_end_to_end.py   # Full CLI invocation with real filesystem
```

---

## R-005: PyInstaller Bundling Strategy

**Decision**: PyInstaller with `--onefile` mode and `.spec` file

**Rationale**: PyInstaller is the most mature and widely tested Python bundling tool. `--onefile` mode produces a single distributable binary -- the expected UX for CLI tools. A `.spec` file ensures reproducible builds.

**Key configuration decisions**:
- **Mode**: `--onefile` for distribution simplicity (users expect a single binary)
- **Startup optimization**: Lazy imports for heavy modules (dulwich, paramiko). Exclude unused stdlib modules (tkinter, unittest, email, html, http, xml, pydoc, doctest). Use `--runtime-tmpdir ~/.cache/myskills` for persistent extraction caching.
- **Platform builds**: CI/CD matrix builds required (cannot cross-compile). macOS arm64 + x86_64, Linux x86_64 (build on Ubuntu 20.04 for glibc compatibility).
- **Size target**: 10-20 MB for an optimized CLI tool.
- **macOS signing**: `codesign --force --sign -` for ad-hoc signing post-build.

**Alternatives considered**:
- **Nuitka**: Compiles to C for faster runtime and smaller binaries, but slower build times and C compiler dependency. Good alternative if PyInstaller's size/perf is insufficient.
- **shiv**: Requires Python on target machine -- not self-contained. Disqualified.
- **PyOxidizer**: Rust-based, less mature ecosystem, complex Starlark configuration. Risky for production.
- **cx_Freeze**: No native `--onefile` mode, less actively maintained.

---

## R-006: Supported AI Agents Configuration

**Decision**: Hardcoded agent definitions in a Python dict/dataclass

**Rationale**: FR-014 specifies a hardcoded list for v1. A simple Python data structure is sufficient and avoids over-engineering.

**Agent directory conventions** (based on spec and common patterns):

| Agent | Primary Dir | Skills Subdir | Notes |
|-------|-------------|---------------|-------|
| Claude | `.claude/` | `.claude/skills/<skill_name>` | OpenCode/Claude Code convention |
| Copilot | `.github/` | `.github/copilot-instructions/skills/<skill_name>` | TBD - needs validation |
| Cursor | `.cursor/` | `.cursor/skills/<skill_name>` | Cursor convention |
| Windsurf | `.windsurf/` | `.windsurf/skills/<skill_name>` | Windsurf convention |

**Note**: The exact directory paths for each agent need to be validated against current agent documentation. The primary copy lives in `.agents/skills/<skill_name>` per FR-004 and existing convention.

---

## R-007: Skill Manifest Format

**Decision**: `SKILL.md` with YAML front-matter as the primary manifest format

**Rationale**: The spec mentions both `SKILL.md` and `skill.json` (FR-015). `SKILL.md` with YAML front-matter is the existing convention in the project (`.agents/skills/` structure already uses `SKILL.md`). This approach provides both machine-readable metadata (YAML front-matter) and human-readable documentation (markdown body) in a single file.

**Required front-matter fields**:
```yaml
---
name: skill-name
description: Brief description of what the skill does
version: 1.0.0
---
```

**Validation rules**:
- `name` is required, must match directory name
- `description` is required, non-empty string
- `version` is required, must be valid semver
- Markdown body may be empty but front-matter must be parseable

**YAML parsing**: Use PyYAML (`pyyaml`) for front-matter parsing. Pure Python, well-supported by PyInstaller, minimal size impact.

---

## R-008: Repository Structure Convention

**Decision**: Flat directory structure in the skills repository

**Rationale**: Simple and predictable. Each skill is a top-level directory in the repository.

**Expected repository layout**:
```
skills-repo/
├── skill-a/
│   ├── SKILL.md          # Manifest (YAML front-matter)
│   ├── instructions.md   # Skill instructions
│   └── ...               # Other skill files
├── skill-b/
│   ├── SKILL.md
│   └── ...
└── README.md             # Optional repository documentation
```

**Version tracking**: Skill versioning uses the `version` field in `SKILL.md` front-matter. The repository always has the latest version. Local installed version is compared against repository version for update detection.
