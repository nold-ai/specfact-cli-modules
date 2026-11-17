# Native PR CI transition

## Why

The maintainer explicitly authorized advancing the CI/security transition before merging PR #524 on 2026-10-25, Europe/Berlin. Capsule repairs remain excluded. Earlier instructions to defer this transition are superseded only for repository CI. The customer runtime sequence 17 → 18 → 19 → paired core → 20 remains separate.

## What changes

Replace the required capsule customer prerequisite with exact-head native acceptance and an independently installed signed reviewer. Preserve the complete ten-member review inventory, contracts, test coverage, changed enforcement, module signatures and the existing quality matrix. Missing tools, errors, unknown evidence, missing rule packs and stale source remain nonaccepting. Run the existing shell/security and native Hatch cases in mandatory native CI. Move the retained customer-gate test file to native CI ownership, preserving all 44 other functions and migrating only its two orchestrator prerequisite tests.

The CI adapter reuses signed reviewer 0.51.2 and core 0.55.4. It does not change the public review dispatcher, introduce a backend selector, publish a release, or produce protected pr_range, core #680 or C15 assurance. Native execution retains the approved non-adversarial project assumption. Dependency installation, hooks, imports and tests execute in a credential-free disposable runner. No hostile-code containment is claimed.

## Capabilities

### New capabilities
- `native-pr-ci`: complete, independent, exact-head native repository review.

### Modified capabilities
None.

## Alternatives and rollback

A prerequisite deletion or static-only scan drops existing obligations. Bare run_review returned exit zero with a CrossHair UNKNOWN in a real probe and cannot own acceptance. Reuse the existing signed adapters behind one CI completeness barrier. Rollback restores the previous prerequisite through a reviewed revert and restores its blocking outcome.

## CI prerequisite correction on 2026-11-17

The maintainer authorized fixing both setup failures and rerunning the full workflow without merging. Attempt 2 failed before signature and reviewer acceptance because no public-key secret was configured and newly resolved Typer 0.29.1 removed an API used by released core 0.55.4. Resolve the existing public key from trusted event history and constrain only the independent controller to the already committed Typer 0.27.0. Keep all existing security, signing, quality and independent-review obligations.

The fresh full run cleared both setup failures and then exposed a required command-overview compatibility defect. Current Typer argument objects no longer expose the display-name property used by the generator. Preserve existing generated labels through the supported argument interface, with a failing-first proof and exact-head review. GitHub account key registration and missing Actions signing secrets remain separate authority/configuration decisions; no signing policy change is authorized by this correction.
