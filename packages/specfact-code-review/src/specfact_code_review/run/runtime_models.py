"""Portable project inputs and local runtime evidence contracts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from icontract import ensure


class ProjectRuntimeError(ValueError):
    """An actionable preparation or runtime identity failure."""


@ensure(lambda result: result.startswith("sha256:") and len(result) == 71)
def content_digest(value: bytes) -> str:
    """Return the content identity used by local runtime artifacts."""
    return "sha256:" + hashlib.sha256(value).hexdigest()


@ensure(lambda result: result.startswith("sha256:") and len(result) == 71)
def document_digest(value: object) -> str:
    """Hash a canonical JSON document independently of file formatting."""
    return content_digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


@dataclass(frozen=True)
class ProjectPlan:
    """Read-only discovery result; executable manager semantics remain adapter-owned."""

    root: Path
    manager: str
    environment: str = "default"
    python: str = ""
    requires_python: str = ""
    source_identity: str = ""
    groups: tuple[str, ...] = ()
    extras: tuple[str, ...] = ()
    requirements: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    source_roots: tuple[str, ...] = (".",)
    native_libraries: tuple[str, ...] = ()
    inputs: dict[str, str] = field(default_factory=dict)
    pytest_config: dict[str, Any] = field(default_factory=dict)

    @ensure(lambda result: "root" not in result)
    def document(self) -> dict[str, Any]:
        """Return relocation-independent inputs suitable for cache identity."""
        result = asdict(self)
        result.pop("root")
        return result

    @property
    def identity(self) -> str:
        return document_digest(self.document())


@dataclass(frozen=True)
class PreparedRuntime:
    """Validated local artifact and the provenance available to the controller."""

    root: Path
    descriptor_path: Path
    identity: str
    descriptor: dict[str, Any]
