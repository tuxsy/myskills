# Tasks: MySkills - CLI Skills Manager

**Input**: Design documents from `/specs/001-skills-manager-cli/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are included based on the testing strategy defined in plan.md and research.md (R-004). The project uses pytest with click.testing.CliRunner, pytest-subprocess, and real local bare repos for integration.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/myskills/` for source, `tests/` for tests at repository root
- Configured via `pyproject.toml` with `src/` layout

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency configuration, and basic structure

- [X] T001 Create project structure with `src/myskills/` and `tests/` directories per implementation plan
- [X] T002 Create `pyproject.toml` with project metadata, click/dulwich/simple-term-menu/pyyaml/paramiko dependencies, dev/test extras (pytest, pytest-cov, pytest-subprocess, pytest-mock, ruff, mypy, pyinstaller), console_scripts entry point, and ruff configuration
- [X] T003 [P] Create `src/myskills/__init__.py` with package version string
- [X] T004 [P] Create `src/myskills/__main__.py` with entry point (`python -m myskills` support)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented. All shared models, Git operations, config management, manifest parsing, UI abstraction, and rollback mechanism.

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement data models (Skill, SkillManifest, Agent, SkillInstallation, SkillsRepository, ProjectContext) in `src/myskills/models.py` per data-model.md with frozen dataclasses, validation properties, and SUPPORTED_AGENTS list
- [X] T006 [P] Implement hardcoded agent definitions (claude, cursor, copilot, windsurf) with display names and skills_dir paths in `src/myskills/agents.py` per data-model.md and R-006
- [X] T007 [P] Implement SKILL.md YAML front-matter parser and validator in `src/myskills/manifest.py` per config-contract.md validation rules (name regex, semver, directory match, required fields) using pyyaml
- [X] T008 [P] Implement project context detection and validation (find project root, verify not outside project) in `src/myskills/project.py` per FR-012
- [X] T009 [P] Implement `.myskills.json` config read/write with atomic file operations (write-to-temp-then-rename) in `src/myskills/config.py` per config-contract.md schema
- [X] T010 [P] Implement Git operations (clone, pull, sync, credential resolution with SSH/HTTPS/fallback) via dulwich in `src/myskills/git_ops.py` per R-002 credential strategy
- [X] T011 [P] Implement symlink creation, removal, and dangling symlink detection in `src/myskills/symlinks.py` per FR-004, FR-006, FR-013
- [X] T012 [P] Implement terminal UI abstraction (agent multi-select via simple-term-menu, confirmation prompts, colored output, verbose logging) in `src/myskills/ui.py` per R-003 with injectable interface for testing
- [X] T013 [P] Implement atomic operation undo stack (register steps with undo actions, execute with rollback on failure) in `src/myskills/rollback.py` per FR-010, SC-006
- [X] T014 Create Click CLI skeleton with group command, global `--verbose` and `--version` options in `src/myskills/cli.py` per cli-contract.md global options
- [X] T015 [P] Create shared test fixtures (tmp project dirs, fake git repos, FakeUI, skill directory factories) in `tests/conftest.py` per R-004 testability decisions
- [X] T016 [P] Write unit tests for manifest parsing (valid/invalid YAML, missing fields, name mismatch, invalid version) in `tests/test_manifest.py`
- [X] T017 [P] Write unit tests for symlink operations (create, remove, detect dangling) in `tests/test_symlinks.py`
- [X] T018 [P] Write unit tests for rollback mechanism (success path, failure-and-rollback, nested operations) in `tests/test_rollback.py`

**Checkpoint**: Foundation ready - all shared modules implemented and tested. User story implementation can begin.

---

## Phase 3: User Story 1 - Install a Skill from the Repository (Priority: P1) MVP

**Goal**: A developer can run `./myskills add <skill_name>`, select target agents, and have the skill installed with primary copy + symlinks.

**Independent Test**: Run `./myskills add <skill_name>`, select agents, verify primary directory exists at `.agents/skills/<skill_name>/` and symlinks point correctly for each selected agent.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T019 [P] [US1] Write tests for add skill logic (happy path, already installed, skill not found, repo unreachable) in `tests/test_add.py`
- [X] T020 [P] [US1] Write CLI tests for `add` command (CliRunner with input simulation for agent selection and confirmation) in `tests/test_cli.py` (add command section)

### Implementation for User Story 1

- [X] T021 [US1] Implement skill install orchestration (validate project, sync repo, check manifest, check already-installed, agent selection, summary display, confirm, copy files, create symlinks, update config) in `src/myskills/skill_ops.py` (`install_skill` function)
- [X] T022 [US1] Implement `add` CLI command with skill_name argument, exit codes (0/1/2/3/130), and verbose output in `src/myskills/cli.py` per cli-contract.md add command flow
- [X] T023 [US1] Add error handling for add operation: permission errors, filesystem failures, interrupted operations with rollback in `src/myskills/skill_ops.py`

