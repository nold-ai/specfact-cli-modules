"""Preserve pinned CrossHair constructor inputs through native CLI dispatch."""

from __future__ import annotations

import inspect
import runpy
import sys
from contextlib import contextmanager
from importlib.metadata import version
from types import FunctionType

from crosshair import core, dynamic_typing


def _ordered_signature(*, parameters, return_annotation):
    """Keep upstream merge precedence and validate only its final parameter order."""
    return inspect.Signature(
        sorted(parameters, key=lambda parameter: parameter.kind), return_annotation=return_annotation
    )


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


if __name__ == "__main__":
    sys.argv[0] = globals().get("ENTRY_PROGRAM", sys.argv[0])
    with _constructor_compatibility():
        runpy.run_module("crosshair", run_name="__main__", alter_sys=True)
