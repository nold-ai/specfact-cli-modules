"""Offline candidate dependency evidence; no installation or production admission.

Run from the repository root: python -B -m
scripts.native_analyzer_inputs.candidate_policy /absolute/basedpyright-1.39.10.tgz
Only the pinned archive is parsed. No archive member is executed or extracted.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

from scripts import native_node_package as node


ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_SEMGREP = "1.175.0"
VERSION_POLICY_INPUT = Path(__file__).resolve().with_name("candidate-version-policy.json")
VERSION_POLICY_SHA256 = "f95986d5dd36bec439c37a753d90c438df08b27186e83b61ec93fb441fa2c451"


def npm_evidence(files: dict[str, tuple[bytes, int]]) -> dict:
    """Bind actual npm metadata and licenses, retaining explicit optional omission."""
    metadata = files.get("basedpyright/package.json", (b"", 0))[0]
    # Reuse the packager's exact distribution contract; no alternate admission path.
    node._validate_npm_metadata(metadata)  # pylint: disable=protected-access
    licenses = {
        name: {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
        for name, (content, _mode) in sorted(files.items())
        if Path(name).name.upper().startswith(("LICENSE", "NOTICE", "COPYING"))
    }
    if "basedpyright/LICENSE.txt" not in licenses or any(entry["size"] == 0 for entry in licenses.values()):
        raise ValueError("missing or empty npm license payload")
    return {
        "schema_version": 1,
        "distribution": f"npm:basedpyright@{node.NPM_VERSION}",
        "source_url": f"https://registry.npmjs.org/basedpyright/-/basedpyright-{node.NPM_VERSION}.tgz",
        "integrity": node.NPM_INTEGRITY,
        "metadata_sha256": hashlib.sha256(metadata).hexdigest(),
        "licenses": licenses,
        "omitted_optional_dependencies": {"fsevents": "~2.3.3"},
        "dependency_admitted": False,
        "production_eligible": False,
    }


def version_evidence() -> dict:
    """Read the complete released version map without importing production code."""
    path = ROOT / "packages/specfact-code-review/src/specfact_code_review/run/runner.py"
    source = path.read_bytes()
    values = [
        ast.literal_eval(statement.value)
        for statement in ast.parse(source).body
        if isinstance(statement, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "_C14_ANALYZER_VERSIONS" for target in statement.targets)
    ]
    if len(values) != 1 or not isinstance(values[0], dict) or len(values[0]) != 10:
        raise ValueError("missing or ambiguous released analyzer version policy")
    versions = values[0]
    drift = {
        member: {"released": versions[member], "candidate": CANDIDATE_SEMGREP}
        for member in ("semgrep-clean", "semgrep-bugs")
        if versions[member] != CANDIDATE_SEMGREP
    }
    data = VERSION_POLICY_INPUT.read_bytes()
    if hashlib.sha256(data).hexdigest() != VERSION_POLICY_SHA256:
        raise ValueError("proposed candidate policy digest mismatch")
    proposed = json.loads(data)
    return {
        "proposed_analyzer_versions": proposed["analyzer_versions"],
        "proposal_only": proposed["proposal_only"],
        "proposed_policy_sha256": VERSION_POLICY_SHA256,
        "proposed_dependency_pins": proposed["dependency_pins"],
        "proposed_semgrep_adapter": proposed["semgrep_adapter"],
        "production_policy_updated": False,
        "parent_required_updates": [
            "producer-version-map",
            "consumer-version-map",
            "toolchain-lock",
            "signed-profile-policy",
            "linux-and-portable-semantic-acceptance",
        ],
        "released_policy_source": path.relative_to(ROOT).as_posix(),
        "released_policy_source_sha256": hashlib.sha256(source).hexdigest(),
        "released_analyzer_versions": versions,
        "candidate_semgrep": CANDIDATE_SEMGREP,
        "policy_drift": drift,
        "version_policy_compatible": not drift,
    }


def main() -> int:
    """Authenticate the archive before bounded parsing and emit candidate evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        data = node.pinned_bytes(args.archive, "sha512", node.NPM_INTEGRITY)
        receipt = npm_evidence(node.payload_files(data, node=False))
        receipt["version_policy"] = version_evidence()
        receipt["archive_sha256"] = hashlib.sha256(data).hexdigest()
    except (OSError, ValueError) as exc:
        parser.exit(1, f"candidate dependency evidence failed: {exc}\n")
    sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
