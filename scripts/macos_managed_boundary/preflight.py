"""Check native prerequisites or optional Apple credentials; never admit a runtime."""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA = "specfact-managed-boundary-signing-preflight-v1"


def receipt(status: str, reason: str) -> dict[str, Any]:
    """Keep credential availability explicitly separate from boundary acceptance."""
    return {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "production_approved": False,
        "signed_boundary_verified": False,
    }


def capture(command: list[str]) -> str | None:
    """Bound prerequisite probes and keep keychain/service errors out of receipts."""
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout if completed.returncode == 0 else None


def identity_available(output: str, identity: str, team: str) -> bool:
    """Require a valid Developer ID Application identity for the configured team."""
    for line in output.splitlines():
        match = re.fullmatch(
            r'\s*\d+\)\s+([A-Fa-f0-9]{40})\s+"Developer ID Application: .+ \(([A-Z0-9]{10})\)"\s*', line
        )
        if match and match[1].upper() == identity.upper() and match[2] == team:
            return True
    return False


def configuration_error(identity: str, team: str, notary_profile: str) -> dict[str, Any] | None:
    """Check explicit credentials without accepting ad-hoc signing or creating output."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return receipt("blocked", "Run the signed boundary milestone on native ARM64 macOS.")
    if not re.fullmatch(r"[A-Fa-f0-9]{40}", identity):
        return receipt("blocked", "Configure an exact Developer ID Application certificate SHA-1 identity.")
    if not re.fullmatch(r"[A-Z0-9]{10}", team):
        return receipt("blocked", "Configure the corresponding ten-character Apple Developer Team ID.")
    if not notary_profile.strip() or any(ord(character) < 32 for character in notary_profile):
        return receipt("blocked", "Configure a notarytool keychain profile; never pass private keys or passwords here.")
    return None


def preflight(identity: str, team: str, notary_profile: str) -> dict[str, Any]:
    """Probe credentials only after explicit configuration validation."""
    error = configuration_error(identity, team, notary_profile)
    if error is not None:
        return error
    identities = capture(["/usr/bin/security", "find-identity", "-v", "-p", "codesigning"])
    if identities is None or not identity_available(identities, identity, team):
        return receipt(
            "blocked", "Install/unlock the matching valid Developer ID Application identity on the build host."
        )
    history = capture(
        ["/usr/bin/xcrun", "notarytool", "history", "--keychain-profile", notary_profile, "--output-format", "json"]
    )
    if history is None:
        return receipt("blocked", "Notarization authentication is unavailable; check the configured keychain profile.")
    try:
        response = json.loads(history)
    except ValueError:
        return receipt("blocked", "Notarization returned unrecognized evidence; inspect the service independently.")
    if not isinstance(response, dict) or not isinstance(response.get("history"), list):
        return receipt("blocked", "Notarization returned unrecognized evidence; inspect the service independently.")
    return receipt(
        "credentials_available",
        "Credential probes passed only; build, strict signature verification, notarization "
        "and signed boundary tests remain required.",
    )


def initial_preflight() -> dict[str, Any]:
    """Check initial native prerequisites without probing Apple credentials."""
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return receipt("blocked", "Run initial-distribution boundary tests on native ARM64 macOS.")
    if not Path("/usr/bin/codesign").is_file():
        return receipt("blocked", "The system native code-signing tool is unavailable.")
    result = receipt(
        "initial_prerequisites_available",
        "Native prerequisite checks passed only. Final native signatures, authenticated "
        "payloads, hardening, independent boundary proof and installation acceptance remain required.",
    )
    result["signing_mode"] = "ad-hoc"
    return result


def main() -> int:
    """Print a redacted prerequisite receipt with a nonzero blocked exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signing-mode", choices=("initial", "developer-id"), default="initial")
    parser.add_argument("--identity", default="", help="Developer ID Application certificate SHA-1, not a private key")
    parser.add_argument("--team", default="", help="Apple Developer Team ID")
    parser.add_argument("--notary-profile", default="", help="Existing notarytool keychain profile name")
    args = parser.parse_args()
    if args.signing_mode == "initial":
        if args.identity or args.team or args.notary_profile:
            parser.error("Apple credential arguments require --signing-mode developer-id")
        result = initial_preflight()
    else:
        result = preflight(args.identity, args.team, args.notary_profile)
    sys.stdout.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return 0 if result["status"] in {"credentials_available", "initial_prerequisites_available"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
