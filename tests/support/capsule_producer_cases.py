import json


FIELD = "snapshot_producer_categories"
_DEPENDENCY = "project_analyzer_dependency_incompatible"
_RUNTIME = "project_runtime_required"
_PRIVATE = "PRIVATE_CANARY:/private/review.py --private-argument return private_source"
_OBSERVATIONS = "snapshot_diagnostic_observations"
_FACTS = "snapshot_diagnostic_facts"
_REPORT = {"assurance_status": "UNKNOWN", "overall_verdict": "FAIL", "findings": []}
_CONTRACT = {"id": "contracts", "diagnostic": "snapshot_member_incomplete"}
_STATE = {"execution_state": "error", "evidence_outcome": "UNKNOWN"}
_BASE_REASON = {"analyzer": "contracts", "side": "base", "reason": "unclassified"}
_HEAD_REASON = {**_BASE_REASON, "side": "head"}
_BASE_FACT = {
    "analyzer": "contracts",
    "side": "base",
    "shape": "string",
    "length_bucket": "within_bound",
    "recognized_leading_token": False,
}
_HEAD_FACT = {**_BASE_FACT, "side": "head"}
_BASE_DEPENDENCY = {"analyzer": "contracts", "side": "base", "category": _DEPENDENCY}
_HEAD_DEPENDENCY = {**_BASE_DEPENDENCY, "side": "head"}
_BASE_RUNTIME = {**_BASE_DEPENDENCY, "category": _RUNTIME}
_HEAD_RUNTIME = {**_BASE_RUNTIME, "side": "head"}
FAILURE_ROWS = [_BASE_DEPENDENCY, _HEAD_RUNTIME]
_BOTH_NODES = {
    "base": {**_STATE, "diagnostic": _DEPENDENCY + ":" + _PRIVATE},
    "head": {**_STATE, "diagnostic": _RUNTIME + ":" + _PRIVATE},
}
_FAILURE_REPORT = {**_REPORT, "analyzer_evidence": [{**_CONTRACT, **_BOTH_NODES}]}
FAILURE_PAYLOAD = json.dumps(_FAILURE_REPORT)
_EMPTY_SUMMARY = {
    "phase": "independent_review",
    "report_outcome": "structured_report",
    "assurance_status": "UNKNOWN",
    "overall_verdict": "FAIL",
    "findings_present": False,
    "tool_error_present": False,
    "execution_error_present": False,
    "unknown_evidence_present": False,
    "error_analyzers": [],
    "unknown_analyzers": [],
    "diagnostic_observations": ["unclassified"],
    "error_analyzer_sides": {},
    "crosshair_failure_observations": [],
}
_INVALID_SUMMARY = {
    "phase": "independent_review",
    "report_outcome": "invalid_report_shape",
    "assurance_status": "UNAVAILABLE",
    "overall_verdict": "UNAVAILABLE",
    "findings_present": False,
    "tool_error_present": False,
    "execution_error_present": False,
    "unknown_evidence_present": False,
    "error_analyzers": [],
    "unknown_analyzers": [],
    "diagnostic_observations": ["unclassified"],
}
_UNAVAILABLE = {"analyzer": "contracts", "diagnostic_class": "candidate_report_unavailable"}
_CODES = {"analyzer": "contracts", "diagnostic_codes": ["snapshot_member_incomplete"]}
_LEGACY = {
    "empty": {"candidate": [], "independent": [_EMPTY_SUMMARY]},
    "parent_only": {"candidate": [_CODES], "independent": [_EMPTY_SUMMARY]},
    "invalid": {"candidate": [_UNAVAILABLE], "independent": [_INVALID_SUMMARY]},
    "wrong_evidence": {"candidate": [], "independent": [_INVALID_SUMMARY]},
    "duplicate_json": {
        "candidate": [_UNAVAILABLE],
        "independent": [{**_INVALID_SUMMARY, "report_outcome": "unreadable_report"}],
    },
    "invalid_json": {
        "candidate": [_UNAVAILABLE],
        "independent": [{**_INVALID_SUMMARY, "report_outcome": "invalid_json"}],
    },
    "over_report_cap": {
        "candidate": [_UNAVAILABLE],
        "independent": [
            {
                **_INVALID_SUMMARY,
                "report_outcome": "oversized_report",
                "report_header_observed": False,
                "error_analyzer_sides": {},
                "crosshair_failure_observations": [],
            }
        ],
    },
    "finding_only": {
        "candidate": [],
        "independent": [{**_EMPTY_SUMMARY, "findings_present": True, "tool_error_present": True}],
    },
    "pylint_only": {
        "candidate": [{"analyzer": "pylint", "incomplete_snapshot_sides": ["base"]}],
        "independent": [
            {
                **_EMPTY_SUMMARY,
                "execution_error_present": True,
                "unknown_evidence_present": True,
                "error_analyzers": ["pylint"],
                "unknown_analyzers": ["pylint"],
                "error_analyzer_sides": {"pylint": ["base"]},
            }
        ],
    },
}
for _name, _sides, _reasons, _facts in (
    ("base", ["base"], [_BASE_REASON], [_BASE_FACT]),
    ("head", ["head"], [_HEAD_REASON], [_HEAD_FACT]),
    ("both", ["base", "head"], [_BASE_REASON, _HEAD_REASON], [_BASE_FACT, _HEAD_FACT]),
):
    _candidate = [
        {"analyzer": "contracts", "incomplete_snapshot_sides": _sides},
        _CODES,
        {_OBSERVATIONS: _reasons},
        {_FACTS: _facts},
    ]
    _summary = {
        **_EMPTY_SUMMARY,
        "execution_error_present": True,
        "unknown_evidence_present": True,
        "error_analyzers": ["contracts"],
        "unknown_analyzers": ["contracts"],
        "error_analyzer_sides": {"contracts": _sides},
        _OBSERVATIONS: _reasons,
        _FACTS: _facts,
    }
    _LEGACY[_name] = {"candidate": _candidate, "independent": [_summary]}
