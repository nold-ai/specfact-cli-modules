#!/usr/bin/env bash
# Emit module signature policy for the current context (consumed by pre-commit-verify-modules-signature.sh).
#
# Contract matches specfact-cli `scripts/git-branch-module-signature-flag.sh`: print a single token
# "require" on `main`, "omit" elsewhere. This repo additionally treats GITHUB_BASE_REF=main (PRs
# targeting main) as "require" so pre-commit matches integration-target semantics.
set -euo pipefail

if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  if [[ "${GITHUB_BASE_REF}" == "main" ]]; then
    printf '%s\n' "require"
    exit 0
  fi
  printf '%s\n' "omit"
  exit 0
fi

branch=""
branch=$(git branch --show-current 2>/dev/null || true)
if [[ -z "${branch}" || "${branch}" == "HEAD" ]]; then
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
fi
if [[ "${branch}" == "main" ]]; then
  printf '%s\n' "require"
else
  printf '%s\n' "omit"
fi
