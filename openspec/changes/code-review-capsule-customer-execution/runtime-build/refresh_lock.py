"""Bind the reviewed beartype correction to independently measured runtime artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import yaml


_WHEEL_SHA256 = "sha256:d16c9bbc61ea14637596c5f6fbff2ee99cbe3573e46a716401734ef50c3060c2"
_BASELINE_SHA256 = "sha256:65e686167a866116aeff86c522d9952d170ee1a1cb947941e2cad55a548afa9d"


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.write_bytes(_canonical(value) + b"\n")


def _component(build_root: Path) -> dict[str, Any]:
    descriptor = _load(build_root / "beartype-wheel-descriptor.json")
    wheel = build_root / descriptor["filename"]
    if _digest(wheel.read_bytes()) != _WHEEL_SHA256:
        raise ValueError("beartype wheel differs from reviewed PyPI identity")
    with zipfile.ZipFile(wheel) as archive:
        payload = [
            {"path": name, "size": len(archive.read(name)), "sha256": _digest(archive.read(name))}
            for name in sorted(archive.namelist())
            if not name.endswith("/")
        ]
    return {
        "id": "beartype",
        "normalized_name": "beartype",
        "kind": "python_distribution",
        "role": "direct",
        "version": "0.22.9",
        "specifier": "==0.22.9",
        "wheel": descriptor["filename"],
        "wheel_sha256": _WHEEL_SHA256,
        "wheel_size": descriptor["size"],
        "wheel_tags": {"python": "py3", "abi": "none", "platform": "any"},
        "top_level_imports": ["beartype"],
        "interpreter": "/opt/specfact/python/bin/python",
        "entry_points": [],
        "entry_points_sha256": descriptor["entry_points_sha256"],
        "metadata_sha256": descriptor["metadata_sha256"],
        "generated_launchers_excluded": [],
        "record_entry_count": len(payload),
        "record_payload_manifest_digest": _digest(_canonical(payload)),
        "record_payload_manifest_algorithm": "canonical-json(sorted archive members: path, size, sha256; includes RECORD)",
    }


def _updated_oci(previous: dict[str, Any], facts: dict[str, Any]) -> dict[str, Any]:
    manifest = facts["manifest"]
    if json.loads(facts["manifest_raw"]) != manifest or json.loads(facts["config_raw"]) != facts["config"]:
        raise ValueError("OCI parsed objects differ from the verified bytes")
    if _digest(facts["manifest_raw"].encode()) != facts["manifest_digest"]:
        raise ValueError("published OCI manifest bytes differ from identity")
    if _digest(facts["config_raw"].encode()) != manifest["config"]["digest"]:
        raise ValueError("published OCI config bytes differ from identity")
    layers = [
        {**layer, "diff_id": diff_id}
        for layer, diff_id in zip(manifest["layers"], facts["config"]["rootfs"]["diff_ids"], strict=True)
    ]
    if layers[: len(previous["layers"])] != previous["layers"] or len(layers) != len(previous["layers"]) + 2:
        raise ValueError("new OCI asset must preserve every old layer and add only wheel and manifest layers")
    result = copy.deepcopy(previous)
    result.update(
        manifest=facts["manifest_digest"],
        config=manifest["config"],
        layers=layers,
        cache_key=facts["manifest_digest"],
        manifest_media_type=manifest["mediaType"],
        manifest_size=len(facts["manifest_raw"].encode()),
    )
    result["locator"] = previous["locator"].rsplit("/", 1)[0] + "/" + facts["manifest_digest"]
    return result


def _update_environment(environment: dict[str, Any], component: dict[str, Any], build_root: Path) -> None:
    abi = environment["python_abi"]
    reference = _load(build_root / f"{abi}-root-manifest.json")
    if reference != _load(build_root / f"{abi}-root-manifest-b.json"):
        raise ValueError(f"independent reference filesystems differ: {abi}")
    old_root = environment["final_root_manifest"]
    for name in ("bin", "bootstrap", "lib", "python"):
        if reference["subroots"][name] != old_root["subroots"][name]:
            raise ValueError(f"unexpected immutable subroot change: {abi}/{name}")
    environment["oci"] = _updated_oci(environment["oci"], _load(build_root / f"{abi}-oci.json"))
    environment["wheelhouse"] = _load(build_root / abi / "manifest.json")
    environment["components"].append(copy.deepcopy(component))
    environment["components"].sort(key=lambda item: item["id"])
    environment["activated_extras"]["beartype"] = []
    environment["reserved_import_prefixes"] = sorted(set(environment["reserved_import_prefixes"]) | {"beartype"})
    old_root.update(reference)
    old_root["wheelhouse_manifest_digest"] = environment["wheelhouse"]["digest"]
    old_root["installed_distributions"].append({"normalized_name": "beartype", "version": "0.22.9"})
    old_root["installed_distributions"].sort(key=lambda item: item["normalized_name"])
    environment["two_storage_root_materialization"] = {
        "first": "independent-reference-container-a",
        "second": "independent-reference-container-b",
        "identical_manifest": True,
        "manifest_digest": reference["manifest_digest"],
    }
    closure = {
        key: environment[key]
        for key in (
            "components",
            "dependency_edges",
            "activated_extras",
            "evaluated_markers",
            "wheelhouse",
            "native_tools",
        )
    }
    environment["closure_digest"] = _digest(_canonical(closure))
    environment["closure_digest_algorithm"] = (
        "canonical-json(components, dependency_edges, activated_extras, evaluated_markers, wheelhouse, native_tools)"
    )


def _logical_component(component: dict[str, Any], environments: list[dict[str, Any]]) -> dict[str, Any]:
    payload_keys = (
        "entry_points_sha256",
        "metadata_sha256",
        "record_entry_count",
        "record_payload_manifest_digest",
        "record_payload_manifest_algorithm",
        "wheel",
        "wheel_sha256",
        "wheel_size",
        "wheel_tags",
    )
    return {
        "id": "beartype",
        "normalized_name": "beartype",
        "version": "0.22.9",
        "exact_specifier": "==0.22.9",
        "kind": "python_distribution",
        "role": "direct",
        "generated_launcher_identity_excluded": True,
        "module_or_entry_point": {"entry_points": [], "top_level_imports": ["beartype"]},
        "environment_payloads": [
            {
                **{key: component[key] for key in payload_keys},
                "environment_id": item["environment_id"],
                "sealed_interpreter_identity": "/opt/specfact/python/bin/python",
            }
            for item in environments
        ],
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--build-root", type=Path, required=True)
    args = parser.parse_args()
    package = args.repo / "packages/specfact-code-review"
    resources = package / "src/specfact_code_review/resources/contracts"
    lock_path = resources / "pr-range-v1-toolchain-lock.json"
    if _digest(lock_path.read_bytes()) != _BASELINE_SHA256:
        raise ValueError("refusing to refresh anything except the reviewed immutable baseline")
    lock = _load(lock_path)
    component = _component(args.build_root)
    for environment in lock["environments"]:
        _update_environment(environment, component, args.build_root)
    lock["logical_components"].append(_logical_component(component, lock["environments"]))
    lock["logical_components"].sort(key=lambda item: item["id"])
    lock["oci_facts_digest"] = _digest(
        _canonical([{"environment_id": item["environment_id"], "oci": item["oci"]} for item in lock["environments"]])
    )
    schema_path = resources / "project-runtime-layer-v1.schema.json"
    schema = _load(schema_path)
    catalog = schema["reserved_component_catalog"]
    catalog["prefixes"] = sorted(set(catalog["prefixes"]) | {"beartype"})
    for environment in catalog["prefixes_by_environment"]:
        environment["prefixes"] = sorted(set(environment["prefixes"]) | {"beartype"})
    _write(lock_path, lock)
    _write(schema_path, schema)
    manifest_path = package / "module-package.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    for path in (lock_path, schema_path):
        key = path.relative_to(package / "src/specfact_code_review").as_posix()
        manifest["authenticated_resources"][key]["digest"] = _digest(path.read_bytes())
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    _main()
