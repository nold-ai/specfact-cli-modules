"""Preserve pinned CrossHair constructor inputs through native CLI dispatch."""

from __future__ import annotations

import inspect
import runpy
import sys
from contextlib import contextmanager
from importlib.metadata import version
from types import FunctionType
from typing import Literal

from crosshair import condition_parser, core, dynamic_typing
from crosshair.util import IgnoreAttempt


def _ordered_signature(*, parameters, return_annotation):
    """Retain argument positions and make impossible optional prefixes required."""
    ordered = sorted(parameters, key=lambda parameter: parameter.kind)
    required_follows = False
    for index in range(len(ordered) - 1, -1, -1):
        parameter = ordered[index]
        if parameter.kind not in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            continue
        if parameter.default is inspect.Parameter.empty:
            required_follows = True
        elif required_follows:
            ordered[index] = parameter.replace(default=inspect.Parameter.empty)
    return inspect.Signature(ordered, return_annotation=return_annotation)


def _ordered_intersection():
    """Clone the pinned helper without changing upstream code or shared globals."""
    original = dynamic_typing.intersect_signatures
    namespace = dict(original.__globals__)
    namespace["Signature"] = _ordered_signature
    return FunctionType(original.__code__, namespace, original.__name__, original.__defaults__, original.__closure__)


def _constructor_member_signature(cls, name):
    """Remove only the receiver actually supplied by type construction."""
    function = getattr(cls, name)
    if function is getattr(object, name):
        return None
    signature = core.resolve_signature(function)
    if not isinstance(signature, inspect.Signature):
        return None
    parameters = list(signature.parameters.values())
    implicit_receiver = name == "__new__" or (
        not inspect.ismethod(function) and not isinstance(inspect.getattr_static(cls, name), staticmethod)
    )
    if (
        implicit_receiver
        and parameters
        and parameters[0].kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ):
        parameters = parameters[1:]
    annotation = object if name == "__init__" else signature.return_annotation
    return signature.replace(parameters=parameters, return_annotation=annotation)


@contextmanager
def _constructor_compatibility():
    """Keep the correction local to one verified analyzer invocation."""
    if version("crosshair-tool") != "0.0.109":
        raise RuntimeError("crosshair_version_unsupported")
    intersection = _ordered_intersection()
    original = core.get_constructor_signature

    def constructor_signature(cls):
        if hasattr(cls, "__signature__"):
            explicit = core.resolve_signature(cls)
            if isinstance(explicit, inspect.Signature):
                return explicit
        signatures = [
            signature
            for name in ("__new__", "__init__")
            if (signature := _constructor_member_signature(cls, name)) is not None
        ]
        if not signatures:
            return inspect.Signature()
        return intersection(*signatures) if len(signatures) == 2 else signatures[0]

    core.get_constructor_signature = constructor_signature
    try:
        yield
    finally:
        core.get_constructor_signature = original


def _registered_lookup(original):
    """Retain upstream lookup for every callable that can be a registry key."""

    def lookup(function):
        return None if type(function).__hash__ is None else original(function)

    return lookup


@contextmanager
def _contract_lookup_compatibility():
    """Keep the impossible-key guard local to the verified pinned invocation."""
    original_core = core.get_contract
    original_parser = condition_parser.get_contract
    core.get_contract = _registered_lookup(original_core)
    condition_parser.get_contract = _registered_lookup(original_parser)
    try:
        yield
    finally:
        core.get_contract = original_core
        condition_parser.get_contract = original_parser


def _literal_value(creator, *values):
    """Explore every declared value without coercing or widening its type."""
    if not values:
        raise IgnoreAttempt("No values for Literal")
    for index, value in enumerate(values[:-1]):
        if creator.space.smt_fork(desc=f"{creator.varname}_literal_{index}"):
            return value
    return values[-1]


@contextmanager
def _literal_compatibility():
    """Register only the missing pinned model after upstream initialization."""
    import importlib

    importlib.import_module("crosshair.core_and_libs")

    registry = vars(core)["_SIMPLE_PROXIES"]
    added = Literal not in registry
    if added:
        core.register_type(Literal, _literal_value)
    try:
        yield
    finally:
        if added and registry.get(Literal) is _literal_value:
            del registry[Literal]


if __name__ == "__main__":
    sys.argv[0] = globals().get("ENTRY_PROGRAM", sys.argv[0])
    with _constructor_compatibility(), _contract_lookup_compatibility(), _literal_compatibility():
        runpy.run_module("crosshair", run_name="__main__", alter_sys=True)
