from __future__ import annotations

import importlib
import sys
from pathlib import Path


def test_runtime_submodule_import_does_not_require_cli_runtime() -> None:
    review_root = Path(__file__).resolve().parents[2] / "packages" / "specfact-code-review" / "src"
    sys.path.insert(0, str(review_root))
    try:
        package = importlib.import_module("specfact_code_review")

        assert package.__all__ == (
            "app",
            "export_from_bundle",
            "import_to_bundle",
            "sync_with_bundle",
            "validate_bundle",
        )
        assert "specfact_code_review.review.app" not in sys.modules

        findings = importlib.import_module("specfact_code_review.run.findings")

        assert findings.__name__ == "specfact_code_review.run.findings"
    finally:
        sys.modules.pop("specfact_code_review", None)
        sys.modules.pop("specfact_code_review.run", None)
        sys.modules.pop("specfact_code_review.run.findings", None)
        sys.path.remove(str(review_root))
