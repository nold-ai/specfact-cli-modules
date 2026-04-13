"""Tests for scripts/validate_agent_rule_applies_when.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_validator_module() -> ModuleType:
    script_path = REPO_ROOT / "scripts" / "validate_agent_rule_applies_when.py"
    spec = importlib.util.spec_from_file_location("_validate_agent_rule_applies_when", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_agent_rule_applies_when_passes() -> None:
    script = REPO_ROOT / "scripts" / "validate_agent_rule_applies_when.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_malformed_frontmatter_is_rejected(tmp_path: Path) -> None:
    rules_dir = tmp_path / "docs" / "agent-rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "broken.md").write_text("no frontmatter block\n", encoding="utf-8")

    mod = _load_validator_module()
    errors = mod._iter_signal_errors(rules_dir)

    assert len(errors) == 1
    assert "broken.md" in errors[0]
    assert "frontmatter" in errors[0].lower()


def test_invalid_yaml_in_frontmatter_is_rejected(tmp_path: Path) -> None:
    rules_dir = tmp_path / "docs" / "agent-rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "bad_yaml.md").write_text(
        "---\nid: x\napplies_when: [unclosed\n---\n",
        encoding="utf-8",
    )

    mod = _load_validator_module()
    errors = mod._iter_signal_errors(rules_dir)

    assert len(errors) == 1
    assert "bad_yaml.md" in errors[0]
    assert "YAML" in errors[0]


def test_frontmatter_scalar_root_is_rejected(tmp_path: Path) -> None:
    rules_dir = tmp_path / "docs" / "agent-rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "scalar.md").write_text("---\njust a string\n---\n", encoding="utf-8")

    mod = _load_validator_module()
    errors = mod._iter_signal_errors(rules_dir)

    assert len(errors) == 1
    assert "scalar.md" in errors[0]
    assert "mapping" in errors[0].lower()


def test_applies_when_list_rejects_non_string_entries(tmp_path: Path) -> None:
    rules_dir = tmp_path / "docs" / "agent-rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "bad_list.md").write_text(
        "---\napplies_when: [session-bootstrap, 42]\n---\n# body\n",
        encoding="utf-8",
    )

    mod = _load_validator_module()
    errors = mod._iter_signal_errors(rules_dir)

    assert len(errors) == 1
    assert "bad_list.md" in errors[0]
    assert "applies_when" in errors[0]


def test_valid_applies_when_in_temp_rules_dir_passes(tmp_path: Path) -> None:
    rules_dir = tmp_path / "docs" / "agent-rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "ok.md").write_text(
        "---\napplies_when: session-bootstrap\n---\n# body\n",
        encoding="utf-8",
    )

    mod = _load_validator_module()
    errors = mod._iter_signal_errors(rules_dir)

    assert errors == []
