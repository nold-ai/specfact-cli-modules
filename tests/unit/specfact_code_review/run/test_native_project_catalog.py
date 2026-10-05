from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from specfact_code_review.run import native_project_catalog
from specfact_code_review.run.runtime_models import ProjectPlan


def _payload(plan: ProjectPlan, *, environment_id: str = "darwin-arm64-cp312") -> bytes:
    document = {
        "entries": [
            {
                "abi": "cp312",
                "artifact": {
                    "digest": "sha256:" + "a" * 64,
                    "size": 4096,
                    "url": "https://ghcr.io/v2/nold-ai/specfact-project-runtimes/blobs/sha256:" + "a" * 64,
                },
                "environment_id": environment_id,
                "manager": {"name": "pip", "version": "26.2.1"},
                "platform": "darwin-arm64",
                "project_identity": plan.identity,
            }
        ],
        "schema": "specfact-native-project-acquisition-catalog-v1",
    }
    return json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii") + b"\n"


def test_resolves_exact_project_manager_abi_and_platform(tmp_path: Path) -> None:
    plan = ProjectPlan(tmp_path, manager="pip", source_identity="sha256:" + "b" * 64)
    payload = _payload(plan)

    locator = native_project_catalog.resolve_project_artifact(
        plan,
        environment_id="darwin-arm64-cp312",
        payload=payload,
        expected_sha256=hashlib.sha256(payload).hexdigest(),
    )

    assert locator.url.endswith("/blobs/sha256:" + "a" * 64)
    assert locator.digest == "sha256:" + "a" * 64
    assert locator.size == 4096
    assert locator.transport == "ghcr"


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda document: document.update(schema="wrong"), "catalog_invalid"),
        (lambda document: document["entries"][0].update(project_identity="sha256:" + "0" * 64), "entry_missing"),
        (lambda document: document["entries"][0].update(platform="linux-x86_64"), "entry_invalid"),
        (lambda document: document["entries"][0]["manager"].update(name=[]), "entry_invalid"),
        (lambda document: document["entries"][0]["artifact"].update(size=0), "entry_invalid"),
        (
            lambda document: document["entries"][0]["artifact"].update(
                url="https://ghcr.io/v2/nold-ai/specfact-project-runtimes/blobs/sha256:" + "b" * 64
            ),
            "entry_invalid",
        ),
    ],
)
def test_rejects_malformed_or_mismatched_catalog_entries(tmp_path: Path, mutation, reason: str) -> None:
    plan = ProjectPlan(tmp_path, manager="pip", source_identity="sha256:" + "b" * 64)
    document = json.loads(_payload(plan))
    mutation(document)
    payload = json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii") + b"\n"

    with pytest.raises(ValueError, match=reason):
        native_project_catalog.resolve_project_artifact(
            plan,
            environment_id="darwin-arm64-cp312",
            payload=payload,
            expected_sha256=hashlib.sha256(payload).hexdigest(),
        )


def test_rejects_catalog_digest_mismatch_and_duplicate_exact_entries(tmp_path: Path) -> None:
    plan = ProjectPlan(tmp_path, manager="pip", source_identity="sha256:" + "b" * 64)
    payload = _payload(plan)
    with pytest.raises(ValueError, match="catalog_digest_mismatch"):
        native_project_catalog.resolve_project_artifact(
            plan,
            environment_id="darwin-arm64-cp312",
            payload=payload,
            expected_sha256="0" * 64,
        )

    document = json.loads(payload)
    document["entries"].append(dict(document["entries"][0]))
    duplicate = json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii") + b"\n"
    with pytest.raises(ValueError, match="catalog_duplicate"):
        native_project_catalog.resolve_project_artifact(
            plan,
            environment_id="darwin-arm64-cp312",
            payload=duplicate,
            expected_sha256=hashlib.sha256(duplicate).hexdigest(),
        )


def test_default_module_catalog_is_exactly_digest_bound_and_fails_closed_without_publication(tmp_path: Path) -> None:
    payload, expected = native_project_catalog.module_catalog_bytes()
    assert hashlib.sha256(payload).hexdigest() == expected
    plan = ProjectPlan(tmp_path, manager="pip", source_identity="sha256:" + "b" * 64)
    with pytest.raises(ValueError, match="project_native_acquisition_entry_missing"):
        native_project_catalog.resolve_project_artifact(plan, environment_id="darwin-arm64-cp312")
