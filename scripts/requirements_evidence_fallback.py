"""Write workflow-level Requirements evidence when adapter setup is unavailable."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path


VALID_STAGES = frozenset({"adapter-unavailable", "setup-unavailable"})


def _write_temporary_text(destination: Path, contents: str) -> Path:
    """Write text beside its destination without exposing a partial final artifact."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(contents)
        return Path(temporary.name)


def _existing_text(path: Path) -> str | None:
    """Return current text when an artifact already exists."""
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _restore_artifact(path: Path, previous_contents: str | None) -> None:
    """Restore a prior artifact using the same atomic replacement primitive."""
    if previous_contents is None:
        path.unlink(missing_ok=True)
        return
    temporary_path = _write_temporary_text(path, previous_contents)
    try:
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _publish_artifact_pair(
    output_temporary_path: Path, output_path: Path, summary_temporary_path: Path, summary_path: Path
) -> None:
    """Publish the paired artifacts and roll back any completed replacement on failure."""
    previous_output = _existing_text(output_path)
    previous_summary = _existing_text(summary_path)
    summary_published = False
    output_published = False
    try:
        summary_temporary_path.replace(summary_path)
        summary_published = True
        output_temporary_path.replace(output_path)
        output_published = True
    except OSError:
        if output_published:
            _restore_artifact(output_path, previous_output)
        if summary_published:
            _restore_artifact(summary_path, previous_summary)
        raise


def _failure_report_contents(stage: str) -> tuple[str, str]:
    """Return the deterministic machine and human evidence for one failed stage."""
    report = {
        "schema_version": "1",
        "verdict": "failed",
        "execution_proof": "not-included",
        "sources": [
            {
                "source": "<workflow>",
                "verdict": "failed",
                "reasons": [stage],
                "import": {"diagnostics": [], "imported": 0},
                "validation": None,
                "coverage": None,
                "gate_finding_counts": {},
            }
        ],
        "summary": {"failed_sources": 1, "passed_sources": 0, "skipped_sources": 0, "total_sources": 1},
    }
    summary = (
        "## Requirements evidence\n\n"
        "- Verdict: **failed**\n"
        f"- Failure stage: `{stage}`\n"
        "- Test-execution proof: not included.\n"
    )
    return json.dumps(report, indent=2) + "\n", summary


def _write_failure_report(output_path: Path, summary_path: Path, *, stage: str) -> None:
    """Persist deterministic failed evidence without importing optional modules."""
    if stage not in VALID_STAGES:
        msg = f"unsupported evidence failure stage: {stage}"
        raise ValueError(msg)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    report_contents, summary_contents = _failure_report_contents(stage)
    output_temporary_path = _write_temporary_text(output_path, report_contents)
    try:
        summary_temporary_path = _write_temporary_text(summary_path, summary_contents)
    except OSError:
        output_temporary_path.unlink(missing_ok=True)
        raise
    try:
        _publish_artifact_pair(output_temporary_path, output_path, summary_temporary_path, summary_path)
    finally:
        output_temporary_path.unlink(missing_ok=True)
        summary_temporary_path.unlink(missing_ok=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--stage", choices=sorted(VALID_STAGES), required=True)
    return parser.parse_args()


def _main() -> int:
    arguments = _parse_args()
    _write_failure_report(arguments.output, arguments.summary, stage=arguments.stage)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
