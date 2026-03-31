# Implementation Plan: MySkills - CLI Skills Manager

**Branch**: `001-skills-manager-cli` | **Date**: 2026-03-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-skills-manager-cli/spec.md`

## Summary

Build a self-contained Python CLI executable (`./myskills`) that manages AI agent skills: install, uninstall, list, import, and update skills from a private Git repository. The tool creates a primary copy in `.agents/skills/<skill_name>` and symlinks for each selected AI agent directory. Distributed as a single-file executable via PyInstaller.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: click (CLI framework), dulwich (pure Python Git), simple-term-menu (interactive selection), pyyaml (manifest parsing), paramiko (SSH credentials via dulwich[paramiko])
**Storage**: Local filesystem + Git repository (clone/pull to local cache via dulwich)
**Testing**: pytest + click.testing.CliRunner + pytest-subprocess + pytest-cov + pytest-mock
**Target Platform**: macOS and Linux (Windows out of scope for v1)
**Project Type**: CLI tool (single-file executable via PyInstaller --onefile)
**Performance Goals**: Install skill <30s excluding network (SC-001); List skills <5s (SC-002)
**Constraints**: Zero partial/inconsistent state on interruption (SC-006); self-contained executable with no runtime deps (FR-001); bundle size target 10-20 MB
**Scale/Scope**: Single developer usage; repository with tens to low-hundreds of skills; hardcoded agent list for v1 (Claude, Copilot, Cursor, Windsurf)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Code Quality — PASS
- **Readability**: Python with type hints and docstrings; descriptive naming enforced via linter.
- **Single Responsibility**: Modular architecture: separate modules for CLI parsing, Git operations, filesystem management, skill validation, and agent configuration.
- **Consistent Style**: Ruff (linter + formatter) will be configured in `pyproject.toml`. All code must pass lint/format before merge.
- **No Dead Code**: Enforced by Ruff rules (unused imports, unreachable code).
- **Error Handling**: All error paths explicitly handled. FR-010 requires graceful error handling with user-friendly messages. Rollback on interrupted operations (SC-006).

### II. Testing Standards — PASS
- **Coverage Minimum**: Every user story has acceptance scenarios that map directly to tests. All 17 FRs must have corresponding tests.
- **Test Pyramid**: Unit tests for core logic (skill validation, symlink management, agent config); integration tests for Git operations and filesystem workflows; minimal E2E tests for full command flows.
- **Test Independence**: pytest fixtures with temporary directories; no shared mutable state.
- **Determinism**: Git operations mocked; filesystem operations use temp dirs; no network calls in unit tests.
- **Descriptive Naming**: pytest-style names (e.g., `test_add_skill_creates_symlinks_for_selected_agents`).

### III. User Experience Consistency — PASS (adapted for CLI context)
- **Design System Adherence**: N/A for CLI (no visual design tokens). Consistent output formatting: structured status messages, color coding for success/error/warning if terminal supports it.
- **Interaction Patterns**: Consistent command structure (`myskills <verb> [args] [--flags]`). Confirmation prompts before destructive or additive operations (FR-016).
- **Accessibility**: N/A for WCAG compliance (CLI tool). Clear text output readable by screen readers; no color-only signaling.
- **Feedback & State Communication**: Every operation produces visible feedback: progress indication, success confirmation, error messages with actionable guidance (FR-010, FR-017 --verbose).
- **Responsive Behavior**: N/A for viewport sizes. Adapts to terminal width where practical.

### IV. Performance Requirements — PASS
- **Response Time**: Install <30s excluding network (SC-001); List <5s (SC-002). CLI commands should feel instantaneous for local operations.
- **Resource Efficiency**: Git operations use shallow clones where possible. No unbounded caches.
- **Bundle Size**: PyInstaller single-file executable; dependency count minimized to control bundle size.
- **Startup Time**: Lazy imports for heavy modules (Git operations) to keep startup snappy for help/version commands.
- **Monitoring**: `--verbose` flag (FR-017) provides detailed timing and operation logging.

### Quality Gates Compliance
1. **Lint & Format**: Ruff configured with strict rules — PLANNED
2. **Test Suite**: pytest with coverage enforcement — PLANNED
3. **Code Review**: Feature branch workflow enforced — ACTIVE (on branch `001-skills-manager-cli`)
4. **Performance Check**: Benchmark against SC-001 and SC-002 thresholds — PLANNED
5. **Accessibility Audit**: N/A (CLI tool, text output only)
6. **Constitution Compliance**: This check — PASS

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
└── myskills/
    ├── __init__.py      # Package init, version
    ├── __main__.py      # Entry point: python -m myskills
    ├── cli.py           # Click CLI definition (commands, options)
    ├── models.py        # Data classes (Skill, Agent, SkillInstallation, etc.)
    ├── git_ops.py       # Git operations via dulwich (clone, pull, push)
    ├── skill_ops.py     # Skill operations (install, remove, update, import)
    ├── manifest.py      # SKILL.md parsing and validation
    ├── symlinks.py      # Symlink creation, removal, validation
    ├── config.py        # .myskills.json read/write
    ├── agents.py        # Supported agent definitions
    ├── project.py       # Project context detection and validation
    ├── ui.py            # Terminal UI abstraction (prompts, output)
    └── rollback.py      # Atomic operation / undo stack

tests/
├── conftest.py          # Shared fixtures
├── test_cli.py          # CliRunner command tests
├── test_add.py          # Add skill logic tests
├── test_remove.py       # Remove skill logic tests
├── test_list.py         # List skills logic tests
├── test_update.py       # Update skill logic tests
├── test_import.py       # Import skill logic tests
├── test_manifest.py     # Manifest parsing tests
├── test_symlinks.py     # Symlink operations tests
├── test_rollback.py     # Atomicity and rollback tests
├── test_errors.py       # Error handling tests
└── integration/
    ├── test_git_workflow.py
    └── test_end_to_end.py
```

**Structure Decision**: Single project layout with `src/myskills/` package. The `src/` layout
is used because it enforces that tests import the installed package, not local files. This is a
CLI tool (not a web app, not a monorepo), so the single-project structure is appropriate.

## Complexity Tracking

No constitutional violations detected. All four principles pass both pre-research and post-design checks.

## Post-Design Constitution Re-check

*Re-evaluated after Phase 1 design completion.*

- **I. Code Quality** — PASS: 12 focused modules with single responsibility each. Type-hinted frozen dataclasses. Ruff linter enforced. All error paths produce explicit user-facing messages with rollback via undo stack.
- **II. Testing Standards** — PASS: pytest-cov fail_under=80%. Test pyramid: unit (9 files), integration (2 files). Injectable filesystem roots, mocked Git operations, deterministic fixtures.
- **III. User Experience Consistency** — PASS (CLI-adapted): All commands follow validate->sync->check->confirm->execute->report pattern. Consistent exit codes (0/1/2/3/130). Text-only output, no color-only signaling.
- **IV. Performance Requirements** — PASS: Dulwich with local caching meets SC-001 and SC-002. Lazy imports for heavy modules. Atomic file operations prevent resource leaks.
