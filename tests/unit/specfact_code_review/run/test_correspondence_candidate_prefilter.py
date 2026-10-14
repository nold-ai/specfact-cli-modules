"""Frozen original public results and necessary-condition work regression."""

from __future__ import annotations

import hashlib
import importlib.metadata
import inspect
import json
import platform
import random
import signal
import sys
import time
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from specfact_code_review.run import differential as api, runner
from specfact_code_review.run.findings import ReviewFinding


# Work counters and exact boundary tests intentionally inspect private primitives.
# pylint: disable=protected-access


FIXTURES = Path(__file__).parent.parent / "fixtures" / "correspondence_prefilter"
ORIGINAL_HASH = "aa60b0854e31fad55b2c8efa53ffb32c92ab772ffbf8c8e565c2d8b6e45988e9"
SEED = 20261014


def finding(line: int = 2, **changes: Any) -> dict[str, Any]:
    return {
        "analyzer": "ruff",
        "rule": "R1",
        "severity": "warning",
        "path": "a.py",
        "line": line,
        "message": "same",
        "blocking": False,
        **changes,
    }


def request(
    before: bytes = b"a\nx\nz\n",
    after: bytes | None = None,
    base: list[dict[str, Any]] | None = None,
    head: list[dict[str, Any]] | None = None,
    **changes: Any,
) -> dict[str, Any]:
    return {
        "base_findings": [finding()] if base is None else base,
        "head_findings": [finding()] if head is None else head,
        "base_sources": {"a.py": before},
        "head_sources": {"a.py": before if after is None else after},
        **changes,
    }


def normalize(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"$bytes_hex": value.hex()}
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if isinstance(value, set):
        return {"$set": sorted(value)}
    return value


def restore(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"$bytes_hex"}:
            return bytes.fromhex(value["$bytes_hex"])
        if set(value) == {"$set"}:
            return set(value["$set"])
        return {key: restore(item) for key, item in value.items()}
    if isinstance(value, list):
        return [restore(item) for item in value]
    return value


def inventory() -> list[tuple[str, dict[str, Any], dict[str, int]]]:
    source = b"\n".join(f"line-{i}".encode() for i in range(32))
    four = [finding(i) for i in (4, 12, 20, 28)]
    cases = [
        ("unique_32_4", request(source, base=four, head=four)),
        ("one_line", request(b"x", base=[finding(1)], head=[finding(1)])),
        ("eof", request(base=[finding(3)], head=[finding(3)])),
        ("literal_sentinels", request(b"<BOF>\nx\n<EOF>")),
        ("changed_predecessor", request(after=b"b\nx\nz\n")),
        ("changed_successor", request(after=b"a\nx\ny\n")),
        ("shift", request(after=b"new\na\nx\nz\n", head=[finding(3)])),
        ("delete_shift", request(b"new\na\nx\nz", b"a\nx\nz", base=[finding(3)])),
        ("repeat_base_only", request(b"a\nx\nz\nx", b"a\nx\nz")),
        ("repeat_head_only", request(b"a\nx\nz", b"a\nx\nz\nx")),
        ("repeat_different_neighbors", request(b"a\nx\nz\nb\nx\nc")),
        ("duplicate_emissions", request(base=[finding(), finding()], head=[finding(), finding()])),
        ("unequal_emissions", request(base=[finding(), finding()], head=[finding()])),
        ("head_surplus", request(base=[finding()], head=[finding(), finding()])),
        ("permuted_emissions", request(source, base=list(reversed(four)), head=four[2:] + four[:2])),
        ("alternate_optimum", request(b"p\nx\nq\na\nb\nc", b"a\nb\nc\np\nx\nq", head=[finding(5)])),
        ("forced_nonoptimal", request(b"p\nx\nq\na\nb\nc\nd\ne", b"a\nb\nc\nd\ne\np\nx\nq", head=[finding(7)])),
        ("empty", request(b"")),
        ("missing", request(base_sources={})),
        ("singleton_fallback", request(base_sources={"other.py": b"a\nx\nz"})),
        ("exact_path_lookup", request(base_sources={"a.py": b"a\nx\nz", "other.py": b"no"})),
        ("multiple_missing_path", request(base_sources={"other.py": b"a", "third.py": b"b"})),
        ("zero_line", request(base=[finding(0)])),
        ("negative_line", request(head=[finding(-1)])),
        ("past_eof", request(head=[finding(4)])),
        ("crlf", request(b"a\nx\nz\n", b"a\r\nx\r\nz\r\n")),
        ("trailing_newline", request(b"a\nx\nz", b"a\nx\nz\n")),
        ("non_utf8_nul", request(b"\xff\nx\x00y\n\xfe")),
        (
            "rename",
            request(
                head=[{**finding(), "path": "b.py"}], rename_facts={"a.py": "b.py"}, head_sources={"b.py": b"a\nx\nz\n"}
            ),
        ),
        ("ambiguous_rename", request(rename_ambiguities={"a.py": ["b.py", "c.py"]})),
        ("added_deleted", request(head=[], deleted_paths=("a.py",), added_paths=("b.py",))),
        ("fixed", request(head=[])),
        ("introduced", request(base=[])),
        ("severity_transition", request(head=[{**finding(), "severity": "error"}])),
        ("blocking_transition", request(head=[{**finding(), "blocking": True}])),
        ("baseline_failure", request(base_analysis_status="error")),
        ("changed_lines", request(changed_lines={"a.py": {9, 10}})),
    ]
    for key in ("analyzer", "rule", "message"):
        cases.append(("partition_" + key, request(head=[{**finding(), key: "different"}])))
    rng = random.Random(SEED)
    for number in range(64):
        lines = [rng.choice([b"a", b"b", b"x", b"\x00", b"\xff"]) for _ in range(rng.randint(1, 8))]
        after = lines.copy()
        rng.shuffle(after)
        base = [finding(rng.randint(1, len(lines))) for _ in range(rng.randint(0, 4))]
        head = [finding(rng.randint(1, len(after))) for _ in range(rng.randint(0, 4))]
        cases.append((f"seeded_{number:02}", request(b"\n".join(lines), b"\n".join(after), base, head)))
    bounded = [
        ("lowered_byte_bound", request(), {"_MAX_SOURCE_BYTES": 5}),
        ("lowered_line_bound", request(), {"_MAX_SOURCE_LINES": 2}),
        ("lowered_cell_bound", request(), {"_MAX_CORRESPONDENCE_CELLS": 15}),
    ]
    return [(name, data, {}) for name, data in cases] + bounded


