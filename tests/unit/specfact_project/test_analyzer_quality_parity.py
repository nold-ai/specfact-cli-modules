import ast
import math
from itertools import product
from pathlib import Path
from types import SimpleNamespace

import pytest
from icontract.errors import ViolationError
from specfact_cli.models.plan import Feature, Story

from specfact_project.analyzers.code_analyzer import CodeAnalyzer


@pytest.fixture
def analyzer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CodeAnalyzer:
    monkeypatch.setenv("TEST_MODE", "true")
    return CodeAnalyzer(tmp_path)


@pytest.mark.parametrize(
    "status_case",
    [
        (available, message, *flags)
        for available, message in [(False, None), (False, "native unavailable"), (True, None)]
        for flags in product([False, True], repeat=5)
    ],
)
def test_plugin_status_keeps_records_and_probe_order(
    analyzer: CodeAnalyzer,
    monkeypatch: pytest.MonkeyPatch,
    status_case: tuple[bool, str | None, bool, bool, bool, bool, bool],
) -> None:
    available, message, enabled, configured, quality, pyan3, networkx = status_case
    analyzer.semgrep_enabled = enabled
    analyzer.semgrep_config = analyzer.repo_path / "rules.yml" if configured else None
    analyzer.semgrep_quality_config = analyzer.repo_path / "quality.yml" if quality else None
    calls: list[str] = []

    def native_probe() -> tuple[bool, str | None]:
        calls.append("native")
        return available, message

    monkeypatch.setattr(analyzer, "_probe_semgrep", native_probe)
    monkeypatch.setattr(
        "specfact_cli.utils.optional_deps.check_cli_tool_available",
        lambda name: (calls.append(name) or pyan3, None),
    )
    monkeypatch.setattr(
        "specfact_cli.utils.optional_deps.check_python_package_available",
        lambda name: calls.append(name) or networkx,
    )
    native_reason = (
        message or "Native Semgrep executable osemgrep is not installed"
        if not available
        else "Semgrep config not found"
        if not configured
        else "Pattern detection enabled" + (" (with code quality rules)" if quality else "")
    )
    graph_reasons = {
        (False, False): "pyan3 and networkx not installed (install: pip install pyan3 networkx)",
        (False, True): "pyan3 not installed (install: pip install pyan3)",
        (True, False): "networkx not installed (install: pip install networkx)",
        (True, True): "Dependency graph analysis enabled",
    }

    assert analyzer.get_plugin_status() == [
        {"name": "AST Analysis", "enabled": True, "used": True, "reason": "Core analysis engine"},
        {
            "name": "Semgrep Pattern Detection",
            "enabled": enabled and available,
            "used": enabled and available and configured,
            "reason": native_reason,
        },
        {
            "name": "Dependency Graph Analysis",
            "enabled": pyan3 and networkx,
            "used": pyan3 and networkx,
            "reason": graph_reasons[pyan3, networkx],
        },
    ]
    assert calls == ["native", "pyan3", "networkx"]


