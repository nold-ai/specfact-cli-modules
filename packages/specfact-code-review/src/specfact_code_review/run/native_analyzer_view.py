"""Fresh controller-owned analyzer views for Python and file-based lookup."""

from __future__ import annotations

import csv
import os
import stat
from importlib.metadata import distributions
from pathlib import Path, PurePosixPath
from typing import Any

from beartype import beartype
from icontract import require
from packaging.utils import canonicalize_name


VIEW_NAME = ".specfact-native-analyzers"
MAX_FILES = 30_000
MAX_BYTES = 512 << 20
_Z3_ALIAS = "z3/lib/libz3.5.1.dylib"
_Z3_LIBRARY = "z3/lib/libz3.dylib"


def _intentionally_omitted(relative: PurePosixPath) -> bool:
    """Match only copy_site's reviewed omissions from its retained RECORD."""
    name = relative.as_posix()
    return (
        name.endswith((".pyc", ".pyo", ".dll", ".exe"))
        or name == _Z3_ALIAS
        or (
            name.startswith("semgrep/bin/")
            and name != "semgrep/bin/semgrep-core"
            and not name.startswith("semgrep/bin/libs/")
        )
    )


def _copy_file(source: Path, destination: Path) -> int:
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError("native analyzer view contains indirection")
        if before.st_size > MAX_BYTES:
            raise ValueError("native analyzer view exceeds bounds")
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        with destination.open("xb") as output:
            while data := os.read(descriptor, 64 << 10):
                total += len(data)
                if total > before.st_size:
                    raise ValueError("native analyzer bytes changed during staging")
                output.write(data)
        after = os.fstat(descriptor)
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if total != before.st_size or any(getattr(before, field) != getattr(after, field) for field in fields):
            raise ValueError("native analyzer bytes changed during staging")
        destination.chmod(0o400)
        return total
    finally:
        os.close(descriptor)


@beartype
@require(lambda analyzer_root: analyzer_root.is_dir())
def build_analyzer_view(analyzer_root: Path, destination: Path, graph: dict[str, Any]) -> None:
    """Copy only recorded files owned by this member's analyzer distributions."""
    if destination.exists() or destination.is_symlink():
        raise ValueError("native analyzer view collides with source")
    if analyzer_root.is_symlink() or analyzer_root.resolve() != analyzer_root:
        raise ValueError("native analyzer root contains indirection")
    selected = {
        str(canonicalize_name(row["name"])): row["version"] for row in graph["installed"] if row["origin"] == "analyzer"
    }
    available = {}
    for distribution in distributions(path=[str(analyzer_root)]):
        name = str(canonicalize_name(distribution.metadata["Name"]))
        if name in available:
            raise ValueError("native analyzer distribution ownership is ambiguous")
        available[name] = distribution
    members: dict[str, Path] = {}
    omitted_z3_alias = False
    for name, version in selected.items():
        distribution = available.get(name)
        if distribution is None or distribution.version != version:
            raise ValueError("native analyzer distribution identity differs from graph")
        # Distribution.files filters missing members on newer Python versions.
        # The retained RECORD must still expose every mandatory dependency.
        record_text = distribution.read_text("RECORD")
        if not record_text:
            raise ValueError("native analyzer distribution identity differs from graph")
        for record in csv.reader(record_text.splitlines()):
            if len(record) != 3 or not record[0]:
                raise ValueError("native analyzer RECORD is malformed")
            relative = PurePosixPath(record[0])
            # Console launchers outside site-packages are separately admitted
            # native images; this view supplies import and analysis files only.
            if relative.is_absolute() or ".." in relative.parts:
                continue
            source = analyzer_root.joinpath(*relative.parts)
            if source.is_symlink() or source.resolve() != source:
                raise ValueError("native analyzer view contains indirection")
            if not source.is_file():
                if not source.exists() and _intentionally_omitted(relative):
                    omitted_z3_alias |= relative.as_posix() == _Z3_ALIAS
                    continue
                raise ValueError("native analyzer recorded payload is missing")
            previous = members.get(relative.as_posix())
            if previous is not None:
                raise ValueError("native analyzer file ownership is ambiguous")
            members[relative.as_posix()] = source
    if omitted_z3_alias and _Z3_LIBRARY not in members:
        raise ValueError("native analyzer recorded payload is missing: canonical Z3 library")
    if (
        (selected and not members)
        or len(members) > MAX_FILES
        or sum(path.stat().st_size for path in members.values()) > MAX_BYTES
    ):
        raise ValueError("native analyzer view exceeds bounds or is empty")
    destination.mkdir(mode=0o700)
    for name, source in sorted(members.items()):
        _copy_file(source, destination / name)
    for directory, _names, _files in os.walk(destination, topdown=False):
        Path(directory).chmod(0o500)
