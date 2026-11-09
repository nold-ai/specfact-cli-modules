from pathlib import Path
from typing import Any

import pytest
from specfact_cli.models.plan import Feature

import specfact_project.analyzers.code_analyzer as module
from specfact_project.analyzers.code_analyzer import CodeAnalyzer


class ObservedProgress:
    instances: list["ObservedProgress"] = []

    def __init__(self, *_: Any, **__: Any) -> None:
        self.updates: list[tuple[int, dict[str, Any]]] = []
        self.tasks: list[str] = []
        self.fail_first_completed = False
        self.instances.append(self)

    def __enter__(self) -> "ObservedProgress":
        return self

    def __exit__(self, *_: Any) -> None:
        pass

    def add_task(self, description: str, **_: Any) -> int:
        self.tasks.append(description)
        return len(self.tasks)

    def update(self, task: int, **kwargs: Any) -> None:
        self.updates.append((task, kwargs))
        if self.fail_first_completed and kwargs.get("completed") == 1:
            self.fail_first_completed = False
            raise ValueError("progress")

    def remove_task(self, _: int) -> None:
        pass


@pytest.fixture
def analyzer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CodeAnalyzer:
    monkeypatch.setenv("TEST_MODE", "true")
    ObservedProgress.instances = []
    monkeypatch.setattr(module, "Progress", ObservedProgress)
    result = CodeAnalyzer(tmp_path)
    monkeypatch.setattr(result, "_build_dependency_graph", lambda _: None)
    monkeypatch.setattr(result, "_analyze_commit_history", lambda: None)
    monkeypatch.setattr(result, "_enhance_features_with_dependencies", lambda: None)
    monkeypatch.setattr(result, "_extract_technology_stack_from_dependencies", lambda: ["technology"])
    return result


def result_feature() -> dict[str, Any]:
    return {"features": [Feature.model_validate({"key": "FEATURE-1", "title": "Service"})], "themes": {"Zeta", "Alpha"}}


def completed_updates() -> list[int]:
    return [
        kwargs["completed"]
        for task, kwargs in ObservedProgress.instances[-1].updates
        if task == 3 and "completed" in kwargs
    ]


@pytest.mark.parametrize("failure", ["callback", "progress"])
def test_successful_merge_then_failure_counts_twice_and_retains_features(
    analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    (analyzer.repo_path / "one.py").write_text("pass", encoding="utf-8")
    monkeypatch.setattr(analyzer, "_analyze_file_parallel", lambda _: result_feature())
    callbacks: list[tuple[int, list[str]]] = []

    def callback(count: int, themes: list[str]) -> None:
        callbacks.append((count, themes))
        if failure == "callback":
            raise ValueError("callback")

    analyzer.incremental_callback = callback
    if failure == "progress":
        original = ObservedProgress.__init__

        def initialize(self: ObservedProgress, *args: Any, **kwargs: Any) -> None:
            original(self, *args, **kwargs)
            self.fail_first_completed = True

        monkeypatch.setattr(ObservedProgress, "__init__", initialize)
    bundle = analyzer.analyze()
    assert len(bundle.features) == 1
    assert completed_updates() == [1, 2]
    assert callbacks == ([(1, ["Alpha", "Zeta"])] if failure == "callback" else [])
    bundle = analyzer.analyze()
    assert len(bundle.features) == 2
    assert completed_updates() == [1, 2]


def test_callback_only_on_growth_and_skipped_files_progress(
    analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ["one.py", "empty.py", "skip.py"]:
        (analyzer.repo_path / name).write_text("pass", encoding="utf-8")
    monkeypatch.setattr(analyzer, "_should_skip_file", lambda path: path.name == "skip.py")
    monkeypatch.setattr(
        analyzer, "_analyze_file_parallel", lambda path: result_feature() if path.name == "one.py" else {}
    )
    callbacks: list[int] = []
    analyzer.incremental_callback = lambda count, _: callbacks.append(count)
    bundle = analyzer.analyze()
    assert callbacks == [1]
    assert completed_updates() == [1, 2, 3]
    assert bundle.product is not None and bundle.product.themes == ["Alpha", "Zeta"]
    assert bundle.idea is not None and bundle.idea.constraints == ["technology"]


def test_sequential_keyboard_interrupt_propagates(analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch) -> None:
    (analyzer.repo_path / "one.py").write_text("pass", encoding="utf-8")
    monkeypatch.setattr(analyzer, "_analyze_file_parallel", lambda _: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        analyzer.analyze()
    assert completed_updates() == []


class ObservedFuture:
    def __init__(self, mode: str, trace: list[str]) -> None:
        self.mode = mode
        self.trace = trace

    def result(self) -> dict[str, Any]:
        if self.mode != "normal":
            raise KeyboardInterrupt
        return result_feature()

    def done(self) -> bool:
        self.trace.append("done")
        if self.mode == "done_failure":
            raise ValueError("done")
        return False

    def cancel(self) -> None:
        self.trace.append("cancel")
        if self.mode == "cancel_failure":
            raise ValueError("cancel")


class ObservedExecutor:
    def __init__(self, mode: str, trace: list[str], shutdowns: list[dict[str, bool]], max_workers: int) -> None:
        self.mode = mode
        self.trace = trace
        self.shutdowns = shutdowns
        assert max_workers == 1

    def submit(self, *_: Any) -> ObservedFuture:
        return ObservedFuture(self.mode, self.trace)

    def shutdown(self, **kwargs: bool) -> None:
        self.shutdowns.append(kwargs)
        if self.mode == "shutdown_failure" and kwargs.get("cancel_futures"):
            raise ValueError("shutdown")


@pytest.mark.parametrize(
    ("mode", "error", "expected_shutdowns", "expected_trace"),
    [
        ("normal", None, [{"wait": True}], []),
        (
            "future_interrupt",
            KeyboardInterrupt,
            [{"wait": False, "cancel_futures": True}, {"wait": False}],
            ["done", "cancel"],
        ),
        (
            "iterator_interrupt",
            KeyboardInterrupt,
            [{"wait": False, "cancel_futures": True}, {"wait": False}],
            ["done", "cancel"],
        ),
        ("done_failure", ValueError, [{"wait": False}], ["done"]),
        ("cancel_failure", ValueError, [{"wait": False}], ["done", "cancel"]),
        (
            "shutdown_failure",
            ValueError,
            [{"wait": False, "cancel_futures": True}, {"wait": False}],
            ["done", "cancel"],
        ),
    ],
)
def test_parallel_interrupt_cleanup_traces(
    analyzer: CodeAnalyzer,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    error: type[BaseException] | None,
    expected_shutdowns: list[dict[str, bool]],
    expected_trace: list[str],
) -> None:
    monkeypatch.setenv("TEST_MODE", "false")
    (analyzer.repo_path / "one.py").write_text("pass", encoding="utf-8")
    trace: list[str] = []
    shutdowns: list[dict[str, bool]] = []
    monkeypatch.setattr(
        module, "ThreadPoolExecutor", lambda max_workers: ObservedExecutor(mode, trace, shutdowns, max_workers)
    )

    def completed(futures: Any) -> Any:
        if mode == "iterator_interrupt":
            raise KeyboardInterrupt
        return list(futures)

    monkeypatch.setattr(module, "as_completed", completed)
    if error:
        with pytest.raises(error):
            analyzer.analyze()
    else:
        assert len(analyzer.analyze().features) == 1
    assert shutdowns == expected_shutdowns
    assert trace == expected_trace
