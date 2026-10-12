"""Preserve pinned CrossHair constructor inputs through native CLI dispatch."""

from __future__ import annotations

import inspect
import io
import runpy
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from importlib.metadata import version
from types import FunctionType
from typing import Literal, cast

from crosshair import condition_parser, core, dynamic_typing
from crosshair.util import IgnoreAttempt
from icontract import ensure


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


@contextmanager
def _sequence_truth_compatibility():
    """Preserve the pinned length predicate while returning a Python Boolean."""
    from crosshair.libimpl.builtinslib import SymbolicArrayBasedUniformTuple
    from crosshair.tracers import NoTracing

    original = SymbolicArrayBasedUniformTuple.__bool__

    def sequence_truth(sequence):
        with NoTracing():
            return bool(original(sequence))

    SymbolicArrayBasedUniformTuple.__bool__ = sequence_truth
    try:
        yield
    finally:
        SymbolicArrayBasedUniformTuple.__bool__ = original


class _TargetRaw(io.RawIOBase):
    """Discard bytes while retaining the unchanged shared stream budgets."""

    def __init__(self, source: io.TextIOBase | None):
        self._source = source
        self.name = getattr(source, "name", None)
        self.mode = getattr(getattr(source, "buffer", None), "mode", "wb")
        self._written = 0

    def _require_open(self) -> None:
        self._checkClosed()

    @ensure(lambda result: result is None)
    def verify_output_bound(self) -> None:
        """Reject physical output beyond the unchanged per-stream limit.

        :raises ValueError: discarded physical output exceeded its bound.
        """
        if self._written > 4 * 1024 * 1024:
            raise ValueError("crosshair_target_output_limit_exceeded")

    @ensure(lambda result: result is True)
    def writable(self) -> bool:
        """Retain the write-only native standard-stream interface.

        :raises ValueError: the private stream is closed.
        """
        self._require_open()
        return True

    @ensure(lambda result: isinstance(result, bool))
    def isatty(self) -> bool:
        """Retain the original standard-stream terminal metadata.

        :raises ValueError: the private or captured stream is closed.
        :raises OSError: original terminal metadata cannot be queried.
        """
        self._require_open()
        return False if self._source is None else self._source.isatty()

    @ensure(lambda result: isinstance(result, int) and not isinstance(result, bool))
    def fileno(self) -> int:
        """Retain supported descriptor metadata without owning the descriptor.

        :raises ValueError: the private or captured stream is closed.
        :raises OSError: the captured stream has no supported descriptor.
        """
        self._require_open()
        return super().fileno() if self._source is None else self._source.fileno()

    @ensure(lambda data, result: result == memoryview(data).nbytes)
    def write(self, data) -> int:
        """Accept standard contiguous bytes-like input without collecting it.

        :raises ValueError: the stream is closed or its shared budget is exceeded.
        :raises TypeError: input has no byte-buffer protocol.
        :raises BufferError: input is not C-contiguous.
        """
        self._require_open()
        view = memoryview(data)
        if not view.c_contiguous:
            raise BufferError("memoryview: underlying buffer is not C-contiguous")
        self._written += view.nbytes
        self.verify_output_bound()
        return view.nbytes


class _TargetBinary(io.BufferedWriter):
    """Preserve the native binary interface while draining each accepted write."""

    @ensure(lambda data, result: result == memoryview(data).nbytes)
    def write(self, data) -> int:
        """Use the native readonly raw binding and reject overflow synchronously.

        :raises ValueError: the stream is closed, detached or exceeds its bound.
        :raises TypeError: input has no byte-buffer protocol.
        :raises BufferError: input is not C-contiguous.
        """
        return cast(_TargetRaw, self.raw).write(data)


class _TargetOutput(io.TextIOWrapper):
    """Retain native codec/reconfiguration behavior without collecting output."""

    def __init__(self, source: io.TextIOBase | None = None):
        self._utf8_written = 0
        self.mode = getattr(source, "mode", "w")
        super().__init__(
            _TargetBinary(_TargetRaw(source)),
            encoding=getattr(source, "encoding", None) or "utf-8",
            errors=getattr(source, "errors", None) or "strict",
            line_buffering=getattr(source, "line_buffering", False),
            write_through=getattr(source, "write_through", False),
        )

    @ensure(lambda text, result: result == len(text))
    def write(self, text: str) -> int:
        """Retain standard text errors and both unchanged shared byte budgets.

        :raises ValueError: the stream is closed or output exceeds its bound.
        :raises TypeError: target writes a non-text value.
        :raises UnicodeEncodeError: text violates the active encoding/error policy.
        """
        errors = self.errors
        result = super().write(text)
        self.flush()
        cast(_TargetRaw, cast(_TargetBinary, self.buffer).raw).verify_output_bound()
        self._utf8_written += len(text.encode("utf-8", errors))
        if self._utf8_written > 4 * 1024 * 1024:
            raise ValueError("crosshair_target_output_limit_exceeded")
        return result


@contextmanager
def _diagnostic_channel_compatibility():
    """Keep reporter arguments intact while isolating analyzed code output."""
    from crosshair import main

    original = main.check

    def check(arguments, options, stdout, stderr):
        with redirect_stdout(_TargetOutput(sys.stdout)), redirect_stderr(_TargetOutput(sys.stderr)):
            return original(arguments, options, stdout, stderr)

    main.check = check
    try:
        yield
    finally:
        main.check = original


if __name__ == "__main__":
    sys.argv[0] = globals().get("ENTRY_PROGRAM", sys.argv[0])
    with (
        _constructor_compatibility(),
        _contract_lookup_compatibility(),
        _literal_compatibility(),
        _sequence_truth_compatibility(),
        _diagnostic_channel_compatibility(),
    ):
        runpy.run_module("crosshair", run_name="__main__", alter_sys=True)
