"""Bind the reviewed beartype correction to independently measured runtime artifacts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import zipfile
from email.parser import BytesParser
from pathlib import Path
from typing import Any

import yaml
from packaging.tags import parse_tag
from packaging.utils import canonicalize_name, parse_wheel_filename


_WHEEL_SHA256 = "sha256:d16c9bbc61ea14637596c5f6fbff2ee99cbe3573e46a716401734ef50c3060c2"
_BASELINE_SHA256 = "sha256:65e686167a866116aeff86c522d9952d170ee1a1cb947941e2cad55a548afa9d"


_YAML_BASELINE_SHA256 = "sha256:1974743107ec766dc4e62a48f654018d44a01db5619f424397defc95e2aa4fb3"
_YAML_WHEEL_SHA256 = {
    "cp311": "sha256:b8bb0864c5a28024fac8a632c443c87c5aa6f215c0b126c449ae1a150412f31d",
    "cp312": "sha256:ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc",
    "cp313": "sha256:0f29edc409a6392443abf94b9cf89ce99889a1dd5376d94316ae5145dfedd5d6",
}


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: object) -> None:
    path.write_bytes(_canonical(value) + b"\n")


def _validate_wheel_descriptor(archive: zipfile.ZipFile, wheel: Path, descriptor: dict[str, Any]) -> None:
    """Validate copied identity fields against the authenticated wheel itself."""
    name, version, _build, filename_tags = parse_wheel_filename(wheel.name)
    metadata_paths = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
    if len(metadata_paths) != 1:
        raise ValueError("wheel descriptor requires one metadata identity")
    metadata_path = metadata_paths[0]
    metadata_bytes = archive.read(metadata_path)
    metadata = BytesParser().parsebytes(metadata_bytes)
    if canonicalize_name(str(metadata["Name"])) != name or str(metadata["Version"]) != str(version):
        raise ValueError("wheel descriptor filename and metadata disagree")
    dist_info = metadata_path.rsplit("/", 1)[0]
    wheel_metadata = BytesParser().parsebytes(archive.read(f"{dist_info}/WHEEL"))
    wheel_tags = {tag for value in wheel_metadata.get_all("Tag", []) for tag in parse_tag(value)}
    if wheel_tags != filename_tags:
        raise ValueError("wheel descriptor filename and archive tags disagree")
    entrypoint_path = f"{dist_info}/entry_points.txt"
    entrypoints = archive.read(entrypoint_path) if entrypoint_path in archive.namelist() else b""
    python_tag, abi_tag, platform_tag = wheel.stem.rsplit("-", 3)[1:]
    expected = {
        "name": str(metadata["Name"]),
        "normalized_name": name,
        "version": str(version),
        "direct_specifier": f"=={version}",
        "size": wheel.stat().st_size,
        "python_tag": python_tag,
        "abi_tag": abi_tag,
        "platform_tag": platform_tag,
        "metadata_sha256": _digest(metadata_bytes),
        "entry_points_sha256": _digest(entrypoints),
    }
    mismatches = [key for key, value in expected.items() if descriptor.get(key) != value]
    if mismatches:
        raise ValueError(f"wheel descriptor differs from authenticated bytes: {', '.join(mismatches)}")


def _component(build_root: Path, *, abi: str = "", addition: str = "beartype") -> dict[str, Any]:
    descriptor_path = f"{abi}-wheel-descriptor.json" if addition == "pyyaml" else "beartype-wheel-descriptor.json"
    descriptor = _load(build_root / descriptor_path)
    wheel_root = build_root / abi if addition == "pyyaml" else build_root
    if Path(descriptor["filename"]).name != descriptor["filename"]:
        raise ValueError("wheel descriptor filename is unsafe")
    wheel = wheel_root / descriptor["filename"]
    expected = _YAML_WHEEL_SHA256[abi] if addition == "pyyaml" else _WHEEL_SHA256
    if _digest(wheel.read_bytes()) != expected or descriptor["sha256"] != expected:
        raise ValueError("wheel differs from reviewed PyPI identity")
    with zipfile.ZipFile(wheel) as archive:
        _validate_wheel_descriptor(archive, wheel, descriptor)
        payload = [
            {"path": name, "size": len(archive.read(name)), "sha256": _digest(archive.read(name))}
            for name in sorted(archive.namelist())
            if not name.endswith("/")
        ]
    return {
        "id": descriptor["normalized_name"],
        "normalized_name": descriptor["normalized_name"],
        "kind": "python_distribution",
        "role": "direct",
        "version": descriptor["version"],
        "specifier": descriptor["direct_specifier"],
        "wheel": descriptor["filename"],
        "wheel_sha256": expected,
        "wheel_size": descriptor["size"],
        "wheel_tags": {
            "python": descriptor["python_tag"],
            "abi": descriptor["abi_tag"],
            "platform": descriptor["platform_tag"],
        },
        "top_level_imports": ["_yaml", "yaml"] if addition == "pyyaml" else ["beartype"],
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
    environment["activated_extras"][component["normalized_name"]] = []
    environment["reserved_import_prefixes"] = sorted(
        set(environment["reserved_import_prefixes"]) | set(component["top_level_imports"])
    )
    old_root.update(reference)
    old_root["wheelhouse_manifest_digest"] = environment["wheelhouse"]["digest"]
    old_root["installed_distributions"].append(
        {"normalized_name": component["normalized_name"], "version": component["version"]}
    )
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
        "id": component["id"],
        "normalized_name": component["normalized_name"],
        "version": component["version"],
        "exact_specifier": component["specifier"],
        "kind": "python_distribution",
        "role": "direct",
        "generated_launcher_identity_excluded": True,
        "module_or_entry_point": {"entry_points": [], "top_level_imports": component["top_level_imports"]},
        "environment_payloads": [
            {
                **{
                    key: next(entry for entry in item["components"] if entry["id"] == component["id"])[key]
                    for key in payload_keys
                },
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
    parser.add_argument("--addition", choices=("beartype", "pyyaml"), default="beartype")
    args = parser.parse_args()
    package = args.repo / "packages/specfact-code-review"
    resources = package / "src/specfact_code_review/resources/contracts"
    lock_path = resources / "pr-range-v1-toolchain-lock.json"
    baseline = _YAML_BASELINE_SHA256 if args.addition == "pyyaml" else _BASELINE_SHA256
    if _digest(lock_path.read_bytes()) != baseline:
        raise ValueError("refusing to refresh anything except the reviewed immutable baseline")
    lock = _load(lock_path)
    component = {}
    for environment in lock["environments"]:
        component = _component(args.build_root, abi=environment["python_abi"], addition=args.addition)
        _update_environment(environment, component, args.build_root)
    lock["logical_components"].append(_logical_component(component, lock["environments"]))
    lock["logical_components"].sort(key=lambda item: item["id"])
    lock["oci_facts_digest"] = _digest(
        _canonical([{"environment_id": item["environment_id"], "oci": item["oci"]} for item in lock["environments"]])
    )
    schema_path = resources / "project-runtime-layer-v1.schema.json"
    schema = _load(schema_path)
    catalog = schema["reserved_component_catalog"]
    catalog["prefixes"] = sorted(set(catalog["prefixes"]) | set(component["top_level_imports"]))
    for environment in catalog["prefixes_by_environment"]:
        environment["prefixes"] = sorted(set(environment["prefixes"]) | set(component["top_level_imports"]))
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
