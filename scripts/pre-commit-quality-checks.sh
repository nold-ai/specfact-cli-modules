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

has_staged_python() {
  staged_files | grep -E '\.py$' >/dev/null 2>&1
}

staged_python_files() {
  staged_files | grep -E '\.pyi?$' || true
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

# Parity with CI quality job (.github/workflows/pr-orchestrator.yml: hatch run lint).
# Ruff does not enforce pylint rules (e.g. C0301 max line length on docstrings); pre-commit must run lint too.
run_lint_if_staged_python() {
  if ! has_staged_python; then
    info "ℹ️  No staged Python files — skipping hatch run lint (pylint-inclusive)"
    return 0
  fi
  info "🔎 Staged Python detected — running hatch run lint (ruff + basedpyright + pylint)"
  if hatch run lint; then
    success "✅ Lint passed"
  else
    error "❌ Lint failed (matches CI quality gate)"
    warn "💡 Run: hatch run lint"
    exit 1
  fi
}

run_code_review_gate() {
  # Build a bash array so we invoke pre_commit_code_review.py exactly once. Using xargs
  # here can split into multiple subprocesses when the argument list is long (default
  # max-chars), each overwriting .specfact/code-review.json — yielding partial or empty
  # findings and a misleading artifact.
  local py_array=()
  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    py_array+=("${line}")
  done < <(staged_python_files)

  if [ ${#py_array[@]} -eq 0 ]; then
    info "ℹ️  Block 2 — stage 1/2: no staged Python files — skipping code review gate"
    return
  fi

  info "🛡️ Block 2 — stage 1/2: code review gate (staged Python)"
  if hatch run python scripts/pre_commit_code_review.py "${py_array[@]}"; then
    success "✅ Code review gate passed"
  else
    error "❌ Code review gate failed"
    warn "💡 Fix blocking review findings or run: hatch run python scripts/pre_commit_code_review.py <files>"
    exit 1
  fi
}

run_contract_tests_visible() {
  info "🧪 Block 2 — stage 2/2: contract tests — checking contract-test-status"
  if hatch run contract-test-status > /dev/null 2>&1; then
    success "✅ No contract-test input changes — skipping contract-test run"
  else
    warn "🔄 Contract-test inputs changed — running contract-first tests..."
    if hatch run contract-test; then
      success "✅ Contract-first tests passed"
      warn "💡 CI may still run the full quality matrix"
    else
      error "❌ Contract-first tests failed"
      warn "💡 Run: hatch run contract-test-status"
      exit 1
    fi
  fi
}

warn "🔍 Running modules pre-commit quality checks"

info "📦 Block 1: format, conditional YAML / bundle imports / lint"
run_format_safety
run_yaml_lint_if_needed
run_bundle_import_checks
run_lint_if_staged_python

if check_safe_change; then
  success "✅ Safe change detected — skipping Block 2 (code review + contract tests)"
  info "💡 Only docs, workflow, version, or pre-commit metadata changed"
  exit 0
fi

warn "📦 Block 2: code review + contract tests"
run_code_review_gate
run_contract_tests_visible