def classify(data: dict[str, Any], limits: dict[str, int]) -> Any:
    with ExitStack() as stack:
        for name, value in limits.items():
            stack.enter_context(patch.object(api, name, value))
        return api.classify_findings(api.FindingClassificationRequest(**data))


def literals() -> list[dict[str, Any]]:
    return json.loads((FIXTURES / "baseline_outputs.json").read_text())["cases"]


def range_projection(data: dict[str, Any]) -> dict[str, Any]:
    def findings(side: str) -> list[ReviewFinding]:
        return [
            ReviewFinding(
                category="style",
                severity=value["severity"],
                tool=value["analyzer"],
                rule=value["rule"],
                file=value["path"],
                line=value["line"],
                message=value["message"],
                blocking=value["blocking"],
            )
            for value in data[side]
        ]

    base = findings("base_findings")
    head = findings("head_findings")
    context = runner.RangeDifferentialContext(
        base_sources=data["base_sources"],
        head_sources=data["head_sources"],
        rename_facts=data.get("rename_facts", {}),
        rename_ambiguities=None,
        added_paths=(),
        deleted_paths=(),
    )
    evidence, classified = runner._classify_range_member(  # pylint: disable=protected-access
        "ruff",
        context,
        base_evidence={
            "execution_state": "ran",
            "evidence_outcome": "FAIL" if any(f.is_blocking() for f in base) else "PASS",
        },
        head_evidence={
            "execution_state": "ran",
            "evidence_outcome": "FAIL" if any(f.is_blocking() for f in head) else "PASS",
        },
        base_findings=base,
        head_findings=head,
    )
    return {"evidence": evidence, "findings": [finding.model_dump(mode="json") for finding in classified]}


