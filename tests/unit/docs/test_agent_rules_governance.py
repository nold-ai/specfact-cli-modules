from __future__ import annotations

import re
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)


def _parse_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    assert match is not None, f"missing frontmatter in {path}"
    loaded = yaml.safe_load(match.group(1))
    assert isinstance(loaded, dict), f"frontmatter must parse to mapping in {path}"
    return loaded


def test_agent_rules_index_and_checklist_exist() -> None:
    index_path = REPO_ROOT / "docs" / "agent-rules" / "INDEX.md"
    checklist_path = REPO_ROOT / "docs" / "agent-rules" / "05-non-negotiable-checklist.md"

    assert index_path.exists()
    assert checklist_path.exists()


def test_agent_rule_docs_have_required_frontmatter_keys() -> None:
    required_keys = {
        "id",
        "always_load",
        "applies_when",
        "priority",
        "blocking",
        "user_interaction_required",
        "stop_conditions",
        "depends_on",
    }

    for path in sorted((REPO_ROOT / "docs" / "agent-rules").glob("*.md")):
        frontmatter = _parse_frontmatter(path)
        assert required_keys.issubset(frontmatter), f"missing governance keys in {path.name}"


def test_agent_rules_index_has_deterministic_bootstrap_metadata() -> None:
    frontmatter = _parse_frontmatter(REPO_ROOT / "docs" / "agent-rules" / "INDEX.md")
    applies_when = frontmatter["applies_when"]
    assert isinstance(applies_when, list)

    assert frontmatter["id"] == "agent-rules-index"
    assert frontmatter["always_load"] is True
    assert "session-bootstrap" in applies_when
    assert frontmatter["priority"] == 0


def test_non_negotiable_checklist_is_always_loaded() -> None:
    frontmatter = _parse_frontmatter(REPO_ROOT / "docs" / "agent-rules" / "05-non-negotiable-checklist.md")
    depends_on = frontmatter["depends_on"]
    assert isinstance(depends_on, list)

    assert frontmatter["id"] == "agent-rules-non-negotiable-checklist"
    assert frontmatter["always_load"] is True
    assert "agent-rules-index" in depends_on


def test_agents_references_canonical_rule_docs() -> None:
    agents_text = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "docs/agent-rules/INDEX.md" in agents_text
    assert "docs/agent-rules/05-non-negotiable-checklist.md" in agents_text
    assert "## Strategic context" in agents_text
    assert "Shared design and governance context lives in the paired public `specfact-cli` repository" in agents_text
