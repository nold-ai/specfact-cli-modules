---
layout: default
title: Code Review bundle overview
nav_order: 2
permalink: /bundles/code-review/overview/
keywords: [code-review, bundle, overview, review, quality]
audience: [solo, team, enterprise]
expertise_level: [beginner, intermediate]
---

# Code Review bundle overview

The **Code Review** bundle (`nold-ai/specfact-code-review`) extends the shared **`specfact code`** command group with **`review`** workflows: governed review runs, **reward ledger** history, and bundled code-review skill management through the **`rules`** command.

Use it together with the [Codebase](/bundles/codebase/overview/) bundle (`import`, `analyze`, `drift`, `validate`, `repro`) on the same `code` surface.

## Prerequisites

- `specfact module install nold-ai/specfact-code-review` — the manifest `bundle_dependencies` list includes **`nold-ai/specfact-codebase`**, so SpecFact CLI **will automatically install** the Codebase bundle alongside this one for the full shared **`specfact code`** command surface (import, analyze, drift, and related commands live there).
- Signed capsule execution requires Linux x86-64 with Python 3.11, 3.12 or 3.13 and permission to create unprivileged user namespaces. Analyzer dependencies come from the verified capsule.

The 0.51.0 development change includes a native macOS ARM64 backend candidate.
Its locally assembled, ad-hoc-signed test artifacts run on a physical ARM64
Mac, but the official native catalogs remain empty pending boundary, external
project, supported-OS and customer-installation acceptance. The released module
does not yet provide automatic macOS capsule installation. On macOS, missing
native artifacts produce incomplete review evidence rather than running tools
from the developer host. See the
[native platform change](https://github.com/nold-ai/specfact-cli-modules/issues/460)
for the current delivery gate. Module signing occurs in the protected CI/CD PR
follow-up; customers do not need an Apple Developer ID.

The current pip candidate derives dependencies from the selected project,
builds its root wheel in a confined worker and uses pinned pip for wheel
resolution and offline installation. Customer projects do not need publisher
catalog entries. Ambiguous `runtime inspect --json` results identify candidate
setups and required caller configuration; explicit `--project-config` selects
the setup. Controlled native projects also use authentic pinned Hatch, uv and
Poetry. The complete upstream corpus and distribution acceptance remain pending;
the candidate does not yet establish general macOS support.
Pinned upstream projects for all four managers now prepare cold and reuse their
private environments offline. On the physical CPython 3.11 candidate, selected unchanged upstream source/test
slices execute all ten analyzers with pytest PASS, including parallel workers
and the selected project plugins. Local doctest/coverage compatibility retains
project-origin provenance and cannot authorize protected range evidence. A controlled project with automatic discovery,
pytest coverage and a native extension executes all ten analyzers successfully.
Matching OS/architecture VMs qualify for acceptance under the same sandbox
requirements as physical machines. Local x86-64 emulation on Apple Silicon
supplements matching-architecture Linux CI acceptance.

## Capsule setup and troubleshooting

Install the released core and official module into user-owned locations, then run the review from your repository:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install specfact-cli
specfact module install nold-ai/specfact-code-review --scope user
specfact code review run --scope full --enforcement full --bug-hunt --json --out review.json
```

The runtime is downloaded anonymously on the first run. `SPECFACT_CODE_REVIEW_CAPSULE_CACHE` selects a user-owned cache location; the default is `~/.cache/specfact/code-review/capsules`. A complete three-Python cold pass downloads approximately 0.78 GB of compressed runtime layers, excluding installation dependencies. Warm runs verify cached identities before reuse.

Ubuntu 24.04 can restrict unprivileged user namespaces through AppArmor. A namespace diagnostic requires administrator review of the host policy. The repository's `capsule-customer-execution` workflow installs a narrowly scoped profile for its temporary cache's `**/opt/specfact/bin/bwrap-static` launcher path, granting `userns` permission while keeping the global restriction enabled. An administrator can adapt that attachment to the customer's actual cache path under the organization's policy. See [Ubuntu's AppArmor guidance](https://documentation.ubuntu.com/security/security-features/privilege-restriction/apparmor/) (checked 2026-09-12). Installation and analyzer execution must still run as the ordinary user; do not solve this by running SpecFact with sudo, disabling host protections, or running analyzers outside the capsule.

Capsule setup and integrity failures remain `UNKNOWN` with a failing exit. Preserve the JSON report, module/core versions, Python ABI, cache identity and the launch diagnostic. Namespace failures identify the denied capability; filesystem launch failures retain the path context; final-root integrity failures show expected and actual digests and entry counts. Do not edit sealed files or replace expected hashes with observed values. To diagnose corruption, retain the failing evidence and retry in a new empty user-owned cache; keep the original cache available for comparison.

Full scope inventories the complete pytest suite. Explicit-file and worktree reviews select reviewed tests or unambiguous corresponding tests for the selected source files; unrelated test suites are not run. If the required test selection cannot be established, pytest evidence is `UNKNOWN` and the review fails, while independent static analyzer results remain available. Linux retains the explicit `--no-tests` control. The macOS ARM64 candidate requires pytest for a complete local review, so `--no-tests` yields `UNKNOWN`. Native pytest results are labeled `project-origin-v1`: project tests and plugins can influence their own reported outcomes. Protected range reviews reject that provenance pending an explicit consumer compatibility change.

The persistent CI matrix separates candidate-source checks on pull requests from public signed-installation checks after release/registry publication or manual dispatch. It requires all ten analyzer members to execute on controlled clean and defective fixtures and on an exact-commit source/test slice of this repository. Skips, empty evidence and `UNKNOWN` fail the gate. A passing candidate run does not constitute signed-release acceptance; repeat the public matrix after canonical signing and publication before closing the bug.

## `specfact code review` — nested commands

| Command | Purpose |
|--------|---------|
| `run` | Execute a governed review (scope, JSON output, `--fix`, TDD gate, etc.) |
| `ledger` | Inspect and update review reward history |
| `rules` | Manage the bundled code-review skill (`show`, `init`, `update`) |

### `ledger` subcommands

| Subcommand | Purpose |
|------------|---------|
| `update` | Update ledger entries |
| `status` | Show ledger status |
| `reset` | Reset ledger state |

### `rules` subcommands

| Subcommand | Purpose |
|------------|---------|
| `show` | Show current rules configuration |
| `init` | Initialize rules/skill assets |
| `update` | Update rules content |

## Bundle-owned skills and policy packs

House rules and review payloads ship **inside the bundle** (for example Semgrep
packs, the `specfact/clean-code-principles` policy-pack manifest, and the
`specfact-code-review` skill). They are **not** core CLI-owned resources. Use
`specfact code review rules init --ide codex` or the matching IDE target to
install the reusable skill instead of copying prompt templates by hand.

## Quick examples

```bash
specfact code review run --help
specfact code review ledger status --help
specfact code review rules show --help
```

## See also

- [Code review run](../run/)
- [Code review ledger](../ledger/)
- [Code review rules](../rules/)
- [Code review module](/modules/code-review/)
- [Codebase bundle overview](/bundles/codebase/overview/) — import, drift, validation, repro

For a verified warm-cache check, set `SPECFACT_CODE_REVIEW_CAPSULE_OFFLINE=1`. Capsule acquisition then revalidates cached descriptors and refuses missing entries without downloading replacements. Use a complete cache from a prior successful cold run; this does not disable the analyzer sandbox or weaken signature checks.