def test_plugin_status_rejects_nontext_native_reason(analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(analyzer, "_probe_semgrep", lambda: (False, 37))
    monkeypatch.setattr("specfact_cli.utils.optional_deps.check_cli_tool_available", lambda name: (False, None))
    monkeypatch.setattr("specfact_cli.utils.optional_deps.check_python_package_available", lambda name: False)

    with pytest.raises(ViolationError):
        analyzer.get_plugin_status()


@pytest.mark.parametrize("configuration", list(product([False, True], repeat=6)))
def test_native_initialization_keeps_path_priority_and_probe_short_circuit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configuration: tuple[bool, ...]
) -> None:
    import specfact_project.analyzers.code_analyzer as module

    feature_resource, feature_tools, quality_resource, quality_tools, test_mode, available = configuration
    monkeypatch.setenv("TEST_MODE", "true" if test_mode else "false")
    resources = Path(module.__file__).parent.parent / "resources" / "semgrep"
    tools = tmp_path / "tools" / "semgrep"
    candidates = [
        resources / "feature-detection.yml",
        tools / "feature-detection.yml",
        resources / "code-quality.yml",
        tools / "code-quality.yml",
    ]
    availability = dict(zip(candidates, configuration[:4], strict=True))
    calls: list[Path | str] = []
    original_exists = Path.exists

    def exists(path: Path) -> bool:
        if path in availability:
            calls.append(path)
            return availability[path]
        return original_exists(path)

    def native_available(_self: CodeAnalyzer) -> bool:
        calls.append("native")
        return available

    monkeypatch.setattr(Path, "exists", exists)
    monkeypatch.setattr(CodeAnalyzer, "_check_semgrep_available", native_available)
    instance = CodeAnalyzer(tmp_path)
    feature = candidates[0] if feature_resource else candidates[1] if feature_tools else None
    quality = candidates[2] if quality_resource else candidates[3] if quality_tools else None
    expected: list[Path | str] = [candidates[0]]
    if not feature_resource:
        expected.append(candidates[1])
    expected.append(candidates[2])
    if not quality_resource:
        expected.append(candidates[3])
    if not test_mode and feature is not None:
        expected.append("native")

    assert instance.semgrep_config == feature
    assert instance.semgrep_quality_config == quality
    assert instance.semgrep_enabled is (not test_mode and feature is not None and available)
    assert calls == expected


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        ([], {}),
        (["_hidden", "__init__"], {"Configuration": ["__init__"]}),
        (
            ["get_user", "create_get", "newton", "setup_validate", "_hidden", "__init__"],
            {
                "Read Operations": ["get_user"],
                "Create Operations": ["create_get", "newton"],
                "Update Operations": ["setup_validate"],
                "Configuration": ["__init__"],
            },
        ),
        (
            ["GET_user", "build_compare", "process_get", "check", "parse", "plain", "find_more"],
            {
                "Read Operations": ["GET_user", "process_get", "find_more"],
                "Generation": ["build_compare"],
                "Validation": ["check"],
                "Analysis": ["parse"],
                "Core Functionality": ["plain"],
            },
        ),
        (["foo__init__bar", "__init__helper"], {"Core Functionality": ["foo__init__bar"]}),
    ],
)
def test_method_groups_preserve_match_priority_and_encounter_order(
    analyzer: CodeAnalyzer, names: list[str], expected: dict[str, list[str]]
) -> None:
    tree = ast.parse("\n".join(f"def {name}(): pass" for name in names))
    methods = [node for node in tree.body if isinstance(node, ast.FunctionDef)]

    grouped = analyzer._group_methods_by_functionality(methods)

    assert list(grouped) == list(expected)
    assert {group: [method.name for method in members] for group, members in grouped.items()} == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("pass", set()),
        (
            "import requests_compat, myfastapi.adapter\nfrom vendor.redis_tools import client",
            {"API", "Caching", "HTTP Client"},
        ),
        ("import FASTAPI as api\nfrom . import redis", {"API"}),
        (
            "from pydantic_sqlalchemy import model\nimport aiohttp, asyncio",
            {"Validation", "ORM", "Async HTTP", "Async"},
        ),
    ],
)
def test_import_themes_keep_substring_matching(analyzer: CodeAnalyzer, source: str, expected: set[str]) -> None:
    assert analyzer._extract_themes_from_imports_parallel(ast.parse(source)) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("def outer():\n    async def inner():\n        await work()", ["inner", "outer"]),
        ("async def task(): pass\nasync def task(): pass", ["task", "task"]),
        ("def outer():\n    def middle():\n        await work()\n        await more()", ["outer", "middle"]),
    ],
)
def test_async_detection_keeps_all_enclosing_functions(
    analyzer: CodeAnalyzer, source: str, expected: list[str]
) -> None:
    assert analyzer._detect_async_patterns_parallel(ast.parse(source), analyzer.repo_path / "sample.py") == expected


def test_return_hints_keep_simplification_and_last_duplicate(analyzer: CodeAnalyzer) -> None:
    tree = ast.parse(
        "def plain(): pass\n"
        "def named() -> Item: pass\n"
        "def generic() -> List[str]: pass\n"
        "def qualified() -> package.Type: pass\n"
        "def nested() -> package.List[str]: pass\n"
        "async def named() -> Changed: pass\n"
    )
    assert analyzer._extract_type_hints_parallel(tree, analyzer.repo_path / "sample.py") == {
        "plain": "None",
        "named": "Changed",
        "generic": "List",
        "qualified": "None",
        "nested": "Any",
    }


