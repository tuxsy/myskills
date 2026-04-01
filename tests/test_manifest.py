"""Unit tests for SKILL.md manifest parsing and validation (T016)."""

from __future__ import annotations

import pytest

from myskills.manifest import (
    ManifestError,
    parse_manifest,
    update_manifest_with_version,
    was_version_missing,
)
from myskills.ui import UIProvider


class TestParseManifestValid:
    """Tests for valid manifest parsing."""

    def test_parse_valid_manifest(self, skill_dir_factory):
        """Parse a well-formed SKILL.md with all required fields."""
        skill = skill_dir_factory("my-skill", version="2.1.0", description="Does things")

        result = parse_manifest(skill)

        assert result.name == "my-skill"
        assert result.description == "Does things"
        assert result.version == "2.1.0"
        assert "---" in result.raw_content

    def test_parse_manifest_preserves_raw_content(self, skill_dir_factory):
        """Raw content should include the full SKILL.md file contents."""
        skill = skill_dir_factory("test-skill")
        raw = (skill / "SKILL.md").read_text()

        result = parse_manifest(skill)

        assert result.raw_content == raw

    def test_parse_manifest_with_markdown_body(self, skill_dir_factory):
        """Manifest with rich markdown body should parse correctly."""
        custom = (
            "---\n"
            "name: rich-skill\n"
            "description: Has markdown body\n"
            "version: 1.0.0\n"
            "---\n\n"
            "# Rich Skill\n\n"
            "## Features\n\n"
            "- Feature 1\n"
            "- Feature 2\n"
        )
        skill = skill_dir_factory("rich-skill", front_matter=custom)

        result = parse_manifest(skill)

        assert result.name == "rich-skill"
        assert "## Features" in result.raw_content


class TestParseManifestMissingFile:
    """Tests for missing SKILL.md."""

    def test_missing_skill_md_raises_error(self, tmp_path):
        """Directory without SKILL.md should raise ManifestError."""
        empty_dir = tmp_path / "no-manifest"
        empty_dir.mkdir()

        with pytest.raises(ManifestError, match="Missing required manifest file"):
            parse_manifest(empty_dir)


class TestParseManifestInvalidYaml:
    """Tests for invalid YAML front-matter."""

    def test_no_front_matter_delimiter(self, skill_dir_factory):
        """SKILL.md without --- delimiter should raise ManifestError."""
        skill = skill_dir_factory("bad-yaml", front_matter="name: bad\nno delimiters\n")

        with pytest.raises(ManifestError, match="must start with YAML front-matter"):
            parse_manifest(skill)

    def test_malformed_yaml(self, skill_dir_factory):
        """Unparseable YAML should raise ManifestError."""
        skill = skill_dir_factory(
            "bad-yaml",
            front_matter="---\n: :\n  - [\n---\n",
        )

        with pytest.raises(ManifestError, match="Failed to parse YAML"):
            parse_manifest(skill)

    def test_front_matter_not_mapping(self, skill_dir_factory):
        """YAML that parses to non-dict should raise ManifestError."""
        skill = skill_dir_factory(
            "not-dict",
            front_matter="---\n- item1\n- item2\n---\n",
        )

        with pytest.raises(ManifestError, match="must be a YAML mapping"):
            parse_manifest(skill)


class TestParseManifestMissingFields:
    """Tests for missing required fields."""

    def test_missing_name(self, skill_dir_factory):
        """Missing name field should raise ManifestError."""
        skill = skill_dir_factory(
            "no-name",
            front_matter="---\ndescription: test\nversion: 1.0.0\n---\n",
        )

        with pytest.raises(ManifestError, match="missing required field 'name'"):
            parse_manifest(skill)

    def test_missing_description(self, skill_dir_factory):
        """Missing description field should raise ManifestError."""
        skill = skill_dir_factory(
            "no-desc",
            front_matter="---\nname: no-desc\nversion: 1.0.0\n---\n",
        )

        with pytest.raises(ManifestError, match="missing required field 'description'"):
            parse_manifest(skill)

    def test_empty_name(self, skill_dir_factory):
        """Empty name field should raise ManifestError."""
        skill = skill_dir_factory(
            "empty-name",
            front_matter="---\nname:\ndescription: test\nversion: 1.0.0\n---\n",
        )

        with pytest.raises(ManifestError, match="missing required field 'name'"):
            parse_manifest(skill)


class TestParseManifestNameValidation:
    """Tests for name format and directory match validation."""

    def test_name_mismatch_raises_error(self, skill_dir_factory):
        """Manifest name that doesn't match directory should raise ManifestError."""
        skill = skill_dir_factory(
            "actual-dir",
            front_matter="---\nname: different-name\ndescription: test\nversion: 1.0.0\n---\n",
        )

        with pytest.raises(ManifestError, match="does not match directory name"):
            parse_manifest(skill)

    def test_name_with_uppercase_raises_error(self, skill_dir_factory):
        """Name with uppercase letters should fail name pattern."""
        skill = skill_dir_factory(
            "Bad-Name",
            front_matter="---\nname: Bad-Name\ndescription: test\nversion: 1.0.0\n---\n",
        )

        with pytest.raises(ManifestError, match="Invalid skill name"):
            parse_manifest(skill)

    def test_single_char_name_raises_error(self, skill_dir_factory):
        """Single character name should fail (min 2 chars)."""
        skill = skill_dir_factory(
            "x",
            front_matter="---\nname: x\ndescription: test\nversion: 1.0.0\n---\n",
        )

        with pytest.raises(ManifestError, match="Invalid skill name"):
            parse_manifest(skill)

    def test_name_starting_with_hyphen_raises_error(self, skill_dir_factory):
        """Name starting with hyphen should fail."""
        skill = skill_dir_factory(
            "-bad",
            front_matter="---\nname: -bad\ndescription: test\nversion: 1.0.0\n---\n",
        )

        with pytest.raises(ManifestError, match="Invalid skill name"):
            parse_manifest(skill)