for _name, _shape, _bucket, _recognized in (
    ("missing", "missing", "not_string", False),
    ("non_string", "non_string", "not_string", False),
    ("empty_string", "string", "empty", False),
    ("over_bound", "string", "over_bound", False),
    ("literal_unclassified", "string", "within_bound", True),
):
    for _side, _fact in (("base", _BASE_FACT), ("head", _HEAD_FACT)):
        _facts = [{**_fact, "shape": _shape, "length_bucket": _bucket, "recognized_leading_token": _recognized}]
        _LEGACY[_side + "_" + _name] = {
            "candidate": [*_LEGACY[_side]["candidate"][:-1], {_FACTS: _facts}],
            "independent": [{**_LEGACY[_side]["independent"][0], _FACTS: _facts}],
        }
for _name, _overrides in (
    ("error_pass", {"unknown_evidence_present": False, "unknown_analyzers": []}),
    ("ran_unknown", {"execution_error_present": False, "error_analyzers": []}),
):
    _LEGACY[_name] = {
        "candidate": _LEGACY["base"]["candidate"],
        "independent": [{**_LEGACY["base"]["independent"][0], **_overrides}],
    }
_LEGACY["both_head_missing"] = {
    "candidate": [
        *_LEGACY["both"]["candidate"][:-1],
        {_FACTS: [_BASE_FACT, {**_HEAD_FACT, "shape": "missing", "length_bucket": "not_string"}]},
    ],
    "independent": [
        {
            **_LEGACY["both"]["independent"][0],
            _FACTS: [_BASE_FACT, {**_HEAD_FACT, "shape": "missing", "length_bucket": "not_string"}],
        }
    ],
}
_MIXED_REASONS = [_BASE_REASON, {**_HEAD_REASON, "reason": "analyzer_process_error"}]
_LEGACY["mixed_old_reason"] = {
    "candidate": [
        *_LEGACY["both"]["candidate"][:2],
        {_OBSERVATIONS: _MIXED_REASONS},
        {_FACTS: [_BASE_FACT]},
    ],
    "independent": [{**_LEGACY["both"]["independent"][0], _OBSERVATIONS: _MIXED_REASONS, _FACTS: [_BASE_FACT]}],
}
_LEGACY["ambiguous"] = {
    "candidate": _LEGACY["base"]["candidate"][:2] * 2,
    "independent": [
        {
            **_EMPTY_SUMMARY,
            "execution_error_present": True,
            "unknown_evidence_present": True,
            "error_analyzers": ["contracts"],
            "unknown_analyzers": ["contracts"],
            "error_analyzer_sides": {"contracts": ["base"]},
        }
    ],
}
_LEGACY["over_evidence_cap"] = {
    "candidate": _LEGACY["base"]["candidate"][:2],
    "independent": _LEGACY["ambiguous"]["independent"],
}
_LEGACY["large"] = {
    "candidate": [_UNAVAILABLE, *_LEGACY["both"]["candidate"]],
    "independent": [
        {
            **_LEGACY["both"]["independent"][0],
            "report_outcome": "oversized_report",
            "assurance_status": "UNAVAILABLE",
            "overall_verdict": "UNAVAILABLE",
            "report_header_observed": True,
        }
    ],
}
_LEGACY["without_findings"] = {"candidate": _LEGACY["base"]["candidate"], "independent": [_INVALID_SUMMARY]}
_EMPTY_CATEGORIES = {"candidate": [], "independent": []}
CASES = []
for _name, _nodes, _categories, _legacy in (
    (
        "bare-families",
        {"base": {**_STATE, "diagnostic": _DEPENDENCY}, "head": {**_STATE, "diagnostic": _RUNTIME}},
        FAILURE_ROWS,
        "both",
    ),
    (
        "bare-families-swapped",
        {"base": {**_STATE, "diagnostic": _RUNTIME}, "head": {**_STATE, "diagnostic": _DEPENDENCY}},
        [_BASE_RUNTIME, _HEAD_DEPENDENCY],
        "both",
    ),
    ("private-suffix-families", _BOTH_NODES, FAILURE_ROWS, "both"),
    (
        "private-suffix-families-swapped",
        {
            "base": {**_STATE, "diagnostic": _RUNTIME + ":" + _PRIVATE},
            "head": {**_STATE, "diagnostic": _DEPENDENCY + ":" + _PRIVATE},
        },
        [_BASE_RUNTIME, _HEAD_DEPENDENCY],
        "both",
    ),
    ("dependency-base", {"base": {**_STATE, "diagnostic": _DEPENDENCY}}, [_BASE_DEPENDENCY], "base"),
    ("dependency-head", {"head": {**_STATE, "diagnostic": _DEPENDENCY}}, [_HEAD_DEPENDENCY], "head"),
    ("runtime-base", {"base": {**_STATE, "diagnostic": _RUNTIME}}, [_BASE_RUNTIME], "base"),
    ("runtime-head", {"head": {**_STATE, "diagnostic": _RUNTIME}}, [_HEAD_RUNTIME], "head"),
    (
        "error-with-pass",
        {"base": {"execution_state": "error", "evidence_outcome": "PASS", "diagnostic": _DEPENDENCY}},
        [_BASE_DEPENDENCY],
        "error_pass",
    ),
    (
        "ran-with-unknown",
        {"base": {"execution_state": "ran", "evidence_outcome": "UNKNOWN", "diagnostic": _RUNTIME}},
        [_BASE_RUNTIME],
        "ran_unknown",
    ),
    (
        "complete-side",
        {"base": {"execution_state": "ran", "evidence_outcome": "PASS", "diagnostic": _DEPENDENCY}},
        [],
        "parent_only",
    ),
    ("absent-sides", {}, [], "parent_only"),
    ("nonobject-sides", {"base": _DEPENDENCY, "head": [_RUNTIME]}, [], "parent_only"),
    ("unrelated-side", {"other": {**_STATE, "diagnostic": _DEPENDENCY}}, [], "parent_only"),
    ("missing-diagnostic", {"base": _STATE}, [], "base_missing"),
    ("family-and-missing", {"base": _BOTH_NODES["base"], "head": _STATE}, [_BASE_DEPENDENCY], "both_head_missing"),
    (
        "family-and-unknown",
        {"base": _BOTH_NODES["base"], "head": {**_STATE, "diagnostic": "unknown:" + _PRIVATE}},
        [_BASE_DEPENDENCY],
        "both",
    ),
    (
        "family-and-old-recognized",
        {"base": _BOTH_NODES["base"], "head": {**_STATE, "diagnostic": "analyzer_process_error:" + _PRIVATE}},
        [_BASE_DEPENDENCY],
        "mixed_old_reason",
    ),
):
    CASES.append(
        {
            "id": _name,
            "payload": json.dumps({**_REPORT, "analyzer_evidence": [{**_CONTRACT, **_nodes}]}),
            "categories": {"candidate": _categories, "independent": _categories},
            "legacy": _LEGACY[_legacy],
        }
    )
