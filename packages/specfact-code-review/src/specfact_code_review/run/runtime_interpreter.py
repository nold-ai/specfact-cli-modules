"""Select a signed target Python from actual project constraints."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from icontract import ensure, require
from packaging.specifiers import SpecifierSet

from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


@ensure(lambda result: bool(result) and all(name.startswith("linux-x86_64-cp") for name in result))
def signed_versions() -> dict[str, str]:
    lock = Path(__file__).parents[1] / "resources/contracts/pr-range-v1-toolchain-lock.json"
    return {row["environment_id"]: row["python_version"] for row in json.loads(lock.read_text())["environments"]}


@ensure(lambda result: result.startswith("linux-x86_64-cp"))
def select_environment(plan: ProjectPlan, *, current: str) -> str:
    """Prefer a compatible current worker; otherwise require an unambiguous match."""
    constraint = SpecifierSet(plan.requires_python)
    matching = [
        name
        for name, version in signed_versions().items()
        if version in constraint
        and (not plan.python or version == plan.python or version.startswith(plan.python + "."))
    ]
    if current in matching:
        return current
    if len(matching) == 1:
        return matching[0]
    if not matching:
        raise ProjectRuntimeError(
            f"project_python_incompatible:pin={plan.python}; "
            f"requires-python={plan.requires_python}; supported={signed_versions()}"
        )
    raise ProjectRuntimeError(f"project_python_ambiguous:{','.join(matching)}; select python in --project-config")


@contextmanager
@require(lambda runtime: bool(runtime.environment_id))
def project_worker(runtime: Any, plan: ProjectPlan) -> Iterator[Any]:
    """Materialize and clean up a different signed ABI only when the project needs it."""
    selected = select_environment(plan, current=runtime.environment_id)
    if selected == runtime.environment_id:
        yield runtime
        return
    from specfact_code_review.run.runner import _cleanup_capsule_runtime, _prepare_capsule_runtime

    alternate, reason = _prepare_capsule_runtime(environment_id=selected)
    if alternate is None:
        raise ProjectRuntimeError(reason)
    try:
        if alternate.environment_id != selected:
            raise ProjectRuntimeError("project_worker_environment_mismatch")
        yield alternate
    finally:
        _cleanup_capsule_runtime(alternate)
