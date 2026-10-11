"""Validate indexed customer-review scheduling before an approved local deferral."""

from __future__ import annotations

import copy
import re
import subprocess
import sys

import yaml
from icontract import ensure


_PR_CONDITION = "github.event_name == 'pull_request'"
_REVIEW_CONDITION = _PR_CONDITION + " && needs.changes.outputs.capsule_changed == 'true'"


class _WorkflowLoader(yaml.SafeLoader):
    """Keep GitHub's literal on key distinct from YAML boolean keys."""

    @ensure(lambda result: isinstance(result, dict))
    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError("duplicate workflow mapping key")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


_WorkflowLoader.yaml_implicit_resolvers = {
    first: [(tag, pattern) for tag, pattern in resolvers if tag != "tag:yaml.org,2002:bool"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_WorkflowLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.IGNORECASE), list("tTfF")
)


def _yaml_mapping(source: str) -> dict:
    loader = _WorkflowLoader(source)
    try:
        document = loader.get_single_data()
    finally:
        loader.dispose()
    if not isinstance(document, dict):
        raise ValueError("YAML document is not a mapping")
    return document


def _workflow_yaml(path: str, revision: str = "") -> dict:
    source = subprocess.check_output(["git", "show", f"{revision}:{path}"], text=True)
    document = _yaml_mapping(source)
    if set(document) - {
        "name",
        "run-name",
        "on",
        "env",
        "defaults",
        "concurrency",
        "permissions",
        "jobs",
    }:
        raise ValueError("workflow is not a mapping")
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
    rules = _yaml_mapping(step["with"]["filters"])["capsule"]
    if not isinstance(rules, list) or any(not isinstance(rule, str) or rule.startswith("!") for rule in rules):
        raise ValueError("capsule filter contains unsupported or excluding rules")
    return rules


def _detector_contract(changes: dict) -> dict:
    contract = copy.deepcopy(changes)
    step = _unique_step(contract, "filter")
    filters = _yaml_mapping(step["with"]["filters"])
    filters["capsule"] = []  # Validated trigger additions do not change execution.
    step["with"]["filters"] = filters
    return contract


def _orchestration_contract(workflow: dict) -> dict:
    """Bind consumers and workflow execution after independently validated triggers."""
    contract = copy.deepcopy(workflow)
    contract["on"]["pull_request"] = None
    contract["jobs"]["changes"] = _detector_contract(contract["jobs"]["changes"])
    return contract


def _validate_detector_execution(changes: dict, baseline: str) -> None:
    integrated = _workflow_yaml(".github/workflows/pr-orchestrator.yml", baseline)["jobs"]["changes"]
    if not set(_capsule_rules(integrated)).issubset(_capsule_rules(changes)):
        raise ValueError("capsule trigger inventory removes an integrated rule")
    if _detector_contract(changes) != _detector_contract(integrated):
        raise ValueError("change detector execution differs from the integrated dev contract")


def _approved_review_budget(workflow: dict) -> dict:
    """Adapt only the owner-approved review and sequential job bounds."""
    integrated = copy.deepcopy(workflow)
    independent = integrated["jobs"]["independent-review"]
    if independent["timeout-minutes"] == 45:
        independent["timeout-minutes"] = 75
    step = _unique_step(independent, "independent_review")
    old = "subprocess.run(sys.argv[1:],timeout=300,check=False)"
    new = "subprocess.run(sys.argv[1:],timeout=1800,check=False)"
    if step["run"].count(old) == 1:
        step["run"] = step["run"].replace(old, new, 1)
    return integrated


