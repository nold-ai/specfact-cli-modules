#!/usr/bin/env bash
# Pre-commit checks for specfact-cli-modules.
#
# Pre-commit buffers each hook's output until that hook finishes; one long hook looks
# "silent" until the end. This script is split into subcommands (see .pre-commit-config.yaml)
# so each stage completes and prints before the next hook starts.
#
# Subcommands: block1-format | block1-yaml | block1-bundle | block1-lint | block2 | all
# Run with no args or `all` for manual/CI full pipeline.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}$*${NC}" >&2; }
success() { echo -e "${GREEN}$*${NC}" >&2; }
warn() { echo -e "${YELLOW}$*${NC}" >&2; }
error() { echo -e "${RED}$*${NC}" >&2; }

print_block1_overview() {
  echo "" >&2
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
  echo "  modules pre-commit — Block 1: quality checks (4 stages)" >&2
  echo "    1/4  format (hatch run format; tree must not change)" >&2
  echo "    2/4  YAML manifests (hatch run yaml-lint) if staged *.yaml/*.yml" >&2
  echo "    3/4  bundle import boundaries (hatch run check-bundle-imports)" >&2
  echo "    4/4  lint (hatch run lint) if staged *.py / *.pyi" >&2
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
  echo "" >&2
}

print_block2_overview() {
  echo "" >&2
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
  echo "  modules pre-commit — Block 2: evidence, review + contract tests (3 stages)" >&2
  echo "    1/3  Requirements evidence for staged active OpenSpec sources" >&2
  echo "    2/3  code review gate (staged paths under packages/, registry/, scripts/, tools/, tests/, openspec/changes/)" >&2
  echo "    3/3  contract-first tests (contract-test-status → hatch run contract-test-contracts)" >&2
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
  echo "" >&2
}

staged_files() {
  git diff --cached --name-only
}

has_staged_yaml() {
  staged_files | grep -E '\.ya?ml$' >/dev/null 2>&1
}

has_staged_python() {
  staged_files | grep -E '\.pyi?$' >/dev/null 2>&1
}

staged_python_files() {
  staged_files | grep -E '\.pyi?$' || true
}

has_staged_active_openspec_source() {
  local staged_source
  while IFS= read -r staged_source; do
    case "${staged_source}" in
      openspec/changes/archive/*) ;;
      openspec/changes/*) return 0 ;;
    esac
  done < <(staged_files)
  return 1
}

# Paths passed to scripts/pre_commit_code_review.py (packages/, registry/, scripts/, tools/, tests/, openspec/changes/).
staged_review_gate_files() {
  local line
  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    case "${line}" in
      */TDD_EVIDENCE.md|TDD_EVIDENCE.md) continue ;;
      packages/*|registry/*|scripts/*|tools/*|tests/*|openspec/changes/*)
        printf '%s\n' "${line}"
        ;;
    esac
  done < <(staged_files)
}

staged_docs_validation_paths() {
  local line
  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    case "${line}" in
      packages/**|registry/**|docs/*|*.md|*.mdc|requirements-docs-ci.txt|pyproject.toml|.pre-commit-config.yaml|scripts/pre-commit-quality-checks.sh|scripts/check-core-documentation-accountability.py|scripts/check-docs-commands.py|scripts/check-prompt-commands.py|scripts/check-command-contract.py|scripts/docs_site_validation.py|scripts/generate-command-overview.py|llms.txt|.github/workflows/docs-review.yml|tests/unit/test_core_documentation_accountability.py|tests/unit/test_pre_commit_quality_parity.py|tests/unit/test_check_docs_commands_script.py|tests/unit/test_check_prompt_commands_script.py|tests/unit/docs/test_docs_review.py|tests/unit/docs/test_code_review_docs_parity.py|tests/unit/docs/test_llms_overview_freshness.py)
        printf '%s\n' "${line}"
        ;;
    esac
  done < <(staged_files)
}

staged_prompt_validation_paths() {
  local line
  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    case "${line}" in
      packages/*/resources/**|packages/*/src/**/commands.py|scripts/check-prompt-commands.py|tests/unit/test_check_prompt_commands_script.py)
        printf '%s\n' "${line}"
        ;;
    esac
  done < <(staged_files)
}

