"""Constructor compatibility keeps actual arguments and native CLI lifetime."""

import importlib.metadata
import inspect
import io as stdio
import json as json_codec
import os
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from typing import Literal

import pytest
from crosshair import condition_parser, core, dynamic_typing
from crosshair.libimpl.builtinslib import SymbolicArrayBasedUniformTuple
from crosshair.options import AnalysisOptionSet
from crosshair.register_contract import REGISTERED_CONTRACTS, ContractOverride
from icontract import ensure

from specfact_code_review.run import target_bootstrap, target_crosshair
from specfact_code_review.run.target_crosshair import _diagnostic_channel_compatibility, _TargetOutput
from specfact_code_review.tools.basedpyright_runner import run_basedpyright


_stream_sink = vars(target_crosshair)["_TargetOutput"]


class NamedConstructor:
    def __new__(cls, value: int = 3):
        return object.__new__(cls)

    def __init__(self, value: int = 3):
        self.value = value


class InheritedConstructor(NamedConstructor):
    pass


class VariadicConstructor:
    def __new__(cls, *items: int, flag: bool = False, **kwargs: str):
        return object.__new__(cls)

    def __init__(self, *items: int, flag: bool = False, **kwargs: str):
        self.items = items


class CollisionConstructor:
    def __new__(cls, *items, **kwargs):
        return object.__new__(cls)

    def __init__(self, items: int = 0, *other, **kwargs):
        self.items = items


class StaticInitialization:
    @staticmethod
    def __init__(value: int = 3):
        return None


class BoundInitialization:
    @classmethod
    def __init__(cls, value: int = 3):
        return None


class BoundAllocation:
    @classmethod
    def __new__(cls, supplied_class, value: int = 3):
        return object.__new__(supplied_class)


class PositionalConstructor:
    def __new__(cls, value: int = 3, /):
        return object.__new__(cls)

    def __init__(self, value: int = 3, /):
        self.value = value


class DefaultPrefixConstructor:
    def __new__(cls, first: int = 1, /, *items: int):
        return object.__new__(cls)

    def __init__(self, first: int, second: int, /):
        self.first, self.second = first, second


class DefaultPrefixWithOptionalConstructor:
    def __new__(cls, first: int = 1, /, *items: int):
        return object.__new__(cls)

    def __init__(self, first: int, second: int, /, third: int = 3):
        self.first, self.second, self.third = first, second, third


class ExplicitConstructor:
    __signature__ = inspect.Signature([inspect.Parameter("chosen", inspect.Parameter.KEYWORD_ONLY, annotation=int)])


@pytest.fixture(name="crosshair_dispatch")
def crosshair_dispatch_fixture(monkeypatch):
    monkeypatch.setattr(target_bootstrap, "_configure_runtime", lambda module: None)
    monkeypatch.setattr(target_bootstrap, "BUILTIN", Path(target_bootstrap.__file__).parents[2])
    original_version = importlib.metadata.version
    monkeypatch.setattr(
        importlib.metadata, "version", lambda name: "0.0.109" if name == "crosshair-tool" else original_version(name)
    )

    def dispatch(callback):
        monkeypatch.setattr(target_bootstrap.runpy, "run_module", callback)
        monkeypatch.setattr(
            sys, "argv", ["target_bootstrap", "crosshair", "check", "--per_path_timeout=10", "target.py"]
        )
        target_bootstrap.main()

    return dispatch


def _parameter(
    name: str, kind, annotation: object = inspect.Parameter.empty, default: object = inspect.Parameter.empty
) -> inspect.Parameter:
    return inspect.Parameter(name, kind, annotation=annotation, default=default)


_VALUE_KEYWORD = _parameter("value", inspect.Parameter.KEYWORD_ONLY, int, 3)
_VALUE_POSITIONAL = _parameter("value", inspect.Parameter.POSITIONAL_OR_KEYWORD, int, 3)


