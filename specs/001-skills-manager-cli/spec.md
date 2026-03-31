# Feature Specification: MySkills - CLI Skills Manager

**Feature Branch**: `001-skills-manager-cli`  
**Created**: 2026-03-31  
**Status**: Draft  
**Input**: User description: "Utilidad CLI auto-ejecutable para gestionar skills de agentes IA: instalar, desinstalar, listar, importar y actualizar skills desde un repositorio privado, con soporte multi-agente y enlaces simbólicos"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install a Skill from the Repository (Priority: P1)

A developer wants to add a new skill to their project. They run the tool, browse or specify the skill they want, select which AI agents should use it, and the tool installs the skill files into the project. The primary copy is placed in the standard directory (e.g., `.agents/skills/<skill_name>`), and symbolic links are created for each additional selected agent's directory (e.g., `.claude/skills/<skill_name>`).

**Why this priority**: Installing skills is the core value proposition of the tool. Without this capability, no other feature is meaningful. This is the primary reason the tool exists.

**Independent Test**: Can be fully tested by running `./myskills add <skill_name>`, selecting target agents, and verifying that the skill files exist in the primary directory and that symlinks point correctly for each selected agent.

**Acceptance Scenarios**:

1. **Given** a project without the skill installed and a valid skills repository configured, **When** the user runs `./myskills add <skill_name>`, **Then** the tool presents a list of supported AI agents for selection.
2. **Given** the user has selected one or more AI agents, **When** the installation proceeds, **Then** the tool displays a summary of the files to be installed and requires user confirmation before placing the skill in the primary standard directory and creating symlinks in each selected agent's skill directory.
3. **Given** the user attempts to install a skill that is already installed, **When** the command runs, **Then** the tool informs the user the skill is already present and offers to reinstall or update it.
4. **Given** the skills repository is unreachable, **When** the user tries to install, **Then** the tool displays a clear error message indicating the repository cannot be accessed.

---

### User Story 2 - List Available Skills (Priority: P2)

A developer wants to discover what skills are available in the repository. They run the list command and see all available skills with their names and brief descriptions, along with an indicator of which ones are already installed in the current project.

**Why this priority**: Discoverability is essential for users to know what skills they can install. This enables informed decision-making before installation.

**Independent Test**: Can be fully tested by running `./myskills list` and verifying that all skills from the repository are displayed with their names, descriptions, and installation status.

**Acceptance Scenarios**:

1. **Given** a configured skills repository with multiple skills, **When** the user runs `./myskills list`, **Then** all available skills are displayed with their name and description.
2. **Given** some skills are already installed in the project, **When** the list is displayed, **Then** installed skills are clearly marked as such.
3. **Given** the repository is empty, **When** the user runs the list command, **Then** the tool displays a message indicating no skills are available.

---

### User Story 3 - Uninstall a Skill (Priority: P3)

A developer no longer needs a skill and wants to remove it completely. They run the uninstall command, and the tool removes the primary skill directory and all associated symbolic links across all agents that were using it.

**Why this priority**: Clean removal is important for project hygiene and avoids broken references. It complements the install flow.

**Independent Test**: Can be fully tested by installing a skill with multiple agents, then running `./myskills remove <skill_name>` and verifying that both the primary directory and all symlinks are removed.

**Acceptance Scenarios**:

1. **Given** a skill is installed and linked to multiple agents, **When** the user runs `./myskills remove <skill_name>`, **Then** the primary skill directory and all agent symlinks are removed.
2. **Given** the user tries to uninstall a skill that is not installed, **When** the command runs, **Then** the tool displays a message indicating the skill is not present.
3. **Given** a symlink has been manually deleted but the primary copy remains, **When** the user runs uninstall, **Then** the tool removes the primary copy and any remaining symlinks without errors.

---

### User Story 4 - Check for Updates and Update Skills (Priority: P4)

A developer wants to ensure their installed skills are up to date. They run the update command, the tool checks the repository for newer versions, and either updates all outdated skills or lets the user choose which ones to update.

