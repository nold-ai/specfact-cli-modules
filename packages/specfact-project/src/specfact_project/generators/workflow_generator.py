"""Render SpecFact validation workflows for GitHub Actions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require
from jinja2 import Environment, FileSystemLoader

from specfact_project.generators.template_paths import resolve_templates_dir


class WorkflowGenerator:
    """Render GitHub Actions workflows from the packaged templates."""

    @beartype
    def __init__(self, templates_dir: Path | None = None) -> None:
        """
        Initialize workflow generator.

        Args:
            templates_dir: Directory containing Jinja2 templates (default: resources/templates)
        """
        self.templates_dir = resolve_templates_dir(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @beartype
    @require(lambda output_path: output_path is not None, "Output path must not be None")
    @require(lambda budget: budget > 0, "Budget must be positive")
    @require(lambda python_version: python_version.startswith("3."), "Python version must be 3.x")
    @ensure(lambda output_path: output_path.exists(), "Output file must exist after generation")
    @ensure(lambda output_path: output_path.suffix == ".yml", "Output must be YAML file")
    def generate_github_action(
        self,
        output_path: Path,
        repo_name: str | None = None,
        budget: int = 90,
        python_version: str = "3.12",
    ) -> None:
        """
        Generate GitHub Action workflow for SpecFact validation.

        Args:
            output_path: Path to write the workflow file (e.g., .github/workflows/specfact-gate.yml)
            repo_name: Repository name for context
            budget: Time budget in seconds for validation (must be > 0)
            python_version: Python version for workflow (must be 3.x)

        Raises:
            FileNotFoundError: If template file doesn't exist
            IOError: If unable to write output file
        """
        # Prepare context
        context: dict[str, Any] = {
            "repo_name": repo_name or "specfact-project",
            "budget": budget,
            "python_version": python_version,
        }

        # Render template
        template = self.env.get_template("github-action.yml.j2")
        rendered = template.render(**context)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write workflow file
        output_path.write_text(rendered, encoding="utf-8")