def capture_original() -> None:
    """One-shot capture refuses modified source and refuses overwriting literals."""
    signal.alarm(30)
    started = time.monotonic()
    source = Path(inspect.getfile(api.classify_findings)).resolve()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == ORIGINAL_HASH
    assert source == Path(api.__file__).resolve()
    assert (
        source
        == Path(__file__).resolve().parents[4]
        / "packages/specfact-code-review/src/specfact_code_review/run/differential.py"
    )
    assert not (FIXTURES / "baseline_outputs.json").exists()

    cases = inventory()
    assert len(cases) <= 256
    records = []
    for name, data, limits in cases:
        assert (
            max(
                [len(value.splitlines()) for side in ("base_sources", "head_sources") for value in data[side].values()]
                or [0]
            )
            <= 32
        )
        assert len(data["base_findings"]) + len(data["head_findings"]) <= 8
        records.append(
            {
                "name": name,
                "request": normalize(data),
                "limits": limits,
                "expected": normalize(asdict(classify(data, limits))),
            }
        )
    selected = {
        "unique_32_4",
        "duplicate_emissions",
        "changed_predecessor",
        "alternate_optimum",
        "forced_nonoptimal",
        "introduced",
        "fixed",
    }
    for record in records:
        if record["name"] in selected:
            record["range_expected"] = range_projection(restore(record["request"]))
    encoded = (json.dumps({"cases": records}, indent=2, ensure_ascii=True) + "\n").encode()

    provenance = {
        "commit": "5b451ec066e0ea5cbd8a97ef3b59d915ae54fe5b",
        "source": str(source),
        "source_sha256": ORIGINAL_HASH,
        "runner_source": runner.__file__,
        "runner_sha256": hashlib.sha256(Path(runner.__file__).read_bytes()).hexdigest(),
        "callable_module": api.classify_findings.__module__,
        "callable_qualname": api.classify_findings.__qualname__,
        "executable": sys.executable,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            key: importlib.metadata.version(key) for key in ("pydantic", "icontract", "PyYAML", "pytest", "beartype")
        },
        "seed": SEED,
        "case_inventory": [name for name, _, _ in cases],
        "case_count": len(cases),
        "capture_command": (
            "PYTHONPATH=packages/specfact-code-review/src:src "
            "/private/tmp/specfact-cli-modules-worktrees/codex/native-pylint-execution-budget/.venv/bin/python "
            "tests/unit/specfact_code_review/run/test_correspondence_candidate_prefilter.py --capture-original"
        ),
        "outputs_sha256": hashlib.sha256(encoded).hexdigest(),
        "elapsed_seconds": time.monotonic() - started,
        "normalization": (
            "bytes tagged hex; tuple/list retain order; sets tagged sorted integers; all output fields retained"
        ),
        "bounds_note": (
            "Three public rejection cases lower one bound each; no production bound changes or large acceptance DP."
        ),
    }
    assert provenance["elapsed_seconds"] < 30
    FIXTURES.mkdir(parents=True, exist_ok=True)
    (FIXTURES / "baseline_outputs.json").write_bytes(encoded)
    (FIXTURES / "baseline_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(provenance, indent=2))


@pytest.mark.parametrize(
    "case", literals() if (FIXTURES / "baseline_outputs.json").exists() else [], ids=lambda case: case["name"]
)
def test_complete_original_classification(case: dict[str, Any]) -> None:
    assert normalize(asdict(classify(restore(case["request"]), case["limits"]))) == case["expected"]


def test_frozen_literal_integrity() -> None:
    provenance = json.loads((FIXTURES / "baseline_provenance.json").read_text())
    assert hashlib.sha256((FIXTURES / "baseline_outputs.json").read_bytes()).hexdigest() == provenance["outputs_sha256"]
    assert provenance["source_sha256"] == ORIGINAL_HASH


def test_unique_candidates_build_only_four_forbidden_matrices() -> None:
    data = inventory()[0][1]
    with patch.object(api, "_edit_costs", wraps=api._edit_costs) as costs:
        result = classify(data, {})
    forbidden = sum(call.kwargs.get("forbidden_pair") is not None for call in costs.call_args_list)
    assert forbidden == 4
    assert costs.call_count == 6
    assert len(result.unchanged) == 4
    assert result.status == "PASS"
    assert not result.introduced and not result.unknown and not result.fixed


@pytest.mark.parametrize(
    "name,decision",
    [("alternate_optimum", "alternate_optimal_correspondence"), ("forced_nonoptimal", "not_on_optimal_correspondence")],
)
def test_equal_unique_anchors_still_need_optimality(name: str, decision: str) -> None:
    data = next(data for case_name, data, _ in inventory() if case_name == name)
    result = classify(data, {})
    evidence = result.correspondence_evidence[0]
    assert evidence["base_distinct_location_count"] == evidence["head_distinct_location_count"] == 1
    assert evidence["base_anchor_digest"] == evidence["head_anchor_digest"]
    assert evidence["decision"] == decision


def test_rejected_search_still_builds_final_fallback_evidence() -> None:
    with patch.object(api, "_edit_costs", wraps=api._edit_costs) as costs:
        result = classify(request(after=b"b\nx\nz\n"), {})
    assert sum(call.kwargs.get("forbidden_pair") is not None for call in costs.call_args_list) == 1
    assert len(result.introduced) == 1
    assert result.correspondence_evidence[0]["decision"] == "occurrence_anchor_changed"
    assert {"global_cost", "forced_cost", "forbidden_cost", "pair_cost"} <= result.correspondence_evidence[0].keys()


def test_exact_bounds_without_large_dp() -> None:
    within = api._continuity_within_bounds
    source = b"x" * api._MAX_SOURCE_BYTES
    assert within(source, b"x", [b"x"], [b"x"], api._MAX_CORRESPONDENCE_CELLS)
    assert not within(source + b"x", b"x", [b"x"], [b"x"], 4)
    lines = [b"x"] * api._MAX_SOURCE_LINES
    assert within(b"x", b"x", lines, [b"x"], 4)
    assert not within(b"x", b"x", [*lines, b"x"], [b"x"], 4)
    assert not within(b"x", b"x", [b"x"], [b"x"], api._MAX_CORRESPONDENCE_CELLS + 1)


@pytest.mark.parametrize(
    "case",
    [case for case in literals() if "range_expected" in case] if (FIXTURES / "baseline_outputs.json").exists() else [],
    ids=lambda case: case["name"],
)
def test_actual_range_member_matches_original(case: dict[str, Any]) -> None:
    assert range_projection(restore(case["request"])) == case["range_expected"]


if __name__ == "__main__":
    assert sys.argv[1:] == ["--capture-original"]
    capture_original()