class TestParseManifestVersionValidation:
    """Tests for version format validation."""

    def test_invalid_version_format(self, skill_dir_factory):
        """Non-semver version should raise ManifestError."""
        skill = skill_dir_factory(
            "bad-version",
            front_matter="---\nname: bad-version\ndescription: test\nversion: 1.0\n---\n",
        )

        with pytest.raises(ManifestError, match="Invalid version"):
            parse_manifest(skill)

    def test_version_with_prefix(self, skill_dir_factory):
        """Version with 'v' prefix should raise ManifestError."""
        skill = skill_dir_factory(
            "v-version",
            front_matter="---\nname: v-version\ndescription: test\nversion: v1.0.0\n---\n",
        )

        with pytest.raises(ManifestError, match="Invalid version"):
            parse_manifest(skill)

    def test_valid_semver_versions(self, skill_dir_factory):
        """Various valid semver versions should parse successfully."""
        for version in ["0.0.1", "1.0.0", "10.20.30", "999.999.999"]:
            name = f"ver-{version.replace('.', '-')}"
            skill = skill_dir_factory(
                name,
                front_matter=f"---\nname: {name}\ndescription: test\nversion: {version}\n---\n",
            )
            result = parse_manifest(skill)
            assert result.version == version


class TestParseManifestVersionDefaults:
    """Tests for version field defaulting behavior."""

    def test_missing_version_defaults_to_1_0_0(self, skill_dir_factory):
        """Missing version field should default to 1.0.0."""
        skill = skill_dir_factory(
            "no-ver",
            front_matter="---\nname: no-ver\ndescription: test\n---\n",
        )

        result = parse_manifest(skill, ui=None)
        assert result.version == "1.0.0"

    def test_empty_version_defaults_to_1_0_0(self, skill_dir_factory):
        """Empty version field should default to 1.0.0."""
        skill = skill_dir_factory(
            "empty-ver",
            front_matter="---\nname: empty-ver\ndescription: test\nversion:\n---\n",
        )

        result = parse_manifest(skill, ui=None)
        assert result.version == "1.0.0"

    def test_version_default_with_verbose_ui_shows_warning(self, skill_dir_factory, mocker):
        """Version defaulting with ui should show warning message."""
        skill = skill_dir_factory(
            "no-ver",
            front_matter="---\nname: no-ver\ndescription: test\n---\n",
        )

        mock_ui = mocker.Mock(spec=UIProvider)
        result = parse_manifest(skill, ui=mock_ui)

        assert result.version == "1.0.0"
        mock_ui.warning.assert_called_once_with(
            "No version specified in SKILL.md for 'no-ver', assuming 1.0.0"
        )

    def test_version_default_without_ui_no_warning(self, skill_dir_factory):
        """Version defaulting without ui should not raise error."""
        skill = skill_dir_factory(
            "no-ver",
            front_matter="---\nname: no-ver\ndescription: test\n---\n",
        )

        # Should not raise any exception
        result = parse_manifest(skill, ui=None)
        assert result.version == "1.0.0"


class TestManifestVersionHelpers:
    """Tests for version helper functions."""

    def test_was_version_missing_returns_true(self, skill_dir_factory):
        """was_version_missing should return True when version field is absent."""
        skill = skill_dir_factory(
            "no-ver",
            front_matter="---\nname: no-ver\ndescription: test\n---\n",
        )

        assert was_version_missing(skill) is True

    def test_was_version_missing_returns_false(self, skill_dir_factory):
        """was_version_missing should return False when version field is present."""
        skill = skill_dir_factory(
            "with-ver",
            front_matter="---\nname: with-ver\ndescription: test\nversion: 2.0.0\n---\n",
        )

        assert was_version_missing(skill) is False

    def test_update_manifest_with_version_adds_field(self, skill_dir_factory):
        """update_manifest_with_version should add version field in correct order."""
        skill = skill_dir_factory(
            "no-ver",
            front_matter="---\nname: no-ver\ndescription: test\n---\n\nBody content",
        )

        update_manifest_with_version(skill, "1.5.0")

        updated_content = (skill / "SKILL.md").read_text()
        lines = updated_content.split("\n")

        # Check field order: name, description, version
        assert lines[0] == "---"
        assert lines[1] == "name: no-ver"
        assert lines[2] == "description: test"
        assert lines[3] == "version: 1.5.0"
        assert lines[4] == "---"
        assert "Body content" in updated_content