needs_docs_site_validation() {
  local line
  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    return 0
  done < <(staged_docs_validation_paths)
  return 1
}

needs_prompt_command_validation() {
  local line
  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    return 0
  done < <(staged_prompt_validation_paths)
  return 1
}

run_docs_site_validation_gate() {
  if ! needs_docs_site_validation; then
    return 0
  fi
  info "📄 Docs site validation — running \`hatch run python scripts/check-docs-commands.py\` (staged docs or docs validation scripts)"
  if hatch run python scripts/check-docs-commands.py; then
    success "✅ Docs site validation passed"
  else
    error "❌ Docs site validation failed"
    warn "💡 Run: hatch run python scripts/check-docs-commands.py"
    exit 1
  fi
}

run_prompt_command_validation_gate() {
  if ! needs_prompt_command_validation; then
    return 0
  fi
  local validation_paths=()
  local full_scan=0
  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    case "${line}" in
      scripts/check-prompt-commands.py|tests/unit/test_check_prompt_commands_script.py)
        full_scan=1
        ;;
      *)
        validation_paths+=("${line}")
        ;;
    esac
  done < <(staged_prompt_validation_paths)
  info "📄 Prompt command validation — running command-reference validation for staged prompts/resources/source guidance"
  if [[ "${full_scan}" -eq 1 ]]; then
    validation_paths=()
  fi
  if hatch run python scripts/check-prompt-commands.py "${validation_paths[@]}"; then
    success "✅ Prompt command validation passed"
  else
    error "❌ Prompt command validation failed"
    warn "💡 Run: hatch run python scripts/check-prompt-commands.py <changed prompt/resource/source paths>"
    exit 1
  fi
}

run_command_overview_validation_gate() {
  if ! needs_docs_site_validation && ! needs_prompt_command_validation; then
    return 0
  fi
  local unstaged_inputs
  unstaged_inputs="$(
    {
      git diff --name-only -- packages registry scripts/generate-command-overview.py scripts/check-command-contract.py pyproject.toml
      git ls-files --others --exclude-standard -- packages registry scripts/generate-command-overview.py scripts/check-command-contract.py pyproject.toml
    } | sort -u
  )"
  if [[ -n "${unstaged_inputs}" ]]; then
    error "❌ Command overview inputs have unstaged changes; refusing to auto-stage generated artifacts"
    warn "Stage or stash these paths before committing:"
    printf '%s\n' "${unstaged_inputs}" >&2
    exit 1
  fi
  info "📄 Command overview validation — regenerating current AI command artifacts"
  if hatch run generate-command-overview; then
    git add -- llms.txt docs/reference/commands.generated.json docs/reference/commands.generated.md
    success "✅ Command overview artifacts regenerated and staged"
  else
    error "❌ Command overview generation failed"
    exit 1
  fi
  info "📄 Command overview validation — running \`hatch run check-command-overview\`"
  if hatch run check-command-overview; then
    success "✅ Command overview validation passed"
  else
    error "❌ Command overview validation failed"
    warn "💡 Run: hatch run generate-command-overview"
    exit 1
  fi
  info "📄 Command contract validation — running \`hatch run check-command-contract\`"
  if hatch run check-command-contract; then
    success "✅ Generated command contract validation passed"
  else
    error "❌ Generated command contract validation failed"
    warn "💡 Run: hatch run check-command-contract"
    exit 1
  fi
}

