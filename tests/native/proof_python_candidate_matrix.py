from pathlib import Path

import pytest

from tests.unit.test_macos_python_candidate_source import candidate


def test_native_candidate_matrix():
    import os
    import platform
    import tempfile

    selected = os.environ.get("SPECFACT_CPYTHON_CANDIDATE_INPUTS")
    if not selected:
        pytest.skip("maintainer-only native inputs not selected")
    assert platform.system() == "Darwin" and platform.machine() == "arm64"
    module = candidate()
    import json

    inputs = json.loads(selected)
    assert set(inputs) == {"3.11", "3.12", "3.13"}
    for version, runtime in sorted(inputs.items()):
        # Retain private raw diagnostics even after a failed measurement.
        root = Path(tempfile.mkdtemp(prefix="sf-python-pytest-", dir="/private/tmp"))
        with (root / "diagnostics.log").open("w") as stream:
            from contextlib import redirect_stdout

            with redirect_stdout(stream):
                result = module.run(root, Path(runtime), version)
        assert result["candidate_passed"] is True
        assert result["cases"] == result["passed"] == 6
        assert result["production_approved"] is False
        assert result["signed_boundary_verified"] is False