for _name, _diagnostic, _legacy in (
    ("null", None, "base_non_string"),
    ("boolean", False, "base_non_string"),
    ("number", 42, "base_non_string"),
    ("list", [_DEPENDENCY], "base_non_string"),
    ("object", {"diagnostic": _RUNTIME, "private": _PRIVATE}, "base_non_string"),
    ("empty", "", "base_empty_string"),
    ("unknown", "unknown:" + _PRIVATE, "base"),
    ("literal-unclassified", "unclassified", "base_literal_unclassified"),
    ("leading-space", " " + _DEPENDENCY + ":" + _PRIVATE, "base"),
    ("space-before-colon", _RUNTIME + " :" + _PRIVATE, "base"),
    ("changed-case", "PROJECT_RUNTIME_REQUIRED:" + _PRIVATE, "base"),
    ("embedded-token", "embedded-" + _DEPENDENCY, "base"),
    ("extended-token", _DEPENDENCY + "_extended:" + _PRIVATE, "base"),
    ("wrong-delimiter", _RUNTIME + ";" + _PRIVATE, "base"),
    ("unknown-then-family", "unknown:" + _DEPENDENCY, "base"),
):
    CASES.append(
        {
            "id": _name,
            "payload": json.dumps(
                {**_REPORT, "analyzer_evidence": [{**_CONTRACT, "base": {**_STATE, "diagnostic": _diagnostic}}]}
            ),
            "categories": _EMPTY_CATEGORIES,
            "legacy": _LEGACY[_legacy],
        }
    )
