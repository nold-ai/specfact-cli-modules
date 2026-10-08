"""Constructor compatibility keeps actual arguments and native CLI lifetime."""

import importlib.metadata
import inspect
import sys
from pathlib import Path

import pytest
from crosshair import condition_parser, core, dynamic_typing
from crosshair.register_contract import REGISTERED_CONTRACTS, ContractOverride
from icontract import ensure

from specfact_code_review.run import target_bootstrap


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

        def __hash__(self):
            raise TypeError("custom_hash_failure")

    def inspect_dispatch(*_args, **_kwargs):
        for lookup in (vars(core)["get_contract"], vars(condition_parser)["get_contract"]):
            with pytest.raises(TypeError, match="custom_hash_failure"):
                lookup(FailingHash())

    crosshair_dispatch(inspect_dispatch)
