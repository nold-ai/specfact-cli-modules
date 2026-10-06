"""Reject missing GitHub deployment protection before accessing release authority."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import requests

from scripts.native_release.release import _unique_pairs, protected_source


NAMES = ("native-capsule-signing", "native-capsule-publication")


def validate_environment(document: dict[str, Any], name: str) -> None:
    """A named environment alone does not establish a human approval gate."""
    policy = document.get("deployment_branch_policy")
    if document.get("name") != name or document.get("can_admins_bypass") is not False:
        raise ValueError("release environment identity or bypass policy is invalid")
    if (
        not isinstance(policy, dict)
        or policy.get("protected_branches") is not True
        or policy.get("custom_branch_policies") is not False
    ):
        raise ValueError("release environment must restrict deployment to protected branches")
    validate_reviewers(document)


def validate_reviewers(document: dict[str, Any]) -> None:
    rules = document.get("protection_rules", [])
    approvals = [rule for rule in rules if isinstance(rule, dict) and rule.get("type") == "required_reviewers"]
    if len(approvals) != 1 or approvals[0].get("prevent_self_review") is not True:
        raise ValueError("release environment must require an independent human reviewer")
    reviewers = approvals[0].get("reviewers", [])
    if not isinstance(reviewers, list) or not 1 <= len(reviewers) <= 6:
        raise ValueError("release environment has no bounded required reviewer list")


def check_environment(name: str) -> None:
    protected_source(os.environ)
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token or name not in NAMES:
        raise ValueError("release environment verification credential is unavailable")
    response = requests.get(
        f"https://api.github.com/repos/nold-ai/specfact-cli-modules/environments/{name}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        allow_redirects=False,
        stream=True,
        timeout=(15, 30),
    )
    try:
        if response.status_code != 200:
            raise ValueError("release environment protection cannot be verified")
        response.raw.decode_content = True
        payload = response.raw.read(64 * 1024 + 1)
        if len(payload) > 64 * 1024:
            raise ValueError("release environment response exceeds bounds")
    finally:
        response.close()
    validate_environment(json.loads(payload, object_pairs_hook=_unique_pairs), name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", choices=NAMES, required=True)
    check_environment(parser.parse_args().name)
    print("Protected release environment verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
