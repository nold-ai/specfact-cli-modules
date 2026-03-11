"""specfact-code-review package entrypoint."""

from __future__ import annotations


__all__ = ("app", "export_from_bundle", "import_to_bundle", "sync_with_bundle", "validate_bundle")


def __getattr__(name: str) -> object:
    if name not in __all__:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    from specfact_code_review.review import app as review_app_module

    return getattr(review_app_module, name)
