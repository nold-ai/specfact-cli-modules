## Audit Evidence

- Captured mounted root command surface with `hatch run specfact --help`
- Captured mounted subcommand surfaces with:
  - `hatch run specfact backlog --help`
  - `hatch run specfact code --help`
  - `hatch run specfact code validate sidecar --help`
  - `hatch run specfact code repro --help`
  - `hatch run specfact code review --help`
  - `hatch run specfact govern --help`
  - `hatch run specfact govern enforce --help`
  - `hatch run specfact project --help`
  - `hatch run specfact project sync --help`
  - `hatch run specfact project sync bridge --help`
  - `hatch run specfact spec --help`
  - `hatch run specfact module install --help`
  - `hatch run specfact module init --help`
  - `hatch run specfact module list --help`
  - `hatch run specfact module uninstall --help`
- Cross-checked official module ids from `packages/*/module-package.yaml`

## Verification Evidence

- Verified explicit mode examples with:
  - `hatch run specfact --mode cicd module list`
  - `hatch run specfact --mode copilot module list`
- Verified `code import` example syntax with:
  - `hatch run specfact code import --repo . --shadow-only my-project`
  - Command started successfully and accepted the updated option ordering
- Verified OpenSpec change validity with:
  - `openspec validate docs-cli-command-alignment --strict`
- Verified edited-file stale pattern cleanup with:
  - `rg -n -- '--write|--dry-run|--budget|specfact hello|import from-code|specfact/(backlog|codebase|project|spec|govern)|backlog-core' ...`
- Verified runnable example cleanup across docs with:
  - `rg -n "^specfact (plan|generate|contract|sdd|sync|repro|validate|enforce|analyze|drift|review)\b|^hatch run specfact (plan|generate|contract|sdd|sync|repro|validate|enforce|analyze|drift|review)\b|^uvx specfact-cli@latest (plan|generate|contract|sdd|sync|repro|validate|enforce|analyze|drift|review)\b" docs -g '*.md'`
  - Final scan returned no remaining runnable examples using removed top-level command groups
- Replaced legacy workflow pages that could not be mapped to current mounted public commands with explicit legacy notes and current `--help` entrypoints, to keep the docs aligned without inventing unsupported replacements
- Note: `openspec` emitted non-blocking PostHog network errors in the sandboxed environment after successful command completion
