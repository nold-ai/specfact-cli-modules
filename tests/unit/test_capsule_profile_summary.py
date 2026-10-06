import json
from pathlib import Path

import pytest

from scripts.capsule_profile_summary import summarize


@pytest.fixture
def profiling_subject(tmp_path):
    subject = tmp_path / "subject"
    subject.mkdir()
    subprocess_file = subject / "public.py"
    subprocess_file.write_text("def slow_operation():\n    pass\n")
    profile = tmp_path / "profile.json"
    data = {
        "shared": {
            "frames": [
                {"file": "/private/customer/public.py", "name": "slow_operation", "line": 1},
                {"file": "/private/customer/public.py", "name": "private-secret", "line": 1},
                {"file": "/private/customer/untracked.py", "name": "hidden", "line": 1},
            ]
        },
        "profiles": [{"type": "sampled", "samples": [[0, 0, 1], [0, 2]]}],
    }
    profile.write_text(json.dumps(data))
    return subject, profile, data


def test_profile_projects_only_static_tracked_symbols(monkeypatch, profiling_subject):
    subject, profile, _data = profiling_subject
    monkeypatch.setattr("scripts.capsule_profile_summary.tracked_python", lambda _root: [Path("public.py")])
    result = summarize(profile, subject)
    assert result == {
        "status": "DIAGNOSTIC_ONLY",
        "samples": 2,
        "public_frames": [{"file": "public.py", "function": "slow_operation", "inclusive_samples": 2}],
    }
    assert "private" not in json.dumps(result)


@pytest.mark.parametrize("sample", [[True], [-1], [3], ["0"], "0"])
def test_profile_rejects_invalid_frame_indexes(monkeypatch, profiling_subject, sample):
    subject, profile, data = profiling_subject
    monkeypatch.setattr("scripts.capsule_profile_summary.tracked_python", lambda _root: [Path("public.py")])
    data["profiles"][0]["samples"] = [sample]
    profile.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="sample"):
        summarize(profile, subject)


def test_profile_does_not_guess_ambiguous_public_suffix(monkeypatch, profiling_subject):
    subject, profile, _data = profiling_subject
    for name in ("one/public.py", "two/public.py"):
        path = subject / name
        path.parent.mkdir()
        path.write_text("def slow_operation():\n    pass\n")
    monkeypatch.setattr(
        "scripts.capsule_profile_summary.tracked_python", lambda _root: [Path("one/public.py"), Path("two/public.py")]
    )
    assert summarize(profile, subject)["public_frames"] == []


def test_profile_rejects_oversized_input(monkeypatch, profiling_subject):
    subject, profile, _data = profiling_subject
    monkeypatch.setattr("scripts.capsule_profile_summary.MAXIMUM_BYTES", 1)
    with pytest.raises(ValueError, match="size"):
        summarize(profile, subject)


def test_profile_rejects_tracked_symlinks(monkeypatch, profiling_subject):
    subject, profile, _data = profiling_subject
    (subject / "linked.py").symlink_to(subject / "public.py")
    monkeypatch.setattr("scripts.capsule_profile_summary.tracked_python", lambda _root: [Path("linked.py")])
    with pytest.raises(ValueError, match="tracked source"):
        summarize(profile, subject)


@pytest.fixture
def review_workflow():
    import yaml

    root = Path(__file__).resolve().parents[2]
    return yaml.safe_load((root / ".github/workflows/capsule-customer-execution.yml").read_text())


@pytest.fixture
def diagnostic_step(review_workflow):
    return next(
        step
        for step in review_workflow["jobs"]["customer"]["steps"]
        if step.get("name") == "Profile failed candidate review privately"
    )


def test_profile_preserves_failed_required_review(review_workflow, diagnostic_step):
    review = next(step for step in review_workflow["jobs"]["customer"]["steps"] if step.get("id") == "deferred_review")
    assert not review.get("continue-on-error", False)
    assert 'exit "$review_exit"' in review["run"]
    assert diagnostic_step["if"] == "failure() && steps.deferred_review.outcome == 'failure'"


@pytest.mark.parametrize(
    "required",
    [
        "unset GITHUB_TOKEN GH_TOKEN PYTHONPATH",
        "--require-hashes",
        "py-spy==0.4.2",
        "--no-deps",
        "timeout --signal=INT --kill-after=5s 280s",
        "--rate 10 --idle --subprocesses --format speedscope",
        'SPECFACT_CODE_REVIEW_SUBJECT_ROOT="$REVIEW_ROOT"',
        'SPECFACT_CODE_REVIEW_PROJECT_CONFIG="$PROJECT_CONFIG"',
        "SPECFACT_CODE_REVIEW_ENFORCEMENT=changed",
        '"$GITHUB_WORKSPACE/scripts/pre_commit_code_review.py" "${review_paths[@]}"',
        "DIAGNOSTIC_UNAVAILABLE",
    ],
)
def test_profile_replay_preserves_subject_and_bounds(diagnostic_step, required):
    assert required in diagnostic_step["run"]


def test_profile_keeps_privileges_artifacts_and_independent_reviewer(review_workflow, diagnostic_step):
    assert "sudo" not in diagnostic_step["run"]
    assert "--locals" not in diagnostic_step["run"]
    uploads = [
        step for step in review_workflow["jobs"]["customer"]["steps"] if "upload-artifact@" in step.get("uses", "")
    ]
    assert all("profile" not in step["with"]["path"] for step in uploads)
    independent = json.dumps(review_workflow["jobs"]["independent-review"])
    assert "capsule_profile_summary" not in independent and "py-spy" not in independent


def test_profile_cli_does_not_print_rejected_private_input(monkeypatch, capsys, profiling_subject):
    from scripts.capsule_profile_summary import main

    subject, profile, _data = profiling_subject
    profile.write_text('{"shared": ["private-secret"]}')
    monkeypatch.setattr("sys.argv", ["summary", "--profile", str(profile), "--repository", str(subject)])
    assert main() == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == {"status": "DIAGNOSTIC_UNAVAILABLE"}
    assert output.err == ""
