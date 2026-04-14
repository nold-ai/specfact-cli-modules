#!/usr/bin/env bash
# Mirror pr-orchestrator verify-module-signatures policy: require cryptographic signatures only when
# the integration target is `main`. Locally that is branch `main`; in GitHub Actions pull_request*
# contexts use GITHUB_BASE_REF (PR base / target), not GITHUB_REF_NAME (head).
set -euo pipefail
_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$_repo_root"

_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
_require_signature=false
if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  if [[ "${GITHUB_BASE_REF}" == "main" ]]; then
    _require_signature=true
  fi
elif [[ "$_branch" == "main" ]]; then
  _require_signature=true
fi

_base=(hatch run ./scripts/verify-modules-signature.py --payload-from-filesystem --enforce-version-bump)
if [[ "$_require_signature" == true ]]; then
  exec "${_base[@]}" --require-signature
else
  exec "${_base[@]}"
fi
