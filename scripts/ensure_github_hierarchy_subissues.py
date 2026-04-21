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


_GH_GRAPHQL_TIMEOUT_SEC = 120

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


def _gh_graphql(*, query: str, variables: dict[str, Any], timeout: int = _GH_GRAPHQL_TIMEOUT_SEC) -> dict[str, Any]:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        if value is None:
            continue
        if isinstance(value, list):
            for item in value:
                args.extend(["-f", f"{key}[]={item}"])
        else:
            if isinstance(value, str):
                args.extend(["-f", f"{key}={value}"])
            else:
                args.extend(["-F", f"{key}={value}"])
    try:
        proc = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"gh graphql timed out after {timeout}s (context: gh api graphql); "
            f"stdout={exc.stdout!r}; stderr={exc.stderr!r}"
        ) from exc
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh graphql failed")
    payload = json.loads(proc.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError(f"gh graphql returned non-dict payload: {proc.stdout}")
    if "errors" in payload:
        raise RuntimeError(json.dumps(payload["errors"], indent=2))
    data = payload.get("data")
    if data is None:
        raise RuntimeError(f"gh graphql returned no data field: {proc.stdout}")
    return data


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
    query($owner:String!,$name:String!,$n:Int!,$after:String){
      repository(owner:$owner,name:$name){
        issue(number:$n){
          subIssues(first:100, after:$after){
            pageInfo{hasNextPage,endCursor}
            nodes{number}
          }
        }
      }
    }
    """.strip()
    collected: set[int] = set()
    after: str | None = None
    while True:
        variables: dict[str, Any] = {"owner": owner, "name": name, "n": parent_number, "after": after}
        data = _gh_graphql(query=q, variables=variables)
        issue = data.get("repository", {}).get("issue")
        if not isinstance(issue, dict):
            raise RuntimeError(f"missing issue #{parent_number}")
        sub = issue.get("subIssues")
        if not isinstance(sub, dict):
            raise RuntimeError(f"missing subIssues for issue #{parent_number}")
        raw_nodes = sub.get("nodes", [])
        if not isinstance(raw_nodes, list):
            raise RuntimeError(f"subIssues nodes is not a list for issue #{parent_number}")
        for node in raw_nodes:
            if isinstance(node, dict) and node.get("number") is not None:
                collected.add(int(node["number"]))
        page_info = sub.get("pageInfo")
        if not isinstance(page_info, dict) or not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
        if not isinstance(cursor, str) or not cursor:
            raise RuntimeError(f"subIssues pagination missing endCursor for issue #{parent_number}")
        after = cursor
    return collected


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
    would_add = 0

    # Simple in-memory caches
    subissue_cache: dict[int, set[int]] = {}
    node_id_cache: dict[int, str] = {}

    for parent_num, child_num in DEFAULT_EDGES:
        # Check cache for sub-issue numbers
        if parent_num not in subissue_cache:
            subissue_cache[parent_num] = _subissue_numbers(owner=owner, name=name, parent_number=parent_num)
        existing = subissue_cache[parent_num]

        if child_num in existing:
            skipped += 1
            continue
        if args.dry_run:
            sys.stdout.write(f"[dry-run] would addSubIssue #{child_num} under #{parent_num}\n")
            would_add += 1
            continue

        # Check cache for node IDs
        if parent_num not in node_id_cache:
            node_id_cache[parent_num] = _issue_node_id(owner=owner, name=name, number=parent_num)
        parent_id = node_id_cache[parent_num]

        if child_num not in node_id_cache:
            node_id_cache[child_num] = _issue_node_id(owner=owner, name=name, number=child_num)
        child_id = node_id_cache[child_num]

        _add_sub_issue(parent_id=parent_id, child_id=child_id)
        sys.stdout.write(f"addSubIssue #{child_num} -> parent #{parent_num}\n")
        added += 1

    if args.dry_run:
        sys.stdout.write(f"Done (dry-run): {would_add} would add, {skipped} already linked (repo {owner}/{name}).\n")
    else:
        sys.stdout.write(f"Done: {added} added, {skipped} already linked (repo {owner}/{name}).\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(1) from exc
