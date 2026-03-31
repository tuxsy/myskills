"""MySkills CLI entry point."""

import sys
from pathlib import Path

import click

from myskills import __version__
from myskills.git_ops import GitError
from myskills.models import SkillsRepository
from myskills.project import ProjectError, get_project_context
from myskills.skill_ops import SkillOperationError, install_skill, list_skills
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

            for skill in skills:
                installed_marker = "  [installed]" if skill["installed"] else ""
                ui.info(
                    f"  {skill['name']:<20} v{skill['version']:<8} {installed_marker:<15} {skill['description']}"
                )

            ui.info(f"\nInstalled: {installed_count}/{len(skills)}")

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