def test_confidence_threshold_precedes_rounding(analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch) -> None:
    node = ast.parse('class Service:\n    """Documented service."""\n    def get_item(self): pass').body[0]
    assert isinstance(node, ast.ClassDef)
    stories = [
        Story(
            key=f"STORY-{number}",
            title="Read item",
            acceptance=["first", "second"],
            story_points=None,
            value_points=None,
            scenarios=None,
            contracts=None,
        )
        for number in range(3)
    ]
    monkeypatch.setattr(analyzer, "_extract_stories_from_methods", lambda *_: stories)
    assert analyzer._calculate_feature_confidence(node, stories) == 0.9999999999999999
    analyzer.confidence_threshold = 1.0
    assert analyzer._extract_feature_from_class_parallel(node, analyzer.repo_path / "sample.py", 0) is None
    analyzer.confidence_threshold = math.nextafter(1.0, 0.0)
    feature = analyzer._extract_feature_from_class_parallel(node, analyzer.repo_path / "sample.py", 0)
    assert feature is not None
    assert feature.confidence == 1.0


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        ({}, 0.3),
        ({"has_database_models": True}, 0.44999999999999996),
        ({"has_api_endpoints": True, "has_database_models": True, "has_auth_patterns": True}, 0.65),
        ({"has_anti_patterns": True, "has_security_issues": True}, 0.15),
        ({"has_crud_operations": True, "has_framework_patterns": True, "has_test_patterns": True}, 0.55),
    ],
)
def test_confidence_keeps_ordered_evidence_arithmetic(
    analyzer: CodeAnalyzer, evidence: dict[str, bool], expected: float
) -> None:
    node = ast.parse("class Service: pass").body[0]
    assert isinstance(node, ast.ClassDef)
    assert analyzer._calculate_feature_confidence(node, [], evidence) == expected


