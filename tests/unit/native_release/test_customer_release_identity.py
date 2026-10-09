"""Published customer proofs bind the event commit and reject registry drift."""

import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import capsule_customer_gate


ROOT = Path(__file__).resolve().parents[3]


def test_native_customer_checkout_preserves_event_commit_and_tag_validation():
    workflow = yaml.load((ROOT / ".github/workflows/native-capsule-customer.yml").read_text(), Loader=yaml.BaseLoader)
    job = workflow["jobs"]["installed-customer"]
    checkout = next(step for step in job["steps"] if "actions/checkout@" in step.get("uses", ""))
    assert checkout["with"].get("ref") in (None, "${{ github.sha }}"), "mutable main cannot attest a published event"
    assert checkout["with"]["fetch-depth"] == "0", "release identity must resolve the published tag"
    assert job["env"]["RELEASE_TAG"] == "${{ github.event.release.tag_name || '' }}"
    install = next(step for step in job["steps"] if step.get("name", "").startswith("Install and verify"))
    assert "--installation-version" in install["run"] and "--verify-installation" in install["run"]


def test_release_checkout_identity_rejects_a_newer_main_before_installation(tmp_path, monkeypatch):
    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(tmp_path), *arguments], text=True).strip()

    git("init", "-q", "-b", "main")
    git("config", "user.name", "Release fixture")
    git("config", "user.email", "fixture@example.invalid")
    (tmp_path / "registry.txt").write_text("published catalog")
    git("add", "registry.txt")
    git("-c", "commit.gpgsign=false", "commit", "-qm", "published")
    release_commit = git("rev-parse", "HEAD")
    git("tag", "published-fixture")
    (tmp_path / "registry.txt").write_text("later main catalog")
    git("-c", "commit.gpgsign=false", "commit", "-qam", "main advances")
    monkeypatch.setenv("RELEASE_TAG", "published-fixture")
    with pytest.raises(ValueError, match="release tag does not match"):
        capsule_customer_gate._release_checkout_identity(tmp_path)
    git("checkout", "-q", "--detach", release_commit)
    assert capsule_customer_gate._release_checkout_identity(tmp_path) == {
        "commit": release_commit,
        "release_tag": "published-fixture",
    }
    monkeypatch.delenv("RELEASE_TAG")
    assert capsule_customer_gate._release_checkout_identity(tmp_path) == {"commit": release_commit, "release_tag": ""}


def _registry_fixture(repository: Path) -> dict:
    import hashlib
    import io
    import json
    import tarfile

    manifest = {
        "name": "nold-ai/specfact-code-review",
        "version": "0.51.2",
        "integrity": {"checksum": "sha256:published", "signature": "published-signature"},
        "resources": [{"path": "native-catalog.json", "checksum": "sha256:published-catalog"}],
    }
    registry = repository / "registry"
    registry.mkdir()
    archive = registry / "module.tar.gz"
    payload = yaml.safe_dump(manifest).encode()
    with tarfile.open(archive, "w:gz") as package:
        member = tarfile.TarInfo("specfact-code-review/module-package.yaml")
        member.size = len(payload)
        package.addfile(member, io.BytesIO(payload))
    (registry / "index.json").write_text(
        json.dumps(
            {
                "modules": [
                    {
                        "id": manifest["name"],
                        "latest_version": manifest["version"],
                        "download_url": archive.name,
                        "checksum_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    }
                ]
            }
        )
    )
    return manifest


@pytest.mark.parametrize("change", ["version", "integrity", "resources", "missing", "malformed"])
def test_native_installation_rejects_source_registry_drift_without_receipt(tmp_path, change):
    manifest = _registry_fixture(tmp_path)
    source = tmp_path / "packages/specfact-code-review/module-package.yaml"
    source.parent.mkdir(parents=True)
    if change == "version":
        manifest["version"] = "0.51.3"
    elif change == "integrity":
        manifest["integrity"] = {"checksum": "sha256:different"}
    elif change == "resources":
        manifest["resources"] = [{"path": "native-catalog.json", "checksum": "sha256:different"}]
    if change != "missing":
        source.write_text("- malformed manifest" if change == "malformed" else yaml.safe_dump(manifest))
    with pytest.raises(ValueError, match=r"source.*manifest"):
        capsule_customer_gate._expected_installation(tmp_path, require_source_identity=True)
    evidence = tmp_path / "evidence"
    with pytest.raises(ValueError, match=r"source.*manifest"):
        capsule_customer_gate._verify_installation(tmp_path, evidence, require_source_identity=True)
    assert not evidence.exists()


def test_native_installation_accepts_matching_source_and_retains_registry_only_baseline(tmp_path):
    manifest = _registry_fixture(tmp_path)
    assert capsule_customer_gate._expected_installation(tmp_path) == manifest
    source = tmp_path / "packages/specfact-code-review/module-package.yaml"
    source.parent.mkdir(parents=True)
    source.write_text(yaml.safe_dump(manifest))
    assert capsule_customer_gate._expected_installation(tmp_path, require_source_identity=True) == manifest


def test_native_workflow_requires_source_identity_for_selection_and_verification():
    workflow = yaml.load((ROOT / ".github/workflows/native-capsule-customer.yml").read_text(), Loader=yaml.BaseLoader)
    install = next(
        step
        for step in workflow["jobs"]["installed-customer"]["steps"]
        if step.get("name", "").startswith("Install and verify")
    )
    commands = install["run"].split("--mode public")[1:]
    assert len(commands) == 2
    assert all("--require-source-identity" in command.split("\n")[0] for command in commands)


@pytest.mark.parametrize("drift", [False, True])
def test_native_installation_cli_enforces_source_identity_before_version_output(tmp_path, monkeypatch, capsys, drift):
    import sys

    manifest = _registry_fixture(tmp_path)
    source = tmp_path / "packages/specfact-code-review/module-package.yaml"
    source.parent.mkdir(parents=True)
    source.write_text(yaml.safe_dump({**manifest, "version": "0.51.3"} if drift else manifest))
    monkeypatch.setattr(capsule_customer_gate, "_release_checkout_identity", lambda _: {})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "gate",
            "--repository",
            str(tmp_path),
            "--evidence",
            str(tmp_path / "evidence"),
            "--mode",
            "public",
            "--require-source-identity",
            "--installation-version",
        ],
    )
    if drift:
        with pytest.raises(ValueError, match=r"source.*manifest"):
            capsule_customer_gate.main()
        assert capsys.readouterr().out == ""
    else:
        assert capsule_customer_gate.main() == 0
        assert capsys.readouterr().out.strip() == "0.51.2"
