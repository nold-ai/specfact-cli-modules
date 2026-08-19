"""C14 red tests for finding continuity, lifecycle, and suppression governance."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest


@pytest.fixture
def differential_api() -> Any:
    from specfact_code_review.run import differential

    return differential


def _finding(
    *,
    path: str = "src/app.py",
    line: int = 2,
    rule: str = "rule-x",
    severity: str = "error",
    message: str = "unsafe value",
) -> dict[str, Any]:
    return {
        "analyzer": "ruff",
        "rule": rule,
        "severity": severity,
        "path": path,
        "line": line,
        "message": message,
        "blocking": severity == "error",
    }


def _classify(
    api: Any,
    *,
    base: list[dict[str, Any]] | None = None,
    head: list[dict[str, Any]] | None = None,
    before: str = "alpha\nunsafe value\nomega\n",
    after: str = "alpha\nunsafe value\nomega\n",
    **kwargs: Any,
) -> Any:
    return api.classify_findings(
        base_findings=base or [],
        head_findings=head or [],
        base_sources={"src/app.py": before.encode()},
        head_sources={"src/app.py": after.encode()},
        **kwargs,
    )


def test_introduced_blocker_off_added_line_still_blocks(differential_api: Any) -> None:
    result = _classify(differential_api, head=[_finding(line=2)], changed_lines={"src/app.py": {10}})

    assert result.status == "FAIL"
    assert result.introduced[0].path == "src/app.py"
    assert result.introduced[0].line == 2


def test_unchanged_baseline_blocker_is_retained_but_not_introduced(differential_api: Any) -> None:
    finding = _finding()
    result = _classify(differential_api, base=[finding], head=[finding])

    assert result.status == "FAIL"
    assert len(result.unchanged) == 1
    assert result.introduced == ()


def test_baseline_analysis_failure_is_unknown(differential_api: Any) -> None:
    result = _classify(differential_api, head=[], base_analysis_status="error")

    assert result.status == "UNKNOWN"
    assert result.reason == "baseline_analysis_error"


def test_range_differential_uses_merge_base_snapshot_when_base_tip_advanced(differential_api: Any) -> None:
    result = differential_api.select_differential_snapshots(
        merge_base="1" * 40,
        base_tip="2" * 40,
        head="3" * 40,
    )

    assert result.baseline_commit == "1" * 40
    assert result.target_tip_commit == "2" * 40


@dataclass(frozen=True)
class _ContinuityCase:
    base: tuple[dict[str, Any], ...]
    head: tuple[dict[str, Any], ...]
    before: str
    after: str
    expected_status: str
    expected_bucket: str
    kwargs: dict[str, Any]


_CONTINUITY_CASES: dict[str, _ContinuityCase] = {
    "test_pure_rename_preserves_unchanged_fingerprint": _ContinuityCase(
        (_finding(path="src/old.py"),),
        (_finding(path="src/new.py"),),
        "alpha\nunsafe value\nomega\n",
        "alpha\nunsafe value\nomega\n",
        "FAIL",
        "unchanged",
        {"rename_facts": {"src/old.py": "src/new.py"}},
    ),
    "test_ambiguous_exact_blob_moves_are_unknown": _ContinuityCase(
        (_finding(path="src/old.py"),),
        (_finding(path="src/new.py"),),
        "alpha\nunsafe value\nomega\n",
        "alpha\nunsafe value\nomega\n",
        "UNKNOWN",
        "unknown",
        {"rename_ambiguities": {"blob-a": ["src/a.py", "src/b.py"]}},
    ),
    "test_modified_delete_add_cannot_claim_fixed": _ContinuityCase(
        (_finding(path="src/old.py"),),
        (),
        "alpha\nunsafe value\nomega\n",
        "alpha\nreplacement\nomega\n",
        "UNKNOWN",
        "unknown",
        {"deleted_paths": ("src/old.py",), "added_paths": ("src/new.py",)},
    ),
    "test_missing_finding_across_any_rename_is_unknown": _ContinuityCase(
        (_finding(path="src/old.py"),),
        (),
        "alpha\nunsafe value\nomega\n",
        "alpha\nsafe value\nomega\n",
        "UNKNOWN",
        "unknown",
        {"rename_facts": {"src/old.py": "src/new.py"}},
    ),
    "test_renamed_file_fix_is_conservatively_unknown": _ContinuityCase(
        (_finding(path="src/old.py"),),
        (),
        "alpha\nunsafe value\nomega\n",
        "alpha\nsafe value\nomega\n",
        "UNKNOWN",
        "unknown",
        {"rename_facts": {"src/old.py": "src/new.py"}},
    ),
    "test_matching_fingerprint_severity_change_is_unknown": _ContinuityCase(
        (_finding(severity="warning"),),
        (_finding(severity="error"),),
        "alpha\nunsafe value\nomega\n",
        "alpha\nunsafe value\nomega\n",
        "UNKNOWN",
        "unknown",
        {},
    ),
    "test_duplicate_finding_multiset_preserves_head_surplus_as_introduced": _ContinuityCase(
        (_finding(),),
        (_finding(), _finding()),
        "alpha\nunsafe value\nomega\n",
        "alpha\nunsafe value\nomega\n",
        "FAIL",
        "introduced",
        {},
    ),
    "test_line_only_shift_preserves_unchanged_occurrence": _ContinuityCase(
        (_finding(line=2),),
        (_finding(line=3),),
        "alpha\nunsafe value\nomega\n",
        "inserted\nalpha\nunsafe value\nomega\n",
        "FAIL",
        "unchanged",
        {},
    ),
    "test_identity_equal_replacement_at_different_source_anchor_is_introduced": _ContinuityCase(
        (_finding(line=2),),
        (_finding(line=2),),
        "alpha\nunsafe value\nomega\n",
        "different\nunsafe value\ncontext\n",
        "FAIL",
        "introduced",
        {},
    ),
    "test_identical_block_moved_to_different_edit_location_is_not_unchanged": _ContinuityCase(
        (_finding(line=2),),
        (_finding(line=4),),
        "alpha\nunsafe value\nomega\nmore\n",
        "alpha\nomega\nmore\nunsafe value\n",
        "FAIL",
        "introduced",
        {},
    ),
    "test_alternate_optimal_line_correspondence_is_unknown": _ContinuityCase(
        (_finding(line=2),),
        (_finding(line=3),),
        "same\nsame\nsame\n",
        "same\nsame\nsame\n",
        "UNKNOWN",
        "unknown",
        {},
    ),
    "test_correspondence_bounds_are_unknown": _ContinuityCase(
        (_finding(),),
        (_finding(),),
        "x\n",
        "x\n",
        "UNKNOWN",
        "unknown",
        {"source_size_override": 16 * 1024 * 1024 + 1},
    ),
    "test_ambiguous_repeated_source_anchor_cannot_pair_unchanged": _ContinuityCase(
        (_finding(line=2),),
        (_finding(line=4),),
        "a\nunsafe value\na\nunsafe value\n",
        "a\nunsafe value\na\nunsafe value\n",
        "UNKNOWN",
        "unknown",
        {},
    ),
    "test_mixed_severity_duplicate_bucket_is_unknown": _ContinuityCase(
        (_finding(severity="warning"), _finding(severity="error")),
        (_finding(severity="warning"),),
        "alpha\nunsafe value\nomega\n",
        "alpha\nunsafe value\nomega\n",
        "UNKNOWN",
        "unknown",
        {},
    ),
}


def _make_continuity_test(name: str, case: _ContinuityCase) -> Callable[[Any], None]:
    def test(differential_api: Any) -> None:
        result = _classify(
            differential_api,
            base=list(case.base),
            head=list(case.head),
            before=case.before,
            after=case.after,
            **case.kwargs,
        )
        assert result.status == case.expected_status
        assert getattr(result, case.expected_bucket)
        assert result.evidence_digest.startswith("sha256:")

    test.__name__ = name
    test.__qualname__ = name
    return test


globals().update({name: _make_continuity_test(name, case) for name, case in _CONTINUITY_CASES.items()})


def test_rename_facts_ignore_ambient_git_config(differential_api: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "diff.renames")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "copies")

    facts = differential_api.canonical_exact_renames(deleted={"src/old.py": "blob-a"}, added={"src/new.py": "blob-a"})

    assert facts.pairs == (("src/old.py", "src/new.py"),)
    assert facts.algorithm == "canonical-exact-rename-v1"


@pytest.mark.parametrize(
    ("source", "kind"),
    [
        ("value = 1  # noqa: F401\n", "introduced_inline_suppression"),
        ("value = 1  # type: ignore\n", "introduced_inline_suppression"),
        ("value = 1  # nosemgrep\n", "introduced_inline_suppression"),
        ("value = 1  # pragma: no cover\n", "introduced_inline_suppression"),
        ("value = 1  # pyright: strict\n", "introduced_analyzer_result_control"),
        ("value = 1  # crosshair: enabled=false\n", "introduced_analyzer_result_control"),
    ],
    ids=["ruff-noqa", "type-ignore", "nosemgrep", "no-cover", "pyright-strict", "crosshair-disabled"],
)
def test_introduced_inline_suppression_blocks_before_fixed_classification(
    differential_api: Any, source: str, kind: str
) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"value = 1\n"},
        head_sources={"src/app.py": source.encode()},
    )

    assert result.status == "FAIL"
    assert result.findings[0].kind == kind
    assert result.findings[0].blocking is True


def test_unchanged_baseline_inline_suppression_is_retained(differential_api: Any) -> None:
    source = b"value = 1  # noqa: F401\n"
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": source}, head_sources={"src/app.py": source}
    )

    assert result.introduced == ()
    assert len(result.unchanged) == 1


def test_suppression_manifest_failure_is_unknown(differential_api: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(differential_api, "_tokenize_comments", lambda *_args: (_ for _ in ()).throw(TokenError()))

    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"x=1\n"}, head_sources={"src/app.py": b"x=2\n"}
    )

    assert result.status == "UNKNOWN"


class TokenError(Exception):
    pass


def test_suppression_waiver_input_is_unsupported_in_cr14(differential_api: Any) -> None:
    with pytest.raises(differential_api.UnsupportedWaiverInput):
        differential_api.classify_suppression_delta(
            base_sources={"src/app.py": b"x=1\n"},
            head_sources={"src/app.py": b"x=1  # noqa\n"},
            waiver={"trusted": True},
        )


@pytest.mark.parametrize(
    "directive",
    [
        "# isort: skip_file",
        "# isort: on",
        "# isort: off",
        "# isort: skip",
        "# isort: split",
        "# ruff: isort: skip_file",
        "# ruff: isort: on",
        "# ruff: isort: off",
        "# ruff: isort: skip",
        "# ruff: isort: split",
    ],
    ids=[
        "isort-skip-file",
        "isort-on",
        "isort-off",
        "isort-skip",
        "isort-split",
        "ruff-isort-skip-file",
        "ruff-isort-on",
        "ruff-isort-off",
        "ruff-isort-skip",
        "ruff-isort-split",
    ],
)
def test_ruff_isort_action_comment_catalog_blocks_before_fixed_classification(
    differential_api: Any, directive: str
) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"x=1\n"}, head_sources={"src/app.py": f"x=1  {directive}\n".encode()}
    )

    assert result.status == "FAIL"
    assert result.findings[0].kind == "introduced_inline_suppression"


@pytest.mark.parametrize(
    "directive",
    [
        "# ruff: ignore[F401]",
        "# ruff: file-ignore[F401, E501,]",
        "# ruff: disable[unused-import]",
        "# ruff: enable[F401]",
    ],
    ids=["ruff-ignore", "ruff-file-ignore", "ruff-disable", "ruff-enable"],
)
def test_ruff_ignore_file_ignore_disable_enable_catalog_blocks_before_fixed_classification(
    differential_api: Any, directive: str
) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"x=1\n"}, head_sources={"src/app.py": f"x=1  {directive}\n".encode()}
    )

    assert result.status == "FAIL"


@pytest.mark.parametrize(
    "directive",
    ["disable=undefined-variable", "disable-next=undefined-variable"],
    ids=["disable", "disable-next"],
)
def test_pylint_disable_and_disable_next_block_before_fixed_classification(
    differential_api: Any, directive: str
) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"print(missing)\n"},
        head_sources={"src/app.py": f"# pylint: {directive}\nprint(missing)\n".encode()},
        missing_base_findings=[_finding(rule="undefined-variable")],
    )

    assert result.status == "FAIL"
    assert result.missing_base_disposition == "unknown"


@pytest.mark.parametrize(
    "directive",
    ["# pylint: skip-file", "# pylint: disable-all", "# pylint: disable-msg=E0602"],
    ids=["skip-file", "disable-all", "disable-msg"],
)
def test_pylint_skip_file_blocks_before_fixed_classification(differential_api: Any, directive: str) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"print(missing)\n"},
        head_sources={"src/app.py": f"{directive}\nprint(missing)\n".encode()},
    )

    assert result.status == "FAIL"


@pytest.mark.parametrize(
    "directive",
    [
        "# pyright: strict",
        "# pyright: basic",
        "# pyright: standard",
        "# pyright: analyzeUnannotatedFunctions=false",
        "# pyright: reportMissingImports=none",
    ],
    ids=["strict", "basic", "standard", "analyze-unannotated-false", "report-missing-imports-none"],
)
def test_basedpyright_complete_source_directive_catalog_blocks_before_fixed_classification(
    differential_api: Any, directive: str
) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"x=1\n"}, head_sources={"src/app.py": f"x=1  {directive}\n".encode()}
    )

    assert result.status == "FAIL"
    assert result.findings[0].kind == "introduced_analyzer_result_control"


@pytest.mark.parametrize(
    "directive",
    ["# pyright: ignore", "# pyright: ignore[reportMissingImports]"],
    ids=["ignore", "ignore-report-missing-imports"],
)
def test_basedpyright_pyright_ignore_comments_block_before_fixed_classification(
    differential_api: Any, directive: str
) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"x=1\n"}, head_sources={"src/app.py": f"x=1  {directive}\n".encode()}
    )

    assert result.status == "FAIL"


@pytest.mark.parametrize(
    "directive",
    [
        "# crosshair: analysis_kind=asserts",
        "# crosshair: specs_complete=yes",
        "# crosshair: max_iterations=0",
        "# crosshair: per_condition_timeout=0",
        "# crosshair: per_path_timeout=0",
        "# crosshair: max_uninteresting_iterations=1",
    ],
    ids=[
        "analysis-kind-asserts",
        "specs-complete-yes",
        "max-iterations-zero",
        "condition-timeout-zero",
        "path-timeout-zero",
        "max-uninteresting-one",
    ],
)
def test_crosshair_source_directive_catalog_blocks_before_fixed_classification(
    differential_api: Any, directive: str
) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"x=1\n"}, head_sources={"src/app.py": f"x=1  {directive}\n".encode()}
    )

    assert result.status == "FAIL"
    assert result.findings[0].kind == "introduced_analyzer_result_control"


@pytest.mark.parametrize("value", ["0", "false", "n", "no", "FALSE", "NO"])
def test_crosshair_disabling_aliases_block_before_fixed_classification(differential_api: Any, value: str) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": b"x=1\n"},
        head_sources={"src/app.py": f"x=1  # crosshair: enabled={value}\n".encode()},
    )

    assert result.status == "FAIL"


@pytest.mark.parametrize(
    "source",
    [
        "x=1  # noqa: F401\ny=2\n",
        "x=1  # type: ignore\ny=2\n",
        "x=1  # pylint: disable=unused-variable\ny=2\n",
        "x=1  # nosemgrep\ny=2\n",
        "x=1  # pragma: no cover\ny=2\n",
        "x=1  # crosshair: enabled=false\ny=2\n",
    ],
    ids=["ruff-noqa", "type-ignore", "pylint-disable", "nosemgrep", "no-cover", "crosshair-disabled"],
)
def test_changed_file_with_unchanged_suppression_is_unknown(differential_api: Any, source: str) -> None:
    result = differential_api.classify_suppression_delta(
        base_sources={"src/app.py": source.encode()},
        head_sources={"src/app.py": source.replace("y=2", "y=3").encode()},
    )

    assert result.status == "UNKNOWN"
    assert result.findings[0].kind == "unchanged_suppression_on_changed_file"
    assert result.findings[0].evidence.changed_hunk_digest.startswith("sha256:")


def test_byte_identical_rename_with_unchanged_suppression_is_not_quarantined(differential_api: Any) -> None:
    source = b"x=1  # noqa: F401\n"
    result = differential_api.classify_suppression_delta(
        base_sources={"src/old.py": source},
        head_sources={"src/new.py": source},
        rename_facts={"src/old.py": "src/new.py"},
    )

    assert result.status != "UNKNOWN"
    assert all(finding.kind != "unchanged_suppression_on_changed_file" for finding in result.findings)


def test_required_profile_findings_have_canonical_location_kind(differential_api: Any) -> None:
    finding = differential_api.normalize_location(
        analyzer="ruff",
        path="src/app.py",
        source=b"caf\xc3\xa9 = 1\n",
        raw={"row": 1, "column": 0, "end_row": 1, "end_column": 5},
    )

    assert finding.location.kind == "source_span"
    assert finding.location.schema == "source-span-v1"


def test_line_only_finding_uses_full_physical_line_span_fallback(differential_api: Any) -> None:
    location = differential_api.line_fallback_location("src/app.py", b"caf\xc3\xa9 = 1\n", line=1)

    assert location.start_column == 0
    assert location.end_column == len("caf\xc3\xa9 = 1".encode())
    assert location.precision == "line"


def test_exact_adapter_coordinates_convert_to_utf8_byte_half_open_span(differential_api: Any) -> None:
    location = differential_api.convert_exact_location(
        path="src/app.py",
        source="caf\u00e9 = 1\n".encode(),
        coordinate_system="utf16-code-units",
        start=(0, 0),
        end=(0, 4),
    )

    assert (location.start_line, location.start_column) == (1, 0)
    assert (location.end_line, location.end_column) == (1, len("caf\u00e9".encode()))
    assert location.precision == "exact"


def test_selector_and_non_source_locations_do_not_enter_source_continuity(differential_api: Any) -> None:
    for kind in ("selector", "infrastructure"):
        result = differential_api.source_continuity(location={"kind": kind, "value": "node-or-tool"})
        assert result.status == "UNKNOWN"
        assert result.reason == "non_source_location"


def test_suppression_catalog_resource_matches_checkpoint(differential_api: Any) -> None:
    resource, checkpoint = differential_api.load_suppression_catalog_and_checkpoint()

    assert resource.digest == checkpoint.suppression_catalog_contract.digest
    assert resource.canonical_bytes == checkpoint.suppression_catalog_contract.canonical_bytes


def test_suppression_catalog_drift_is_unknown_before_profile_activation(differential_api: Any) -> None:
    result = differential_api.activate_suppression_catalog(
        checkpoint_digest="sha256:" + "a" * 64,
        resource_digest="sha256:" + "b" * 64,
        package_digest="sha256:" + "a" * 64,
        profile_digest="sha256:" + "a" * 64,
    )

    assert result.status == "UNKNOWN"
    assert result.profile_activated is False