**Why this priority**: Keeping skills current is important for ongoing maintenance, but it is less critical than the ability to install and manage skills in the first place.

**Independent Test**: Can be fully tested by installing a skill, modifying the repository version to be newer, running `./myskills update`, and verifying the local skill files match the updated repository version.

**Acceptance Scenarios**:

1. **Given** installed skills have newer versions in the repository, **When** the user runs `./myskills update`, **Then** the tool lists which skills have available updates.
2. **Given** the user confirms the update, **When** the update proceeds, **Then** skill files in the primary directory are replaced with the new version and symlinks remain intact.
3. **Given** all installed skills are already up to date, **When** the user runs update, **Then** the tool displays a message indicating everything is current.

---

### User Story 5 - Import a Skill to the Repository (Priority: P5)

A developer has created a custom skill in their project and wants to share it by importing it into the private skills repository. They run the import command, specify the skill directory, and the tool packages and pushes it to the repository.

**Why this priority**: Importing enables the repository to grow organically from real project needs. However, it is a less frequent operation than installing or managing existing skills.

**Independent Test**: Can be fully tested by creating a skill in a project, running `./myskills import <path_to_skill>`, and verifying the skill appears in the repository and can be listed/installed by other projects.

**Acceptance Scenarios**:

1. **Given** a valid skill directory exists in the project, **When** the user runs `./myskills import <path_to_skill>`, **Then** the skill is packaged and added to the private repository.
2. **Given** a skill with the same name already exists in the repository, **When** the user imports, **Then** the tool warns about the conflict and asks whether to overwrite or rename.
3. **Given** the specified path does not contain a valid skill structure, **When** the import command runs, **Then** the tool displays an error describing what is missing or invalid.

---

### Edge Cases

- What happens when symlink creation fails due to file system permissions? The tool should display a clear error identifying which agent directory could not be linked and suggest corrective actions.
- What happens when the primary skill directory is deleted but symlinks still exist? The tool should detect dangling symlinks during list or update operations and offer to clean them up.
- What happens when the user runs the tool outside of a project directory (no project context)? The tool should display an error indicating it must be run from within a project root.
- What happens when network connectivity is lost mid-operation (e.g., during install or update)? The tool should not leave the project in a partially modified state; it should roll back incomplete changes.
- What happens when a skill has dependencies on other skills? For v1, the tool should inform the user of dependencies but not automatically resolve them (documented as assumption).
- What happens when the private repository requires authentication and credentials are missing or expired? The tool should prompt for authentication or display a clear message about how to configure access.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST be a self-contained executable that can be invoked directly (e.g., `./myskills`) without requiring a package manager or runtime wrapper like `npx`. It will be implemented in Python and distributed as a bundled single-file executable using PyInstaller or a similar tool.
- **FR-002**: The tool MUST support an `add` command that installs a skill from the private repository into the current project.
- **FR-003**: During installation, the tool MUST present a list of supported AI agents and allow the user to select which agents should use the skill.
- **FR-004**: The tool MUST install the skill files into a primary standard directory (e.g., `.agents/skills/<skill_name>`) and create symbolic links in each additional selected agent's skill directory (e.g., `.claude/skills/<skill_name>`).
- **FR-005**: The tool MUST support a `list` command that displays all skills available in the repository along with their installation status in the current project.
- **FR-006**: The tool MUST support a `remove` command that uninstalls a skill by removing the primary directory and all associated symbolic links across all agents.
- **FR-007**: The tool MUST support an `update` command that checks installed skills against the repository and updates outdated skills.
- **FR-008**: The tool MUST support an `import` command that takes a local skill directory and publishes it to the private repository.
- **FR-009**: The tool MUST connect to a private skills repository via Git (clone/pull) to fetch, list, and publish skills. The repository is a standard Git repository accessed using the user's existing Git credentials (SSH keys or HTTPS tokens).
- **FR-010**: The tool MUST gracefully handle errors (network failures, permission issues, missing files) with user-friendly messages and without leaving the project in an inconsistent state.
- **FR-011**: The tool MUST detect and warn about already-installed skills during installation, and missing skills during uninstallation.
- **FR-012**: The tool MUST validate that it is being run from within a project directory before performing any operations.
- **FR-013**: The tool MUST detect and handle dangling symbolic links (e.g., when a primary skill directory was manually removed).
- **FR-014**: The tool MUST ship with a hardcoded list of supported AI agents (e.g., Claude, Copilot, Cursor) in the initial release. Support for user-configurable agent definitions will be added in a future version.
- **FR-015**: The tool MUST validate the presence and correctness of a skill manifest file (e.g., `SKILL.md` or `skill.json`) during install, import, and update operations. A missing or malformed manifest MUST produce a clear error describing what is missing or invalid.
- **FR-016**: Before installing or updating a skill, the tool MUST display a summary of the files that will be added, modified, or removed, and require explicit user confirmation before proceeding.
- **FR-017**: The tool MUST support a `--verbose` flag on all commands that outputs detailed operation information (Git commands executed, files copied, symlinks created/removed, error details) for troubleshooting purposes.

