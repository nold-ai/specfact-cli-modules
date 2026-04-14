#!/usr/bin/env bash
# Mirror pr-orchestrator verify-module-signatures policy: require cryptographic signatures on `main`
# only; on other branches (feature, dev, detached HEAD) use checksum + version enforcement so local
# commits work without a private signing key (CI signs on approval before main).
set -euo pipefail
_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$_repo_root"

_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
_require_signature=false
if [[ "$_branch" == "main" || "${GITHUB_REF_NAME:-}" == "main" ]]; then
  _require_signature=true
fi

_base=(hatch run ./scripts/verify-modules-signature.py --payload-from-filesystem --enforce-version-bump)
if [[ "$_require_signature" == true ]]; then
  exec "${_base[@]}" --require-signature
else
  exec "${_base[@]}"
fi
