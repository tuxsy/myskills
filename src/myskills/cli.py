"""MySkills CLI entry point."""

import sys
import textwrap
from pathlib import Path

import click

from myskills import __version__
from myskills.git_ops import GitError
from myskills.models import SkillsRepository
from myskills.project import ProjectError, get_project_context
from myskills.skill_ops import (
    SkillOperationError,
    import_skill,
    install_skill,
    list_skills,
    remove_skill,
    update_skills,
)
from myskills.ui import TerminalUI


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable detailed operation output.")
@click.version_option(version=__version__, prog_name="myskills")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """MySkills - Manage AI agent skills from a private Git repository."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@main.command()
@click.argument("skill_name")
@click.pass_context
def add(ctx: click.Context, skill_name: str) -> None:
    """Install a skill from the repository.

    SKILL_NAME is the name of the skill to install.

    This command will:
    1. Sync the skills repository
    2. Validate the skill exists and has a valid manifest
    3. Prompt you to select which AI agents to install for
    4. Display an installation summary
    5. Ask for confirmation before proceeding
    6. Copy the skill files and create symlinks

    Exit codes:
        0: Skill installed successfully
        1: General error (invalid manifest, permission error, etc.)
        2: Skill not found in repository
        3: Repository unreachable
        130: User cancelled (declined confirmation or Ctrl+C)
    """
    verbose = ctx.obj.get("verbose", False)
    ui = TerminalUI(verbose_mode=verbose)

    try:
        # Get project context
        project = get_project_context()
        ui.verbose(f"Project root: {project.root}")

        # Get repository configuration
        from myskills.config import read_config

        if project.config_path.exists():
            config = read_config(project.config_path)
            repo_url = config.get("repository")
        else:
            # Prompt for repository URL on first use
            import os

            repo_url = os.getenv("MYSKILLS_REPO_URL")
            if not repo_url:
                ui.error(
                    "No repository configured. Please set MYSKILLS_REPO_URL "
                    "environment variable or run 'myskills add' from a project "
                    "with an existing .myskills.json configuration."
                )
                sys.exit(1)

        # Set up repository cache location
        cache_dir = Path.home() / ".cache" / "myskills" / "repo"
        repo = SkillsRepository(url=repo_url, local_cache=cache_dir)

        # Install the skill
        install_skill(
            skill_name=skill_name,
            project=project,
            repo=repo,
            ui=ui,
        )

    except ProjectError as e:
        ui.error(str(e))
        sys.exit(1)

    except GitError as e:
        ui.error(f"Repository error: {e}")
        ui.info("Check your network connection and repository URL.")
        sys.exit(3)

    except SkillOperationError as e:
        error_msg = str(e).lower()

        if "not found" in error_msg:
            ui.error(str(e))
            sys.exit(2)
        elif "cancelled" in error_msg or "abort" in error_msg:
            sys.exit(130)
        else:
            ui.error(str(e))
            sys.exit(1)

    except KeyboardInterrupt:
        ui.warning("\nOperation cancelled by user.")
        sys.exit(130)

    except Exception as e:
        ui.error(f"Unexpected error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all available skills in the repository.

    This command will:
    1. Sync the skills repository
    2. Display all available skills with their versions
    3. Mark installed skills with [installed]

    Exit codes:
        0: Success
        3: Repository unreachable
    """
    verbose = ctx.obj.get("verbose", False)
    ui = TerminalUI(verbose_mode=verbose)

    try:
        # Get project context
        project = get_project_context()
        ui.verbose(f"Project root: {project.root}")

        # Get repository configuration
        from myskills.config import read_config

        if project.config_path.exists():
            config = read_config(project.config_path)
            repo_url = config.get("repository")
        else:
            # Prompt for repository URL on first use
            import os

            repo_url = os.getenv("MYSKILLS_REPO_URL")
            if not repo_url:
                ui.error(
                    "No repository configured. Please set MYSKILLS_REPO_URL "
                    "environment variable or run 'myskills add' from a project "
                    "with an existing .myskills.json configuration."
                )
                sys.exit(1)

        # Set up repository cache location
        cache_dir = Path.home() / ".cache" / "myskills" / "repo"
        repo = SkillsRepository(url=repo_url, local_cache=cache_dir)

        # List skills
        skills = list_skills(
            project=project,
            repo=repo,
            ui=ui,
        )

        # Display results
        if not skills:
            ui.info("Available skills (0 total):\n")
            ui.info("  No skills available in repository.")
        else:
            installed_count = sum(1 for s in skills if s["installed"])
            ui.info(f"Available skills ({len(skills)} total):\n")

            # Calculate column widths for tabular format
            # We'll use fixed widths: name (25), version (10), then description fills the rest
            name_width = 25
            version_width = 10

            # Get terminal width, default to 80 if not available
            import shutil

            terminal_width = shutil.get_terminal_size(fallback=(80, 24)).columns

            # Calculate available width for description (accounting for indent and spacing)
            # Format: "  name           version     description..."
            indent = 2
            description_start = indent + name_width + version_width
            description_width = max(
                40, terminal_width - description_start - 5
            )  # -5 for safety margin

            for skill in skills:
                # Format with ANSI codes: bold name, italic version
                name_display = f"\033[1m{skill['name']}\033[0m"  # Bold
                version_display = f"\033[3mv{skill['version']}\033[0m"  # Italic

                # Pad name and version for alignment (accounting for ANSI codes)
                # ANSI codes add 9 characters (\033[1m and \033[0m) but don't display
                # Ensure at least 1 space between name and version
                name_padding = max(1, name_width - len(skill["name"]))
                version_padding = max(1, version_width - len(skill["version"]) - 1)  # -1 for 'v'

                # Build the first line with name and version
                first_line = (
                    f"  {name_display}{' ' * name_padding}{version_display}{' ' * version_padding}"
                )

                # Wrap the description to fit in the remaining space
                wrapped_lines = textwrap.wrap(
                    skill["description"],
                    width=description_width,
                    break_long_words=False,
                    break_on_hyphens=False,
                )

                if wrapped_lines:
                    # First line: name, version, and first part of description
                    first_line += wrapped_lines[0]
                    ui.info(first_line)

                    # Subsequent lines: indented to align with description start
                    continuation_indent = " " * description_start
                    for line in wrapped_lines[1:]:
                        ui.info(continuation_indent + line)

                    # Add installed marker on a separate indented line if installed
                    if skill["installed"]:
                        marker = "\033[32m✓ installed\033[0m"
                        ui.info(continuation_indent + f"[{marker}]")
                else:
                    ui.info(first_line)

                ui.info("")  # Blank line between skills

            ui.info(f"Installed: {installed_count}/{len(skills)}")

    except ProjectError as e:
        ui.error(str(e))
        sys.exit(1)

    except GitError as e:
        ui.error(f"Repository error: {e}")
        ui.info("Check your network connection and repository URL.")
        sys.exit(3)

    except KeyboardInterrupt:
        ui.warning("\nOperation cancelled by user.")
        sys.exit(130)

    except Exception as e:
        ui.error(f"Unexpected error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.argument("skill_name")
@click.pass_context
def remove(ctx: click.Context, skill_name: str) -> None:
    """Uninstall a skill from the project.

    SKILL_NAME is the name of the skill to remove.

    This command will:
    1. Check if the skill is installed
    2. Display a removal summary (primary directory and symlinks)
    3. Ask for confirmation before proceeding
    4. Remove all symlinks for the skill
    5. Remove the primary skill directory
    6. Update the configuration

    Exit codes:
        0: Skill removed successfully
        1: General error (permission error, etc.)
        2: Skill not installed
        130: User cancelled (declined confirmation or Ctrl+C)
    """
    verbose = ctx.obj.get("verbose", False)
    ui = TerminalUI(verbose_mode=verbose)

    try:
        # Get project context
        project = get_project_context()
        ui.verbose(f"Project root: {project.root}")

        # Remove the skill
        remove_skill(
            skill_name=skill_name,
            project=project,
            ui=ui,
        )

    except ProjectError as e:
        ui.error(str(e))
        sys.exit(1)

    except SkillOperationError as e:
        error_msg = str(e).lower()

        if "not installed" in error_msg:
            ui.error(str(e))
            sys.exit(2)
        elif "cancelled" in error_msg:
            sys.exit(130)
        else:
            ui.error(str(e))
            sys.exit(1)

    except KeyboardInterrupt:
        ui.warning("\nOperation cancelled by user.")
        sys.exit(130)

    except Exception as e:
        ui.error(f"Unexpected error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.pass_context
def update(ctx: click.Context) -> None:
    """Check for updates to installed skills and apply them.

    Exit codes:
        0: Success
        1: General error
        3: Repository unreachable
        130: User cancelled (Ctrl+C)
    """
    verbose = ctx.obj.get("verbose", False)
    ui = TerminalUI(verbose_mode=verbose)

    try:
        project = get_project_context()
        ui.verbose(f"Project root: {project.root}")

        from myskills.config import read_config

        if project.config_path.exists():
            config = read_config(project.config_path)
            repo_url = config.get("repository")
        else:
            import os

            repo_url = os.getenv("MYSKILLS_REPO_URL")
            if not repo_url:
                ui.error(
                    "No repository configured. Please set MYSKILLS_REPO_URL or create a .myskills.json."
                )
                sys.exit(1)

        cache_dir = Path.home() / ".cache" / "myskills" / "repo"
        repo = SkillsRepository(url=repo_url, local_cache=cache_dir)

        summary = update_skills(project=project, repo=repo, ui=ui)

        ui.info("\nUpdate summary:")
        ui.info(f"  Updated: {len(summary.get('updated', []))}")
        ui.info(f"  Current: {len(summary.get('current', []))}")
        ui.info(f"  Failed: {len(summary.get('failed', []))}")

    except ProjectError as e:
        ui.error(str(e))
        sys.exit(1)

    except GitError as e:
        ui.error(f"Repository error: {e}")
        ui.info("Check your network connection and repository URL.")
        sys.exit(3)

    except KeyboardInterrupt:
        ui.warning("\nOperation cancelled by user.")
        sys.exit(130)

    except Exception as e:
        ui.error(f"Unexpected error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command("import")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def import_command(ctx: click.Context, path: Path) -> None:
    """Import a local skill directory to the repository.

    PATH is the path to the local skill directory containing SKILL.md.

    This command will:
    1. Validate the skill directory has a valid manifest
    2. Sync the skills repository
    3. Check for name conflicts in the repository
    4. Display an import summary
    5. Ask for confirmation before proceeding
    6. Copy the skill to the repository and commit/push

    Exit codes:
        0: Skill imported successfully
        1: General error (invalid manifest, push failure, etc.)
        2: Invalid skill directory
        3: Repository unreachable
        130: User cancelled (declined confirmation or Ctrl+C)
    """
    verbose = ctx.obj.get("verbose", False)
    ui = TerminalUI(verbose_mode=verbose)

    try:
        # Get project context
        project = get_project_context()
        ui.verbose(f"Project root: {project.root}")

        # Get repository configuration
        from myskills.config import read_config

        if project.config_path.exists():
            config = read_config(project.config_path)
            repo_url = config.get("repository")
        else:
            import os

            repo_url = os.getenv("MYSKILLS_REPO_URL")
            if not repo_url:
                ui.error(
                    "No repository configured. Please set MYSKILLS_REPO_URL "
                    "environment variable or run from a project with .myskills.json."
                )
                sys.exit(1)

        # Set up repository cache location
        cache_dir = Path.home() / ".cache" / "myskills" / "repo"
        repo = SkillsRepository(url=repo_url, local_cache=cache_dir)

        # Import the skill
        import_skill(
            skill_path=path,
            project=project,
            repo=repo,
            ui=ui,
        )

    except ProjectError as e:
        ui.error(str(e))
        sys.exit(1)

    except GitError as e:
        ui.error(f"Repository error: {e}")
        ui.info("Check your network connection and repository URL.")
        sys.exit(3)

    except SkillOperationError as e:
        error_msg = str(e).lower()

        # Check for repository errors
        if hasattr(e, "is_repo_error") and e.is_repo_error:
            ui.error(str(e))
            sys.exit(3)
        elif "invalid" in error_msg or "missing" in error_msg:
            ui.error(str(e))
            sys.exit(2)
        elif "cancelled" in error_msg or "abort" in error_msg:
            sys.exit(130)
        else:
            ui.error(str(e))
            sys.exit(1)

    except KeyboardInterrupt:
        ui.warning("\nOperation cancelled by user.")
        sys.exit(130)

    except Exception as e:
        ui.error(f"Unexpected error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
