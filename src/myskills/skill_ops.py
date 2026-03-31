"""Skill operations: install, remove, update, import orchestration."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from myskills.agents import SUPPORTED_AGENTS, get_agent_by_id
from myskills.config import CONFIG_VERSION, read_config, write_config
from myskills.git_ops import GitError, clone_repository, pull_repository
from myskills.manifest import ManifestError, parse_manifest
from myskills.models import ProjectContext, Skill, SkillsRepository
from myskills.rollback import UndoStack
from myskills.symlinks import create_skill_symlinks, remove_skill_symlinks
from myskills.ui import UIProvider


class SkillOperationError(Exception):
    """Raised when skill operations fail."""


def sync_repository(repo: SkillsRepository, ui: UIProvider) -> None:
    """Sync repository (clone if needed, pull if exists).

    Args:
        repo: SkillsRepository instance.
        ui: UI provider for user feedback.

    Raises:
        GitError: If sync fails.
    """
    ui.verbose(f"Syncing repository: {repo.url}")

    if not repo.is_cloned:
        ui.info("Cloning repository...")
        clone_repository(repo.url, repo.local_cache, verbose=True)
        ui.verbose(f"Repository cloned to {repo.local_cache}")
    else:
        ui.verbose("Pulling latest changes...")
        pull_repository(repo.local_cache, verbose=True)
        ui.verbose("Repository updated")


def get_skill_from_repo(skill_name: str, repo: SkillsRepository) -> Skill:
    """Load a skill from the repository.

    Args:
        skill_name: Name of the skill to load.
        repo: SkillsRepository instance.

    Returns:
        Skill instance.

    Raises:
        SkillOperationError: If skill not found or invalid manifest.
    """
    skill_dir = repo.local_cache / skill_name

    if not skill_dir.exists():
        raise SkillOperationError(
            f"Skill '{skill_name}' not found in repository.\n"
            "Use 'myskills list' to see available skills."
        )

    try:
        manifest = parse_manifest(skill_dir)
    except ManifestError as e:
        raise SkillOperationError(f"Invalid skill manifest: {e}") from e

    return Skill(
        name=manifest.name,
        description=manifest.description,
        version=manifest.version,
        path=skill_dir,
    )


def is_skill_installed(skill_name: str, project: ProjectContext) -> bool:
    """Check if a skill is already installed.

    Args:
        skill_name: Name of the skill.
        project: ProjectContext instance.

    Returns:
        True if skill is installed.
    """
    if not project.config_path.exists():
        return False

    config = read_config(project.config_path)
    return skill_name in config.get("installations", {})


def install_skill(
    skill_name: str,
    project: ProjectContext,
    repo: SkillsRepository,
    ui: UIProvider,
) -> None:
    """Install a skill from the repository.

    Flow:
    1. Validate project context
    2. Sync repository
    3. Load and validate skill manifest
    4. Check if already installed (prompt for action)
    5. Agent selection (multi-select)
    6. Display installation summary
    7. Confirm with user
    8. Copy skill files to primary directory
    9. Create symlinks for selected agents
    10. Update config
    11. Display success message

    Args:
        skill_name: Name of the skill to install.
        project: ProjectContext instance.
        repo: SkillsRepository instance.
        ui: UI provider for user interaction.

    Raises:
        SkillOperationError: If installation fails.
        GitError: If repository sync fails.
    """
    # 1. Validate project context
    if not project.root.exists():
        raise SkillOperationError(f"Project root '{project.root}' does not exist.")

    # 2. Sync repository
    try:
        sync_repository(repo, ui)
    except GitError as e:
        ui.error(f"Failed to sync repository: {e}")
        raise

    # 3. Load and validate skill
    skill = get_skill_from_repo(skill_name, repo)
    ui.verbose(f"Found skill: {skill.name} (v{skill.version}) - {skill.description}")

    # 4. Check if already installed
    if is_skill_installed(skill_name, project):
        ui.warning(f"Skill '{skill_name}' is already installed.")
        action = ui.select_action(
            "Choose an action:",
            ["[R]einstall", "[U]pdate", "[A]bort"],
        )

        if action == 2:  # Abort
            ui.info("Aborted.")
            raise SkillOperationError("User aborted installation.")
        elif action == 1:  # Update
            ui.info("Update functionality not yet implemented. Please use 'myskills update'.")
            raise SkillOperationError("Update not implemented in add command.")
        # action == 0: Reinstall - continue with installation

    # 5. Agent selection
    agent_options = [agent.display_name for agent in SUPPORTED_AGENTS]
    ui.info(f"\nSelect agents to install '{skill_name}' for:")

    selected_indices = ui.multi_select(
        title="Select agents (Space to toggle, Enter to confirm):",
        options=agent_options,
    )

    if not selected_indices:
        ui.warning("No agents selected. Installation cancelled.")
        raise SkillOperationError("No agents selected.")

    selected_agents = [SUPPORTED_AGENTS[i] for i in selected_indices]
    ui.verbose(f"Selected agents: {[a.id for a in selected_agents]}")

    # 6. Display installation summary
    ui.info("\nInstallation summary:")
    primary_path = project.primary_skills_dir / skill_name
    ui.info(f"  Primary: {primary_path.relative_to(project.root)}/")

    file_count = len(skill.files)
    ui.info(f"    Files: {file_count}")

    ui.info("  Symlinks:")
    for agent in selected_agents:
        symlink_path = project.root / agent.skills_dir / skill_name
        ui.info(
            f"    {symlink_path.relative_to(project.root)} -> {primary_path.relative_to(project.root)}"
        )

    # 7. Confirm with user
    if not ui.confirm("\nProceed with installation?", default=False):
        ui.info("Installation cancelled.")
        raise SkillOperationError("User cancelled installation.")

    # 8-10. Execute installation with rollback on failure
    undo_stack = UndoStack(verbose=False)

    # Step 1: Copy skill files to primary directory
    def copy_skill_files() -> None:
        try:
            primary_path.parent.mkdir(parents=True, exist_ok=True)

            # If primary path already exists (reinstall), remove it first
            if primary_path.exists():
                shutil.rmtree(primary_path)
                ui.verbose(f"Removed existing installation at {primary_path}")

            shutil.copytree(skill.path, primary_path)
            ui.verbose(f"Copied skill files to {primary_path}")
        except OSError as e:
            raise SkillOperationError(
                f"Failed to copy skill files: {e}\n"
                f"Check file permissions and available disk space."
            ) from e

    def undo_copy_skill_files() -> None:
        if primary_path.exists():
            try:
                shutil.rmtree(primary_path)
                ui.verbose(f"Removed primary directory: {primary_path}")
            except OSError as e:
                ui.warning(f"Failed to remove primary directory during rollback: {e}")

    undo_stack.add("Copy skill files", copy_skill_files, undo_copy_skill_files)

    # Step 2: Create symlinks
    created_symlinks: list[Path] = []

    def create_symlinks() -> None:
        nonlocal created_symlinks
        agent_dirs = [agent.skills_dir for agent in selected_agents]
        try:
            created_symlinks = create_skill_symlinks(
                primary_dir=primary_path,
                project_root=project.root,
                agent_skills_dirs=agent_dirs,
                skill_name=skill_name,
            )
            ui.verbose(f"Created {len(created_symlinks)} symlinks")
        except Exception as e:
            raise SkillOperationError(
                f"Failed to create symlinks: {e}\n"
                f"The skill files were copied but symlinks could not be created."
            ) from e

    def undo_create_symlinks() -> None:
        for symlink in created_symlinks:
            if symlink.is_symlink():
                try:
                    symlink.unlink()
                    ui.verbose(f"Removed symlink: {symlink}")
                except OSError as e:
                    ui.warning(f"Failed to remove symlink {symlink} during rollback: {e}")

    undo_stack.add("Create symlinks", create_symlinks, undo_create_symlinks)

    # Step 3: Update config
    original_config = None

    def update_config() -> None:
        nonlocal original_config
        try:
            # Read existing config or create default
            if project.config_path.exists():
                config = read_config(project.config_path)
                original_config = config.copy()
            else:
                config = {
                    "version": CONFIG_VERSION,
                    "repository": repo.url,
                    "installations": {},
                }
                original_config = None

            # Add installation entry
            config["installations"][skill_name] = {
                "version": skill.version,
                "agents": [agent.id for agent in selected_agents],
                "installed_at": datetime.utcnow().isoformat() + "Z",
            }

            write_config(project.config_path, config)
            ui.verbose("Updated configuration")
        except Exception as e:
            raise SkillOperationError(
                f"Failed to update configuration: {e}\n"
                f"The skill was installed but configuration tracking failed."
            ) from e

    def undo_update_config() -> None:
        try:
            if original_config is not None:
                write_config(project.config_path, original_config)
                ui.verbose("Restored original configuration")
            elif project.config_path.exists():
                project.config_path.unlink()
                ui.verbose("Removed configuration file")
        except Exception as e:
            ui.warning(f"Failed to restore configuration during rollback: {e}")

    undo_stack.add("Update config", update_config, undo_update_config)

    # Execute all steps with rollback on failure
    try:
        undo_stack.execute()
    except Exception as e:
        ui.error(f"Installation failed: {e}")
        raise SkillOperationError(f"Installation failed: {e}") from e

    # 11. Display success message
    agent_names = ", ".join(agent.id for agent in selected_agents)
    ui.success(f"Installed {skill_name} (v{skill.version}) for {agent_names}")
