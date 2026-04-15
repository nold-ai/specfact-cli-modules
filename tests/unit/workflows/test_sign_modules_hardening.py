from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def _workflow_text() -> str:
    path = REPO_ROOT / ".github" / "workflows" / "sign-modules.yml"
    return path.read_text(encoding="utf-8")


def _parsed_workflow() -> dict[Any, Any]:
    loaded = yaml.safe_load(_workflow_text())
    assert isinstance(loaded, dict)
    return cast(dict[Any, Any], loaded)


def _workflow_on_section(doc: dict[Any, Any]) -> dict[str, Any]:
    section = doc.get(True)
    if isinstance(section, dict):
        return cast(dict[str, Any], section)
    raw = doc.get("on")
    assert isinstance(raw, dict)
    return cast(dict[str, Any], raw)


def test_sign_modules_hardening_triggers_on_push_pr_and_dispatch() -> None:
    doc = _parsed_workflow()
    on = _workflow_on_section(doc)
    push = on["push"]
    assert isinstance(push, dict)
    assert push["branches"] == ["dev", "main"]
    paths = push["paths"]
    assert isinstance(paths, list)
    assert "packages/**" in paths

    pr = on["pull_request"]
    assert isinstance(pr, dict)
    assert pr["branches"] == ["dev", "main"]

    dispatch = on["workflow_dispatch"]
    assert isinstance(dispatch, dict)
    assert "base_branch" in dispatch["inputs"]


def test_sign_modules_hardening_auto_signs_on_push_non_bot() -> None:
    workflow = _workflow_text()
    assert "github.event_name == 'push'" in workflow
    assert "github.actor != 'github-actions[bot]'" in workflow
    assert "scripts/sign-modules.py" in workflow
    assert "--changed-only" in workflow
    assert "--bump-version patch" in workflow
    assert "chore(modules): auto-sign module manifests [skip ci]" in workflow


def test_sign_modules_hardening_strict_verify_on_push() -> None:
    workflow = _workflow_text()
    assert "--require-signature" in workflow
    assert "github.event_name == 'push'" in workflow
    assert "github.ref_name == 'dev' || github.ref_name == 'main'" in workflow


def test_sign_modules_hardening_pr_verify_checksum_only() -> None:
    workflow = _workflow_text()
    assert "github.event_name != 'push'" in workflow
    assert "pull_request" in workflow
    assert "scripts/verify-modules-signature.py" in workflow


def test_sign_modules_hardening_reproducibility_on_main() -> None:
    doc = _parsed_workflow()
    repro = doc["jobs"]["reproducibility"]
    assert isinstance(repro, dict)
    assert repro["if"] == "github.event_name == 'push' && github.ref_name == 'main'"
    needs = repro["needs"]
    assert needs == ["verify"]


def test_sign_modules_hardening_manual_dispatch_job() -> None:
    doc = _parsed_workflow()
    manual = doc["jobs"]["sign-and-push"]
    assert isinstance(manual, dict)
    assert manual["if"] == "github.event_name == 'workflow_dispatch'"
    assert manual["needs"] == ["verify"]
