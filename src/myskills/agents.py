"""Supported AI agent definitions (hardcoded for v1 per FR-014, R-006)."""

from __future__ import annotations

from myskills.models import Agent

SUPPORTED_AGENTS: list[Agent] = [
    Agent(id="claude", display_name="Claude", skills_dir=".claude/skills"),
    Agent(id="cursor", display_name="Cursor", skills_dir=".cursor/skills"),
    Agent(id="copilot", display_name="Copilot", skills_dir=".github/copilot/skills"),
    Agent(id="windsurf", display_name="Windsurf", skills_dir=".windsurf/skills"),
]


def get_agent_by_id(agent_id: str) -> Agent | None:
    """Look up an agent by its ID. Returns None if not found."""
    for agent in SUPPORTED_AGENTS:
        if agent.id == agent_id:
            return agent
    return None


def get_agent_ids() -> list[str]:
    """Return list of all supported agent IDs."""
    return [agent.id for agent in SUPPORTED_AGENTS]
