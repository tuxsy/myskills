"""Tests for __main__ module."""

import subprocess
import sys


def test_main_module_executable():
    """Test that myskills can be run as a module."""
    # Just check that it doesn't crash when called with --help
    result = subprocess.run(
        [sys.executable, "-m", "myskills", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "MySkills" in result.stdout or "myskills" in result.stdout.lower()
