# Enforce the approved native review migration

## Why

The owner approved trusted local native execution on 2026-10-16. During #513, the agent repeatedly returned to capsule diagnostic repairs and then offered capsule expansion as an option. The owner corrected this again on 2026-10-25 and explicitly requested an enforced correction, OpenSpec/TDD, the native Hatch milestone and identification of the CI transition. Existing prose did not prevent this regression.

## What changes

Add a native-only scope ratchet to the existing local import-boundary check and a separate lightweight CI job. A machine-readable policy freezes known legacy capsule implementation, tooling, workflow and test surfaces at signed head `23967ee8dc22545935427cd737b418e5b21198e5`. Existing content and retirement deletions remain allowed; additions and edits fail with an actionable native-owner message. The check also rejects an alternative execution direction. Prove rejection against an actual earlier capsule diagnostic commit.

Re-run the existing native Hatch acceptance through the Codebase project boundary. Record its actual result and the exact legacy CI dependency that requires an approved migration transition. Preserve signing, independent security and all adverse gate outcomes. Do not repair capsules, reroute the 37 legacy-sensitive tests or bring forward ordinary reviewer cutover.

## Capabilities

### New capabilities
- `native-review-migration-scope`: enforce native-only implementation ownership while retaining historical capsule evidence and retirement.

### Modified capabilities
None. This unit does not grant protected review authority or change customer runtime behavior.

## Scope and alternatives

Reuse the existing mandatory local boundary stage and add one small standard-library checker with one policy owner. More prose alone failed. Removing the old runtime now would prematurely implement changes 19/20. A capsule repair or a second backend contradicts the confirmed direction. A narrow ratchet is the smallest enforceable correction before cutover.

User and outcome remain #513's trusted developer-owned repository and first existing/cold detached Hatch workflow, with customer, controller and analyzer dependencies separate. The current task authorizes this governance correction; it does not authorize a new hostile-code runtime, other managers or publication. Existing #513 ownership/takeover is reused. Parent #163, project/labels and downstream #514/#515 remain unchanged.

No signed module payload changes are planned. Completion requires genuine RED before checker implementation, GREEN for rejection and preservation controls, a real historical rejection, the same checker locally/CI, native workflow execution and applicable gates/review. The ratchet prevents changes on its classified surfaces; it cannot prove that an arbitrary renamed implementation or agent prose is correct. Independent review remains required.

Rollback is a reviewed revert, never a force push or silent gate bypass. No merge or archive is authorized.