for _name, _diagnostic, _category in (
    ("dependency-before-runtime", _DEPENDENCY + ":" + _RUNTIME + ":" + _PRIVATE, _BASE_DEPENDENCY),
    ("runtime-before-dependency", _RUNTIME + ":" + _DEPENDENCY + ":" + _PRIVATE, _BASE_RUNTIME),
):
    CASES.append(
        {
            "id": _name,
            "payload": json.dumps(
                {**_REPORT, "analyzer_evidence": [{**_CONTRACT, "base": {**_STATE, "diagnostic": _diagnostic}}]}
            ),
            "categories": {"candidate": [_category], "independent": [_category]},
            "legacy": _LEGACY["base"],
        }
    )
for _family_name, _family, _side, _category in (
    ("dependency", _DEPENDENCY, "base", _BASE_DEPENDENCY),
    ("runtime", _RUNTIME, "head", _HEAD_RUNTIME),
):
    for _char_name, _character in (("ascii", "x"), ("unicode", "é")):
        for _length, _category_rows, _legacy_suffix in ((4096, [_category], ""), (4097, [], "_over_bound")):
            CASES.append(
                {
                    "id": f"{_family_name}-{_char_name}-{_length}",
                    "payload": json.dumps(
                        {
                            **_REPORT,
                            "analyzer_evidence": [
                                {
                                    **_CONTRACT,
                                    _side: {
                                        **_STATE,
                                        "diagnostic": _family + ":" + _character * (_length - len(_family) - 1),
                                    },
                                }
                            ],
                        },
                        ensure_ascii=False,
                    ),
                    "categories": {"candidate": _category_rows, "independent": _category_rows},
                    "legacy": _LEGACY[_side + _legacy_suffix],
                }
            )
