"""Skill operations: install, remove, update, import orchestration."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from myskills.agents import SUPPORTED_AGENTS
from myskills.config import CONFIG_VERSION, read_config, write_config
from myskills.git_ops import (
    GitError,
    clone_repository,
    commit_changes,
    pull_repository,
    push_repository,
)
from myskills.manifest import (
    ManifestError,
    parse_manifest,
    update_manifest_with_version,
    was_version_missing,
)
from myskills.models import ProjectContext, Skill, SkillsRepository
from myskills.rollback import UndoStack
from myskills.symlinks import create_skill_symlinks
from myskills.ui import UIProvider


class SkillOperationError(Exception):
    """Raised when skill operations fail."""

    def __init__(self, message: str, is_repo_error: bool = False):
        """Initialize SkillOperationError.

        Args:
            message: Error message.
            is_repo_error: Whether this is a repository connectivity error.
        """
        super().__init__(message)
        self.is_repo_error = is_repo_error


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
        # Pass ui=None since get_skill_from_repo doesn't have ui context
        manifest = parse_manifest(skill_dir, ui=None)
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


def remove_skill(
    skill_name: str,
    project: ProjectContext,
    ui: UIProvider,
) -> None:
    """Remove a skill from the project.

    Flow:
    1. Validate project context
    2. Check if skill is installed
    3. Load installation info from config
    4. Display removal summary
    5. Confirm with user
    6. Remove symlinks for all agents
    7. Remove primary directory
    8. Update config
    9. Display success message

    Args:
        skill_name: Name of the skill to remove.
        project: ProjectContext instance.
        ui: UI provider for user interaction.

    Raises:
        SkillOperationError: If removal fails or skill not installed.
    """
    # 1. Validate project context
    if not project.root.exists():
        raise SkillOperationError(f"Project root '{project.root}' does not exist.")

    # 2. Check if skill is installed
    if not is_skill_installed(skill_name, project):
        raise SkillOperationError(
            f"Skill '{skill_name}' is not installed.\nUse 'myskills list' to see installed skills."
        )

    # 3. Load installation info from config
    config = read_config(project.config_path)
    installation = config["installations"][skill_name]
    installed_agents = installation["agents"]
    installed_version = installation["version"]

    primary_dir = project.primary_skills_dir / skill_name

    # 4. Display removal summary
    ui.info(f"\nRemoving skill: {skill_name} (v{installed_version})")
    ui.info(f"  Primary: {primary_dir.relative_to(project.root)}/")

    # Check if primary directory exists (might be dangling)
    if not primary_dir.exists():
        ui.warning("  Primary directory not found (may have been manually deleted)")

    ui.info(f"  Agents: {', '.join(installed_agents)}")

    # 5. Confirm with user
    if not ui.confirm("\nProceed with removal?", default=False):
        ui.info("Removal cancelled.")
        raise SkillOperationError("User cancelled removal.")

    # 6-8. Execute removal

    # Step 1: Remove symlinks (including dangling ones)
    agent_dirs = []
    for agent in SUPPORTED_AGENTS:
        if agent.id in installed_agents:
            agent_dirs.append(agent.skills_dir)

    removed_symlinks = []
    try:
        # Check for dangling symlinks and remove them manually if needed
        for agent_dir in agent_dirs:
            link_path = project.root / agent_dir / skill_name
            if link_path.is_symlink():
                try:
                    link_path.unlink()
                    removed_symlinks.append(link_path)
                    ui.verbose(f"Removed symlink: {link_path}")
                except OSError as e:
                    ui.warning(f"Failed to remove symlink {link_path}: {e}")
    except Exception as e:
        raise SkillOperationError(
            f"Failed to remove symlinks: {e}\nSome symlinks may remain."
        ) from e

    ui.verbose(f"Removed {len(removed_symlinks)} symlinks")

    # Step 2: Remove primary directory (if it exists)
    if primary_dir.exists():
        try:
            shutil.rmtree(primary_dir)
            ui.verbose(f"Removed primary directory: {primary_dir}")
        except OSError as e:
            raise SkillOperationError(
                f"Failed to remove primary directory: {e}\n"
                f"Check file permissions and that no files are in use."
            ) from e
    else:
        ui.verbose("Primary directory already removed")

    # Step 3: Update config
    try:
        config = read_config(project.config_path)
        if skill_name in config["installations"]:
            del config["installations"][skill_name]
            write_config(project.config_path, config)
            ui.verbose("Updated configuration")
    except Exception as e:
        raise SkillOperationError(
            f"Failed to update configuration: {e}\n"
            f"The skill was removed but configuration tracking may be inconsistent."
        ) from e

    # 9. Display success message
    ui.success(f"Removed {skill_name} (v{installed_version})")


def list_skills(
    project: ProjectContext,
    repo: SkillsRepository,
    ui: UIProvider,
) -> list[dict]:
    """List all available skills in the repository with installation status.

    Flow:
    1. Validate project context
    2. Sync repository
    3. Read all skills from repository
    4. Cross-reference with installed config
    5. Return list of skill dictionaries

    Args:
        project: ProjectContext instance.
        repo: SkillsRepository instance.
        ui: UI provider for user feedback.

    Returns:
        List of skill dictionaries with keys: name, description, version, installed.
        Sorted alphabetically by name.

    Raises:
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

    # 3. Read all skills from repository
    skills = []

    # Get list of all directories in the repository
    if not repo.local_cache.exists():
        ui.warning("Repository cache does not exist")
        return []

    for item in repo.local_cache.iterdir():
        # Skip non-directories and hidden files
        if not item.is_dir() or item.name.startswith("."):
            continue

        # Try to parse manifest
        try:
            manifest = parse_manifest(item, ui=ui)
            skills.append(
                {
                    "name": manifest.name,
                    "description": manifest.description,
                    "version": manifest.version,
                    "path": item,
                }
            )
        except ManifestError as e:
            ui.warning(f"Skipping invalid skill '{item.name}': {e}")
            ui.verbose(f"Invalid manifest at {item}")
            continue

    # 4. Cross-reference with installed config
    installed_skills = set()
    if project.config_path.exists():
        config = read_config(project.config_path)
        installed_skills = set(config.get("installations", {}).keys())

    # 5. Build result list with installation status
    result = []
    for skill in skills:
        result.append(
            {
                "name": skill["name"],
                "description": skill["description"],
                "version": skill["version"],
                "installed": skill["name"] in installed_skills,
            }
        )

    # Sort by name
    result.sort(key=lambda s: s["name"])

    ui.verbose(f"Found {len(result)} skills in repository")
    ui.verbose(f"Installed: {len(installed_skills)}/{len(result)}")

    return result


