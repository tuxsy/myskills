"""Tests for agents module."""

from myskills.agents import SUPPORTED_AGENTS, get_agent_by_id, get_agent_ids


def test_get_agent_by_id_found():
    """Test getting an agent by ID when it exists."""
    agent = get_agent_by_id("claude")
    assert agent is not None
    assert agent.id == "claude"
    assert agent.display_name == "Claude"


def test_get_agent_by_id_not_found():
    """Test getting an agent by ID when it doesn't exist."""
    agent = get_agent_by_id("nonexistent")
    assert agent is None


def test_get_agent_ids():
    """Test getting all agent IDs."""
    ids = get_agent_ids()
    assert "claude" in ids
    assert "cursor" in ids
    assert "copilot" in ids
    assert "windsurf" in ids
    assert len(ids) == len(SUPPORTED_AGENTS)
