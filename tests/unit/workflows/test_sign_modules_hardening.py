from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from pytest import FixtureRequest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _workflow_text() -> str:
    path = REPO_ROOT / ".github" / "workflows" / "sign-modules.yml"
    return path.read_text(encoding="utf-8")


def _parsed_workflow() -> dict[Any, Any]:
    loaded = yaml.safe_load(_workflow_text())
    assert isinstance(loaded, dict)
    return cast(dict[Any, Any], loaded)


def _strict_push_verify_step_block(workflow: str) -> str:
    marker = "- name: Strict verify module manifests (push to dev/main)\n"
    idx = workflow.find(marker)
    if idx < 0:
        msg = "strict push verify step not found in sign-modules workflow"
        raise AssertionError(msg)
    lines = workflow[idx:].splitlines(keepends=True)
    block: list[str] = [lines[0]]
    for line in lines[1:]:
        if line.startswith("      - name:"):
            break
        block.append(line)
    return "".join(block)


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
    assert "registry/**" in paths

    pr = on["pull_request"]
    assert isinstance(pr, dict)
    assert pr["branches"] == ["dev", "main"]
    pr_paths = pr["paths"]
    assert isinstance(pr_paths, list)
    assert "registry/**" in pr_paths

    dispatch = on["workflow_dispatch"]
    assert isinstance(dispatch, dict)
    assert "base_branch" in dispatch["inputs"]


def test_sign_modules_hardening_verify_job_exports_public_signing_secrets() -> None:
    doc = _parsed_workflow()
    verify = doc["jobs"]["verify"]
    assert isinstance(verify, dict)
    env = verify.get("env")
    assert isinstance(env, dict)
    assert env["SPECFACT_MODULE_PUBLIC_SIGN_KEY"] == "${{ secrets.SPECFACT_MODULE_PUBLIC_SIGN_KEY }}"
    assert env["SPECFACT_MODULE_SIGNING_PUBLIC_KEY_PEM"] == "${{ secrets.SPECFACT_MODULE_SIGNING_PUBLIC_KEY_PEM }}"


def test_sign_modules_hardening_auto_signs_on_push_non_bot() -> None:
    workflow = _workflow_text()
    assert "github.event_name == 'push'" in workflow
    assert "github.actor != 'github-actions[bot]'" in workflow
    assert "scripts/sign-modules.py" in workflow
    assert "--changed-only" in workflow
    assert "--bump-version patch" in workflow
    assert 'git commit -m "chore(modules): auto-sign module manifests"' in workflow
    assert "auto-sign module manifests [skip ci]" not in workflow


@pytest.mark.parametrize(
    "needles",
    (
        pytest.param(
            (
                "--require-signature",
                "github.event_name == 'push'",
                "github.ref_name == 'dev' || github.ref_name == 'main'",
            ),
            id="push_strict_verify",
        ),
        pytest.param(
            ("github.event_name != 'push'", "pull_request", "scripts/verify-modules-signature.py"),
            id="pr_non_push_verify",
        ),
    ),
)
def test_sign_modules_hardening_workflow_contains_verify_snippets(
    needles: tuple[str, ...], request: FixtureRequest
) -> None:
    workflow = _workflow_text()
    if request.node.callspec.id == "push_strict_verify":
        block = _strict_push_verify_step_block(workflow)
        for needle in needles:
            assert needle in block
    else:
        for needle in needles:
            assert needle in workflow


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