run_core_documentation_accountability_gate() {
  if ! needs_docs_site_validation; then
    return 0
  fi
  info "📄 Core documentation accountability — running \`hatch run check-core-documentation-accountability\`"
  if hatch run check-core-documentation-accountability; then
    success "✅ Core documentation accountability passed"
  else
    error "❌ Core documentation accountability failed"
    warn "💡 Set SPECFACT_CLI_REPO to the paired core checkout and synchronize its catalogue documentation"
    exit 1
  fi
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
  info "📦 Block 1 — stage 1/4: format — running \`hatch run format\` (fails if working tree would change)"
  local before_unstaged after_unstaged
  before_unstaged=$(git diff --binary -- . || true)
  if hatch run format; then
    after_unstaged=$(git diff --binary -- . || true)
    if [ "${before_unstaged}" != "${after_unstaged}" ]; then
      error "❌ Formatter changed files. Review and re-stage before committing."
      warn "💡 Run: hatch run format && git add -A"
      exit 1
    fi
    success "✅ Block 1 — stage 1/4: format passed"
  else
    error "❌ Block 1 — stage 1/4: format failed"
    exit 1
  fi
}

run_yaml_lint_if_needed() {
  if has_staged_yaml; then
    info "📦 Block 1 — stage 2/4: YAML — running \`hatch run yaml-lint\` (staged YAML detected)"
    if hatch run yaml-lint; then
      success "✅ Block 1 — stage 2/4: YAML validation passed"
    else
      error "❌ Block 1 — stage 2/4: YAML validation failed"
      exit 1
    fi
  else
    info "📦 Block 1 — stage 2/4: YAML — skipped (no staged *.yaml / *.yml)"
  fi
}

run_bundle_import_checks() {
  info "📦 Block 1 — stage 3/4: bundle imports — running \`hatch run check-bundle-imports\`"
  if hatch run check-bundle-imports; then
    success "✅ Block 1 — stage 3/4: bundle import boundaries passed"
  else
    error "❌ Block 1 — stage 3/4: bundle import boundary check failed"
    exit 1
  fi
}

# Parity with CI quality job (.github/workflows/pr-orchestrator.yml: hatch run lint).
run_lint_if_staged_python() {
  if ! has_staged_python; then
    info "📦 Block 1 — stage 4/4: lint — skipped (no staged *.py / *.pyi)"
    return 0
  fi
  info "📦 Block 1 — stage 4/4: lint — running \`hatch run lint\` (ruff, basedpyright, pylint)"
  if hatch run lint; then
    success "✅ Block 1 — stage 4/4: lint passed"
  else
    error "❌ Block 1 — stage 4/4: lint failed (matches CI quality gate)"
    warn "💡 Run: hatch run lint"
    exit 1
  fi
}

