"""Require reviewed indexed orchestration bytes before local review deferral.

Any byte change requires a reviewed pin update, including comments. This local
eligibility check does not replace mandatory hosted exact-head review.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys


_REVIEWED_ORCHESTRATOR_SHA256 = "827e26667ef9951783bfeaffebca5833e1e16a90151676b164b88d303f7ac371"


def validate_schedule(source: bytes) -> None:
    """Reject every indexed workflow outside the reviewed byte contract."""
    if hashlib.sha256(source).hexdigest() != _REVIEWED_ORCHESTRATOR_SHA256:
        raise ValueError("indexed orchestrator bytes differ from the reviewed SHA-256 pin")


def main() -> int:
    """Read the Git index so an unstaged restoration cannot authorize deferral."""
    try:
        source = subprocess.check_output(
            ["git", "show", ":.github/workflows/pr-orchestrator.yml"], stderr=subprocess.PIPE
        )
        validate_schedule(source)
    except (subprocess.CalledProcessError, ValueError) as error:
        sys.stderr.write(
            f"Capsule review deferral requires supported indexed orchestration: {error}. "
            "Restore the staged workflow or review an explicit pin update; "
            "otherwise run local review without deferral.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
