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
# On the `omit` policy, if verify fails, the hook runs `sign-modules.py --changed-only` against
# `HEAD` (staged + unstaged changes) with `--bump-version patch --allow-unsigned`, re-stages only
# manifests that script reports updating, then re-runs verify so commits self-heal formal drift.
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

_base=(hatch run ./scripts/verify-modules-signature.py --payload-from-filesystem --enforce-version-bump)

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
    set +e
    _verify_out="$("${_base[@]}" 2>&1)"
    _verify_rc=$?
    set -e
    if ((_verify_rc == 0)); then
      exit 0
    fi
    printf '%s\n' "${_verify_out}" >&2

    _failed_manifests=()
    while IFS= read -r mf; do
      [[ -n "${mf}" ]] && _failed_manifests+=("${mf}")
    done < <(printf '%s\n' "${_verify_out}" | grep '^FAIL packages/' | sed -n 's/^FAIL \(packages\/[^[:space:]]*\/module-package\.yaml\):.*/\1/p' | sort -u)

    echo "⚠️  Module verify failed; auto-remediating checksums and patch bumps for changed modules..." >&2
    _sign_log="$(mktemp "${TMPDIR:-/tmp}/specfact-sign-modules.XXXXXX")"
    trap 'rm -f "${_sign_log}"' EXIT
    if ! hatch run ./scripts/sign-modules.py \
      --changed-only \
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
    set +e
    _verify2_out="$("${_base[@]}" 2>&1)"
    _verify2_rc=$?
    set -e
    if ((_verify2_rc != 0)) && ((${#_failed_manifests[@]} > 0)); then
      # Covers committed manifest drift (no diff vs HEAD) or partial first-pass fixes.
      printf '%s\n' "${_verify2_out}" >&2
      echo "⚠️  Retrying sign for failing manifests (compare base HEAD~1)..." >&2
      if ! hatch run ./scripts/sign-modules.py \
        --changed-only \
        --base-ref HEAD~1 \
        --bump-version patch \
        --allow-unsigned \
        --payload-from-filesystem \
        "${_failed_manifests[@]}" >>"${_sign_log}" 2>&1
      then
        cat "${_sign_log}" >&2
        echo "❌ sign-modules fallback remediation failed." >&2
        exit 1
      fi
      _stage_manifests_from_sign_output <"${_sign_log}"
      echo "🔐 Re-verifying after fallback remediation..." >&2
      if ! "${_base[@]}"; then
        echo "❌ Module verify still failing after remediation (manual fix or signing key may be required)." >&2
        exit 1
      fi
      echo "✅ Module manifests updated and staged; continuing the commit." >&2
      exit 0
    fi
    if ((_verify2_rc != 0)); then
      printf '%s\n' "${_verify2_out}" >&2
      echo "❌ Module verify still failing after remediation (manual fix or signing key may be required)." >&2
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
