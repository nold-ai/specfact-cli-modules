from __future__ import annotations

from pathlib import Path

import pytest

from specfact_project.analyzers.code_analyzer import CodeAnalyzer


@pytest.mark.parametrize(
    ("parent", "root", "source_path", "expected_features"),
    [
        ("parent", "project", "src/service.py", 1),
        ("tmpenvabc", "project", "src/service.py", 1),
        ("parent", "builder-project", "src/service.py", 1),
        ("parent", "project", "src/distribution/environment.py", 1),
        ("parent", "project", "src/env/service.py", 0),
        ("parent", "project", "src/build/service.py", 0),
        ("parent", "project", "src/dist/service.py", 0),
        ("parent", "project", "src/tests/service.py", 0),
        ("parent", "project", "src/test_service.py", 0),
    ],
    ids=["ordinary", "ancestor", "root", "source", "env", "build", "dist", "tests", "test-file"],
)
def test_analyzer_matches_excluded_directories_within_repository(
    tmp_path: Path, parent: str, root: str, source_path: str, expected_features: int
) -> None:
    repository = tmp_path / parent / root
    source = repository / source_path
    source.parent.mkdir(parents=True)
    source.write_text(
        '"""Nested package module."""\n\n'
        "class NestedService:\n"
        '    """Service in a nested package."""\n'
        "    def method(self) -> str:\n"
        '        """Return the service value."""\n'
        '        return "nested"\n',
        encoding="utf-8",
    )

    assert len(CodeAnalyzer(repository, confidence_threshold=0.5).analyze().features) == expected_features