def _validate_reusable_review(baseline: str) -> None:
    workflow = _workflow_yaml(".github/workflows/capsule-customer-execution.yml")
    if "workflow_call" not in workflow["on"]:
        raise ValueError("required review is not reusable")
    customer = workflow["jobs"]["customer"]
    _blocking_scope(customer)
    if "3.12" not in customer["strategy"]["matrix"]["python"]:
        raise ValueError("blocking candidate review interpreter is not scheduled")
    _blocking_scope(_unique_step(customer, "deferred_review"), _PR_CONDITION + " && matrix.python == '3.12'")
    independent = workflow["jobs"]["independent-review"]
    _blocking_scope(independent, _PR_CONDITION)
    _blocking_scope(_unique_step(independent, "independent_review"))
    # A local deferral cannot prove arbitrary changed shell/action execution.
    # Pin the entire already integrated contract, including runner/matrix,
    # commands, supporting steps, environment, inputs and deadlines.
    if workflow != _approved_review_budget(
        _workflow_yaml(".github/workflows/capsule-customer-execution.yml", baseline)
    ):
        raise ValueError("reusable review execution differs from the integrated dev contract")


def _validate_pr_trigger(workflow: dict, paths: list[str]) -> None:
    event = workflow["on"]["pull_request"]
    if event is None:
        event = {}
    if not isinstance(event, dict) or set(event) - {"branches", "paths-ignore"}:
        raise ValueError("PR trigger has unverified lifecycle or path selectors")
    if event.get("branches", ["main", "dev"]) != ["main", "dev"]:
        raise ValueError("PR trigger does not cover both release target branches")
    ignored = event.get("paths-ignore", [])
    if ignored not in ([], ["**/*.md", "docs/**"]):
        raise ValueError("PR trigger has unverified path exclusions")
    if ignored and not any(not (path.endswith(".md") or path.startswith("docs/")) for path in paths):
        raise ValueError("PR trigger excludes the entire candidate")


def _validate_review_surface(capsule_paths: list[str], paths: list[str]) -> None:
    for path in paths:
        if path.endswith("/TDD_EVIDENCE.md") or path == "TDD_EVIDENCE.md":
            continue  # Same evidence-only exclusion as the ordinary local gate.
        if not path.startswith(("packages/", "registry/", "scripts/", "tools/", "tests/", "openspec/changes/")):
            continue  # These paths never bypass an ordinary local review.
        if path in capsule_paths or path.startswith("openspec/changes/code-review-native-platform-execution/"):
            continue
        raise ValueError("unrelated staged reviewable path cannot use capsule deferral")


@ensure(lambda result: result is None)
def validate_indexed_scheduling(paths: list[str], candidate_paths: list[str], baseline: str) -> None:
    workflow = _workflow_yaml(".github/workflows/pr-orchestrator.yml")
    _validate_pr_trigger(workflow, candidate_paths)
    _validate_review_surface(paths, candidate_paths)
    jobs = workflow["jobs"]
    rules = _capsule_rules(jobs["changes"])
    _validate_detector_execution(jobs["changes"], baseline)
    if not paths or any(_path_rule(path) not in rules for path in paths):
        raise ValueError("capsule filter does not cover the staged delta")
    job = jobs["customer-capsules"]
    _blocking_scope(job, _REVIEW_CONDITION)
    if job["needs"] != ["changes"] or job["uses"] != "./.github/workflows/capsule-customer-execution.yml":
        raise ValueError("customer job does not invoke the required filtered review")
    integrated = _workflow_yaml(".github/workflows/pr-orchestrator.yml", baseline)["jobs"]["customer-capsules"]
    if job != integrated:
        raise ValueError("reusable review caller differs from the integrated dev contract")
    _validate_reusable_review(baseline)
    integrated_workflow = _workflow_yaml(".github/workflows/pr-orchestrator.yml", baseline)
    if _orchestration_contract(workflow) != _orchestration_contract(integrated_workflow):
        raise ValueError("review orchestration differs from the integrated dev contract")


@ensure(lambda result: result in {0, 1})
def main() -> int:
    try:
        validate_indexed_scheduling(sys.argv[1].splitlines(), sys.argv[2].splitlines(), sys.argv[3])
    except (
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        AttributeError,
        RecursionError,
        yaml.YAMLError,
        subprocess.SubprocessError,
    ):
        print("Capsule review deferral requires effective indexed blocking customer scheduling.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
