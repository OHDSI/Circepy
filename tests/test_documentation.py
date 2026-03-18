"""
Tests for documentation consistency and integrity.

This module validates that documentation is consistent across files,
links are valid, and version numbers match.
"""

import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python <3.11 fallback
    import tomli as tomllib


class TestDocumentation:
    """Test suite for documentation validation."""

    @staticmethod
    def get_project_root():
        """Get the project root directory."""
        return Path(__file__).parent.parent

    def test_version_consistency(self):
        """Verify version numbers match across all files."""
        root = self.get_project_root()

        # Read version from pyproject.toml
        with open(root / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        pyproject_version = pyproject["project"]["version"]

        # Read version from circe/__init__.py
        init_file = root / "circe" / "__init__.py"
        init_content = init_file.read_text()
        init_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init_content)
        assert init_match, "Could not find __version__ in circe/__init__.py"
        init_version = init_match.group(1)

        # Read version from docs/conf.py
        docs_conf = root / "docs" / "conf.py"
        docs_content = docs_conf.read_text()
        release_match = re.search(r"release\s*=\s*['\"]([^'\"]+)['\"]", docs_content)
        assert release_match, "Could not find release in docs/conf.py"
        docs_version = release_match.group(1)

        # Assert all versions match
        assert pyproject_version == init_version == docs_version, (
            f"Version mismatch: pyproject.toml={pyproject_version}, __init__.py={init_version}, docs/conf.py={docs_version}"
        )

    def test_repository_urls_consistent(self):
        """Verify repository URLs are consistent across documentation."""
        root = self.get_project_root()
        expected_repo = "OHDSI/Circepy"

        files_to_check = [
            root / "README.md",
            root / "CONTRIBUTING.md",
            root / "INSTALLATION.md",
            root / "examples" / "README.md",
        ]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text()

            # Check for incorrect URLs
            incorrect_patterns = [
                r"github\.com/OHDSI/circe-be-python",
                r"github\.com/OHDSI/CIRCE-Python",
                r"github\.com/YOUR_USERNAME/",
            ]

            for pattern in incorrect_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                assert not matches, f"Found incorrect repository URL in {file_path.name}: {matches}"

            # Verify correct URL is present if any github.com link exists
            if "github.com" in content:
                assert expected_repo in content, (
                    f"Expected repository URL '{expected_repo}' not found in {file_path.name}"
                )

    def test_installation_instructions_present(self):
        """Verify installation instructions are present in key files."""
        root = self.get_project_root()

        # README should have installation section
        readme = (root / "README.md").read_text()
        assert "## Installation" in readme
        assert "git clone" in readme.lower()
        assert "uv sync" in readme.lower()

        # INSTALLATION.md should exist and have comprehensive instructions
        installation = (root / "INSTALLATION.md").read_text()
        assert "git clone" in installation.lower()
        assert "troubleshooting" in installation.lower()
        assert "uv sync --extra dev" in installation.lower()
        assert 'pip install -e ".[dev]"' in installation.lower()

        # CONTRIBUTING.md should have setup instructions
        contributing = (root / "CONTRIBUTING.md").read_text()
        assert "git clone" in contributing.lower()
        assert "pip install" in contributing.lower()

    def test_internal_links_valid(self):
        """Verify internal documentation links are valid."""
        root = self.get_project_root()

        # Check links in README
        readme = (root / "README.md").read_text()
        internal_links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", readme)

        for link_text, link_url in internal_links:
            # Skip external URLs
            if link_url.startswith(("http://", "https://", "#")):
                continue

            # Check if file exists
            link_path = root / link_url
            assert link_path.exists(), f"Broken link in README.md: [{link_text}]({link_url}) - file not found"

    def test_changelog_has_current_version(self):
        """Verify CHANGELOG.md includes the current version."""
        root = self.get_project_root()

        # Get current version
        with open(root / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        current_version = pyproject["project"]["version"]

        # Check CHANGELOG
        changelog = (root / "CHANGELOG.md").read_text()
        assert f"[{current_version}]" in changelog or f"## {current_version}" in changelog, (
            f"Current version {current_version} not found in CHANGELOG.md"
        )

    def test_readme_shields_badges(self):
        """Verify README has appropriate status badges."""
        root = self.get_project_root()
        readme = (root / "README.md").read_text()

        # Should have badges
        assert "![" in readme or "[![" in readme, "No badges found in README"

        # Should mention alpha/development status somewhere
        assert any(
            marker in readme.lower() for marker in ["alpha", "development", "under active", "testing"]
        ), "README should clearly indicate development status"

    def test_contributing_has_code_style_section(self):
        """Verify CONTRIBUTING.md has code style guidelines."""
        root = self.get_project_root()
        contributing = (root / "CONTRIBUTING.md").read_text()

        assert "## Code Style" in contributing or "### Code Style" in contributing
        assert "ruff" in contributing.lower()
        assert "pytest" in contributing.lower()

    def test_examples_readme_references_parent_docs(self):
        """Verify examples README links to parent documentation."""
        root = self.get_project_root()
        examples_readme = (root / "examples" / "README.md").read_text()

        # Should link to parent README
        assert "../README.md" in examples_readme
        assert "../INSTALLATION.md" in examples_readme

    def test_no_placeholder_text(self):
        """Verify documentation doesn't contain placeholder text."""
        root = self.get_project_root()

        files_to_check = [
            root / "README.md",
            root / "CONTRIBUTING.md",
            root / "INSTALLATION.md",
        ]

        forbidden_placeholders = [
            "TODO",
            "FIXME",
            "XXX",
            "YOUR_USERNAME",
            "PLACEHOLDER",
            "example.com",
        ]

        for file_path in files_to_check:
            content = file_path.read_text()

            for placeholder in forbidden_placeholders:
                if placeholder in ["TODO", "FIXME", "XXX"]:
                    # More lenient - just warn if found
                    if placeholder in content:
                        print(f"Warning: Found {placeholder} in {file_path.name} - verify if intentional")
                else:
                    assert placeholder not in content, (
                        f"Found placeholder text '{placeholder}' in {file_path.name}"
                    )
