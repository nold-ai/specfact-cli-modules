"""Validate indexed customer-review scheduling before an approved local deferral."""

from __future__ import annotations

import subprocess
import sys

import yaml


_PR_CONDITION = "github.event_name == 'pull_request'"
_REVIEW_CONDITION = _PR_CONDITION + " && needs.changes.outputs.capsule_changed == 'true'"


def _indexed_yaml(path: str) -> dict:
    source = subprocess.check_output(["git", "show", f":{path}"], text=True)
    document = yaml.safe_load(source)
    if not isinstance(document, dict):
        raise ValueError("indexed workflow is not a mapping")
    return document


def _path_rule(path: str) -> str:
    for prefix in ("packages/specfact-code-review/", "tests/native/", "tests/unit/specfact_code_review/"):
        if path.startswith(prefix):
            return prefix + "**"
    return path


def _blocking_scope(node: dict, condition: str | None = None) -> None:
    condition_matches = "if" not in node if condition is None else node.get("if") == condition
    if not condition_matches or node.get("continue-on-error", False):
        raise ValueError("review scheduling is conditional or nonblocking")


def _unique_step(job: dict, identity: str) -> dict:
    steps = [step for step in job["steps"] if step.get("id") == identity]
    if len(steps) != 1:
        raise ValueError("required review step is not uniquely defined")
    return steps[0]


def _capsule_rules(changes: dict) -> list[str]:
    _blocking_scope(changes)
    if changes["outputs"]["capsule_changed"] != "${{ steps.filter.outputs.capsule }}":
        raise ValueError("capsule output does not bind the effective filter")
    step = _unique_step(changes, "filter")
    _blocking_scope(step)
    if step["uses"] != "dorny/paths-filter@v3" or step["with"].get("predicate-quantifier", "some") != "some":
        raise ValueError("capsule filter uses an unsupported implementation")
    rules = yaml.safe_load(step["with"]["filters"])["capsule"]
    if not isinstance(rules, list) or any(not isinstance(rule, str) or rule.startswith("!") for rule in rules):
        raise ValueError("capsule filter contains unsupported or excluding rules")
    return rules


def _validate_reusable_review() -> None:
    workflow = _indexed_yaml(".github/workflows/capsule-customer-execution.yml")
    # PyYAML's YAML 1.1 loader represents the GitHub `on` key as True.
    if "workflow_call" not in workflow.get("on", workflow.get(True, {})):
        raise ValueError("required review is not reusable")
    customer = workflow["jobs"]["customer"]
    _blocking_scope(customer)
    if "3.12" not in customer["strategy"]["matrix"]["python"]:
        raise ValueError("blocking candidate review interpreter is not scheduled")
    _blocking_scope(_unique_step(customer, "deferred_review"), _PR_CONDITION + " && matrix.python == '3.12'")
    independent = workflow["jobs"]["independent-review"]
    _blocking_scope(independent, _PR_CONDITION)
    _blocking_scope(_unique_step(independent, "independent_review"))


def validate_indexed_scheduling(paths: list[str]) -> None:
    jobs = _indexed_yaml(".github/workflows/pr-orchestrator.yml")["jobs"]
    rules = _capsule_rules(jobs["changes"])
    if not paths or any(_path_rule(path) not in rules for path in paths):
        raise ValueError("capsule filter does not cover the staged delta")
    job = jobs["customer-capsules"]
    _blocking_scope(job, _REVIEW_CONDITION)
    if job["needs"] != ["changes"] or job["uses"] != "./.github/workflows/capsule-customer-execution.yml":
        raise ValueError("customer job does not invoke the required filtered review")
    _validate_reusable_review()


def main() -> int:
    try:
        validate_indexed_scheduling(sys.argv[1].splitlines())
    except (IndexError, KeyError, TypeError, ValueError, AttributeError, yaml.YAMLError, subprocess.SubprocessError):
        print("Capsule review deferral requires effective indexed blocking customer scheduling.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
