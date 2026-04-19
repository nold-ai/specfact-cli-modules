#!/usr/bin/env python3
"""Ensure GitHub Epic/Feature sub-issue edges via GraphQL ``addSubIssue``.

``createIssue`` with ``parentIssueId`` often creates the same links, but this
script matches the explicit ``addSubIssue`` workflow used for specfact-cli
hierarchy setup: it only calls ``addSubIssue`` when the child is not already
listed on the parent's ``subIssues`` connection.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any


# Five-pillar modules wave (2026-04): epic #216 -> features -> user stories.
DEFAULT_EDGES: tuple[tuple[int, int], ...] = (
    (216, 217),
    (216, 218),
    (216, 219),
    (216, 220),
    (216, 221),
    (216, 222),
    (217, 226),
    (218, 227),
    (218, 228),
    (218, 229),
    (219, 230),
    (220, 223),
    (221, 224),
    (221, 225),
    (222, 231),
    (222, 232),
)


def _gh_graphql(*, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        if isinstance(value, list):
            for item in value:
                args.extend(["-F", f"{key}[]={item}"])
        else:
            args.extend(["-F", f"{key}={value}"])
    proc = subprocess.run(args, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh graphql failed")
    payload = json.loads(proc.stdout)
    if "errors" in payload:
        raise RuntimeError(json.dumps(payload["errors"], indent=2))
    return payload["data"]


def _issue_node_id(*, owner: str, name: str, number: int) -> str:
    q = """
    query($owner:String!,$name:String!,$n:Int!){
      repository(owner:$owner,name:$name){issue(number:$n){id}}
    }
    """.strip()
    data = _gh_graphql(query=q, variables={"owner": owner, "name": name, "n": number})
    node = data.get("repository", {}).get("issue")
    if not isinstance(node, dict) or not node.get("id"):
        raise RuntimeError(f"missing issue node id for #{number}")
    return str(node["id"])


def _subissue_numbers(*, owner: str, name: str, parent_number: int) -> set[int]:
    q = """
    query($owner:String!,$name:String!,$n:Int!){
      repository(owner:$owner,name:$name){
        issue(number:$n){subIssues(first:50){nodes{number}}}
      }
    }
    """.strip()
    data = _gh_graphql(query=q, variables={"owner": owner, "name": name, "n": parent_number})
    issue = data.get("repository", {}).get("issue")
    if not isinstance(issue, dict):
        raise RuntimeError(f"missing issue #{parent_number}")
    raw_nodes = issue.get("subIssues", {}).get("nodes", [])
    return {int(n["number"]) for n in raw_nodes if isinstance(n, dict) and n.get("number") is not None}


def _add_sub_issue(*, parent_id: str, child_id: str) -> None:
    m = """
    mutation($issueId:ID!,$subIssueId:ID!){
      addSubIssue(input:{issueId:$issueId,subIssueId:$subIssueId,replaceParent:true}){
        issue{number}
        subIssue{number}
      }
    }
    """.strip()
    _gh_graphql(query=m, variables={"issueId": parent_id, "subIssueId": child_id})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-owner", default="nold-ai")
    parser.add_argument("--repo-name", default="specfact-cli-modules")
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    args = parser.parse_args(argv)

    owner, name = args.repo_owner, args.repo_name
    added = 0
    skipped = 0

    for parent_num, child_num in DEFAULT_EDGES:
        existing = _subissue_numbers(owner=owner, name=name, parent_number=parent_num)
        if child_num in existing:
            skipped += 1
            continue
        if args.dry_run:
            sys.stdout.write(f"would addSubIssue #{child_num} under #{parent_num}\n")
            added += 1
            continue
        parent_id = _issue_node_id(owner=owner, name=name, number=parent_num)
        child_id = _issue_node_id(owner=owner, name=name, number=child_num)
        _add_sub_issue(parent_id=parent_id, child_id=child_id)
        sys.stdout.write(f"addSubIssue #{child_num} -> parent #{parent_num}\n")
        added += 1

    sys.stdout.write(f"Done: {added} added, {skipped} already linked (repo {owner}/{name}).\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc
