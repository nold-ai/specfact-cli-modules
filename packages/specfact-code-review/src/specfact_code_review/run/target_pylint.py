"""Run Pylint with verified runtime roots as defaults beneath native configuration."""

from __future__ import annotations

import sys
from pathlib import Path

from pylint.lint import PyLinter, Run


SNAPSHOT_ROOT = Path(globals().get("SNAPSHOT_ROOT", "/opt/specfact/snapshot"))


def _runtime_source_roots() -> list[str]:
    """Use only attached snapshot imports, including validated editable .pth roots."""
    snapshot = SNAPSHOT_ROOT.resolve()
    roots = {Path(path).resolve() for path in sys.path if path}
    attached = [root for root in roots if root.is_relative_to(snapshot) and root.is_dir()]
    # Pylint selects the first matching ancestor; prefer the specific import root.
    return [str(root) for root in sorted(attached, key=lambda root: (-len(root.parts), str(root)))]


def _runtime_linter(*args, **kwargs) -> PyLinter:
    """Set defaults before Run applies native config selection and CLI overrides."""
    linter = PyLinter(*args, **kwargs)
    linter.set_option("source-roots", _runtime_source_roots())
    return linter


class _RuntimeRun(Run):
    """Keep the native runner and ordinary picklable PyLinter instance."""

    LinterClass = staticmethod(_runtime_linter)


if __name__ == "__main__":
    _RuntimeRun(sys.argv[1:])
