"""Offline workers receive only identity-bound public trust from the signed worker."""

import ssl
from pathlib import Path
from types import SimpleNamespace

import certifi
import pytest

from specfact_code_review.run import runtime_builder
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


SOURCE = "opt/specfact/analyzers/certifi/cacert.pem"
DESTINATION = "worker-config/ssl/certs/ca-certificates.crt"


@pytest.fixture(name="trust_case")
def trust_case_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Keep the real capture/seal/cache path; replace only dependency acquisition."""
    capsule = tmp_path / "capsule"
    source = capsule / SOURCE
    source.parent.mkdir(parents=True)
    source.write_bytes(Path(certifi.where()).read_bytes())
    case = SimpleNamespace(
        source=source,
        payload=source.read_bytes(),
        plan=ProjectPlan(tmp_path, manager="pip"),
        runtime=SimpleNamespace(root=capsule, environment_id="linux-x86_64-cp312", identity="sha256:" + "a" * 64),
        cache=tmp_path / "cache",
        mutation=lambda _artifact: None,
    )
    monkeypatch.setattr(runtime_builder, "git_identity", lambda: "isolated-test-git")
    monkeypatch.setattr(runtime_builder, "verify_inputs", lambda _plan: None)
    monkeypatch.setattr(runtime_builder, "inventory_native", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(runtime_builder, "analyzer_dependency_conflicts", lambda *_args: {})
    monkeypatch.setattr(runtime_builder, "member_dependency_graphs", lambda *_args: {})

    def build(_plan, _runtime, staging, **_kwargs):
        artifact = staging / "artifact"
        (artifact / "worker-config").mkdir(parents=True)
        (artifact / "worker-config/hosts").write_text("127.0.0.1 localhost\n")
        (artifact / "inventory.json").write_text("{}")
        case.mutation(artifact)
        return artifact

    monkeypatch.setattr(runtime_builder, "_build", build)
    return case


def _prepare(case: SimpleNamespace, *, offline: bool = False):
    return runtime_builder.prepare_runtime(case.plan, runtime=case.runtime, cache_root=case.cache, offline=offline)


def test_signed_public_trust_survives_offline_attachment(trust_case: SimpleNamespace) -> None:
    prepared = _prepare(trust_case)
    target = prepared.root / DESTINATION
    assert target.is_file(), "attached worker /etc lacks the signed public certificate bundle"
    assert target.read_bytes() == trust_case.payload
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=str(target))
    assert context.cert_store_stats()["x509_ca"] > 0
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    assert prepared.descriptor["inventory"]["public_trust"] == {
        "source": SOURCE,
        "path": DESTINATION,
        "sha256": runtime_builder.content_digest(trust_case.payload),
    }
    assert _prepare(trust_case, offline=True).identity == prepared.identity
    assert (prepared.root / "worker-config/hosts").read_text() == "127.0.0.1 localhost\n"


def test_public_trust_change_invalidates_warm_cache(trust_case: SimpleNamespace) -> None:
    _prepare(trust_case)
    trust_case.source.write_bytes(trust_case.payload + b"\n# changed signed fixture bundle\n")
    with pytest.raises(ProjectRuntimeError, match="offline_cache_miss"):
        _prepare(trust_case, offline=True)


def test_builder_cannot_replace_captured_public_trust(trust_case: SimpleNamespace) -> None:
    trust_case.mutation = lambda _artifact: trust_case.source.write_bytes(b"builder modified fixture source")
    prepared = _prepare(trust_case)
    assert (prepared.root / DESTINATION).is_file(), "public trust must be captured before building"
    assert (prepared.root / DESTINATION).read_bytes() == trust_case.payload


@pytest.mark.parametrize("violation", ["missing", "symlink", "escaped-parent", "private-key", "malformed", "oversized"])
def test_unverified_public_trust_is_rejected(trust_case: SimpleNamespace, violation: str) -> None:
    source = trust_case.source
    if violation == "missing":
        source.unlink()
    elif violation == "symlink":
        destination = source.parent / "elsewhere.pem"
        source.rename(destination)
        source.symlink_to(destination)
    elif violation == "escaped-parent":
        outside = trust_case.cache.parent / "outside-trust"
        source.parent.rename(outside)
        source.parent.symlink_to(outside)
    else:
        content = {
            "private-key": trust_case.payload + b"\n-----BEGIN PRIVATE KEY-----\nsecret\n",
            "malformed": b"not a certificate",
            "oversized": b"x" * 2_000_001,
        }[violation]
        source.write_bytes(content)
    with pytest.raises(ProjectRuntimeError, match="project_runtime_public_trust"):
        _prepare(trust_case)
    assert not list(trust_case.cache.glob("*/project-runtime.json"))


@pytest.mark.parametrize("collision_kind", ["leaf", "parent"])
def test_builder_certificate_destination_collision_fails_closed(
    trust_case: SimpleNamespace, collision_kind: str
) -> None:
    def collision(artifact):
        destination = artifact / (DESTINATION if collision_kind == "leaf" else "worker-config/ssl")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"builder-selected trust")

    trust_case.mutation = collision
    with pytest.raises(ProjectRuntimeError, match="project_runtime_public_trust_collision"):
        _prepare(trust_case)
    assert not list(trust_case.cache.glob("*/project-runtime.json"))