_BASE_ROW = {**_CONTRACT, "base": _BOTH_NODES["base"]}
for _name, _evidence, _categories, _legacy in (
    ("zero-contracts", [], [], "empty"),
    ("duplicate-contracts", [_BASE_ROW, _BASE_ROW], [], "ambiguous"),
    ("wrong-evidence-list-type", {"contracts": _BASE_ROW}, [], "wrong_evidence"),
    ("exactly-ten-entries", [{"id": "ruff"}] * 9 + [_BASE_ROW], [_BASE_DEPENDENCY], "base"),
    ("eleven-entries", [{"id": "ruff"}] * 9 + [_BASE_ROW, {"id": "ruff"}], [], "over_evidence_cap"),
    ("duplicate-after-ten", [{"id": "ruff"}] * 9 + [_BASE_ROW, _BASE_ROW], [], "over_evidence_cap"),
    ("unrelated-values", [None, [], _PRIVATE, {"id": "ruff"}, _BASE_ROW], [_BASE_DEPENDENCY], "base"),
    ("parent-only-family", [{"id": "contracts", "diagnostic": _DEPENDENCY}], [], "empty"),
    (
        "pylint-only-family",
        [{"id": "pylint", "diagnostic": _RUNTIME, "base": _BOTH_NODES["base"]}],
        [],
        "pylint_only",
    ),
):
    CASES.append(
        {
            "id": _name,
            "payload": json.dumps({**_REPORT, "analyzer_evidence": _evidence}),
            "categories": {"candidate": _categories, "independent": _categories},
            "legacy": _LEGACY[_legacy],
        }
    )
for _name, _report, _legacy in (
    ("root-only-family", {**_REPORT, "analyzer_evidence": [], "diagnostic": _DEPENDENCY}, "empty"),
    (
        "finding-only-family",
        {
            **_REPORT,
            "analyzer_evidence": [],
            "findings": [{"category": "tool_error", "message": _RUNTIME + ":" + _PRIVATE}],
        },
        "finding_only",
    ),
    ("null-root", None, "invalid"),
    ("number-root", 42, "invalid"),
    ("string-root", _DEPENDENCY, "invalid"),
    ("list-root", [_FAILURE_REPORT], "invalid"),
):
    CASES.append(
        {
            "id": _name,
            "payload": json.dumps(_report),
            "categories": _EMPTY_CATEGORIES,
            "legacy": _LEGACY[_legacy],
        }
    )
for _name, _old, _replacement in (
    ("duplicate-root-key", '"findings": []', '"findings": [], "findings": []'),
    ("duplicate-row-id", '"id": "contracts"', '"id": "contracts", "id": "contracts"'),
    ("duplicate-side-key", '"base": {', '"base": {}, "base": {'),
    (
        "duplicate-diagnostic-key",
        '"diagnostic": "project_analyzer',
        '"diagnostic": null, "diagnostic": "project_analyzer',
    ),
):
    CASES.append(
        {
            "id": _name,
            "payload": FAILURE_PAYLOAD.replace(_old, _replacement),
            "categories": _EMPTY_CATEGORIES,
            "legacy": _LEGACY["duplicate_json"],
        }
    )
for _name, _payload, _categories, _legacy in (
    ("truncated-json", FAILURE_PAYLOAD[:-1], [], "invalid_json"),
    ("trailing-json", FAILURE_PAYLOAD + _PRIVATE, [], "invalid_json"),
    ("above-two-mib", FAILURE_PAYLOAD + " " * (2 * 1024 * 1024), FAILURE_ROWS, "large"),
    ("exactly-thirty-two-mib", FAILURE_PAYLOAD.ljust(32 * 1024 * 1024), FAILURE_ROWS, "large"),
    ("over-thirty-two-mib", FAILURE_PAYLOAD.ljust(32 * 1024 * 1024 + 1), [], "over_report_cap"),
):
    CASES.append(
        {
            "id": _name,
            "payload": _payload,
            "categories": {"candidate": _categories, "independent": _categories},
            "legacy": _LEGACY[_legacy],
        }
    )
CASES.append(
    {
        "id": "candidate-without-findings",
        "payload": json.dumps({"analyzer_evidence": [_BASE_ROW]}),
        "categories": {"candidate": [_BASE_DEPENDENCY], "independent": []},
        "legacy": _LEGACY["without_findings"],
    }
)
for _name, _family in (("dependency-only-in-log", _DEPENDENCY), ("runtime-only-in-log", _RUNTIME)):
    CASES.append(
        {
            "id": _name,
            "payload": "{}",
            "log": _family + ":" + _PRIVATE,
            "categories": _EMPTY_CATEGORIES,
            "legacy": _LEGACY["wrong_evidence"],
        }
    )
