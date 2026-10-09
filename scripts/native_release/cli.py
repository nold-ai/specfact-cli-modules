"""Protected-CI release entry point; no candidate payload execution."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization

from scripts.native_release.artifacts import read_bounded
from scripts.native_release.release import ABIS, StageRequest, _unique_pairs, protected_source, stage_release


PUBLIC_KEY = Path(__file__).with_name("module-signing-public.pem")


def collect_receipts(root: Path, output: Path) -> None:
    """Combine job receipts without accepting duplicate platform cells."""
    rows: list[dict[str, Any]] = []
    identities: set[tuple[str, str]] = set()
    for path in sorted(root.rglob("*.json")):
        document = json.loads(read_bounded(path, 1024 * 1024), object_pairs_hook=_unique_pairs)
        for row in document if isinstance(document, list) else [document]:
            identity = row["environment_id"], row["runner"]
            if identity in identities:
                raise ValueError("duplicate native receipt cell")
            identities.add(identity)
            rows.append(row)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(rows, stream, sort_keys=True)


def _environment_key() -> Any:
    encoded = os.environ.get("SPECFACT_NATIVE_CAPSULE_PRIVATE_SIGN_KEY", "")
    password = os.environ.get("SPECFACT_NATIVE_CAPSULE_PRIVATE_SIGN_KEY_PASSPHRASE", "")
    if not encoded or len(encoded) > 64 * 1024:
        raise ValueError("protected native signing key unavailable")
    return serialization.load_pem_private_key(encoded.encode(), password=password.encode() if password else None)


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    collect = subcommands.add_parser("collect")
    collect.add_argument("--receipts", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    sign = subcommands.add_parser("sign")
    sign.add_argument("--artifacts", type=Path, required=True)
    sign.add_argument("--receipts", type=Path, required=True)
    sign.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(arguments)
    if args.command == "collect":
        collect_receipts(args.receipts, args.output)
    else:
        protected_source(os.environ)
        directories = [args.artifacts / f"darwin-arm64-{abi}" for abi in ABIS]
        stage_release(
            StageRequest(directories, args.receipts, args.output, read_bounded(PUBLIC_KEY, 64 * 1024), os.environ),
            _environment_key,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