def update_skills(
    project: ProjectContext,
    repo: SkillsRepository,
    ui: UIProvider,
) -> dict[str, list[str]]:
    """Check installed skills and update any that have newer versions in the repo.

    Returns a summary dict with keys: updated, current, failed.

    The function:
    1. Validates project context
    2. Syncs repository
    3. Loads installed skills from config
    4. For each installed skill, compares versions and updates if repo has newer
    5. Uses UndoStack to ensure partial updates roll back
    """
    if not project.root.exists():
        raise SkillOperationError(f"Project root '{project.root}' does not exist.")

    try:
        sync_repository(repo, ui)
    except GitError:
        ui.error("Failed to sync repository for update check")
        raise

    # Load installations
    installations = {}
    if project.config_path.exists():
        config = read_config(project.config_path)
        installations = config.get("installations", {})

    summary = {"updated": [], "current": [], "failed": []}

    # Iterate installed skills
    for skill_name, info in installations.items():
        try:
            repo_skill = get_skill_from_repo(skill_name, repo)
        except SkillOperationError:
            ui.warning(f"Skill '{skill_name}' not found in repository; skipping")
            summary["failed"].append(skill_name)
            continue

        installed_version = info.get("version")
        if repo_skill.version == installed_version:
            ui.verbose(f"{skill_name} is up-to-date (v{installed_version})")
            summary["current"].append(skill_name)
            continue

        # Prepare update: replace primary dir contents atomically using UndoStack
        primary_path = project.primary_skills_dir / skill_name

        undo_stack = UndoStack(verbose=ui.verbose_mode if hasattr(ui, "verbose_mode") else False)

        # Step: backup existing primary dir by moving it aside
        backup_dir = primary_path.with_name(primary_path.name + ".backup")

        def do_backup() -> None:
            if primary_path.exists():
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                primary_path.replace(backup_dir)
                ui.verbose(f"Backed up {primary_path} -> {backup_dir}")

        def undo_backup() -> None:
            # restore from backup if present
            if backup_dir.exists():
                if primary_path.exists():
                    shutil.rmtree(primary_path)
                backup_dir.replace(primary_path)
                ui.verbose(f"Restored backup {backup_dir} -> {primary_path}")

        undo_stack.add("Backup primary dir", do_backup, undo_backup)

        # Step: copy new files into primary location
        def do_copy_new() -> None:
            try:
                # Ensure parent exists
                primary_path.parent.mkdir(parents=True, exist_ok=True)
                # If primary exists (shouldn't after backup) remove
                if primary_path.exists():
                    shutil.rmtree(primary_path)
                shutil.copytree(repo_skill.path, primary_path)
                ui.verbose(f"Copied new version to {primary_path}")
            except OSError as e:
                raise SkillOperationError(f"Failed to copy new version: {e}") from e

        def undo_copy_new() -> None:
            if primary_path.exists():
                try:
                    shutil.rmtree(primary_path)
                    ui.verbose(f"Removed primary dir during rollback: {primary_path}")
                except OSError as e:
                    ui.warning(f"Failed to remove primary dir during rollback: {e}")

        undo_stack.add("Copy new version", do_copy_new, undo_copy_new)

        # Step: recreate symlinks based on recorded agents
        def do_create_symlinks() -> None:
            agents = info.get("agents", [])
            agent_dirs = [a.skills_dir for a in SUPPORTED_AGENTS if a.id in agents]
            create_skill_symlinks(
                primary_dir=primary_path,
                project_root=project.root,
                agent_skills_dirs=agent_dirs,
                skill_name=skill_name,
            )
            ui.verbose(f"Recreated symlinks for {skill_name}")

        def undo_create_symlinks() -> None:
            # Best-effort: remove symlinks pointing to primary_path
            for agent in SUPPORTED_AGENTS:
                if agent.id in info.get("agents", []):
                    link = project.root / agent.skills_dir / skill_name
                    try:
                        if link.is_symlink():
                            link.unlink()
                            ui.verbose(f"Removed symlink during rollback: {link}")
                    except OSError as e:
                        ui.warning(f"Failed to remove symlink during rollback: {e}")

        undo_stack.add("Create symlinks", do_create_symlinks, undo_create_symlinks)

        # Step: update config entry
        original_config = None

        def do_update_config() -> None:
            nonlocal original_config
            if project.config_path.exists():
                original_config = read_config(project.config_path).copy()
            else:
                original_config = None

            # Write new version
            from myskills.config import add_installation

            add_installation(
                project.config_path,
                repo.url,
                skill_name,
                repo_skill.version,
                info.get("agents", []),
            )
            ui.verbose("Configuration updated with new version")

        def undo_update_config() -> None:
            try:
                if original_config is not None:
                    write_config(project.config_path, original_config)
                    ui.verbose("Restored original configuration during rollback")
                elif project.config_path.exists():
                    project.config_path.unlink()

            except Exception as e:
                ui.warning(f"Failed to restore configuration during rollback: {e}")

        undo_stack.add("Update config", do_update_config, undo_update_config)

        # Execute update steps
        try:
            undo_stack.execute()
        except Exception as e:
            ui.error(f"Failed to update {skill_name}: {e}")
            summary["failed"].append(skill_name)
            # Attempt to clean backup if present
            try:
                if backup_dir.exists():
                    # If backup still exists and primary doesn't, restore
                    if not primary_path.exists():
                        backup_dir.replace(primary_path)
            except Exception:
                ui.warning("Failed to restore backup after failed update")
            continue

        # If successful, remove backup if present
        try:
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
                ui.verbose(f"Removed backup dir {backup_dir}")
        except Exception:
            ui.warning(f"Failed to remove backup dir {backup_dir}")

        ui.success(f"Updated {skill_name}: {installed_version} -> {repo_skill.version}")
        summary["updated"].append(skill_name)

    return summary


