#!/usr/bin/env bash
# Pre-commit checks for specfact-cli-modules.
# - Always enforce formatter safety and bundle import boundaries.
# - Run YAML validation when staged YAML files exist.
# - Skip heavier tests for safe-only doc/version/workflow changes.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}$*${NC}"; }
success() { echo -e "${GREEN}$*${NC}"; }
warn() { echo -e "${YELLOW}$*${NC}"; }
error() { echo -e "${RED}$*${NC}"; }

staged_files() {
  git diff --cached --name-only
}

has_staged_yaml() {
  staged_files | grep -E '\.ya?ml$' >/dev/null 2>&1
}

check_safe_change() {
  local files
  files=$(staged_files)

  if [ -z "${files}" ]; then
    return 0
  fi

  local other_changes=0
  local file
  for file in ${files}; do
    case "${file}" in
      *.md|*.rst|*.txt|docs/*|images/*|papers/*|presentations/*)
        ;;
      .github/workflows/*|*.yaml|*.yml)
        ;;
      pyproject.toml|README.md|CHANGELOG.md|.pre-commit-config.yaml)
        ;;
      scripts/pre-commit-quality-checks.sh)
        ;;
      *)
        other_changes=$((other_changes + 1))
        ;;
    esac
  done

  [ "${other_changes}" -eq 0 ]
}

run_format_safety() {
  info "🧹 Running formatter safety check"
  local before_unstaged after_unstaged
  before_unstaged=$(git diff --binary -- . || true)
  if hatch run format; then
    after_unstaged=$(git diff --binary -- . || true)
    if [ "${before_unstaged}" != "${after_unstaged}" ]; then
      error "❌ Formatter changed files. Review and re-stage before committing."
      warn "💡 Run: hatch run format && git add -A"
      exit 1
    fi
    success "✅ Formatting check passed"
  else
    error "❌ Formatting check failed"
    exit 1
  fi
}

run_yaml_lint_if_needed() {
  if has_staged_yaml; then
    info "🔎 YAML changes detected — running manifest validation"
    if hatch run yaml-lint; then
      success "✅ YAML validation passed"
    else
      error "❌ YAML validation failed"
      exit 1
    fi
  else
    info "ℹ️  No staged YAML changes — skipping YAML validation"
  fi
}

run_bundle_import_checks() {
  info "🔎 Running bundle import boundary checks"
  if hatch run check-bundle-imports; then
    success "✅ Bundle import boundaries passed"
  else
    error "❌ Bundle import boundary check failed"
    exit 1
  fi
}

run_contract_test_fast_path() {
  info "🧪 Running contract-test fast path"
  if hatch run contract-test; then
    success "✅ Contract-first tests passed"
  else
    error "❌ Contract-first tests failed"
    warn "💡 Run 'hatch run contract-test-status' for details"
    exit 1
  fi
}

warn "🔍 Running modules pre-commit quality checks"

run_format_safety
run_yaml_lint_if_needed
run_bundle_import_checks

if check_safe_change; then
  success "✅ Safe change detected - skipping contract tests"
  info "💡 Only docs, workflow, version, or pre-commit metadata changed"
  exit 0
fi

run_contract_test_fast_path
