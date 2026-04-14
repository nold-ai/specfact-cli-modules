#!/usr/bin/env bash
# Pre-commit entry: branch-aware module verify (same policy shape as specfact-cli
# `scripts/pre-commit-verify-modules.sh`, adapted for this repository).
#
# Uses `scripts/git-branch-module-signature-flag.sh` (require | omit). When policy is `require`
# (checkout or PR target is `main`), run full payload + signature verification. When `omit`,
# run `verify-modules-signature.py --metadata-only` so local commits are not blocked by checksum
# drift before CI / approval-time signing refreshes manifests (specfact-cli `omit` still runs full
# checksum verification against bundled modules under modules/).
set -euo pipefail

_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$_repo_root"

_flag_script="${_repo_root}/scripts/git-branch-module-signature-flag.sh"
if [[ ! -f "${_flag_script}" ]]; then
  echo "❌ Missing ${_flag_script}" >&2
  exit 1
fi
sig_policy=$(bash "${_flag_script}")
sig_policy="${sig_policy//$'\r'/}"
sig_policy="${sig_policy//$'\n'/}"

_base=(hatch run ./scripts/verify-modules-signature.py --payload-from-filesystem --enforce-version-bump)

case "${sig_policy}" in
  require)
    echo "🔐 Verifying module manifests (strict: --require-signature, --enforce-version-bump, --payload-from-filesystem)" >&2
    exec "${_base[@]}" --require-signature
    ;;
  omit)
    echo "🔐 Verifying module manifests (metadata-only for local commits; full verify runs in CI — see docs/reference/module-security.md)" >&2
    exec "${_base[@]}" --metadata-only
    ;;
  *)
    echo "❌ Invalid module signature policy from ${_flag_script}: '${sig_policy}' (expected require or omit)" >&2
    exit 1
    ;;
esac
