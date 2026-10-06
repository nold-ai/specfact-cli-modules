"""Build an unsigned native candidate from the existing pinned maintainer inputs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from scripts import assemble_macos_native_capsule as assembler, build_macos_native_capsule as builder
from scripts.macos_managed_boundary import python_analyzers
from scripts.native_release.artifacts import inspect_archive
from specfact_code_review.run import native_backend


ROOT = Path(__file__).resolve().parents[2]


def requirement_file(image: Path, destination: Path) -> Path:
    observed = subprocess.run(
        ["/usr/bin/codesign", "--display", "--requirements", "-", str(image)],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    lines = (observed.stdout + "\n" + observed.stderr).splitlines()
    requirements = [line.removeprefix("# designated => ") for line in lines if line.startswith("# designated => ")]
    if len(requirements) != 1 or not requirements[0]:
        raise ValueError("native image has no unique designated requirement")
    destination.write_text(requirements[0] + "\n")
    return destination


def build_components(work: Path, candidate: dict) -> Path:
    payload = candidate["payload"]
    images = {
        "PYTHON": Path(candidate["target"]),
        "RUFF": payload / "bin/ruff",
        "SEMGREP": payload / "site-packages/semgrep/bin/semgrep-core",
        "NODE": payload / "node/bin/node",
        "UV": payload / "uv/bin/uv",
        "GIT": payload / "git/bin/git",
    }
    environment = dict(os.environ)
    for name, image in images.items():
        environment[f"SPECFACT_{name}_REQUIREMENT_FILE"] = str(requirement_file(image, work / f"{name}.requirement"))
    components = work / "components"
    environment["SPECFACT_NATIVE_BUILD_DIR"] = str(components)
    subprocess.run(
        ["/bin/sh", str(ROOT / "packages/specfact-code-review/native/macos-arm64/build.sh")],
        env=environment,
        check=True,
        timeout=180,
    )
    return components


def assemble_candidate(work: Path, venv: Path, version: str) -> Path:
    analyzer = work / "analyzer"
    analyzer.mkdir()
    candidate = python_analyzers.prepare(analyzer, venv, version, library_loading_experiment=True)
    (analyzer / "candidate.json").write_text(json.dumps(candidate, default=str))
    components = build_components(work, candidate)
    identity = f"darwin-arm64-cp{version.replace('.', '')}"
    assembled = assembler.assemble_macos_native_capsule(
        analyzer_root=analyzer, component_root=components, output_root=work / "runtime", environment_id=identity
    )
    policy = json.loads((ROOT / "scripts/native_analyzer_inputs/candidate-version-policy.json").read_bytes())
    result = builder.build_native_capsule(
        runtime_root=assembled.runtime_root,
        output_dir=work / identity,
        closure=json.loads(assembled.closure.read_bytes()),
        environment_id=identity,
        backend=native_backend.BACKEND_VERSION,
        policy=native_backend.POLICY_VERSION,
        analyzer_versions=policy["analyzer_versions"],
        private_key=None,
    )
    inspect_archive(result.archive.parent)
    return result.archive.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument("--version", choices=("3.11", "3.12", "3.13"), required=True)
    args = parser.parse_args()
    args.work.mkdir(mode=0o700)
    print(assemble_candidate(args.work.resolve(), args.venv.resolve(), args.version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
