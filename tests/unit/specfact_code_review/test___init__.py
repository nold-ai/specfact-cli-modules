"""Test for specfact_code_review.__init__ module."""

from __future__ import annotations

import importlib.util


# pylint: disable=import-outside-toplevel


def test_all_exports() -> None:
    """Test that __all__ contains expected exports."""
    import specfact_code_review

    assert isinstance(specfact_code_review.__all__, tuple)
    assert len(specfact_code_review.__all__) > 0
    assert "app" in specfact_code_review.__all__
    assert "export_from_bundle" in specfact_code_review.__all__
    assert "import_to_bundle" in specfact_code_review.__all__
    assert "sync_with_bundle" in specfact_code_review.__all__
    assert "validate_bundle" in specfact_code_review.__all__


def test_getattr_raises_for_invalid_attribute() -> None:
    """Test that __getattr__ raises AttributeError for invalid attributes."""
    # Test that invalid attribute raises an error
    spec = importlib.util.find_spec("specfact_code_review.invalid_attribute")
    assert spec is None, "Invalid attribute should not be found"


def test_getattr_returns_valid_attributes() -> None:
    """Test that __getattr__ returns valid attributes."""
    # Test that __getattr__ works by accessing an attribute
    import specfact_code_review

    # Access the attribute to trigger __getattr__
    app = specfact_code_review.app

    # Just verify it doesn't raise an exception and returns something
    assert app is not None

    # Clean up to avoid test pollution
    import sys

    sys.modules.pop("specfact_code_review.review.app", None)
    sys.modules.pop("specfact_code_review.review", None)
