"""Resolve immutable native project bundles from an exactly bound module catalog.

The module ships only public catalog data. Maintainer infrastructure produces and
signs acquisition bundles; this client never owns a private signing key.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from importlib.resources import files
from typing import TYPE_CHECKING, Any, Literal, cast
from urllib.parse import urlparse


if TYPE_CHECKING:
    from specfact_code_review.run.runtime_models import ProjectPlan


_SCHEMA = "specfact-native-project-acquisition-catalog-v1"
_RESOURCE = "resources/contracts/native-project-acquisition-catalog-v1.json"
_MODULE_CATALOG_SHA256 = "da064e1631499ca159950c2394118531df9bd2818b65d2221ef9228d146f2a2e"
_MAX_CATALOG_BYTES = 8 << 20
_MAX_ENTRIES = 10_000
_MAX_ARTIFACT_BYTES = 1 << 30
_MANAGER_VERSIONS = {"pip": "26.2.1", "hatch": "1.18.0", "uv": "0.12.13", "poetry": "2.4.3"}
_IDENTITY = re.compile(r"sha256:[0-9a-f]{64}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_ENVIRONMENT = re.compile(r"darwin-arm64-(cp3(?:11|12|13))")
_REPOSITORY = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)+")


@dataclass(frozen=True)
class ProjectArtifactLocator:
    """Authenticated outer transport facts for one signed acquisition bundle."""

    url: str
    digest: str
    size: int
    transport: Literal["https", "ghcr"]


def _fail(reason: str) -> ValueError:
    return ValueError(f"project_native_acquisition_{reason}")


def _strict_json(payload: bytes) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise _fail("catalog_invalid")
            result[key] = value
        return result

    if not 0 < len(payload) <= _MAX_CATALOG_BYTES:
        raise _fail("catalog_invalid")
    try:
        document = json.loads(payload.decode("ascii", "strict"), object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise _fail("catalog_invalid") from exc
    if not isinstance(document, dict):
        raise _fail("catalog_invalid")
    canonical = json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii") + b"\n"
    if payload != canonical:
        raise _fail("catalog_invalid")
    return document


def _exact(value: object, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise _fail("entry_invalid")
    return cast(dict[str, Any], value)


def _locator(value: object) -> ProjectArtifactLocator:
    artifact = _exact(value, {"url", "digest", "size"})
    url, digest, size = artifact["url"], artifact["digest"], artifact["size"]
    if (
        not isinstance(url, str)
        or not isinstance(digest, str)
        or _DIGEST.fullmatch(digest) is None
        or type(size) is not int
        or not 0 < size <= _MAX_ARTIFACT_BYTES
    ):
        raise _fail("entry_invalid")
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise _fail("entry_invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise _fail("entry_invalid")
    transport: Literal["https", "ghcr"] = "https"
    if parsed.hostname == "ghcr.io":
        match = re.fullmatch(r"/v2/(.+)/blobs/(sha256:[0-9a-f]{64})", parsed.path)
        if match is None or _REPOSITORY.fullmatch(match.group(1)) is None or match.group(2) != digest:
            raise _fail("entry_invalid")
        transport = "ghcr"
    return ProjectArtifactLocator(url=url, digest=digest, size=size, transport=transport)


def module_catalog_bytes() -> tuple[bytes, str]:
    payload = files("specfact_code_review").joinpath(_RESOURCE).read_bytes()
    return payload, _MODULE_CATALOG_SHA256


def resolve_project_artifact(
    plan: ProjectPlan,
    *,
    environment_id: str,
    payload: bytes | None = None,
    expected_sha256: str | None = None,
) -> ProjectArtifactLocator:
    """Resolve one exact project/manager/ABI/platform entry or fail closed."""
    if payload is None:
        payload, module_digest = module_catalog_bytes()
        expected_sha256 = module_digest
    if not isinstance(expected_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise _fail("catalog_digest_invalid")
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _fail("catalog_digest_mismatch")
    document = _strict_json(payload)
    if set(document) != {"schema", "entries"} or document.get("schema") != _SCHEMA:
        raise _fail("catalog_invalid")
    entries = document.get("entries")
    if not isinstance(entries, list) or len(entries) > _MAX_ENTRIES:
        raise _fail("catalog_invalid")
    environment_match = _ENVIRONMENT.fullmatch(environment_id)
    if environment_match is None:
        raise _fail("entry_invalid")
    selected: ProjectArtifactLocator | None = None
    seen: set[tuple[str, str, str, str]] = set()
    for raw_entry in entries:
        entry = _exact(
            raw_entry,
            {"project_identity", "manager", "environment_id", "abi", "platform", "artifact"},
        )
        identity = entry["project_identity"]
        manager = _exact(entry["manager"], {"name", "version"})
        manager_name, manager_version = manager["name"], manager["version"]
        entry_environment, abi, platform = entry["environment_id"], entry["abi"], entry["platform"]
        if (
            not isinstance(identity, str)
            or _IDENTITY.fullmatch(identity) is None
            or not isinstance(manager_name, str)
            or manager_name not in _MANAGER_VERSIONS
            or manager_version != _MANAGER_VERSIONS[manager_name]
            or not isinstance(entry_environment, str)
            or _ENVIRONMENT.fullmatch(entry_environment) is None
            or abi != entry_environment.removeprefix("darwin-arm64-")
            or platform != "darwin-arm64"
        ):
            raise _fail("entry_invalid")
        key = (identity, str(manager_name), str(manager_version), entry_environment)
        if key in seen:
            raise _fail("catalog_duplicate")
        seen.add(key)
        locator = _locator(entry["artifact"])
        if (
            identity == plan.identity
            and manager_name == plan.manager
            and manager_version == _MANAGER_VERSIONS.get(plan.manager)
            and entry_environment == environment_id
            and abi == environment_match.group(1)
        ):
            selected = locator
    if selected is None:
        raise _fail("entry_missing")
    return selected


__all__ = ["ProjectArtifactLocator", "module_catalog_bytes", "resolve_project_artifact"]
