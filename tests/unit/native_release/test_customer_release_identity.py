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