def test_dependency_graph_keeps_first_known_leaf_and_external_filter(
    analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = analyzer.repo_path / "first" / "item.py"
    second = analyzer.repo_path / "second" / "item.py"
    caller = analyzer.repo_path / "caller.py"
    broken = analyzer.repo_path / "broken.py"
    for path in [first, second, caller, broken]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("pass", encoding="utf-8")
    broken.write_text("invalid (", encoding="utf-8")
    analyzer.entry_point = caller
    monkeypatch.setattr(
        analyzer,
        "_extract_imports_from_ast",
        lambda tree, path: ["item", "second.item", "external", "src.missing"] if path == caller else [],
    )
    analyzer._build_dependency_graph([first, second, caller, broken])
    assert list(analyzer.dependency_graph.nodes) == ["first.item", "second.item", "caller", "broken"]
    assert list(analyzer.dependency_graph.edges) == [("caller", "first.item"), ("caller", "second.item")]
    assert analyzer.external_dependencies == {"external"}


def test_dependency_graph_preserves_io_error_propagation(
    analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = analyzer.repo_path / "caller.py"
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unreadable")))
    with pytest.raises(OSError, match="unreadable"):
        analyzer._build_dependency_graph([path])
    assert list(analyzer.dependency_graph.nodes) == ["caller"]


def test_import_roots_keep_local_resolution_and_moduleless_relative_exclusion(analyzer: CodeAnalyzer) -> None:
    analyzer.dependency_graph.add_node("package.local")
    tree = ast.parse("import external.deep as alias\nfrom package.local import value\nfrom . import ignored\nimport os")
    assert set(analyzer._extract_imports_from_ast(tree, analyzer.repo_path / "package" / "caller.py")) == {
        "external",
        "package",
    }
    assert analyzer._extract_imports_from_ast(
        ast.parse("import local"), analyzer.repo_path / "package" / "caller.py"
    ) == ["package.local"]


def test_dependency_import_exclusions_keep_existing_vocabulary(analyzer: CodeAnalyzer) -> None:
    analyzer.dependency_graph.add_node("package.local")
    tree = ast.parse(
        "import sys, os, json, yaml, pathlib, typing, collections, dataclasses, enum, abc, asyncio\n"
        "import functools, itertools, re, datetime, time, logging, hashlib, base64, urllib, http\n"
        "import socket, threading, multiprocessing, external.deep, local\n"
        "from . import ignored\n"
    )

    assert set(analyzer._extract_imports_from_ast(tree, analyzer.repo_path / "package" / "caller.py")) == {
        "external",
        "package.local",
    }


def test_commit_bounds_keep_bytes_first_match_and_inner_failure(
    analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    import git

    class BrokenCommit:
        @property
        def message(self) -> str:
            raise ValueError("corrupt")

    analyzer.features = [
        Feature.model_validate({"key": "FEATURE-1", "title": "First"}),
        Feature.model_validate({"key": "FEATURE-10", "title": "Second"}),
    ]
    (analyzer.repo_path / ".git").mkdir()
    observed: list[int] = []
    commits = [
        SimpleNamespace(message=b"FEATURE-1\xff", hexsha="12345678abcdef"),
        BrokenCommit(),
        SimpleNamespace(message="feature 1 and feature 10", hexsha="87654321abcdef"),
        SimpleNamespace(message="unrelated", hexsha="abcdefabcdef"),
    ]

    def iter_commits(*, max_count: int) -> list[object]:
        observed.append(max_count)
        return commits

    monkeypatch.setattr(git, "Repo", lambda *_: SimpleNamespace(iter_commits=iter_commits))
    analyzer._analyze_commit_history()
    assert observed == [100]
    assert analyzer.commit_bounds == {"FEATURE-1": ("12345678", "87654321")}


def test_commit_bounds_preserve_outer_failure(analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch) -> None:
    import git

    (analyzer.repo_path / ".git").mkdir()
    analyzer.commit_bounds["existing"] = ("first", "last")
    monkeypatch.setattr(git, "Repo", lambda *_: (_ for _ in ()).throw(ValueError("repository failure")))
    analyzer._analyze_commit_history()
    assert analyzer.commit_bounds == {"existing": ("first", "last")}


@pytest.mark.parametrize(
    ("requirements", "expected"),
    [
        ("fastapi[standard]>=1", ["Python 3.11+", "Typer for CLI", "Pydantic for data validation"]),
        ("python>=3.10,<4\npython==3.12", ["Python 3.10+", "Python 3.12"]),
        ("python>=", ["Python +"]),
        (
            "# comment\n\nfastapi>=1\npytest\ndocker\nfastapi==2",
            ["FastAPI framework", "pytest for testing", "Docker for containerization"],
        ),
        (
            "django\nflask\ntyper\ntornado\nbottle",
            ["Django framework", "Flask framework", "Typer for CLI", "Tornado framework", "Bottle framework"],
        ),
        (
            "psycopg2\npsycopg2-binary\nmysql-connector-python\npymongo\nredis\nsqlalchemy\npydantic",
            [
                "PostgreSQL database",
                "MySQL database",
                "MongoDB database",
                "Redis database",
                "SQLAlchemy ORM",
                "Pydantic for data validation",
            ],
        ),
        (
            "unittest\nnose\ntox\nkubernetes",
            ["unittest for testing", "nose for testing", "tox for testing", "Kubernetes for orchestration"],
        ),
    ],
)
def test_requirement_constraints_keep_version_and_mapping_rules(
    analyzer: CodeAnalyzer, requirements: str, expected: list[str]
) -> None:
    (analyzer.repo_path / "requirements.txt").write_text(requirements, encoding="utf-8")
    assert analyzer._extract_technology_stack_from_dependencies() == expected


def test_project_constraints_differ_from_requirements_and_keep_first_order(
    analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    (analyzer.repo_path / "requirements.txt").write_text("redis\npydantic", encoding="utf-8")
    (analyzer.repo_path / "pyproject.toml").write_text("placeholder", encoding="utf-8")
    data = {
        "project": {
            "requires-python": ">=3.11",
            "dependencies": ["pytest", "docker", "python>=3.12", "fastapi[standard]", "fastapi", "redis", "pydantic"],
        }
    }
    monkeypatch.setitem(sys.modules, "tomli", SimpleNamespace(loads=lambda _: data))
    assert analyzer._extract_technology_stack_from_dependencies() == [
        "Redis database",
        "Pydantic for data validation",
        "Python >=3.11",
        "FastAPI framework",
    ]


def test_primary_project_parse_error_does_not_retry(analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    (analyzer.repo_path / "pyproject.toml").write_text("placeholder", encoding="utf-8")
    monkeypatch.setitem(
        sys.modules, "tomli", SimpleNamespace(loads=lambda _: (_ for _ in ()).throw(ValueError("parse")))
    )
    monkeypatch.setitem(sys.modules, "tomllib", SimpleNamespace(load=lambda _: pytest.fail("unexpected fallback")))
    assert analyzer._extract_technology_stack_from_dependencies() == [
        "Python 3.11+",
        "Typer for CLI",
        "Pydantic for data validation",
    ]


def test_primary_project_partial_constraints_survive(analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    (analyzer.repo_path / "pyproject.toml").write_text("placeholder", encoding="utf-8")
    monkeypatch.setitem(
        sys.modules,
        "tomli",
        SimpleNamespace(loads=lambda _: {"project": {"requires-python": ">=3.11", "dependencies": 1}}),
    )
    assert analyzer._extract_technology_stack_from_dependencies() == ["Python >=3.11"]


@pytest.mark.parametrize("missing_fallback", [False, True])
def test_project_import_fallback(
    analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch, missing_fallback: bool
) -> None:
    import sys

    (analyzer.repo_path / "pyproject.toml").write_text("placeholder", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "tomli", None)
    monkeypatch.setitem(
        sys.modules,
        "tomllib",
        None
        if missing_fallback
        else SimpleNamespace(load=lambda _: {"project": {"requires-python": ">=3.13", "dependencies": ["flask"]}}),
    )
    expected = (
        ["Python 3.11+", "Typer for CLI", "Pydantic for data validation"]
        if missing_fallback
        else ["Python >=3.13", "Flask framework"]
    )
    assert analyzer._extract_technology_stack_from_dependencies() == expected


def test_fallback_project_parse_error_propagates(analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    (analyzer.repo_path / "pyproject.toml").write_text("placeholder", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "tomli", None)
    monkeypatch.setitem(
        sys.modules, "tomllib", SimpleNamespace(load=lambda _: (_ for _ in ()).throw(ValueError("parse")))
    )
    with pytest.raises(ValueError, match="parse"):
        analyzer._extract_technology_stack_from_dependencies()


@pytest.mark.parametrize(
    ("source", "patterns", "expected"),
    [
        (
            'def first():\n    """First description."""\ndef second():\n    """Second description."""',
            [],
            ["infer first", "First description.", "infer second", "Second description."],
        ),
        (
            'def first():\n    """Repeated."""\ndef second():\n    """Repeated."""',
            ["one", "two", "three", "four"],
            ["one", "two", "three", "Repeated."],
        ),
        (
            'def first():\n    """Given input, When run, Then accepted."""\ndef second():\n    """Given input, When run, Then accepted."""',
            ["tested"],
            ["tested", "accepted", "accepted"],
        ),
        ('def first():\n    """Given input When run Then accepted"""', ["tested"], ["tested"]),
        (
            'def first():\n    """given input, when run, then accepted."""',
            ["tested"],
            ["tested", "given input, when run, then accepted."],
        ),
        ("def first(): pass", [], ["Read Operations functionality works correctly"]),
    ],
)
def test_story_acceptance_keeps_interleaving_and_docstring_rules(
    analyzer: CodeAnalyzer,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    patterns: list[str],
    expected: list[str],
) -> None:
    methods = [node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)]
    monkeypatch.setattr(analyzer.test_extractor, "extract_test_patterns_for_class", lambda *_, **__: patterns)
    monkeypatch.setattr(
        analyzer.test_extractor,
        "infer_from_code_patterns",
        lambda method, _: [] if source == "def first(): pass" else [f"infer {method.name}"],
    )
    observed: list[str] = []
    monkeypatch.setattr(
        analyzer.control_flow_analyzer,
        "extract_scenarios_from_method",
        lambda method, *_: observed.append(f"scenario {method.name}") or {"primary": ["scenario"]},
    )
    monkeypatch.setattr(
        analyzer.contract_extractor,
        "extract_function_contracts",
        lambda method: observed.append(f"contract {method.name}") or {"return_type": "Any"},
    )
    story = analyzer._create_story_from_method_group("Read Operations", methods, "Service", 7)
    assert story is not None
    assert story.key == "STORY-SERVICE-007"
    assert story.acceptance == expected
    assert story.tasks == [f"{method.name}()" for method in methods]
    assert story.scenarios == {"primary": ["scenario"]}
    assert story.contracts == {"return_type": "Any"}
    assert observed == ["scenario first", "contract first"]


@pytest.mark.parametrize("failure", ["scenario", "contract"])
def test_story_extraction_failure_propagates_in_order(
    analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    methods = [node for node in ast.parse("def first(): pass").body if isinstance(node, ast.FunctionDef)]
    monkeypatch.setattr(analyzer.test_extractor, "extract_test_patterns_for_class", lambda *_, **__: ["tested"])
    observed: list[str] = []

    def extract(kind: str) -> None:
        observed.append(kind)
        if kind == failure:
            raise ValueError(kind)

    monkeypatch.setattr(analyzer.control_flow_analyzer, "extract_scenarios_from_method", lambda *_: extract("scenario"))
    monkeypatch.setattr(analyzer.contract_extractor, "extract_function_contracts", lambda *_: extract("contract"))
    with pytest.raises(ValueError, match=failure):
        analyzer._create_story_from_method_group("Read Operations", methods, "Service", 7)
    assert observed == (["scenario"] if failure == "scenario" else ["scenario", "contract"])


def test_empty_story_group_returns_before_extractors(analyzer: CodeAnalyzer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        analyzer.test_extractor,
        "extract_test_patterns_for_class",
        lambda *_, **__: pytest.fail("unexpected extraction"),
    )
    assert analyzer._create_story_from_method_group("Read Operations", [], "Service", 7) is None