**Checkpoint**: User Story 1 fully functional. `./myskills add <skill_name>` works end-to-end with agent selection, confirmation, file copy, symlinks, and rollback on failure.

---

## Phase 4: User Story 2 - List Available Skills (Priority: P2)

**Goal**: A developer can run `./myskills list` to see all available skills with names, descriptions, versions, and installation status.

**Independent Test**: Run `./myskills list` and verify all repository skills are displayed with correct names, descriptions, and `[installed]` markers matching actual installation state.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T024 [P] [US2] Write tests for list skill logic (skills available, some installed, empty repo, repo unreachable) in `tests/test_list.py`
- [X] T025 [P] [US2] Write CLI tests for `list` command (CliRunner output format verification) in `tests/test_cli.py` (list command section)

### Implementation for User Story 2

- [X] T026 [US2] Implement skill listing logic (sync repo, read all skills from repo, cross-reference with installed config, format output) in `src/myskills/skill_ops.py` (`list_skills` function)
- [X] T027 [US2] Implement `list` CLI command with exit codes (0/3) and formatted table output in `src/myskills/cli.py` per cli-contract.md list command flow

**Checkpoint**: User Story 2 fully functional. `./myskills list` displays all skills with installation status.

---

## Phase 5: User Story 3 - Uninstall a Skill (Priority: P3)

**Goal**: A developer can run `./myskills remove <skill_name>` to completely remove a skill's primary directory and all associated symlinks.

**Independent Test**: Install a skill with multiple agents, run `./myskills remove <skill_name>`, verify primary directory and all symlinks are removed, and config is updated.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T028 [P] [US3] Write tests for remove skill logic (happy path, not installed, dangling symlinks, partial removal) in `tests/test_remove.py`
- [X] T029 [P] [US3] Write CLI tests for `remove` command (CliRunner with confirmation input) in `tests/test_cli.py` (remove command section)

### Implementation for User Story 3

- [X] T030 [US3] Implement skill removal orchestration (validate project, check installed, display summary, confirm, remove symlinks, remove primary dir, update config) in `src/myskills/skill_ops.py` (`remove_skill` function)
- [X] T031 [US3] Implement `remove` CLI command with skill_name argument, exit codes (0/1/2/130), and verbose output in `src/myskills/cli.py` per cli-contract.md remove command flow
- [X] T032 [US3] Handle edge case: dangling symlinks where primary was manually deleted (detect and clean up remaining symlinks) in `src/myskills/skill_ops.py`

**Checkpoint**: User Story 3 fully functional. `./myskills remove <skill_name>` cleanly removes all traces of a skill.

---

## Phase 6: User Story 4 - Check for Updates and Update Skills (Priority: P4)

**Goal**: A developer can run `./myskills update` to check all installed skills against the repository and update outdated ones.

**Independent Test**: Install a skill, modify repo to have newer version, run `./myskills update`, verify local files match updated version and symlinks remain intact.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T033 [P] [US4] Write tests for update logic (updates available, already current, repo unreachable, symlinks preserved after update) in `tests/test_update.py`
- [X] T034 [P] [US4] Write CLI tests for `update` command (CliRunner with confirmation input, version comparison output) in `tests/test_cli.py` (update command section)

### Implementation for User Story 4

- [X] T035 [US4] Implement update checking and execution logic (sync repo, compare installed versions vs repo versions, replace primary dir files, verify symlinks, update config) in `src/myskills/skill_ops.py` (`update_skills` function)
- [X] T036 [US4] Implement `update` CLI command with exit codes (0/1/3/130), update summary display, and verbose output in `src/myskills/cli.py` per cli-contract.md update command flow
- [X] T037 [US4] Ensure update uses rollback mechanism so partial updates don't leave inconsistent state in `src/myskills/skill_ops.py`

**Checkpoint**: User Story 4 fully functional. `./myskills update` detects and applies skill updates while preserving symlinks.

---

## Phase 7: User Story 5 - Import a Skill to the Repository (Priority: P5)

**Goal**: A developer can run `./myskills import <path>` to publish a local skill directory to the private skills repository.

**Independent Test**: Create a skill directory with valid SKILL.md, run `./myskills import <path>`, verify the skill appears in the repository and can be listed.

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T038 [P] [US5] Write tests for import logic (happy path, duplicate name conflict, invalid manifest, push failure) in `tests/test_import.py`
- [ ] T039 [P] [US5] Write CLI tests for `import` command (CliRunner with path arg and confirmation) in `tests/test_cli.py` (import command section)

### Implementation for User Story 5

- [ ] T040 [US5] Implement skill import orchestration (validate manifest at path, sync repo, check name conflict, display summary, confirm, copy to repo clone, commit, push) in `src/myskills/skill_ops.py` (`import_skill` function)
- [ ] T041 [US5] Implement `import` CLI command with path argument, exit codes (0/1/2/3/130), and verbose output in `src/myskills/cli.py` per cli-contract.md import command flow
- [ ] T042 [US5] Handle name conflict resolution (prompt for overwrite/rename/abort) in `src/myskills/skill_ops.py`

