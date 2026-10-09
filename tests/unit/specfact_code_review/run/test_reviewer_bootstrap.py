"""Prove explicit selection and bounded upstream Pylint result parity."""

from pathlib import Path

import pytest
from pylint.checkers import symilar

from specfact_code_review.run import target_pylint
from specfact_code_review.run.portable_worker import select_test_paths
from specfact_code_review.run.runtime_models import ProjectPlan


@pytest.mark.parametrize("reverse", [False, True])
def test_explicit_correspondence_resolves_only_matching_tests(tmp_path, reverse):
    source = tmp_path / "src/commands.py"
    first = tmp_path / "tests/first/test_commands.py"
    second = tmp_path / "tests/second/test_commands.py"
    unrelated = tmp_path / "tests/test_other.py"
    for path in (source, first, second, unrelated):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pass\n")
    plan = ProjectPlan(tmp_path, manager="hatch", pytest_config={"testpaths": ["tests"], "python_files": ["test_*.py"]})
    files = [source, second]
    assert select_test_paths(plan, list(reversed(files)) if reverse else files, full=False) == (
        "tests/second/test_commands.py",
    )
    assert select_test_paths(plan, [source, first, second], full=False) == (
        "tests/first/test_commands.py",
        "tests/second/test_commands.py",
    )
    for selected in ([source], [source, unrelated]):
        with pytest.raises(ValueError, match="project_test_selection_ambiguous"):
            select_test_paths(plan, selected, full=False)


def _similarity_engine(minimum, ignored, disabled):
    engine = symilar.Symilar(minimum)
    body = [
        "def shared():\n",
        "    alpha = 1\n",
        "    beta = 2\n",
        "    gamma = 3\n",
        "    delta = 4\n",
        "    epsilon = 5\n",
        "    return alpha + beta + gamma + delta + epsilon\n",
    ]
    for number in range(4):
        raw = ["import os\n", "# fixture comment\n", *body, f"unique_{number} = {number}\n"]
        engine.linesets.append(
            symilar.LineSet(
                str(number),
                raw,
                ignore_comments=ignored,
                ignore_imports=ignored,
                ignore_signatures=ignored,
                line_enabled_callback=lambda _message, line: not disabled or line != 4,
            )
        )
    return engine


@pytest.mark.parametrize("minimum", [3, 4, 6])
@pytest.mark.parametrize("ignored", [False, True])
@pytest.mark.parametrize("disabled", [False, True])
def test_cached_windows_preserve_same_object_groups_and_locations(minimum, ignored, disabled, monkeypatch):
    engine = _similarity_engine(minimum, ignored, disabled)
    expected = engine._compute_sims()
    expected_order = list(engine._iter_sims())
    original = symilar.hash_lineset
    calls = []

    def counted(lineset, min_common_lines=4):
        calls.append((id(lineset), min_common_lines))
        return original(lineset, min_common_lines)

    monkeypatch.setattr(symilar, "hash_lineset", counted)
    with target_pylint._bounded_similarity_hashes() as cached:
        assert engine._compute_sims() == expected
        assert list(engine._iter_sims()) == expected_order
        assert len(calls) == len(engine.linesets)
        assert cached.cache_info().hits > 0
    assert symilar.hash_lineset is counted
    assert cached.cache_info().currsize == 0


def _window_signature(windows):
    hashes, limits = windows
    return (
        [(hash(chunk), chunk._fileid, chunk._index, indices) for chunk, indices in hashes.items()],
        {index: (limit.start, limit.end) for index, limit in limits.items()},
    )


def test_cache_distinguishes_minima_and_evicts_without_changing_windows():
    original = symilar.hash_lineset
    linesets = [symilar.LineSet(str(index), [f"value_{line} = {line}\n" for line in range(8)]) for index in range(257)]
    with target_pylint._bounded_similarity_hashes() as cached:
        for lineset in linesets:
            assert _window_signature(cached(lineset, 3)) == _window_signature(original(lineset, 3))
        assert cached.cache_info().currsize == 256
        assert _window_signature(cached(linesets[0], 3)) == _window_signature(original(linesets[0], 3))
        assert _window_signature(cached(linesets[0], 6)) == _window_signature(original(linesets[0], 6))
    assert symilar.hash_lineset is original
    assert cached.cache_info().currsize == 0


@pytest.mark.parametrize("error", [RuntimeError, SystemExit])
def test_cache_restores_upstream_function_after_exception(error):
    original = symilar.hash_lineset
    with pytest.raises(error), target_pylint._bounded_similarity_hashes() as cached:
        cached(symilar.LineSet("fixture", ["a\n", "b\n", "c\n", "d\n"]), 3)
        raise error("fixture failure")
    assert symilar.hash_lineset is original
    assert cached.cache_info().currsize == 0


def test_runtime_wrapper_preserves_messages_statistics_and_exit_status(tmp_path, monkeypatch):
    from pylint.reporters import CollectingReporter

    paths = []
    for number in range(4):
        path = tmp_path / f"fixture_{number}.py"
        path.write_text(
            "def shared():\n" + "".join(f"    value_{line} = {line}\n" for line in range(12)) + "    return value_0\n"
        )
        paths.append(str(path))
    monkeypatch.chdir(tmp_path)
    arguments = ["--persistent=no", "--reports=no", "--score=no", "--min-similarity-lines=4", *paths]
    expected_reporter = CollectingReporter()
    expected = target_pylint._RuntimeRun(arguments, reporter=expected_reporter, exit=False)
    reporter = CollectingReporter()
    with target_pylint._bounded_similarity_hashes():
        actual = target_pylint._RuntimeRun(arguments, reporter=reporter, exit=False)
    assert any(message.symbol == "duplicate-code" for message in expected_reporter.messages)
    assert reporter.messages == expected_reporter.messages
    assert vars(actual.linter.stats) == vars(expected.linter.stats)
    assert actual.linter.msg_status == expected.linter.msg_status


@pytest.mark.parametrize("extra_args", [[], ["-k", "test_target_crosshair"]])
@pytest.mark.parametrize("codes,expected,calls", [([9], 9, 1), ([0, 7], 7, 2), ([0, 0], 0, 2)])
def test_smart_entry_preserves_required_host_and_portable_failures(codes, expected, calls, extra_args, monkeypatch):
    import importlib.util
    from types import SimpleNamespace

    root = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(root / "tools"))
    spec = importlib.util.spec_from_file_location("bootstrap_smart", root / "tools/smart_test_coverage.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    invoked = []
    results = iter(codes)

    def run(command, **_options):
        invoked.append(command)
        return SimpleNamespace(returncode=next(results))

    monkeypatch.setattr(module.subprocess, "run", run)
    assert module._run_pytest(extra_args) == expected
    assert len(invoked) == calls
    assert "tests/host/proof_capsule_deferred_review_ci.py" in invoked[0]
    assert invoked[0][-1] == "tests/host/proof_capsule_deferred_review_ci.py"
    if calls == 2:
        if extra_args:
            assert invoked[1][-len(extra_args) :] == extra_args
        assert "--ignore=tests/unit/test_capsule_deferred_review_ci.py" in invoked[1]
