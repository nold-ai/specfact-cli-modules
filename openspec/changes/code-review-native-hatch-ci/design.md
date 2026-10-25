# Native Hatch acceptance in CI

The existing change-17 Requirements sidecar owns the executable selector list. The CI program reads its test cases, invokes pytest with executable-first argv and verifies the emitted JUnit selector properties against that exact list. An empty or duplicate mapping, missing report, missing/extra/duplicate observed selector, skipped case, error, failure or nonzero pytest exit cannot pass. Planning inspections are not executable acceptance.

Use the active change mapping when present. After normal OpenSpec archival, resolve exactly one dated archive directory for the same change identity. Multiple archived candidates are an explicit failure. This preserves one mapping owner through its lifecycle without copying or synchronizing another selector list.

Use one Ubuntu job and the existing reusable-workflow pattern. Checkout explicitly selects the event's pull-request head, with full history and no persisted credentials. Setup actions provision the two Python installations separately. Native Hatch is installed into the controller's external installation; the target project receives only its declared dependencies through the existing service. The workflow sets all three existing native acceptance inputs before executing the mapping. Its receipt and JUnit live outside the checkout in invocation-owned runner storage.

The data shapes are the mapped selector list and observed JUnit selector list. Set equality plus equal lengths establishes exact once-only execution. Existing pytest return codes and adverse testcase elements retain their meaning. The inline acceptance program belongs to this workflow; tests execute that same program through a disposable pytest-output producer to exercise outcome validation. The actual hosted run separately proves native execution.

Add a required native acceptance prerequisite to the existing quality matrix without editing its existing signature/customer-capsule step. The native job has no capsule dependency. Its result does not waive or satisfy independently owned security work. No custom runner framework, manager bridge, product option or new signed module payload is introduced.
