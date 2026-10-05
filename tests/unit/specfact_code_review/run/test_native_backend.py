from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pytest import MonkeyPatch

from specfact_code_review.run import native_backend, native_capsule, runner as runner_api


def test_live_worker_backend_and_profile_have_distinct_cache_identity() -> None:
    assert native_backend.BACKEND_VERSION == "managed-v3"
    assert native_backend.POLICY_VERSION == "project-domains-v3"


class _RawResponse:
    def __init__(
        self,
        status: int,
        payload: bytes = b"",
        *,
        headers: dict[str, str] | None = None,
        token: str | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.status_code = status
        self.headers = headers or {}
        if token is not None and not payload:
            payload = json.dumps({"token": token}, separators=(",", ":")).encode()
        self.raw = io.BytesIO(payload)
        self._token = token
        self._error = error
        self.closed = False

    def json(self) -> dict[str, str]:
        return {"token": self._token} if self._token is not None else {}

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error
        if self.status_code >= 400:
            raise ValueError(f"http status {self.status_code}")

    def close(self) -> None:
        self.closed = True
        self.raw.close()


class _FailingRaw(io.BytesIO):
    def read(self, size: int | None = -1) -> bytes:
        raise native_backend.requests.ReadTimeout("read deadline")


def _packaged_catalog(
    root: Path,
    payload: bytes,
    *,
    repository: str = "nold-ai/specfact-code-review-native",
    redirects: list[dict[str, str]] | None = None,
    digest: str | None = None,
    size: int | None = None,
) -> tuple[str, dict[str, object]]:
    environment = "darwin-arm64-cp312"
    archive_digest = hashlib.sha256(payload).hexdigest()
    resources = root / "resources" / "native-capsules" / environment
    resources.mkdir(parents=True)
    manifest = {
        "schema": "specfact-native-capsule-v1",
        "environment_id": environment,
        "backend": "managed-v3",
        "policy": "project-domains-v3",
        "archive": {"size": len(payload), "sha256": archive_digest},
    }
    (resources / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    (resources / "manifest.sig").write_text("detached-signature", encoding="ascii")
    (resources / "manifest-public.pem").write_bytes(b"public-key")
    entry: dict[str, object] = {
        "environment_id": environment,
        "backend": "managed-v3",
        "policy": "project-domains-v3",
        "resources": {
            "manifest": f"resources/native-capsules/{environment}/manifest.json",
            "signature": f"resources/native-capsules/{environment}/manifest.sig",
            "public_key": f"resources/native-capsules/{environment}/manifest-public.pem",
        },
        "ghcr": {
            "repository": repository,
            "blob": {
                "digest": digest or f"sha256:{archive_digest}",
                "size": len(payload) if size is None else size,
            },
            "redirect_allowlist": redirects
            or [
                {"host": "ghcr.io", "path_prefix": f"/v2/{repository}/blobs/"},
                {"host": "pkg-containers.githubusercontent.com", "path_prefix": "/"},
            ],
            "max_redirects": 4,
        },
    }
    catalog = {"schema": "specfact-native-capsule-catalog-v1", "entries": {environment: entry}}
    (root / "resources" / "contracts").mkdir(parents=True)
    (root / "resources" / "contracts" / "native-capsule-catalog-v1.json").write_text(
        json.dumps(catalog, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    return environment, entry


def _load_packaged(monkeypatch: MonkeyPatch, root: Path) -> native_backend.NativeArtifact:
    monkeypatch.delenv("SPECFACT_CODE_REVIEW_NATIVE_ARTIFACT_DIR", raising=False)
    monkeypatch.delenv("SPECFACT_CODE_REVIEW_NATIVE_OFFLINE", raising=False)
    monkeypatch.setattr(native_backend, "files", lambda _package: root)
    catalog = native_backend.load_native_artifact_catalog()
    return catalog["darwin-arm64-cp312"]


@pytest.mark.parametrize(
    ("minor", "expected"),
    [(11, "darwin-arm64-cp311"), (12, "darwin-arm64-cp312"), (13, "darwin-arm64-cp313")],
)
def test_darwin_arm64_backend_identity_is_bound_to_supported_python_abi(minor: int, expected: str) -> None:
    selected = native_backend.select_runtime_backend("Darwin", "arm64", (3, minor))

    assert selected.kind == "darwin-arm64"
    assert selected.environment_id == expected
    assert selected.reason == ""


def test_newer_controller_python_selects_pinned_native_analyzer_abi() -> None:
    selected = native_backend.select_runtime_backend("Darwin", "arm64", (3, 14))

    assert selected.kind == "darwin-arm64"
    assert selected.environment_id == "darwin-arm64-cp312"
    assert selected.reason == ""


@pytest.mark.parametrize(
    ("system", "machine", "version", "reason"),
    [
        ("Darwin", "x86_64", (3, 12), "unsupported_controller_platform"),
        ("Darwin", "arm64", (3, 10), "native_capsule_python_abi_unsupported:darwin-arm64-cp310"),
        ("Windows", "AMD64", (3, 12), "unsupported_controller_platform"),
    ],
)
def test_backend_selection_fails_closed_for_unadmitted_platforms(
    system: str, machine: str, version: tuple[int, int], reason: str
) -> None:
    selected = native_backend.select_runtime_backend(system, machine, version)

    assert selected.kind == "unsupported"
    assert selected.reason == reason


def test_linux_backend_selection_preserves_existing_identity() -> None:
    selected = native_backend.select_runtime_backend("Linux", "x86_64", (3, 12))

    assert selected.kind == "linux-x86_64"
    assert selected.environment_id == "linux-x86_64-cp312"
    assert selected.reason == ""


def test_native_backend_without_admitted_artifact_is_actionable_and_never_uses_reader(tmp_path: Path) -> None:
    selected = native_backend.select_runtime_backend("Darwin", "arm64", (3, 12))

    result = native_backend.prepare_native_runtime(
        selected,
        cache_root=tmp_path,
        artifact_catalog={},
    )

    assert result.lease is None
    assert result.status == "INCOMPLETE"
    assert result.reason == "native_capsule_artifact_not_admitted:darwin-arm64-cp312"
    assert result.evidence == {
        "status": "INCOMPLETE",
        "backend": "managed-v3",
        "environment_id": "darwin-arm64-cp312",
        "reason": "native_capsule_artifact_not_admitted:darwin-arm64-cp312",
        "production_eligible": False,
    }


def test_admitted_artifact_is_provisioned_with_exact_backend_bindings(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    selected = native_backend.select_runtime_backend("Darwin", "arm64", (3, 12))
    captured: dict[str, object] = {}
    lease = SimpleNamespace(evidence={"status": "VERIFIED_CACHE_CANDIDATE", "production_eligible": False})

    def acquire(*args: object, **kwargs: object) -> object:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return lease

    monkeypatch.setattr(native_capsule, "acquire_native_capsule", acquire)
    artifact = native_backend.NativeArtifact(
        manifest=b"manifest",
        signature="signature",
        public_key=b"public-key",
        reader=lambda: io.BytesIO(b"payload"),
        signature_inspector=lambda _path: {},
    )

    result = native_backend.prepare_native_runtime(
        selected,
        cache_root=tmp_path,
        artifact_catalog={selected.environment_id: artifact},
    )

    assert result.status == "VERIFIED"
    assert result.lease is cast(object, lease)
    assert captured["args"] == (tmp_path, b"manifest", "signature", b"public-key")
    assert cast(dict[str, object], captured["kwargs"])["environment_id"] == "darwin-arm64-cp312"
    assert cast(dict[str, object], captured["kwargs"])["backend"] == "managed-v3"
    assert cast(dict[str, object], captured["kwargs"])["policy"] == "project-domains-v3"


def test_runner_dispatches_darwin_to_native_backend_without_linux_materialization(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    selected = native_backend.BackendSelection("darwin-arm64", "darwin-arm64-cp312", "")
    captured: list[tuple[native_backend.BackendSelection, Path]] = []

    monkeypatch.setattr(runner_api.native_backend, "select_runtime_backend", lambda *_args: selected)

    def prepare(
        selection: native_backend.BackendSelection,
        *,
        cache_root: Path,
        artifact_catalog: object,
    ) -> native_backend.NativePreparation:
        assert artifact_catalog == {}
        captured.append((selection, cache_root))
        return native_backend.NativePreparation.incomplete(
            selection,
            "native_capsule_artifact_not_admitted:darwin-arm64-cp312",
        )

    monkeypatch.setattr(runner_api.native_backend, "prepare_native_runtime", prepare)
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_CAPSULE_CACHE", str(tmp_path / "capsules"))
    monkeypatch.setattr(
        runner_api.toolchain,
        "materialize_capsule",
        lambda *_args, **_kwargs: pytest.fail("Darwin must not enter Linux materialization"),
    )

    runtime, reason = runner_api._prepare_capsule_runtime()

    assert runtime is None
    assert reason == "native_capsule_artifact_not_admitted:darwin-arm64-cp312"
    assert captured == [(selected, tmp_path / "capsules")]


def test_native_incomplete_reason_does_not_enable_development_host_fallback(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(runner_api, "_is_development_source_checkout", lambda: True)

    assert not runner_api._allows_development_host_compatibility(
        "native_capsule_artifact_not_admitted:darwin-arm64-cp312"
    )


def test_packaged_native_catalog_is_authenticated_but_empty_until_publication() -> None:
    assert native_backend.load_native_artifact_catalog() == {}


def test_local_native_artifact_directory_uses_the_same_published_file_contract(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    environment = "darwin-arm64-cp312"
    root = tmp_path / environment
    root.mkdir(parents=True)
    manifest = {"schema": "specfact-native-capsule-v1", "environment_id": environment}
    (root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")))
    (root / "manifest.sig").write_text("detached-signature")
    (root / "manifest-public.pem").write_bytes(b"public-key")
    (root / "capsule.tar").write_bytes(b"capsule-bytes")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_NATIVE_ARTIFACT_DIR", str(tmp_path))

    catalog = native_backend.load_native_artifact_catalog()

    assert set(catalog) == {environment}
    artifact = catalog[environment]
    assert artifact.manifest == (root / "manifest.json").read_bytes()
    assert artifact.signature == "detached-signature"
    assert artifact.public_key == b"public-key"
    assert artifact.reader is not None
    with artifact.reader() as stream:
        assert stream.read() == b"capsule-bytes"


def test_local_native_artifact_directory_reuses_verified_cache_without_source_archive(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    environment = "darwin-arm64-cp312"
    root = tmp_path / environment
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(
        json.dumps({"schema": "specfact-native-capsule-v1", "environment_id": environment})
    )
    (root / "manifest.sig").write_text("detached-signature")
    (root / "manifest-public.pem").write_bytes(b"public-key")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_NATIVE_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_NATIVE_OFFLINE", "1")

    artifact = native_backend.load_native_artifact_catalog()[environment]

    assert artifact.offline is True
    assert artifact.reader is None


def test_packaged_catalog_streams_exact_ghcr_blob_after_anonymous_bearer_challenge(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    payload = b"bounded-capsule"
    environment, _entry = _packaged_catalog(tmp_path, payload)
    challenge = (
        'Bearer realm="https://ghcr.io/token",service="ghcr.io",'
        'scope="repository:nold-ai/specfact-code-review-native:pull"'
    )
    responses = [
        _RawResponse(401, headers={"WWW-Authenticate": challenge}),
        _RawResponse(200, token="anonymous-token"),
        _RawResponse(200, payload, headers={"Content-Length": str(len(payload))}),
    ]
    calls: list[tuple[str, dict[str, Any]]] = []

    def get(url: str, **kwargs: Any) -> _RawResponse:
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(native_backend.requests, "get", get)
    artifact = _load_packaged(monkeypatch, tmp_path)

    assert artifact.reader is not None
    with artifact.reader() as stream:
        assert stream.read(7) + stream.read(64) == payload
        assert stream.read(1) == b""
    assert not responses
    assert calls[0][0].endswith(
        "/v2/nold-ai/specfact-code-review-native/blobs/sha256:" + hashlib.sha256(payload).hexdigest()
    )
    assert calls[0][1]["stream"] is True
    assert calls[0][1]["timeout"] == (15, 60)
    assert calls[1][0] == "https://ghcr.io/token"
    assert calls[1][1]["params"] == {
        "service": "ghcr.io",
        "scope": "repository:nold-ai/specfact-code-review-native:pull",
    }
    assert calls[2][1]["headers"]["Authorization"] == "Bearer anonymous-token"
    assert environment == "darwin-arm64-cp312"


def test_bearer_token_uses_real_requests_stream_without_eager_consumption(monkeypatch: MonkeyPatch) -> None:
    payload = b'{"token":"bounded-public-token"}'
    responses = []

    class MemoryAdapter(native_backend.requests.adapters.BaseAdapter):
        def send(self, request, **_kwargs):
            response = native_backend.requests.Response()
            response.status_code = 200
            response.url = request.url
            response.headers["Content-Length"] = str(len(payload))
            response.raw = io.BytesIO(payload)
            responses.append(response)
            return response

        def close(self):
            pass

    challenge = native_backend.requests.Response()
    challenge.status_code = 401
    challenge.headers["WWW-Authenticate"] = (
        'Bearer realm="https://ghcr.io/token",service="ghcr.io",'
        'scope="repository:nold-ai/specfact-code-review-native:pull"'
    )
    with native_backend.requests.Session() as session:
        session.trust_env = False
        session.mount("https://", MemoryAdapter())
        monkeypatch.setattr(native_backend.requests, "get", session.get)
        assert native_backend._bearer_token(challenge, "nold-ai/specfact-code-review-native", None) == (
            "bounded-public-token"
        )
    assert len(responses) == 1
    assert responses[0].raw.closed


def test_ghcr_token_response_is_bounded_without_content_length(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    payload = b"capsule"
    _packaged_catalog(tmp_path, payload)
    challenge = (
        'Bearer realm="https://ghcr.io/token",service="ghcr.io",'
        'scope="repository:nold-ai/specfact-code-review-native:pull"'
    )
    responses = [
        _RawResponse(401, headers={"WWW-Authenticate": challenge}),
        _RawResponse(200, b"{" + b'"padding":"' + b"x" * (64 * 1024) + b'"}'),
    ]
    monkeypatch.setattr(native_backend.requests, "get", lambda *_args, **_kwargs: responses.pop(0))
    artifact = _load_packaged(monkeypatch, tmp_path)

    assert artifact.reader is not None
    with pytest.raises(native_backend.NativeRegistryError, match="token response is oversized"):
        artifact.reader()


def test_ghcr_reader_accepts_bounded_redirect_without_forwarding_authorization(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    payload = b"redirected-capsule"
    _packaged_catalog(tmp_path, payload)
    destination = "https://pkg-containers.githubusercontent.com/ghcr1/blobs/capsule"
    responses = [
        _RawResponse(307, headers={"Location": destination}),
        _RawResponse(200, payload, headers={"Content-Length": str(len(payload))}),
    ]
    calls: list[tuple[str, dict[str, Any]]] = []

    def get(url: str, **kwargs: Any) -> _RawResponse:
        calls.append((url, kwargs))
        return responses.pop(0)

    monkeypatch.setenv("GITHUB_ACTOR", "maintainer")
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.setattr(native_backend.requests, "get", get)
    artifact = _load_packaged(monkeypatch, tmp_path)

    assert artifact.reader is not None
    with artifact.reader() as stream:
        assert stream.read(64) == payload
        assert stream.read(1) == b""
    assert calls[1][0] == destination
    assert "Authorization" not in calls[1][1]["headers"]
    assert calls[0][1]["auth"] == ("maintainer", "secret-token")
    assert calls[1][1]["auth"] is None


@pytest.mark.parametrize("kind", ["oversize", "truncated"])
def test_ghcr_reader_rejects_response_size_disagreement(monkeypatch: MonkeyPatch, tmp_path: Path, kind: str) -> None:
    payload = b"signed-size"
    _packaged_catalog(tmp_path, payload)
    received = payload + b"x" if kind == "oversize" else payload[:-1]
    response = _RawResponse(200, received)
    monkeypatch.setattr(native_backend.requests, "get", lambda *_args, **_kwargs: response)
    artifact = _load_packaged(monkeypatch, tmp_path)

    assert artifact.reader is not None
    with artifact.reader() as stream, pytest.raises(ValueError, match="size"):
        while stream.read(4):
            pass
    assert response.closed


def test_ghcr_reader_closes_response_on_timeout_and_rejects_unbounded_reads(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    payload = b"capsule"
    _packaged_catalog(tmp_path, payload)
    response = _RawResponse(200, payload)
    monkeypatch.setattr(native_backend.requests, "get", lambda *_args, **_kwargs: response)
    artifact = _load_packaged(monkeypatch, tmp_path)

    assert artifact.reader is not None
    stream = artifact.reader()
    with pytest.raises(ValueError, match="positive bounded size"):
        stream.read()
    stream.close()
    assert response.closed

    read_timeout = _RawResponse(200, payload)
    read_timeout.raw = _FailingRaw(payload)
    monkeypatch.setattr(native_backend.requests, "get", lambda *_args, **_kwargs: read_timeout)
    stream = artifact.reader()
    with pytest.raises(native_backend.NativeRegistryError, match="read timeout"):
        stream.read(1)
    assert read_timeout.closed

    monkeypatch.setattr(
        native_backend.requests,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(native_backend.requests.ConnectTimeout("deadline")),
    )
    with pytest.raises(native_backend.NativeRegistryError, match="timeout"):
        artifact.reader()


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("repository", "repository"),
        ("digest", "digest"),
        ("size", "size"),
        ("redirect-host", "redirect"),
        ("platform", "backend or policy"),
        ("public-key", "resource"),
    ],
)
def test_catalog_rejects_registry_substitution_before_network(
    monkeypatch: MonkeyPatch, tmp_path: Path, mutation: str, error: str
) -> None:
    payload = b"capsule"
    _environment, entry = _packaged_catalog(tmp_path, payload)
    ghcr = cast(dict[str, object], entry["ghcr"])
    blob = cast(dict[str, object], ghcr["blob"])
    if mutation == "repository":
        ghcr["repository"] = "Other/Mutable"
    elif mutation == "digest":
        blob["digest"] = "sha256:" + "0" * 64
    elif mutation == "size":
        blob["size"] = len(payload) + 1
    elif mutation == "redirect-host":
        ghcr["redirect_allowlist"] = [{"host": "evil.example", "path_prefix": "/"}]
    elif mutation == "platform":
        entry["backend"] = "host-v1"
    else:
        resources = cast(dict[str, object], entry["resources"])
        resources["public_key"] = "resources/native-capsules/other/manifest-public.pem"
    catalog_path = tmp_path / "resources" / "contracts" / "native-capsule-catalog-v1.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["entries"]["darwin-arm64-cp312"] = entry
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    monkeypatch.setattr(
        native_backend.requests,
        "get",
        lambda *_args, **_kwargs: pytest.fail("invalid catalog must fail before network"),
    )
    monkeypatch.setattr(native_backend, "files", lambda _package: tmp_path)

    with pytest.raises(ValueError, match=error):
        native_backend.load_native_artifact_catalog()


def test_ghcr_reader_rejects_untrusted_bearer_realm_and_redirect(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    payload = b"capsule"
    _packaged_catalog(tmp_path, payload)
    responses = [
        _RawResponse(
            401,
            headers={
                "WWW-Authenticate": (
                    'Bearer realm="https://evil.example/token",service="ghcr.io",'
                    'scope="repository:nold-ai/specfact-code-review-native:pull"'
                )
            },
        )
    ]
    monkeypatch.setattr(native_backend.requests, "get", lambda *_args, **_kwargs: responses.pop(0))
    artifact = _load_packaged(monkeypatch, tmp_path)
    assert artifact.reader is not None
    with pytest.raises(native_backend.NativeRegistryError, match="realm"):
        artifact.reader()

    responses.append(_RawResponse(307, headers={"Location": "https://evil.example/blob"}))
    with pytest.raises(native_backend.NativeRegistryError, match="redirect"):
        artifact.reader()


def test_offline_catalog_reuse_constructs_no_network_reader(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    _packaged_catalog(tmp_path, b"capsule")
    monkeypatch.setenv("SPECFACT_CODE_REVIEW_NATIVE_OFFLINE", "1")
    monkeypatch.setattr(native_backend, "files", lambda _package: tmp_path)
    monkeypatch.setattr(
        native_backend.requests,
        "get",
        lambda *_args, **_kwargs: pytest.fail("offline catalog loading must not access the network"),
    )

    artifact = native_backend.load_native_artifact_catalog()["darwin-arm64-cp312"]

    assert artifact.offline is True
    assert artifact.reader is None