@pytest.mark.parametrize(
    "constructor,expected_parameters",
    [
        (NamedConstructor, [_VALUE_KEYWORD]),
        (InheritedConstructor, [_VALUE_KEYWORD]),
        (
            VariadicConstructor,
            [
                _parameter("items", inspect.Parameter.VAR_POSITIONAL, int),
                _parameter("flag", inspect.Parameter.KEYWORD_ONLY, bool, False),
                _parameter("kwargs", inspect.Parameter.VAR_KEYWORD, str),
            ],
        ),
        (
            CollisionConstructor,
            [
                _parameter("items", inspect.Parameter.VAR_POSITIONAL),
                _parameter("kwargs", inspect.Parameter.VAR_KEYWORD),
            ],
        ),
        (StaticInitialization, [_VALUE_POSITIONAL]),
        (BoundInitialization, [_VALUE_POSITIONAL]),
        (BoundAllocation, [_VALUE_POSITIONAL]),
        (PositionalConstructor, [_parameter("value", inspect.Parameter.POSITIONAL_ONLY, int, 3)]),
        (ExplicitConstructor, [_parameter("chosen", inspect.Parameter.KEYWORD_ONLY, int)]),
        (object, []),
    ],
)
def test_dispatch_preserves_constructor_arguments(crosshair_dispatch, constructor, expected_parameters):
    def inspect_dispatch(module, **options):
        assert module == "crosshair" and options == {"run_name": "__main__", "alter_sys": True}
        assert sys.argv[1:] == ["check", "--per_path_timeout=10", "target.py"]
        signature = core.get_constructor_signature(constructor)
        assert isinstance(signature, inspect.Signature)
        assert list(signature.parameters.values()) == expected_parameters

    crosshair_dispatch(inspect_dispatch)


@pytest.mark.parametrize("failure", [None, RuntimeError, SystemExit])
def test_dispatch_restores_upstream_resolver_on_every_exit(crosshair_dispatch, failure):
    original = core.get_constructor_signature
    intersection = dynamic_typing.intersect_signatures
    signature_factory = intersection.__globals__["Signature"]
    observed = []

    def inspect_dispatch(module, **options):
        observed.append(core.get_constructor_signature is not original)
        assert dynamic_typing.intersect_signatures is intersection
        assert intersection.__globals__["Signature"] is signature_factory
        if failure:
            raise failure(7)

    if failure:
        with pytest.raises(failure):
            crosshair_dispatch(inspect_dispatch)
    else:
        crosshair_dispatch(inspect_dispatch)
    assert observed == [True]
    assert core.get_constructor_signature is original


def test_dispatch_rejects_unverified_dependency_version(crosshair_dispatch, monkeypatch):
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "0.0.999")
    called = []
    with pytest.raises(RuntimeError, match="crosshair_version_unsupported"):
        crosshair_dispatch(lambda *args, **kwargs: called.append(True))
    assert called == []


class MarkedContract:
    pytestmark = pytest.mark.usefixtures("fixture_name")

    @ensure(lambda result: isinstance(result, int))
    def value(self) -> int:
        return 3


def test_dispatch_parses_marked_class_without_dropping_real_contract(crosshair_dispatch):
    def inspect_dispatch(*_args, **_kwargs):
        parser = condition_parser.CompositeConditionParser()
        parser.parsers = [
            condition_parser.IcontractParser(parser),
            condition_parser.RegisteredContractsParser(parser),
        ]
        parsed = parser.get_class_conditions(MarkedContract)
        assert parsed.methods["value"].post
        assert parsed.methods["value"].sig.return_annotation is int
        assert "pytestmark" not in parsed.methods

    crosshair_dispatch(inspect_dispatch)


@pytest.mark.parametrize("lookup_module", [core, condition_parser])
def test_dispatch_unhashable_lookup_has_no_registered_override(crosshair_dispatch, lookup_module):
    marker = MarkedContract.pytestmark
    assert callable(marker) and type(marker).__hash__ is None

    def inspect_dispatch(*_args, **_kwargs):
        assert lookup_module.get_contract(marker) is None

    crosshair_dispatch(inspect_dispatch)


@pytest.mark.parametrize("failure", [None, RuntimeError, SystemExit])
def test_dispatch_restores_registered_lookup_on_every_exit(crosshair_dispatch, failure):
    original_core = vars(core)["get_contract"]
    original_parser = vars(condition_parser)["get_contract"]
    observed = []

    def inspect_dispatch(*_args, **_kwargs):
        observed.append(
            (
                vars(core)["get_contract"] is not original_core,
                vars(condition_parser)["get_contract"] is not original_parser,
            )
        )
        if failure:
            raise failure(7)

    if failure:
        with pytest.raises(failure):
            crosshair_dispatch(inspect_dispatch)
    else:
        crosshair_dispatch(inspect_dispatch)
    assert observed == [(True, True)]
    assert vars(core)["get_contract"] is original_core and vars(condition_parser)["get_contract"] is original_parser


