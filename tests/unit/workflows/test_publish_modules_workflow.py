from __future__ import annotations

import runpy
import textwrap
from pathlib import Path
from typing import Any, cast


REPO_ROOT = Path(__file__).resolve().parents[3]


def _workflow_text() -> str:
    return (REPO_ROOT / ".github" / "workflows" / "publish-modules.yml").read_text(encoding="utf-8")


def _publish_python_block() -> str:
    workflow = _workflow_text()
    start = workflow.index("          import hashlib")
    end = workflow.index("\n          PY", start)
    return textwrap.dedent(workflow[start:end])


def _signature_sidecar_globals(tmp_path: Path) -> dict[str, object]:
    block = _publish_python_block()
    start = block.index("def write_registry_signature_sidecar")
    end = block.index("\nskipped_bundles", start)
    source = "\n".join(
        [
            "from pathlib import Path",
            f"repo_root = Path({str(tmp_path)!r})",
            'registry_signatures_dir = repo_root / "registry" / "signatures"',
            "registry_signatures_dir.mkdir(parents=True, exist_ok=True)",
            block[start:end],
            "skipped_bundles = {'specfact-example': '1.2.3'}",
        ]
    )
    script_path = tmp_path / "isolated_publish_module_sidecar.py"
    script_path.write_text(source, encoding="utf-8")
    return runpy.run_path(str(script_path))


def test_publish_modules_writes_signature_sidecars_for_skipped_bundles() -> None:
    workflow = _workflow_text()

    assert "def write_registry_signature_sidecar(" in workflow
    assert 'signature_path = registry_signatures_dir / f"{bundle}-{version}.tar.sig"' in workflow
    assert "for bundle, published_version in skipped_bundles.items():" in workflow
    assert "write_registry_signature_sidecar(bundle, manifest, expected_version=published_version)" in workflow


def test_publish_modules_skipped_signature_sidecar_requires_published_version(tmp_path: Path) -> None:
    namespace = _signature_sidecar_globals(tmp_path)
    write_registry_signature_sidecar = cast(Any, namespace["write_registry_signature_sidecar"])
    registry_signatures_dir = cast(Path, namespace["registry_signatures_dir"])
    skipped_bundles = cast(dict[str, str], namespace["skipped_bundles"])

    bundle = "specfact-example"
    version = skipped_bundles[bundle]
    write_registry_signature_sidecar(
        bundle,
        {"version": version, "integrity": {"signature": "signed"}},
        expected_version=version,
    )
    sidecar_path = registry_signatures_dir / f"{bundle}-{version}.tar.sig"
    assert sidecar_path.read_text(encoding="utf-8") == "signed\n"

    write_registry_signature_sidecar(
        "specfact-other",
        {"version": "9.9.9", "integrity": {"signature": "wrong"}},
        expected_version=version,
    )
    assert not (registry_signatures_dir / "specfact-other-9.9.9.tar.sig").exists()


def test_publish_modules_tracks_registry_signatures_in_publish_commit() -> None:
    workflow = _workflow_text()

    assert "git diff --quiet -- registry/index.json registry/modules registry/signatures" in workflow
    assert "git add registry/index.json registry/modules registry/signatures" in workflow
