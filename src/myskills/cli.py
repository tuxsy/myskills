"""MySkills CLI entry point."""

import click

from myskills import __version__


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable detailed operation output.")
@click.version_option(version=__version__, prog_name="myskills")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """MySkills - Manage AI agent skills from a private Git repository."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