def test_dispatch_hashable_registry_override_is_preserved(crosshair_dispatch, monkeypatch):
    def registered(value: int) -> int:
        return value

    contract = ContractOverride(pre=None, post=None, sigs=[inspect.signature(registered)], skip_body=False)
    monkeypatch.setitem(REGISTERED_CONTRACTS, registered, contract)

    def inspect_dispatch(*_args, **_kwargs):
        assert vars(core)["get_contract"](registered) is contract
        assert vars(condition_parser)["get_contract"](registered) is contract

    crosshair_dispatch(inspect_dispatch)


def test_dispatch_custom_hash_error_is_preserved(crosshair_dispatch):
    class FailingHash:
        def __call__(self):
            return None

        def __eq__(self, other):
            return self is other

        def __hash__(self):
            raise TypeError("custom_hash_failure")

    def inspect_dispatch(*_args, **_kwargs):
        for lookup in (vars(core)["get_contract"], vars(condition_parser)["get_contract"]):
            with pytest.raises(TypeError, match="custom_hash_failure"):
                lookup(FailingHash())

    crosshair_dispatch(inspect_dispatch)


@pytest.mark.parametrize("failure", [None, RuntimeError, SystemExit])
def test_literal_registration_is_scoped_to_native_dispatch(crosshair_dispatch, monkeypatch, failure):
    import importlib

    importlib.import_module("crosshair.core_and_libs")

    registry = vars(core)["_SIMPLE_PROXIES"]
    monkeypatch.delitem(registry, Literal, raising=False)
    original_integer = registry[int]
    observed = []

    def inspect_dispatch(*_args, **_kwargs):
        observed.append(Literal in registry)
        assert registry[int] is original_integer
        if failure:
            raise failure(7)

    if failure:
        with pytest.raises(failure):
            crosshair_dispatch(inspect_dispatch)
    else:
        crosshair_dispatch(inspect_dispatch)
    assert observed == [True]
    assert Literal not in registry and registry[int] is original_integer


def test_existing_literal_registration_is_preserved(crosshair_dispatch, monkeypatch):
    import importlib

    importlib.import_module("crosshair.core_and_libs")

    registry = vars(core)["_SIMPLE_PROXIES"]

    def original(*_args):
        return "existing_model"

    monkeypatch.setitem(registry, Literal, original)

    def inspect_dispatch(*_args, **_kwargs):
        assert registry[Literal] is original

    crosshair_dispatch(inspect_dispatch)
    assert registry[Literal] is original


def test_empty_literal_is_an_impossible_attempt(crosshair_dispatch):
    from crosshair.core_and_libs import standalone_statespace
    from crosshair.util import IgnoreAttempt

    def inspect_dispatch(*_args, **_kwargs):
        with standalone_statespace, pytest.raises(IgnoreAttempt):
            core.proxy_for_type(Literal[()], "empty")

    crosshair_dispatch(inspect_dispatch)


def test_nested_literal_scope_preserves_the_outer_registration(crosshair_dispatch):
    from specfact_code_review.run.target_crosshair import _literal_compatibility

    registry = vars(core)["_SIMPLE_PROXIES"]

    def inspect_dispatch(*_args, **_kwargs):
        outer = registry[Literal]
        with _literal_compatibility():
            assert registry[Literal] is outer
        assert registry[Literal] is outer

    crosshair_dispatch(inspect_dispatch)


def test_cached_argument_proxy_reads_scoped_literal_registration(crosshair_dispatch, monkeypatch):
    from crosshair.core_and_libs import NoTracing, standalone_statespace
    from crosshair.util import renamed_function

    cached = renamed_function(core.proxy_for_type, "proxy_arg_review_mode")
    monkeypatch.setitem(vars(core)["_ARG_GENERATION_RENAMES"], "review_mode", cached)
    signature = inspect.Signature([_parameter("review_mode", inspect.Parameter.POSITIONAL_OR_KEYWORD, Literal["full"])])

    def inspect_dispatch(*_args, **_kwargs):
        with standalone_statespace, NoTracing():
            arguments = core.gen_args(signature)
            assert arguments.arguments["review_mode"] == "full"
        assert vars(core)["_ARG_GENERATION_RENAMES"]["review_mode"] is cached

    crosshair_dispatch(inspect_dispatch)


