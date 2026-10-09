"""Run Pylint with verified runtime roots as defaults beneath native configuration."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from pylint.checkers import symilar
from pylint.lint import PyLinter, Run


SNAPSHOT_ROOT = Path(globals().get("SNAPSHOT_ROOT", "/opt/specfact/snapshot"))


@contextmanager
def _bounded_similarity_hashes():
    """Reuse pinned immutable LineSet windows only within this Pylint invocation."""
    original = symilar.hash_lineset
    cached = lru_cache(maxsize=256)(original)
    symilar.hash_lineset = cached
    try:
        yield cached
    finally:
        symilar.hash_lineset = original
        cached.cache_clear()


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
    with _bounded_similarity_hashes():
        _RuntimeRun(sys.argv[1:])
