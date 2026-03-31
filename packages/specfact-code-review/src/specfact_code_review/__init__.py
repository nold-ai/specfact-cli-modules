"""specfact-code-review package entrypoint."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING


__all__ = ("app", "export_from_bundle", "import_to_bundle", "sync_with_bundle", "validate_bundle")

if TYPE_CHECKING:
    from specfact_code_review.review.app import (
        app,
        export_from_bundle,
        import_to_bundle,
        sync_with_bundle,
        validate_bundle,
    )


def __getattr__(name: str) -> object:
    if name not in __all__:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    review_app_module = import_module("specfact_code_review.review.app")
    return getattr(review_app_module, name)