@pytest.mark.parametrize("constructor", [DefaultPrefixConstructor, DefaultPrefixWithOptionalConstructor])
def test_constructor_required_prefix_keeps_real_positional_values(crosshair_dispatch, constructor):
    def inspect_dispatch(*_args, **_kwargs):
        signature = core.get_constructor_signature(constructor)
        assert isinstance(signature, inspect.Signature)
        parameters = signature.parameters
        assert list(parameters)[:2] == ["first", "second"]
        assert parameters["first"].default is inspect.Parameter.empty
        assert parameters["second"].default is inspect.Parameter.empty
        assert parameters["first"].annotation is int and parameters["second"].annotation is int
        with pytest.raises(TypeError):
            signature.bind(11)
        constructed = constructor(*signature.bind(11, 22).args, **signature.bind(11, 22).kwargs)
        assert constructed.first == 11 and constructed.second == 22
        if constructor is DefaultPrefixWithOptionalConstructor:
            assert parameters["third"].default == 3 and constructed.third == 3

    crosshair_dispatch(inspect_dispatch)


def test_dispatch_fixture_retains_later_project_contract_enforcement():
    import shlex
    import tomllib

    root = Path(__file__).parents[4]
    configured = shlex.split(
        tomllib.loads((root / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]["addopts"]
    )
    serial = []
    options = iter(configured)
    for option in options:
        if option == "-n":
            next(options)
        elif not option.startswith("--max-worker-restart="):
            serial.append(option)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            (
                "tests/unit/specfact_code_review/run/test_crosshair_dispatch.py::"
                "test_production_dispatch_preserves_attachment_argv_and_exit_without_sampling"
            ),
            (
                "tests/unit/specfact_code_review/run/test_target_crosshair.py::"
                "test_dispatch_preserves_constructor_arguments"
            ),
            "tests/unit/sync_runtime/test_bridge_probe.py::TestBridgeProbe::test_auto_generate_bridge_unknown",
            "-o",
            "addopts=" + shlex.join(serial),
            "-q",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("phase", ["import", "call"])
@pytest.mark.parametrize("violated", [False, True])
def test_pinned_dispatch_separates_target_output_from_real_diagnostics(tmp_path: Path, phase: str, violated: bool):
    """Target prints cannot forge evidence; actual contract failures still report."""
    source = tmp_path / "target_output.py"
    noise = "print('TARGET_OUTPUT_MARKER'); print('TARGET_ERROR_MARKER', file=sys.stderr)"
    imported = noise if phase == "import" else ""
    called = "    " + noise if phase == "call" else ""
    source.write_text(
        "import sys\nfrom icontract import ensure\n"
        + imported
        + "\n@ensure(lambda value, result: result == value)\ndef observed(value: int) -> int:\n"
        + called
        + "\n    return "
        + ("0" if violated else "value")
        + "\n"
    )
    dispatch = (
        Path(__file__).parents[4] / "packages/specfact-code-review/src/specfact_code_review/run/target_crosshair.py"
    )
    result = subprocess.run(
        [sys.executable, str(dispatch), "check", str(source), "--per_condition_timeout=3"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == int(violated), result.stdout + result.stderr
    assert "TARGET_OUTPUT_MARKER" not in result.stdout
    assert "TARGET_ERROR_MARKER" not in result.stderr
    if violated:
        assert str(source) in result.stdout and ": error:" in result.stdout
        assert "false when calling" in result.stdout


def test_pinned_dispatch_rejects_target_output_over_existing_bound(tmp_path: Path):
    source = tmp_path / "excess_output.py"
    source.write_text(
        "from icontract import ensure\nprint('x' * (4 * 1024 * 1024 + 1))\n"
        "@ensure(lambda result: result == 1)\ndef observed() -> int:\n    return 1\n"
    )
    dispatch = (
        Path(__file__).parents[4] / "packages/specfact-code-review/src/specfact_code_review/run/target_crosshair.py"
    )
    result = subprocess.run(
        [sys.executable, str(dispatch), "check", str(source), "--per_condition_timeout=3"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0, "Oversized analyzed output was admitted"
    assert "crosshair_target_output_limit_exceeded" in result.stderr


@pytest.mark.parametrize("length", [0, 2])
def test_pinned_dispatch_preserves_actual_symbolic_tuple_truth(crosshair_dispatch, length: int):
    from crosshair.core_and_libs import NoTracing, standalone_statespace

    def inspect_dispatch(*_args, **_kwargs):
        with standalone_statespace as space, NoTracing():
            sequence = SymbolicArrayBasedUniformTuple("tuple_truth", tuple[str, ...])
            space.add(sequence._len() == length)
            observed = bool(sequence)
            assert type(observed) is bool and observed == (length != 0)
            assert space.is_possible(sequence._len() == length)

    crosshair_dispatch(inspect_dispatch)


@pytest.mark.parametrize("implementation", ["1 if values else 0", "0", "1"])
def test_pinned_dispatch_keeps_empty_and_nonempty_contract_paths(tmp_path: Path, implementation: str):
    source = tmp_path / "sequence_truth.py"
    source.write_text(
        "from icontract import ensure\n"
        "@ensure(lambda values, result: result == (1 if values else 0))\n"
        "def observed(values: tuple[str, ...]) -> int:\n    return " + implementation + "\n"
    )
    dispatch = (
        Path(__file__).parents[4] / "packages/specfact-code-review/src/specfact_code_review/run/target_crosshair.py"
    )
    result = subprocess.run(
        [sys.executable, str(dispatch), "check", str(source), "--per_condition_timeout=3"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == int(implementation != "1 if values else 0"), result.stdout + result.stderr
    assert "TypeError" not in result.stdout + result.stderr
    if implementation in {"0", "1"}:
        assert "false when calling" in result.stdout


@pytest.mark.parametrize("failure", [None, RuntimeError, SystemExit])
def test_diagnostic_scope_retains_reporter_streams_exit_and_restoration(monkeypatch, failure):
    from crosshair import main

    reporter_stdout, reporter_stderr = stdio.StringIO(), stdio.StringIO()
    initial_stdout, initial_stderr = sys.stdout, sys.stderr
    arguments, options = Namespace(target=["fixture.py"]), AnalysisOptionSet()

    def original(actual_arguments, actual_options, stdout, stderr):
        assert actual_arguments is arguments and actual_options is options
        assert stdout is reporter_stdout and stderr is reporter_stderr
        print("target output")
        print("target error", file=sys.stderr)
        print("real diagnostic", file=stdout)
        print("real analyzer error", file=stderr)
        if failure:
            raise failure(7)
        return 7

    monkeypatch.setattr(main, "check", original)
    if failure:
        with pytest.raises(failure), _diagnostic_channel_compatibility():
            main.check(arguments, options, reporter_stdout, reporter_stderr)
    else:
        with _diagnostic_channel_compatibility():
            assert main.check(arguments, options, reporter_stdout, reporter_stderr) == 7
    assert main.check is original and sys.stdout is initial_stdout and sys.stderr is initial_stderr
    assert reporter_stdout.getvalue() == "real diagnostic\n"
    assert reporter_stderr.getvalue() == "real analyzer error\n"


def test_target_output_bound_counts_utf8_bytes_without_retaining_text():
    sink = _TargetOutput()
    assert sink.write("é" * (2 * 1024 * 1024)) == 2 * 1024 * 1024
    with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
        sink.write("x")
    with pytest.raises(UnicodeEncodeError):
        _TargetOutput().write("\ud800")
    assert not hasattr(sink, "getvalue")


@pytest.mark.parametrize("channel", ["stdout", "stderr"])
def test_pinned_dispatch_reports_real_write_after_target_stream_close(tmp_path: Path, channel: str):
    source = tmp_path / "closed_stream.py"
    source.write_text(
        "import sys\nfrom icontract import ensure\n"
        "@ensure(lambda result: result == 1)\ndef observed() -> int:\n"
        f"    sys.{channel}.close()\n    print('after close', file=sys.{channel})\n    return 1\n"
    )
    dispatch = (
        Path(__file__).parents[4] / "packages/specfact-code-review/src/specfact_code_review/run/target_crosshair.py"
    )
    result = subprocess.run(
        [sys.executable, str(dispatch), "check", str(source), "--per_condition_timeout=3"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 1, "Closed target stream falsely accepted writes: " + result.stdout + result.stderr
    assert str(source) in result.stdout and ": error:" in result.stdout
    assert "ValueError" in result.stdout and "closed" in result.stdout.lower()


@pytest.mark.parametrize("channel", ["stdout", "stderr"])
@pytest.mark.parametrize("value", ["b'bytes'", "1", "True", "None"])
def test_pinned_dispatch_preserves_standard_nontext_write_rejection(tmp_path: Path, channel: str, value: str):
    source = tmp_path / "nontext_stream.py"
    source.write_text(
        "import sys\nfrom icontract import ensure\n"
        "@ensure(lambda result: result == 1)\ndef observed() -> int:\n"
        f"    try:\n        sys.{channel}.write({value})\n    except TypeError:\n        return 1\n    return 0\n"
        "if __name__ == '__main__':\n    assert observed() == 1\n"
    )
    baseline = subprocess.run([sys.executable, str(source)], capture_output=True, text=True, timeout=30, check=False)
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    dispatch = (
        Path(__file__).parents[4] / "packages/specfact-code-review/src/specfact_code_review/run/target_crosshair.py"
    )
    result = subprocess.run(
        [sys.executable, str(dispatch), "check", str(source), "--per_condition_timeout=3"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "AttributeError" not in result.stdout + result.stderr


@pytest.mark.parametrize("channel", ["stdout", "stderr"])
@pytest.mark.parametrize("operation", ["metadata", "reconfigure", "bytes", "bytearray", "memoryview"])
def test_real_standard_stream_protocol_remains_valid_under_pinned_dispatch(
    tmp_path: Path, channel: str, operation: str
):
    profile = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json,sys; s=sys."
            + channel
            + "; print(json.dumps([s.encoding,s.errors,s.line_buffering,s.write_through,"
            "s.name,s.mode,s.buffer.name,s.buffer.mode,s.isatty()]))",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    properties = json_codec.loads(profile.stdout)
    operations = {
        "metadata": "    return int((s.encoding,s.errors,s.line_buffering,s.write_through,"
        "s.name,s.mode,s.buffer.name,s.buffer.mode,s.isatty()) == " + repr(tuple(properties)) + ")\n",
        "reconfigure": "    s.reconfigure(encoding='latin-1',errors='replace',"
        "line_buffering=False,write_through=True)\n"
        "    s.write('é'); s.flush()\n"
        "    return int(s.encoding == 'latin-1' and s.errors == 'replace' "
        "and s.write_through and not s.line_buffering)\n",
        "bytes": "    s.buffer.write(b'TARGET_BINARY_MARKER'); s.buffer.flush(); return 1\n",
        "bytearray": "    s.buffer.write(bytearray(b'TARGET_BINARY_MARKER')); s.buffer.flush(); return 1\n",
        "memoryview": "    s.buffer.write(memoryview(b'TARGET_BINARY_MARKER')); s.buffer.flush(); return 1\n",
    }
    source = tmp_path / "standard_protocol.py"
    source.write_text(
        "import sys\nfrom icontract import ensure\n"
        "@ensure(lambda result: result == 1)\ndef observed() -> int:\n"
        + "    s=sys."
        + channel
        + "\n"
        + operations[operation]
        + "if __name__ == '__main__': assert observed() == 1\n",
        encoding="utf-8",
    )
    baseline = subprocess.run([sys.executable, str(source)], capture_output=True, timeout=30, check=False)
    assert baseline.returncode == 0, baseline.stderr.decode("utf-8", errors="replace")
    dispatch = (
        Path(__file__).parents[4] / "packages/specfact-code-review/src/specfact_code_review/run/target_crosshair.py"
    )
    actual = subprocess.run(
        [sys.executable, str(dispatch), "check", str(source), "--per_condition_timeout=3"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert actual.returncode == 0, actual.stdout + actual.stderr
    assert "TARGET_BINARY_MARKER" not in actual.stdout + actual.stderr
    assert "AttributeError" not in actual.stdout + actual.stderr


@pytest.mark.parametrize(
    "codec,errors", [("utf-8", "surrogateescape"), ("ascii", "backslashreplace"), ("latin-1", "replace")]
)
@pytest.mark.parametrize("line_buffering,write_through", [(False, True), (True, False)])
def test_discard_native_standard_properties_and_reconfiguration_preserve_reporter(
    codec, errors, line_buffering, write_through
):
    with stdio.TextIOWrapper(
        stdio.BytesIO(), encoding=codec, errors=errors, line_buffering=line_buffering, write_through=write_through
    ) as reporter:
        original = reporter.encoding, reporter.errors, reporter.line_buffering, reporter.write_through
        with _stream_sink(reporter) as sink:
            assert (sink.encoding, sink.errors, sink.line_buffering, sink.write_through) == original
            assert sink.isatty() == reporter.isatty() and sink.writable()
            sink.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=False, write_through=True)
            assert (sink.encoding, sink.errors, sink.line_buffering, sink.write_through) == (
                "utf-8",
                "backslashreplace",
                False,
                True,
            )
            assert sink.write("é\ud800") == 2
            assert sink.buffer.write(b"PRIVATE_BINARY") == 14
            assert sink.buffer.raw.write(b"PRIVATE_RAW") == 11
            assert (
                not hasattr(sink, "getvalue")
                and not hasattr(sink.buffer, "getvalue")
                and not hasattr(sink.buffer.raw, "getvalue")
            )
        assert not reporter.closed and reporter.buffer.getvalue() == b""
        assert (reporter.encoding, reporter.errors, reporter.line_buffering, reporter.write_through) == original


@pytest.mark.parametrize("surface", ["buffer", "raw"])
def test_discard_binary_surface_preserves_exact_physical_bound(surface):
    with _stream_sink() as sink:
        writer = sink.buffer if surface == "buffer" else sink.buffer.raw
        assert writer.write(b"x" * (4 * 1024 * 1024)) == 4 * 1024 * 1024
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            writer.write(b"x")


@pytest.mark.parametrize("final_surface", ["text", "buffer", "raw"])
def test_discard_mixed_writes_share_exact_physical_bound_after_reconfiguration(final_surface):
    with _stream_sink() as sink:
        sink.reconfigure(encoding="utf-8", errors="strict")
        assert sink.write("é" * (1024 * 1024)) == 1024 * 1024
        assert sink.buffer.write(b"x" * (2 * 1024 * 1024)) == 2 * 1024 * 1024
        writer = {"text": sink, "buffer": sink.buffer, "raw": sink.buffer.raw}[final_surface]
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            writer.write("x" if final_surface == "text" else b"x")


def test_discard_reconfigured_encoding_retains_exact_physical_bound():
    with _stream_sink() as sink:
        sink.reconfigure(encoding="utf-16", errors="strict")
        baseline = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys;sys.stdout.reconfigure(encoding='utf-16',errors='strict');sys.stdout.write('x')",
            ],
            capture_output=True,
            timeout=10,
            check=True,
        )
        assert len(baseline.stdout) == 2, "Native pipe reconfiguration must supply the actual byte count"
        characters = (4 * 1024 * 1024) // len(baseline.stdout)
        assert sink.write("x" * characters) == characters
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            sink.buffer.write(b"x")


@pytest.mark.parametrize("surface", ["text", "buffer", "raw"])
def test_discard_surface_close_rejects_real_writes_without_closing_reporter(surface):
    with stdio.TextIOWrapper(stdio.BytesIO(), encoding="utf-8") as reporter:
        sink = _stream_sink(reporter)
        writer = {"text": sink, "buffer": sink.buffer, "raw": sink.buffer.raw}[surface]
        writer.close()
        with pytest.raises(ValueError, match="closed"):
            writer.write("x" if surface == "text" else b"x")
        assert not reporter.closed and reporter.buffer.getvalue() == b""
        sink.close()


@pytest.mark.parametrize("value", ["text", True, 1, None])
@pytest.mark.parametrize("surface", ["buffer", "raw"])
def test_discard_binary_surface_retains_standard_type_rejection(value, surface):
    with stdio.BytesIO() as baseline, pytest.raises(TypeError):
        baseline.write(value)
    with _stream_sink() as sink:
        writer = sink.buffer if surface == "buffer" else sink.buffer.raw
        with pytest.raises(TypeError):
            writer.write(value)


def test_discard_raw_surface_rejects_noncontiguous_buffer_like_native_io():
    view = memoryview(b"abcd")[::2]
    with stdio.BytesIO() as baseline, pytest.raises(BufferError):
        baseline.write(view)
    with _stream_sink() as sink, pytest.raises(BufferError):
        sink.buffer.raw.write(view)


@pytest.mark.parametrize("surface", ["text", "buffer", "raw"])
def test_discard_writelines_retains_shared_quota(surface):
    with _stream_sink() as sink:
        writer = {"text": sink, "buffer": sink.buffer, "raw": sink.buffer.raw}[surface]
        unit = "x" if surface == "text" else b"x"
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            writer.writelines([unit * (4 * 1024 * 1024), unit])


@pytest.mark.parametrize("violated", [False, True])
def test_native_discard_preserves_real_symbolic_text_contract_paths(tmp_path: Path, violated: bool):
    source = tmp_path / "symbolic_output.py"
    source.write_text(
        "import sys\nfrom icontract import require,ensure\n"
        "@require(lambda value: value.isascii() and len(value) < 10)\n"
        "@ensure(lambda value,result: result == value)\n"
        "def observed(value: str) -> str:\n    sys.stdout.write(value)\n    return "
        + ("'wrong'" if violated else "value")
        + "\n",
        encoding="utf-8",
    )
    dispatch = (
        Path(__file__).parents[4] / "packages/specfact-code-review/src/specfact_code_review/run/target_crosshair.py"
    )
    result = subprocess.run(
        [sys.executable, str(dispatch), "check", str(source), "--per_condition_timeout=3"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == int(violated), result.stdout + result.stderr
    assert "TypeError" not in result.stdout + result.stderr
    if violated:
        assert "false when calling" in result.stdout


@pytest.mark.parametrize("chunks", [("xx",), ("x", "x")])
def test_discard_codec_transition_at_exact_original_text_bound_has_no_false_rejection(chunks):
    with _stream_sink() as sink:
        sink.reconfigure(encoding="latin-1", errors="strict")
        assert sink.write("é" * (2 * 1024 * 1024 - 1)) == 2 * 1024 * 1024 - 1
        sink.reconfigure(encoding="utf-16", errors="strict")
        for chunk in chunks:
            assert sink.write(chunk) == len(chunk)
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            sink.write("x")


@pytest.mark.parametrize("surface", ["text", "buffer", "raw"])
def test_discard_physical_quota_rejection_stays_terminal_even_for_empty_write(surface):
    with _stream_sink() as sink:
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            sink.buffer.raw.write(b"x" * (4 * 1024 * 1024 + 1))
        writer = {"text": sink, "buffer": sink.buffer, "raw": sink.buffer.raw}[surface]
        with pytest.raises(ValueError, match="crosshair_target_output_limit_exceeded"):
            writer.write("" if surface == "text" else b"")


@pytest.mark.parametrize("channel", ["stdout", "stderr"])
@pytest.mark.parametrize("surface", ["text", "binary", "raw"])
def test_target_descriptor_access_cannot_write_original_reporter(tmp_path, monkeypatch, channel, surface):
    reporter_path = tmp_path / (channel + ".txt")
    crosshair_cli = importlib.import_module("crosshair.main")

    def target(arguments, options, stdout, stderr):
        assert arguments is None and options is None
        assert stdout is reporter and stderr is reporter
        stream = getattr(sys, channel)
        layers = {"text": stream, "binary": stream.buffer, "raw": stream.buffer.raw}
        return os.write(layers[surface].fileno(), b"TARGET_REPORTER_DESCRIPTOR_ESCAPE")

    monkeypatch.setattr(crosshair_cli, "check", target)
    with reporter_path.open("w+", encoding="utf-8") as reporter:
        monkeypatch.setattr(sys, channel, reporter)
        with vars(target_crosshair)["_diagnostic_channel_compatibility"](), pytest.raises(stdio.UnsupportedOperation):
            crosshair_cli.check(None, None, reporter, reporter)
        assert getattr(sys, channel) is reporter and not reporter.closed
        reporter.flush()
        assert reporter_path.read_bytes() == b""


def test_complete_crosshair_adapter_has_no_public_type_findings():
    source = (
        Path(__file__).parents[4] / "packages/specfact-code-review/src/specfact_code_review/run/target_crosshair.py"
    )
    findings = run_basedpyright([source])
    assert not findings, [(finding.rule, finding.line, finding.message) for finding in findings]
