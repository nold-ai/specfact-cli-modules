"""Preserve signed public trust data without exposing host trust or credentials."""

from __future__ import annotations

import os
import ssl
import stat
from pathlib import Path

from icontract import ensure

from specfact_code_review.run.runtime_models import ProjectRuntimeError, content_digest


SOURCE = "opt/specfact/analyzers/certifi/cacert.pem"
DESTINATION = "worker-config/ssl/certs/ca-certificates.crt"
_MAX_BUNDLE = 2_000_000


@ensure(lambda result: bool(result) and len(result) <= _MAX_BUNDLE)
def capture_public_trust(capsule_root: Path | None) -> bytes:
    """Capture validated public certificates from the already authenticated worker."""
    try:
        if capsule_root is None:
            raise ValueError("signed worker root missing")
        source = capsule_root / SOURCE
        if not source.resolve().is_relative_to(capsule_root.resolve()):
            raise ValueError("certificate path leaves signed worker")
        descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("certificate bundle is not regular")
            payload = stream.read(_MAX_BUNDLE + 1)
        if len(payload) > _MAX_BUNDLE or b"PRIVATE KEY" in payload:
            raise ValueError("certificate bundle is oversized or contains private material")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cadata=payload.decode("ascii"))
        if not context.cert_store_stats()["x509_ca"]:
            raise ValueError("certificate bundle has no public trust anchors")
        return payload
    except (OSError, ValueError) as exc:
        raise ProjectRuntimeError(
            "project_runtime_public_trust_invalid; reinstall the authenticated worker certificate bundle"
        ) from exc


@ensure(lambda result: result["sha256"].startswith("sha256:"))
def install_public_trust(payload: bytes, artifact: Path) -> dict[str, str]:
    """Install controller-captured bytes after untrusted output validation."""
    directory = artifact
    for name in Path(DESTINATION).parts[:-1]:
        directory /= name
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ProjectRuntimeError("project_runtime_public_trust_collision; builder changed certificate parents")
        directory.mkdir(exist_ok=True)
    destination = artifact / DESTINATION
    if destination.exists() or destination.is_symlink():
        raise ProjectRuntimeError("project_runtime_public_trust_collision; builder supplied certificate destination")
    with destination.open("xb") as stream:
        stream.write(payload)
    return {"source": SOURCE, "path": DESTINATION, "sha256": content_digest(payload)}