### Key Entities

- **Skill**: A self-contained package of files that provides a specific capability to an AI agent. Has a name, description, version, and a set of files. Each skill MUST contain a manifest file (e.g., `SKILL.md` with front-matter or `skill.json`) that declares its metadata (name, description, version). A directory without a valid manifest is not considered a valid skill. Lives in the repository and can be installed into projects.
- **Skills Repository**: A private centralized store of skills. Serves as the source of truth for available skills, their versions, and their contents.
- **Project**: The local working directory where a developer uses AI agents. Contains installed skills in agent-specific directories.
- **AI Agent**: A supported AI coding assistant (e.g., Claude, Copilot, Cursor). Each agent has a designated skill directory path within a project.
- **Skill Installation**: The relationship between a skill and a project. Tracks which agents are using the skill, the primary directory location, and the symlink locations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can install a new skill into their project in under 30 seconds (excluding network download time).
- **SC-002**: A user can list all available skills and identify which are installed in under 5 seconds.
- **SC-003**: Uninstalling a skill removes 100% of associated files and symlinks with a single command.
- **SC-004**: After updating skills, all symlinks remain valid and point to the updated primary skill files.
- **SC-005**: 95% of first-time users can successfully install a skill on their first attempt without consulting external documentation.
- **SC-006**: The tool produces no partial or inconsistent state in the project after any interrupted operation.
- **SC-007**: Importing a skill to the repository makes it immediately available for installation in other projects.

## Clarifications

### Session 2026-03-31

- Q: How does the CLI access the skills repository? → A: Git repository (cloned/pulled locally)
- Q: What defines a valid skill structure? → A: Manifest file required (e.g., SKILL.md with front-matter or skill.json)
- Q: What is the implementation language for the CLI? → A: Python with PyInstaller or similar bundling
- Q: What skill integrity verification should the tool perform on install? → A: Show file summary/diff and require user confirmation before install
- Q: Should the tool support a verbose/debug output mode? → A: --verbose flag for detailed operation output

## Assumptions

- Target users are developers familiar with command-line tools and version control workflows.
- The private skills repository is a Git repository accessible via network from the user's development environment.
- The tool will be implemented in Python and packaged as a self-contained executable via PyInstaller or similar bundling tool for macOS and Linux.
- The tool will run on macOS and Linux; Windows support is out of scope for v1.
- Skills do not have inter-skill dependencies in v1; the tool will inform users of dependencies but will not auto-resolve them.
- Authentication to the private repository uses the same Git credentials/tokens already configured in the user's development environment (e.g., SSH keys or HTTPS Git credentials).
- The tool follows the same directory conventions as skills.sh, with `.agents/skills/` as the primary standard location.
- The initial release will support a defined set of AI agents (e.g., Claude, Copilot, Cursor); additional agents can be added in future versions.
- Skill versioning follows a simple model where the latest version in the repository is considered the current version.