def import_skill(
    skill_path: Path,
    project: ProjectContext,
    repo: SkillsRepository,
    ui: UIProvider,
) -> None:
    """Import a local skill directory to the repository.

    Args:
        skill_path: Path to the local skill directory.
        project: ProjectContext instance.
        repo: SkillsRepository instance.
        ui: UI provider for user feedback.

    Raises:
        SystemExit: With appropriate exit code on error or cancellation.
    """
    import sys

    # 1. Validate skill directory and manifest
    ui.verbose(f"Validating skill directory: {skill_path}")

    if not skill_path.exists():
        ui.error(f"Skill directory '{skill_path}' does not exist.")
        sys.exit(2)

    if not skill_path.is_dir():
        ui.error(f"Path '{skill_path}' is not a directory.")
        sys.exit(2)

    try:
        manifest = parse_manifest(skill_path, ui=ui)
    except ManifestError as e:
        ui.error(f"Invalid skill directory. {e}")
        sys.exit(2)

    # If version was missing, add explicit version field before importing
    if was_version_missing(skill_path):
        ui.verbose(f"Adding explicit version field to {skill_path / 'SKILL.md'}")
        try:
            update_manifest_with_version(skill_path, manifest.version)
        except Exception as e:
            ui.error(f"Failed to add version field to manifest: {e}")
            sys.exit(1)

    skill_name = manifest.name
    ui.info(f"Found: {skill_name} (v{manifest.version}) - {manifest.description}")

    # 2. Sync repository
    ui.verbose("Syncing repository...")
    try:
        sync_repository(repo, ui)
    except GitError as e:
        ui.error(f"Repository unreachable: {e}")
        raise SkillOperationError(str(e), is_repo_error=True) from e

    # 3. Check if skill name already exists in repository
    repo_skill_dir = repo.local_cache / skill_name
    conflict_exists = repo_skill_dir.exists()

    if conflict_exists:
        ui.warning(f"Skill '{skill_name}' already exists in the repository.")

        # Get choice response from UI (for testing) or prompt user
        if hasattr(ui, "get_choice_response"):
            choice = ui.get_choice_response()
        else:
            # In real UI, use select_action
            action_idx = ui.select_action(
                "Choose action:",
                ["Overwrite existing skill", "Abort import"],
            )
            choice = "overwrite" if action_idx == 0 else "abort"

        if choice == "abort":
            ui.info("Import aborted.")
            sys.exit(130)

        if choice == "overwrite":
            ui.warning(f"Will overwrite existing skill '{skill_name}'")
            # Remove existing skill directory
            try:
                shutil.rmtree(repo_skill_dir)
                ui.verbose(f"Removed existing skill directory: {repo_skill_dir}")
            except Exception as e:
                ui.error(f"Failed to remove existing skill: {e}")
                sys.exit(1)

    # 4. Display import summary
    files = sorted(f.relative_to(skill_path) for f in skill_path.rglob("*") if f.is_file())
    ui.info("\nImport summary:")
    ui.info(f"  Skill: {skill_name} (v{manifest.version})")
    ui.info(f"  Files to publish ({len(files)}):")
    for f in files[:5]:  # Show first 5 files
        ui.info(f"    {f}")
    if len(files) > 5:
        ui.info(f"    ... and {len(files) - 5} more")

    # 5. Require user confirmation
    if not ui.confirm("\nPublish to repository?", default=False):
        ui.info("Import cancelled.")
        sys.exit(130)

    # 6. Copy skill to repository clone
    ui.verbose(f"Copying skill to repository: {repo_skill_dir}")
    try:
        shutil.copytree(skill_path, repo_skill_dir)
        ui.verbose(f"Copied {len(files)} files")
    except Exception as e:
        ui.error(f"Failed to copy skill files: {e}")
        sys.exit(1)

    # 7. Commit changes
    ui.verbose("Committing changes...")
    commit_message = f"Import skill: {skill_name} v{manifest.version}"
    try:
        commit_changes(repo.local_cache, message=commit_message, verbose=False)
        ui.verbose("Changes committed")
    except GitError as e:
        ui.error(f"Failed to commit changes: {e}")
        sys.exit(1)

    # 8. Push to repository
    ui.verbose("Pushing to repository...")
    try:
        push_repository(repo.local_cache, verbose=False)
        ui.verbose("Changes pushed to remote")
    except GitError as e:
        ui.error(f"Failed to push to repository: {e}")
        sys.exit(1)

    # 9. Display success message
    ui.success(f"Imported {skill_name} (v{manifest.version}) to repository.")