**Checkpoint**: User Story 5 fully functional. `./myskills import <path>` publishes skills to the repository.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Error handling hardening, integration testing, edge cases, and build configuration

- [ ] T043 [P] Write comprehensive error handling tests (permission errors, network failures, disk full, corrupted config) in `tests/test_errors.py`
- [ ] T044 [P] Write Git workflow integration tests with real local bare repos in `tests/integration/test_git_workflow.py` per R-004
- [ ] T045 [P] Write end-to-end tests for full CLI command flows (add, list, remove, update, import) in `tests/integration/test_end_to_end.py`
- [ ] T046 Implement dangling symlink detection and cleanup offer during `list` and `update` commands per FR-013 edge case in `src/myskills/skill_ops.py`
- [ ] T047 [P] Create PyInstaller spec file (`myskills.spec`) with --onefile mode, lazy imports, excluded modules (tkinter, unittest, email, html, http, xml, pydoc, doctest), and runtime-tmpdir per R-005
- [ ] T048 Verify all exit codes match cli-contract.md (0/1/2/3/130) across all commands in `src/myskills/cli.py`
- [ ] T049 Run full test suite with coverage enforcement (`pytest --cov=myskills --cov-fail-under=80`) and fix any gaps
- [ ] T050 Run `ruff check src/ tests/` and `ruff format src/ tests/` to ensure code passes lint and format standards

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Phase 2 completion
  - User stories can proceed in priority order (P1 -> P2 -> P3 -> P4 -> P5)
  - US2 (List) and US3 (Remove) can run in parallel after US1 (both use foundational modules independently)
  - US4 (Update) can run in parallel with US3 or US5
  - US5 (Import) is fully independent of US2-US4
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 - No dependencies on other stories. MVP target.
- **User Story 2 (P2)**: Can start after Phase 2 - Independent of US1 (uses shared foundational modules only)
- **User Story 3 (P3)**: Can start after Phase 2 - Independent (only needs foundational symlink/config modules)
- **User Story 4 (P4)**: Can start after Phase 2 - Independent (uses git_ops sync + config comparison)
- **User Story 5 (P5)**: Can start after Phase 2 - Independent (uses git_ops push + manifest validation)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Skill operations logic before CLI command wiring
- Core flow before edge case handling
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1**: T003, T004 can run in parallel (different files)
- **Phase 2**: T006, T007, T008, T009, T010, T011, T012, T013 can all run in parallel (different files). T015, T016, T017, T018 can run in parallel (different test files)
- **Phase 3-7**: Within each story, test tasks marked [P] can run in parallel. After Phase 2, multiple stories can be worked on concurrently.
- **Phase 8**: T043, T044, T045, T047 can run in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch test tasks in parallel:
Task: T019 "Write tests for add skill logic in tests/test_add.py"
Task: T020 "Write CLI tests for add command in tests/test_cli.py"

# Then implement sequentially:
Task: T021 "Implement skill install orchestration in src/myskills/skill_ops.py"
Task: T022 "Implement add CLI command in src/myskills/cli.py"
Task: T023 "Add error handling for add operation in src/myskills/skill_ops.py"
```

## Parallel Example: Foundational Phase

```bash
# Launch all independent module implementations in parallel:
Task: T006 "Implement agent definitions in src/myskills/agents.py"
Task: T007 "Implement manifest parser in src/myskills/manifest.py"
Task: T008 "Implement project context in src/myskills/project.py"
Task: T009 "Implement config read/write in src/myskills/config.py"
Task: T010 "Implement Git operations in src/myskills/git_ops.py"
Task: T011 "Implement symlinks in src/myskills/symlinks.py"
Task: T012 "Implement UI abstraction in src/myskills/ui.py"
Task: T013 "Implement rollback mechanism in src/myskills/rollback.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T018)
3. Complete Phase 3: User Story 1 - Install (T019-T023)
4. **STOP and VALIDATE**: Test `./myskills add <skill_name>` independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational -> Foundation ready
2. Add User Story 1 (Install) -> Test independently -> MVP!
3. Add User Story 2 (List) -> Test independently -> Users can discover skills
4. Add User Story 3 (Remove) -> Test independently -> Full lifecycle management
5. Add User Story 4 (Update) -> Test independently -> Maintenance capability
6. Add User Story 5 (Import) -> Test independently -> Repository growth
7. Polish phase -> Production-ready executable

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Install) + User Story 4 (Update)
   - Developer B: User Story 2 (List) + User Story 3 (Remove)
   - Developer C: User Story 5 (Import) + Polish phase prep
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Write tests first, verify they fail, then implement
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All filesystem paths are injectable for testability (R-004)
- UI abstraction enables FakeUI injection in tests (R-004)
- Rollback undo stack ensures no partial state on interruption (SC-006)
- Exit codes per cli-contract.md: 0 (success), 1 (general error), 2 (not found), 3 (repo unreachable), 130 (user cancelled)