run_code_review_gate() {
  local review_array=()
  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    review_array+=("${line}")
  done < <(staged_review_gate_files)

  if [ ${#review_array[@]} -eq 0 ]; then
    info "📦 Block 2 — stage 2/3: code review — skipped (no staged paths under packages/, registry/, scripts/, tools/, tests/, or openspec/changes/)"
    return
  fi

  local enforcement="${SPECFACT_CODE_REVIEW_ENFORCEMENT:-changed}"
  info "📦 Block 2 — stage 2/3: code review — running \`hatch run python scripts/pre_commit_code_review.py\` (${#review_array[@]} path(s), enforcement=${enforcement})"
  if hatch run python scripts/pre_commit_code_review.py "${review_array[@]}"; then
    success "✅ Block 2 — stage 2/3: code review gate passed"
  else
    error "❌ Block 2 — stage 2/3: code review gate failed"
    warn "💡 Fix blocking review findings or run: hatch run python scripts/pre_commit_code_review.py <paths>"
    exit 1
  fi
}

run_requirements_evidence_gate() {
  if ! has_staged_active_openspec_source; then
    info "📦 Block 2 — stage 1/3: Requirements evidence — skipped (no staged active OpenSpec source)"
    return 0
  fi
  local report_path=".specfact/reports/requirements-evidence.json"
  local summary_path=".specfact/reports/requirements-evidence.md"
  mkdir -p "$(dirname "${report_path}")"
  info "📦 Block 2 — stage 1/3: Requirements evidence — running the module adapter against the staged Git index"
  if PYTHONPATH=packages/specfact-project/src:packages/specfact-requirements/src hatch run python scripts/requirements_evidence_gate.py --staged --required-maturity planned --output "${report_path}" --summary "${summary_path}"; then
    success "✅ Block 2 — stage 1/3: Requirements evidence passed (${report_path})"
  else
    error "❌ Block 2 — stage 1/3: Requirements evidence failed; report retained at ${report_path}"
    warn "💡 Review ${summary_path}, fix the source or requirements-evidence.yaml sidecar, then re-stage the change."
    exit 1
  fi
}

run_contract_tests_visible() {
  info "📦 Block 2 — stage 3/3: contract tests — running \`hatch run contract-test-status\`"
  if hatch run contract-test-status > /dev/null 2>&1; then
    success "✅ Block 2 — stage 3/3: contract tests — skipped (contract-test-status: no input changes)"
  else
    info "📦 Block 2 — stage 3/3: contract tests — running \`hatch run contract-test-contracts\`"
    if hatch run contract-test-contracts; then
      success "✅ Block 2 — stage 3/3: contract-first tests passed"
      warn "💡 CI may still run the full quality matrix"
    else
      error "❌ Block 2 — stage 3/3: contract-first tests failed"
      warn "💡 Run: hatch run contract-test-contracts"
      exit 1
    fi
  fi
}

run_block1_format() {
  warn "🔍 modules pre-commit — Block 1 — hook: format (1/4)"
  print_block1_overview
  run_format_safety
}

run_block1_yaml() {
  warn "🔍 modules pre-commit — Block 1 — hook: YAML (2/4)"
  run_yaml_lint_if_needed
}

run_block1_bundle() {
  warn "🔍 modules pre-commit — Block 1 — hook: bundle imports (3/4)"
  run_bundle_import_checks
}

run_block1_lint() {
  warn "🔍 modules pre-commit — Block 1 — hook: lint (4/4)"
  run_lint_if_staged_python
}

run_block2() {
  warn "🔍 modules pre-commit — Block 2 — hook: review + contract tests"
  run_command_overview_validation_gate
  run_core_documentation_accountability_gate
  run_docs_site_validation_gate
  run_prompt_command_validation_gate
  run_requirements_evidence_gate
  if check_safe_change; then
    success "✅ Safe change detected — skipping Block 2 (code review + contract tests)"
    info "💡 Only docs, workflow, version, or pre-commit metadata changed"
    exit 0
  fi
  print_block2_overview
  run_code_review_gate
  run_contract_tests_visible
}

run_all() {
  warn "🔍 Running full modules pre-commit pipeline (\`all\` — manual or CI)"
  print_block1_overview
  run_format_safety
  run_yaml_lint_if_needed
  run_bundle_import_checks
  run_lint_if_staged_python
  success "✅ Block 1 complete (all stages passed or skipped as expected)"
  run_command_overview_validation_gate
  run_core_documentation_accountability_gate
  run_docs_site_validation_gate
  run_prompt_command_validation_gate
  run_requirements_evidence_gate
  if check_safe_change; then
    success "✅ Safe change detected — skipping Block 2 (code review + contract tests)"
    info "💡 Only docs, workflow, version, or pre-commit metadata changed"
    exit 0
  fi
  print_block2_overview
  run_code_review_gate
  run_contract_tests_visible
}

usage_error() {
  error "Usage: $0 {block1-format|block1-yaml|block1-bundle|block1-lint|block2|all} (also: -h | --help | help)"
  exit 2
}

show_help() {
  echo "Usage: $0 {block1-format|block1-yaml|block1-bundle|block1-lint|block2|all}" >&2
  echo "Help aliases: -h, --help, help" >&2
  exit 0
}

main() {
  case "${1:-all}" in
    block1-format)
      run_block1_format
      ;;
    block1-yaml)
      run_block1_yaml
      ;;
    block1-bundle)
      run_block1_bundle
      ;;
    block1-lint)
      run_block1_lint
      ;;
    block2)
      run_block2
      ;;
    all)
      run_all
      ;;
    -h|--help|help)
      show_help
      ;;
    *)
      usage_error
      ;;
  esac
}

main "$@"
