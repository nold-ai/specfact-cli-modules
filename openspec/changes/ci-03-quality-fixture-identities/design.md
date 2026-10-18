# Quality workflow input selection

The user is the maintainer running candidate modules quality gates. Three identities have different purposes. The dynamically selected paired core owns integration checks. Immutable core 0.55.4 owns the declared-baseline full suite. The modules commit and tree in the paired core's `ci/runtime-smoke-fixture.lock.json` own installed discovery smoke.

Reuse the existing checkout action and the paired core composite action's validation pattern. Calling that composite directly assumes repository-root paths that do not fit the nested paired checkout. A small inline adaptation preserves the same clean Git identity check without a new helper or runtime interface. Custom fixture infrastructure would add maintenance without improving this bounded repair.

The baseline is commit `d579970565530c3fd7b98bad4de90cf874c2a99d`, tree `f49667f21e4a20a432ad80032a01a5c6894b0c91`, from v0.55.4. `ensure_core_dependency` reinstalls its selected checkout, so the full suite needs a step-scoped `SPECFACT_CLI_REPO` override. The paired export remains the job default. Baseline checkout occurs after all candidate formatting and lint gates, immediately before the full suite.

The smoke lock is trusted only after repository and full SHA validation. Checkout is credential-free in `runtime-smoke-modules`, beside `specfact-cli`. Verify commit, tree and clean status before passing the absolute path to the unchanged smoke verifier. The current reviewed lock is commit `046d366c190af7a188d6f48953a96edb65e766db`, tree `c5b44db3477d1c9ea8dae1dceab2af276d265353`. The verifier retains authority to reject other snapshots. After verification, move the smoke fixture to `$RUNNER_TEMP/runtime-smoke-modules` before exporting its absolute path. This keeps historical fixture code outside candidate formatting and lint traversal without changing lint scope.

This is one workflow repair with no paid service or new runtime. Additional checkout cost is bounded to one baseline checkout per matrix job and one smoke fixture checkout on Python 3.12; elapsed CI cost has not been measured. A missing or malformed lock fails before checkout, a changed fixture fails identity verification, and a drifting baseline fails its pinned commit/tree check. Revert this change to roll back the workflow wiring; that also restores the diagnosed failures. Hosted Linux acceptance remains required.

## Approved local eligibility alignment

The maintainer approved this bounded addition on 2026-10-18 (Europe/Berlin). Reuse the existing deferral mechanism with one extra path, `.github/workflows/pr-orchestrator.yml`. Leaving the mechanism unchanged rejects the already-scheduled orchestrator-only candidate; custom review infrastructure would exceed the approved scope. The eligibility input remains a staged candidate delta against the merge-base with origin/dev. Preserve local ARM64 Darwin, explicit opt-in, feature worktree, indexed blocking candidate review and independent signed-review checks. Preserve the DEFERRED warning and every other Block 2 check.

A disposable Git worktree containing an orchestrator-only candidate must pass eligibility and retain all other Block 2 checks. CI, Linux, invalid opt-in, missing or only unstaged-restored independent review, and unrelated workflow changes must remain rejected. This is local eligibility evidence; it does not prove hosted review success. Revert the single added path to roll back this extension. No dependency, signature, runtime, workflow trigger or enforcement changes are part of this addition.

## Indexed scheduling correction for PR 519

The reported bypass was reproduced on 2026-10-18. A candidate could stage an orchestrator that disabled capsule scheduling while retaining the reusable workflow names, and the hook still reported DEFERRED. This correction preserves the approved all-checks-intact scope.

Reuse the existing PyYAML dependency at one Git-index boundary. Compare the parsed pull-request trigger, change detection and reusable workflow call with the currently supported routing contract, and require the quality job's dependency, condition and first blocking prerequisite. Parse the nested path-filter YAML as data. Keep exact known shell bodies and expressions rather than interpreting arbitrary Actions expressions or shell programs. Workflow-level defaults are unsupported because inherited shell or working-directory settings can alter the otherwise matched routing steps. Reject the defaults key rather than evaluate overrides. Unknown routing fails local deferral with an actionable diagnostic. This is a local eligibility contract; mandatory hosted exact-head review remains the authority over execution.

A filename check cannot establish scheduling. A general Actions evaluator would add unnecessary maintenance. The closed contract needs deliberate review when these protected routing sections change; unrelated quality steps remain outside that comparison. The existing platform, worktree, opt-in, indexed reusable-review and merge-base guards remain in place. Capsule-payload candidates use the same indexed routing check. Restoring only the unstaged working copy cannot repair a staged bypass.

Verification uses the maintained host proof and real disposable Git indexes. Tests retain all existing Block 2 trace assertions. No workflow, runtime, dependency declaration, signed asset, version, or public planning scope changes. Reverting the hook call and validator restores the prior local behavior, including the reproduced bypass.


### Reviewed byte pin and host proof ownership (2026-10-18)

Independent review found the partial YAML contract left execution context unchecked.
The selected correction replaces that parser with one literal SHA-256 digest of
reviewed commit 59b1c048's entire orchestrator blob. The independently recomputed
digest is `827e26667ef9951783bfeaffebca5833e1e16a90151676b164b88d303f7ac371`.
The input is raw indexed bytes. No expected value is derived from the candidate.
Any byte change, including comments, conservatively refuses local deferral until
an explicit pin update is reviewed. Existing platform, worktree, branch and
independent-review guards remain applicable, as does hosted exact-head acceptance.
This removes partial Actions semantics rather than extending a custom interpreter.

The twelve Bash-spawning quality fixture proofs belong in a host-only proof file,
explicitly included in the default Hatch test command before the ordinary suite.
Static workflow checks and a host-schedule assertion remain capsule-compatible unit
checks. Runtime capabilities, namespace policy and dependencies are unchanged.
Public hosted records identify failing test nodes but redact private tracebacks;
FileNotFoundError attribution requires separate local reproduction, not inference
from those public records alone.
