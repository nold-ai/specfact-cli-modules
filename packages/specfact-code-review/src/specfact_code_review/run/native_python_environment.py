"""Bind interpreter installation metadata to verified, relocatable native roots."""

from __future__ import annotations

import site
import sys
import sysconfig
from pathlib import Path

from beartype import beartype

from specfact_code_review.run.runtime_models import ProjectRuntimeError


@beartype
def activate(capsule: Path, *, prefix: str = "", alias: str = "") -> None:
    """Correct installation locations without changing upstream build provenance."""
    base = capsule / "python"
    if Path(sys.base_prefix).resolve() != base.resolve():
        raise ProjectRuntimeError("project_native_interpreter_prefix_mismatch")
    selected = Path(prefix) if prefix else base
    if selected.resolve() != selected or not selected.is_dir():
        raise ProjectRuntimeError("project_native_interpreter_prefix_invalid")
    variables = sysconfig.get_config_vars()
    if prefix:
        if alias not in {"python", "python3", f"python{sys.version_info.major}.{sys.version_info.minor}"}:
            raise ProjectRuntimeError("project_native_interpreter_alias_invalid")
        sys.prefix = sys.exec_prefix = str(selected)
        sys.executable = str(selected / "bin" / alias)
    old_library = Path(str(variables.get("LIBDIR", "")))
    if old_library.is_absolute() and old_library.name == "lib":
        old_base = old_library.parent
        for name in (
            "LIBDIR",
            "LIBPL",
            "INCLUDEDIR",
            "CONFINCLUDEDIR",
            "LIBDEST",
            "BINLIBDEST",
            "BINDIR",
            "DATAROOTDIR",
        ):
            value = variables.get(name)
            if isinstance(value, str) and Path(value).is_relative_to(old_base):
                variables[name] = str(base / Path(value).relative_to(old_base))
    variables.update(
        prefix=str(selected),
        exec_prefix=str(selected),
        base=str(selected),
        platbase=str(selected),
        installed_base=str(base),
        installed_platbase=str(base),
    )
    site.PREFIXES = [str(selected)]
    site.ENABLE_USER_SITE = False
