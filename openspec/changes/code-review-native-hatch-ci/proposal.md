# Native CI for the first Hatch milestone

## Why

The owner asked to continue the corrected native implementation on 2026-10-25. The existing/cold detached Hatch workflow is already implemented and proved locally. Hosted quality currently waits for the superseded capsule prerequisite and does not configure the native acceptance cell. Add the missing native execution evidence without repairing capsules or waiving an existing gate.

## What changes

Run change 17's exact executable test mapping in a mandatory, read-only Linux job against the pull-request head. Provision the already proved Python 3.12.13 controller, Python 3.11.15 project interpreter and Hatch 1.18.1 separately. Use the repository's existing Hatch controller environment and pinned core dependency. Require every mapped test exactly once, with no skips, errors or failures. Preserve the real native receipt and JUnit as ordinary CI artifacts.

The existing required quality jobs consume this result. Existing module signing and independent security requirements remain unchanged and blocking. This is additional native acceptance, not a transfer of security-test ownership or the replacement CI cutover. No capsule code, runtime API, manager support, public reviewer adoption, release or archive is changed.

## Capabilities

### New capabilities
- `native-hatch-ci`: mandatory exact-head execution of the already approved first Hatch acceptance.

### Modified capabilities
None.

## Scope and alternatives

Reuse the mapped tests and existing reusable-workflow/required-prerequisite pattern. More local reruns cannot establish hosted native acceptance. A new runtime adapter or generic CI framework is unnecessary. Moving security cases or removing capsule gates would change acceptance ownership and is excluded. Native Hatch script/context fidelity remains a separate pending runtime unit.

This continues #513's existing takeover and first-milestone scope. Rollback is a reviewed revert. The check grants no protected `pr_range`, C15 or installed-release authority.
