"""Native complete coverage keeps physical and logical snapshot identities aligned."""

from __future__ import annotations

from pathlib import Path

import pytest

from specfact_code_review.run import native_worker, runner


@pytest.mark.parametrize("test_root", [".", "tests"])
@pytest.mark.parametrize(
    "production_coverage,expected_rule", [(100.0, None), (20.0, "TEST_COVERAGE_LOW"), (None, "tool_error")]
)
def test_native_complete_coverage_excludes_tests_without_omitting_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_root: str,
    production_coverage: float | None,
    expected_rule: str | None,
) -> None:
    capsule, project, temporary = (tmp_path / name for name in ("capsule", "project", "temporary"))
    for root in (capsule, project, temporary):
        root.mkdir()
    source, test, helper = (project / name for name in ("src/app.py", "tests/test_app.py", "tests/support.py"))
    for path in (source, test, helper):
        path.parent.mkdir(exist_ok=True)
        path.write_text("VALUE = 1\n", encoding="utf-8")
    config, coverage_config = (project / name for name in ("pytest.ini", "coveragerc"))
    config.write_text(f"[pytest]\ntestpaths = /opt/specfact/snapshot/{test_root}\n", encoding="utf-8")
    coverage_config.write_text("[report]\nfail_under = 95\n", encoding="utf-8")
    transport = native_worker.ReplayTransport(
        member="targeted-pytest-coverage",
        tool="pytest",
        replies=[],
        capsule=capsule,
        project=project,
        temporary=temporary,
    )
    examined = []

    def evaluate(source_files, _execute, **policy):
        examined.extend(source_files)
        assert policy["planned"] == ("tests/test_app.py::test_app",)
        assert policy["coverage_threshold"] == 95.0
        assert policy["blocking_low_coverage"] is True
        assert policy["allow_project_omitted_initializers"] is False
        files = (
            {}
            if production_coverage is None
            else {
                str(source): {"summary": {"percent_covered": production_coverage}},
            }
        )
        return runner._coverage_findings(
            source_files,
            {"files": files},
            allow_project_omitted_initializers=False,
            threshold=95.0,
            blocking_low_coverage=True,
        )

    monkeypatch.setattr(runner, "_evaluate_pytest_execution", evaluate)
    findings = native_worker._pytest_external_adapter(
        [source, test, helper],
        transport.run,
        [
            "-c",
            str(config),
            "--rootdir",
            str(project),
            "--cov-config",
            str(coverage_config),
            "--",
            "tests/test_app.py::test_app",
        ],
        False,
        True,
    )
    assert examined == [source]
    if expected_rule is None:
        assert findings == []
    elif expected_rule == "tool_error":
        assert len(findings) == 1 and findings[0].category == "tool_error"
    else:
        assert [finding.rule for finding in findings] == [expected_rule]
        assert findings[0].severity == "error"


@pytest.mark.parametrize("configured_root", ["/outside/tests", "/opt/specfact/snapshot/../outside"])
def test_native_complete_coverage_rejects_escaping_test_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    configured_root: str,
) -> None:
    capsule, project, temporary = (tmp_path / name for name in ("capsule", "project", "temporary"))
    for root in (capsule, project, temporary):
        root.mkdir()
    source = project / "app.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    config = project / "pytest.ini"
    config.write_text(f"[pytest]\ntestpaths = {configured_root}\n", encoding="utf-8")
    (project / "coveragerc").write_text("[report]\nfail_under = 95\n", encoding="utf-8")
    transport = native_worker.ReplayTransport(
        member="targeted-pytest-coverage",
        tool="pytest",
        replies=[],
        capsule=capsule,
        project=project,
        temporary=temporary,
    )

    def reject_execution(*_args, **_kwargs):
        pytest.fail("Escaping test roots must fail before pytest or coverage execution")

    monkeypatch.setattr(runner, "_evaluate_pytest_execution", reject_execution)
    with pytest.raises(ValueError, match="escapes"):
        native_worker._pytest_external_adapter(
            [source],
            transport.run,
            [
                "-c",
                str(config),
                "--rootdir",
                str(project),
                "--cov-config",
                str(project / "coveragerc"),
                "--",
                "tests/test_app.py::test_app",
            ],
            False,
            True,
        )
