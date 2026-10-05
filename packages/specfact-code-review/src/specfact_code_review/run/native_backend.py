"""Platform selection for the native Code Review capsule backend."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, BinaryIO, Literal, NoReturn, cast
from urllib.parse import urljoin, urlparse

import requests


if TYPE_CHECKING:
    from specfact_code_review.run.native_capsule import NativeCapsuleLease


BACKEND_VERSION = "managed-v3"
POLICY_VERSION = "project-domains-v3"
_SUPPORTED_PYTHON_MINORS = {11, 12, 13}
_CATALOG_RESOURCE = "resources/contracts/native-capsule-catalog-v1.json"
_MAX_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024
_MAX_READ_BYTES = 64 * 1024
_MAX_REDIRECTS = 4
_HTTP_TIMEOUT = (15, 60)
_GHCR_HOST = "ghcr.io"
_GHCR_TOKEN_PATH = "/token"
_STORAGE_HOST = "pkg-containers.githubusercontent.com"
_REPOSITORY = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)+")
_DIGEST = re.compile(r"sha256:([0-9a-f]{64})")
_CHALLENGE = re.compile(r'Bearer realm="([^"]+)",service="([^"]+)",scope="([^"]+)"')


class NativeRegistryError(ValueError):
    """A bounded registry operation failed without yielding artifact bytes."""


def _strict_json(payload: str) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        document: dict[str, Any] = {}
        for key, value in values:
            if key in document:
                raise ValueError(f"duplicate JSON field:{key}")
            document[key] = value
        return document

    document = json.loads(payload, object_pairs_hook=pairs)
    if not isinstance(document, dict):
        raise ValueError("native capsule catalog is invalid")
    return document


def _exact_fields(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"native capsule catalog {label} is invalid")
    return cast(dict[str, Any], value)


def _resource_name(environment_id: str, value: object, filename: str) -> str:
    expected = f"resources/native-capsules/{environment_id}/{filename}"
    if value != expected or PurePosixPath(expected).parts != tuple(expected.split("/")):
        raise ValueError(f"native capsule catalog {filename} resource is invalid")
    return expected


def _read_resource(root: Any, name: str, *, text: bool, limit: int) -> bytes | str:
    resource = root.joinpath(name)
    payload = resource.read_bytes()
    if not payload or len(payload) > limit:
        raise ValueError(f"native capsule catalog resource size is invalid:{name}")
    if text:
        return payload.decode("ascii")
    return payload


def _authorized_url(url: str, allowlist: tuple[tuple[str, str], ...]) -> bool:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.fragment
        or (parsed.query and parsed.hostname != _STORAGE_HOST)
    ):
        return False
    return any(parsed.hostname == host and parsed.path.startswith(prefix) for host, prefix in allowlist)


def _request(url: str, **kwargs: Any) -> requests.Response:
    try:
        return requests.get(url, timeout=_HTTP_TIMEOUT, allow_redirects=False, **kwargs)
    except requests.Timeout as exc:
        raise NativeRegistryError("native registry timeout") from exc
    except requests.RequestException as exc:
        raise NativeRegistryError("native registry request failed") from exc


def _bearer_realm(response: requests.Response, repository: str) -> tuple[str, str, str]:
    challenge = response.headers.get("WWW-Authenticate", "")
    match = _CHALLENGE.fullmatch(challenge)
    if match is None:
        raise NativeRegistryError("native registry bearer challenge is invalid")
    realm, service, scope = match.groups()
    parsed = urlparse(realm)
    if (
        parsed.scheme != "https"
        or parsed.hostname != _GHCR_HOST
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != _GHCR_TOKEN_PATH
        or parsed.query
        or parsed.fragment
    ):
        raise NativeRegistryError("native registry bearer realm is unauthorized")
    expected_scope = f"repository:{repository}:pull"
    if service != _GHCR_HOST or scope != expected_scope:
        raise NativeRegistryError("native registry bearer scope is unauthorized")
    return realm, service, scope


def _bounded_token_body(token_response: requests.Response) -> bytes:
    length = token_response.headers.get("Content-Length")
    if length is not None and (not length.isdecimal() or int(length) > 64 * 1024):
        raise NativeRegistryError("native registry token response is oversized")
    if hasattr(token_response.raw, "decode_content"):
        token_response.raw.decode_content = True
    payload = bytearray()
    while len(payload) <= 64 * 1024:
        chunk = token_response.raw.read(min(_MAX_READ_BYTES, 64 * 1024 + 1 - len(payload)))
        if not isinstance(chunk, bytes):
            raise NativeRegistryError("native registry token response is malformed")
        if not chunk:
            break
        payload.extend(chunk)
    if len(payload) > 64 * 1024:
        raise NativeRegistryError("native registry token response is oversized")
    if length is not None and len(payload) != int(length):
        raise NativeRegistryError("native registry token response size disagrees with header")
    return bytes(payload)


def _read_bearer_token(token_response: requests.Response) -> str:
    token_response.raise_for_status()
    payload = _bounded_token_body(token_response)
    try:
        document = _strict_json(payload.decode("utf-8", "strict"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise NativeRegistryError("native registry token response is malformed") from exc
    token = document.get("token") or document.get("access_token") if isinstance(document, dict) else None
    if not isinstance(token, str) or not token or len(token) > 16 * 1024:
        raise NativeRegistryError("native registry returned no bounded bearer token")
    return token


def _bearer_token(response: requests.Response, repository: str, credential: tuple[str, str] | None) -> str:
    realm, service, scope = _bearer_realm(response, repository)
    token_response = _request(
        realm,
        params={"service": service, "scope": scope},
        auth=credential,
        stream=True,
    )
    try:
        return _read_bearer_token(token_response)
    except (requests.RequestException, OSError, TimeoutError) as exc:
        raise NativeRegistryError("native registry token request failed") from exc
    finally:
        token_response.close()


class _RegistryBlobReader:
    """Expose an exact registry response through bounded, cancelable reads."""

    def __init__(self, response: requests.Response, *, size: int, digest: str) -> None:
        self._response = response
        self._size = size
        self._digest = digest
        self._hash = hashlib.sha256()
        self._consumed = 0
        self._verified = False
        self._closed = False
        if hasattr(response.raw, "decode_content"):
            response.raw.decode_content = False

    def __enter__(self) -> _RegistryBlobReader:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    @property
    def closed(self) -> bool:
        return self._closed

    def readable(self) -> bool:
        return not self._closed

    def cancel(self) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._response.close()

    def _fail(self, message: str, cause: BaseException | None = None) -> NoReturn:
        self.close()
        if cause is None:
            raise NativeRegistryError(message)
        raise NativeRegistryError(message) from cause

    def _finish(self) -> None:
        if self._verified:
            return
        try:
            trailing = self._response.raw.read(1)
        except (requests.RequestException, OSError, TimeoutError) as exc:
            self._fail("native registry read timeout", exc)
        if trailing != b"":
            self._fail("native registry blob exceeds signed size")
        if self._hash.hexdigest() != self._digest:
            self._fail("native registry blob digest mismatch")
        self._verified = True

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            raise ValueError("I/O operation on closed native registry reader")
        if not isinstance(size, int) or size <= 0 or size > _MAX_READ_BYTES:
            raise ValueError("native registry reads require a positive bounded size")
        if self._consumed == self._size:
            self._finish()
            return b""
        budget = min(size, self._size - self._consumed)
        try:
            chunk = self._response.raw.read(budget)
        except (requests.RequestException, OSError, TimeoutError) as exc:
            return self._fail("native registry read timeout", exc)
        if not isinstance(chunk, bytes) or not chunk:
            return self._fail("native registry blob is shorter than signed size")
        if len(chunk) > budget:
            return self._fail("native registry blob exceeds signed size")
        self._consumed += len(chunk)
        self._hash.update(chunk)
        if self._consumed == self._size:
            self._finish()
        return chunk


def _redirect_url(
    url: str, response: requests.Response, *, allowlist: tuple[tuple[str, str], ...], redirects: int, maximum: int
) -> str:
    destination = urljoin(url, response.headers.get("Location", ""))
    response.close()
    if redirects >= maximum or not _authorized_url(destination, allowlist):
        raise NativeRegistryError("native registry redirect is unauthorized")
    return destination


def _checked_blob_response(response: requests.Response, *, size: int, digest: str) -> BinaryIO:
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        response.close()
        raise NativeRegistryError("native registry blob request failed") from exc
    length = response.headers.get("Content-Length")
    if length is not None and (not length.isdecimal() or int(length) != size):
        response.close()
        raise NativeRegistryError("native registry blob content size disagrees with catalog")
    return cast(BinaryIO, _RegistryBlobReader(response, size=size, digest=digest.removeprefix("sha256:")))


def _open_registry_blob(
    *,
    repository: str,
    digest: str,
    size: int,
    allowlist: tuple[tuple[str, str], ...],
    max_redirects: int,
) -> BinaryIO:
    url = f"https://{_GHCR_HOST}/v2/{repository}/blobs/{digest}"
    actor = os.environ.get("GITHUB_ACTOR", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    credential = (actor, token) if actor and token else None
    bearer: str | None = None
    redirects = 0
    authenticated = False
    while True:
        if not _authorized_url(url, allowlist):
            raise NativeRegistryError("native registry URL is unauthorized")
        host = urlparse(url).hostname
        headers = {"Accept": "application/octet-stream"}
        if host == _GHCR_HOST and bearer is not None:
            headers["Authorization"] = f"Bearer {bearer}"
        response = _request(url, headers=headers, stream=True, auth=credential if host == _GHCR_HOST else None)
        if response.status_code == 401 and host == _GHCR_HOST and not authenticated:
            authenticated = True
            try:
                bearer = _bearer_token(response, repository, credential)
            finally:
                response.close()
            credential = None
            continue
        if response.status_code in {301, 302, 303, 307, 308}:
            url = _redirect_url(url, response, allowlist=allowlist, redirects=redirects, maximum=max_redirects)
            redirects += 1
            credential = None
            bearer = None
            continue
        return _checked_blob_response(response, size=size, digest=digest)


@dataclass(frozen=True)
class BackendSelection:
    kind: Literal["linux-x86_64", "darwin-arm64", "unsupported"]
    environment_id: str
    reason: str


@dataclass(frozen=True)
class NativePreparation:
    status: Literal["VERIFIED", "INCOMPLETE"]
    lease: NativeCapsuleLease | None
    reason: str
    evidence: dict[str, object]

    @classmethod
    def incomplete(cls, selection: BackendSelection, reason: str) -> NativePreparation:
        return cls(
            "INCOMPLETE",
            None,
            reason,
            {
                "status": "INCOMPLETE",
                "backend": BACKEND_VERSION,
                "environment_id": selection.environment_id,
                "reason": reason,
                "production_eligible": False,
            },
        )


@dataclass(frozen=True)
class NativeArtifact:
    """Authenticated artifact inputs selected from maintainer-owned catalog data."""

    manifest: bytes
    signature: str
    public_key: bytes
    reader: Callable[[], BinaryIO] | None
    offline: bool = False
    progress: Callable[[str, int], None] | None = None
    signature_inspector: Callable[[Path], dict[str, object]] | None = None


def _local_artifact(environment_id: str, root: Path, *, offline: bool) -> NativeArtifact | None:
    selected = root / environment_id
    if not selected.is_dir() or selected.is_symlink():
        return None
    required = {
        "manifest": selected / "manifest.json",
        "signature": selected / "manifest.sig",
        "public_key": selected / "manifest-public.pem",
    }
    if any(path.is_symlink() or not path.is_file() for path in required.values()):
        raise ValueError(f"native artifact directory is incomplete:{environment_id}")
    archive = selected / "capsule.tar"
    if not offline and (archive.is_symlink() or not archive.is_file()):
        raise ValueError(f"native artifact directory is incomplete:{environment_id}")
    return NativeArtifact(
        manifest=required["manifest"].read_bytes(),
        signature=required["signature"].read_text(encoding="ascii").strip(),
        public_key=required["public_key"].read_bytes(),
        reader=None if offline else lambda archive=archive: archive.open("rb"),
        offline=offline,
    )


def _catalog_resources(
    root: Any, environment_id: str, entry: dict[str, Any]
) -> tuple[bytes, str, bytes, dict[str, Any]]:
    names = _exact_fields(entry["resources"], {"manifest", "signature", "public_key"}, "resources")
    manifest_name = _resource_name(environment_id, names["manifest"], "manifest.json")
    signature_name = _resource_name(environment_id, names["signature"], "manifest.sig")
    public_key_name = _resource_name(environment_id, names["public_key"], "manifest-public.pem")
    manifest = cast(bytes, _read_resource(root, manifest_name, text=False, limit=64 * 1024 * 1024))
    signature = cast(str, _read_resource(root, signature_name, text=True, limit=64 * 1024)).strip()
    public_key = cast(bytes, _read_resource(root, public_key_name, text=False, limit=64 * 1024))
    document = _strict_json(manifest.decode("utf-8"))
    if (
        document.get("environment_id") != environment_id
        or document.get("backend") != BACKEND_VERSION
        or document.get("policy") != POLICY_VERSION
    ):
        raise ValueError("native capsule catalog manifest platform substitution")
    archive = document.get("archive")
    if not isinstance(archive, dict):
        raise ValueError("native capsule catalog manifest archive is invalid")
    return manifest, signature, public_key, archive


def _catalog_redirects(values: object, repository: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(values, list) or len(values) != 2:
        raise ValueError("native capsule catalog redirect allowlist is invalid")
    allowlist: list[tuple[str, str]] = []
    for raw_redirect in values:
        redirect = _exact_fields(raw_redirect, {"host", "path_prefix"}, "redirect")
        host, prefix = redirect["host"], redirect["path_prefix"]
        if not isinstance(host, str) or not isinstance(prefix, str):
            raise ValueError("native capsule catalog redirect allowlist is invalid")
        allowlist.append((host, prefix))
    if set(allowlist) != {(_GHCR_HOST, f"/v2/{repository}/blobs/"), (_STORAGE_HOST, "/")}:
        raise ValueError("native capsule catalog redirect allowlist is unauthorized")
    return tuple(allowlist)


def _catalog_blob_identity(ghcr: dict[str, Any]) -> tuple[str, str, int]:
    repository = ghcr["repository"]
    if not isinstance(repository, str) or _REPOSITORY.fullmatch(repository) is None:
        raise ValueError("native capsule catalog GHCR repository is invalid")
    blob = _exact_fields(ghcr["blob"], {"digest", "size"}, "GHCR blob")
    digest, size = blob["digest"], blob["size"]
    if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
        raise ValueError("native capsule catalog GHCR digest is invalid")
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= _MAX_ARCHIVE_BYTES:
        raise ValueError("native capsule catalog GHCR size is invalid")
    return repository, digest, size


def _catalog_blob(
    entry: dict[str, Any], archive: dict[str, Any]
) -> tuple[str, str, int, tuple[tuple[str, str], ...], int]:
    ghcr = _exact_fields(
        entry["ghcr"], {"repository", "blob", "redirect_allowlist", "max_redirects"}, "GHCR descriptor"
    )
    repository, digest, size = _catalog_blob_identity(ghcr)
    if archive.get("sha256") != digest.removeprefix("sha256:"):
        raise ValueError("native capsule catalog GHCR digest disagrees with manifest")
    if archive.get("size") != size:
        raise ValueError("native capsule catalog GHCR size disagrees with manifest")
    allowlist = _catalog_redirects(ghcr["redirect_allowlist"], repository)
    max_redirects = ghcr["max_redirects"]
    if (
        not isinstance(max_redirects, int)
        or isinstance(max_redirects, bool)
        or not 0 <= max_redirects <= _MAX_REDIRECTS
    ):
        raise ValueError("native capsule catalog redirect bound is invalid")
    return repository, digest, size, allowlist, max_redirects


def _catalog_entry(root: Any, environment_id: str, raw_entry: object, *, offline: bool) -> NativeArtifact:
    entry = _exact_fields(raw_entry, {"environment_id", "backend", "policy", "resources", "ghcr"}, "entry")
    if entry["environment_id"] != environment_id:
        raise ValueError("native capsule catalog environment substitution")
    if entry["backend"] != BACKEND_VERSION or entry["policy"] != POLICY_VERSION:
        raise ValueError("native capsule catalog backend or policy substitution")
    manifest, signature, public_key, archive = _catalog_resources(root, environment_id, entry)
    repository, digest, size, allowlist, max_redirects = _catalog_blob(entry, archive)
    return NativeArtifact(
        manifest=manifest,
        signature=signature,
        public_key=public_key,
        reader=(
            None
            if offline
            else lambda: _open_registry_blob(
                repository=repository, digest=digest, size=size, allowlist=allowlist, max_redirects=max_redirects
            )
        ),
        offline=offline,
    )


def _catalog_offline() -> bool:
    offline_value = os.environ.get("SPECFACT_CODE_REVIEW_NATIVE_OFFLINE", "").strip()
    if offline_value not in {"", "1"}:
        raise ValueError("SPECFACT_CODE_REVIEW_NATIVE_OFFLINE must be 1 when set")
    return offline_value == "1"


def _local_artifact_catalog(local_value: str, *, offline: bool) -> dict[str, NativeArtifact]:
    local_root = Path(local_value).expanduser().absolute()
    if local_root.is_symlink() or not local_root.is_dir():
        raise ValueError("native artifact directory is unavailable")
    return {
        environment_id: artifact
        for environment_id in sorted(f"darwin-arm64-cp3{minor}" for minor in _SUPPORTED_PYTHON_MINORS)
        if (artifact := _local_artifact(environment_id, local_root, offline=offline)) is not None
    }


def _packaged_artifact_catalog(*, offline: bool) -> dict[str, NativeArtifact]:

    root = files("specfact_code_review")
    resource = root.joinpath(_CATALOG_RESOURCE)
    document = _strict_json(resource.read_text(encoding="utf-8"))
    if (
        set(document) != {"schema", "entries"}
        or document.get("schema") != "specfact-native-capsule-catalog-v1"
        or not isinstance(document.get("entries"), dict)
    ):
        raise ValueError("native capsule catalog is invalid")
    catalog: dict[str, NativeArtifact] = {}
    for environment_id, raw_entry in cast(dict[str, object], document["entries"]).items():
        if environment_id not in {f"darwin-arm64-cp3{minor}" for minor in _SUPPORTED_PYTHON_MINORS}:
            raise ValueError("native capsule catalog environment is unsupported")
        catalog[environment_id] = _catalog_entry(root, environment_id, raw_entry, offline=offline)
    return catalog


def load_native_artifact_catalog() -> dict[str, NativeArtifact]:
    """Load signed module catalog data or an explicit local publication layout.

    The local directory uses the same four files emitted by the maintainer
    builder. It is an explicit integration input and never triggers host build
    or analyzer fallback.
    """

    offline = _catalog_offline()
    local_value = os.environ.get("SPECFACT_CODE_REVIEW_NATIVE_ARTIFACT_DIR", "").strip()
    if local_value:
        return _local_artifact_catalog(local_value, offline=offline)
    return _packaged_artifact_catalog(offline=offline)


def select_runtime_backend(
    system: str | None = None,
    machine: str | None = None,
    version: tuple[int, int] | None = None,
) -> BackendSelection:
    system = platform.system() if system is None else system
    machine = platform.machine() if machine is None else machine
    version = (sys.version_info.major, sys.version_info.minor) if version is None else version
    abi = f"cp{version[0]}{version[1]}"
    if system == "Linux" and machine in {"x86_64", "AMD64"}:
        return BackendSelection("linux-x86_64", f"linux-x86_64-{abi}", "")
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        environment_id = f"darwin-arm64-{abi}"
        if version[0] == 3 and version[1] in _SUPPORTED_PYTHON_MINORS:
            return BackendSelection("darwin-arm64", environment_id, "")
        if version == (3, 14):
            return BackendSelection("darwin-arm64", "darwin-arm64-cp312", "")
        return BackendSelection(
            "unsupported",
            environment_id,
            f"native_capsule_python_abi_unsupported:{environment_id}",
        )
    return BackendSelection("unsupported", "", "unsupported_controller_platform")


def prepare_native_runtime(
    selection: BackendSelection,
    *,
    cache_root: Path,
    artifact_catalog: Mapping[str, NativeArtifact] | None = None,
) -> NativePreparation:
    if selection.kind == "unsupported":
        return NativePreparation.incomplete(selection, selection.reason)
    if selection.kind != "darwin-arm64":
        raise ValueError("native preparation requires a Darwin ARM64 backend selection")
    artifact = (artifact_catalog or {}).get(selection.environment_id)
    if artifact is None:
        return NativePreparation.incomplete(
            selection,
            f"native_capsule_artifact_not_admitted:{selection.environment_id}",
        )

    from specfact_code_review.run.native_capsule import (
        NativeCapsuleIncompleteError,
        acquire_native_capsule,
        inspect_native_signature,
    )

    try:
        lease = acquire_native_capsule(
            cache_root,
            artifact.manifest,
            artifact.signature,
            artifact.public_key,
            environment_id=selection.environment_id,
            backend=BACKEND_VERSION,
            policy=POLICY_VERSION,
            reader=artifact.reader,
            offline=artifact.offline,
            progress=artifact.progress,
            signature_inspector=artifact.signature_inspector or inspect_native_signature,
        )
    except NativeCapsuleIncompleteError as exc:
        return NativePreparation.incomplete(selection, str(exc))
    return NativePreparation("VERIFIED", lease, "", dict(lease.evidence))
