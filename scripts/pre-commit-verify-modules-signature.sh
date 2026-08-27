#!/usr/bin/env bash
# Pre-commit entry: branch-aware module verify (same policy shape as specfact-cli
# `scripts/pre-commit-verify-modules.sh`, adapted for this repository).
#
# Uses `scripts/git-branch-module-signature-flag.sh` (require | omit). When policy is `require`
# (checkout or PR target is `main`), run full payload + signature verification. When `omit`,
# run the same baseline verifier as PRs targeting `dev` (full payload checksum + version bump;
# cryptographic signature is enforced only in the `require` branch below). Contributors refresh
# checksums with `scripts/sign-modules.py
# --allow-unsigned --payload-from-filesystem` when they lack a release signing key.
#
# On the `omit` policy, checksum/version repair is limited to module payloads staged for the
# pending commit. Existing optional signatures without a locally available public key do not
# trigger repair. The hook never rewrites unrelated manifests.
# Registry rows and published tarballs are intentionally left to CI (`publish-modules`); do not
# rewrite registry/index.json or registry/modules from pre-commit.
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

_target_branch="${GITHUB_BASE_REF:-dev}"
if [[ -z "${GITHUB_BASE_REF:-}" ]] && [[ "$(git branch --show-current 2>/dev/null || true)" == "main" ]]; then
  _target_branch="main"
fi
_version_check_base="refs/remotes/origin/${_target_branch}"
if ! git rev-parse --verify --quiet "${_version_check_base}^{commit}" >/dev/null; then
  echo "❌ Missing fetched target branch ${_version_check_base}; fetch it before committing." >&2
  exit 1
fi

_base=(
  hatch run ./scripts/verify-modules-signature.py
  --payload-from-filesystem
  --enforce-version-bump
  --version-check-base "${_version_check_base}"
)

_staged_module_manifests() {
  local path bundle manifest
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    case "${path}" in
      packages/*/*)
        bundle="${path#packages/}"
        bundle="${bundle%%/*}"
        manifest="packages/${bundle}/module-package.yaml"
        [[ -f "${manifest}" ]] && printf '%s\n' "${manifest}"
        ;;
    esac
  done < <(git diff --cached --name-only -- packages) | sort -u
}

_stage_manifests_from_sign_output() {
  # sign-modules prints lines like "packages/<bundle>/module-package.yaml: checksum" or ": version a -> b"
  local line mf
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ "${line}" == *:* ]] || continue
    mf="${line%%:*}"
    [[ "${mf}" == packages/*/module-package.yaml ]] || continue
    [[ -f "${mf}" ]] || continue
    git add -- "${mf}"
  done
}

case "${sig_policy}" in
  require)
    echo "🔐 Verifying module manifests (strict: --require-signature, --enforce-version-bump, --payload-from-filesystem)" >&2
    exec "${_base[@]}" --require-signature
    ;;
  omit)
    echo "🔐 Verifying module manifests (formal: payload checksum + version bump; signatures not required on this branch — see docs/reference/module-security.md)" >&2
    _omit_base=("${_base[@]}" --allow-missing-public-key)
    if _verify_out="$("${_omit_base[@]}" 2>&1)"; then
      exit 0
    fi
    printf '%s\n' "${_verify_out}" >&2

    _staged_manifests=()
    while IFS= read -r mf; do
      [[ -n "${mf}" ]] && _staged_manifests+=("${mf}")
    done < <(_staged_module_manifests)
    if ((${#_staged_manifests[@]} == 0)); then
      echo "❌ Module verification failed, but no module payload is staged; refusing to rewrite unrelated manifests." >&2
      exit 1
    fi

    echo "⚠️  Module verify failed; auto-remediating staged module checksums and patch bumps..." >&2
    _sign_log="$(mktemp "${TMPDIR:-/tmp}/specfact-sign-modules.XXXXXX")"
    trap 'rm -f "${_sign_log}"' EXIT
    if ! hatch run ./scripts/sign-modules.py \
      --staged-only \
      --base-ref HEAD \
      --bump-version patch \
      --allow-unsigned \
      --payload-from-filesystem >"${_sign_log}" 2>&1
    then
      cat "${_sign_log}" >&2
      echo "❌ sign-modules auto-remediation failed." >&2
      exit 1
    fi
    if [[ -s "${_sign_log}" ]]; then
      cat "${_sign_log}" >&2
    fi

    _stage_manifests_from_sign_output <"${_sign_log}"
    echo "🔐 Re-verifying after auto-remediation..." >&2
    if ! _verify2_out="$("${_omit_base[@]}" 2>&1)"; then
      printf '%s\n' "${_verify2_out}" >&2
      echo "❌ Module verify still failing after staged-only remediation; no unrelated manifest will be rewritten." >&2
      exit 1
    fi
    echo "✅ Module manifests updated and staged; continuing the commit." >&2
    exit 0
    ;;
  *)
    echo "❌ Invalid module signature policy from ${_flag_script}: '${sig_policy}' (expected require or omit)" >&2
    exit 1
    ;;
esac
