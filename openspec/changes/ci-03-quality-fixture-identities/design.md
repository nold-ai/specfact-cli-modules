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


## Structured failure diagnostics for PR 519

The maintainer needs the failing snapshot side and any recognized error class from the existing independent review failure. Exact-head run 39167860375 reports contracts error and UNKNOWN with an unclassified structured report. The actual contract fault remains unidentified. The public artifact contains no failed-review report.

Reuse the existing validated `evidence_source`, `incomplete_sides` and `crosshair_failure_observations`. Minimal adaptation removes only the report-size restriction on the two diagnostic fields. A separate parser or new classifier would add maintenance without improving this bounded observation. The data shape remains an allowlisted analyzer-to-side map and a list of fixed class names. Structured output keeps its existing status, findings and enforcement semantics. Oversized output retains unavailable status and its header observation.

The first milestone executes the actual embedded workflow projector against structured private fixtures and proves bounded output, privacy and validation behavior. It does not establish a contracts fix or hosted review success. Runtime, dependencies, security capabilities, signatures, thresholds, required checks, timeouts, the orchestrator byte pin and planning changes are outside scope. Reverting this diagnostic addition restores the prior projection. Runtime cost is bounded by the existing ten analyzer rows and ten thousand finding rows; elapsed cost has not been measured.


## Caller-selected immutable local policy (2026-10-19)

PR review 4308833955 demonstrates that a candidate can update both indexed workflow bytes and the digest in the candidate-owned checker. The caller must select an independently inspected full commit SHA and an absolute external host Python executable. Those two explicit environment strings are the entire new data shape. The existing checker is reused unchanged from that commit; a private shell subshell extracts it with replacement objects disabled and runs it with isolated, no-site Python from the candidate repository root. Extraction and execution failures refuse eligibility, with temporary-file cleanup and no fallback.

Reuse of the mutable working-copy checker cannot satisfy this boundary. The minimal adaptation is one private shell function at its existing invocation. An installed hook, protected bootstrap, trust store or external policy service would invent authority and maintenance outside the approved workflow. This selection records caller review only, not owner acceptance, protected-branch policy or independence from a caller who can edit or bypass hooks. Candidate hook/control changes still need independent review, and exact-head Linux candidate and independent signed review remain blocking.

The initial caller-reviewed source is commit `413f8f1211222eb7d2a15d530d86f8423234adff`, checker blob `ec30685c4755e4d0f78faf3bc88fe292b022fb79`, with the existing orchestrator digest unchanged. It is an explicit invocation input, never a default in code. A new policy selection requires caller inspection. Tests use disposable Git commits and real indexes with an external host interpreter. Reverting the private function and its call restores the mutable-checker vulnerability. No runtime, package, dependency, workflow-policy or forge authority changes are included.


### External interpreter location guard (2026-10-19)

Review 4311300796 exposed an executable-location gap. An absolute executable path could still select candidate `.venv/bin/python`, whose successful exit skipped the immutable checker. The existing two caller-selected strings remain the data shape. Resolve the repository with physical `pwd`, the selected interpreter parent with physical `cd` and `pwd`, and its target with native `realpath` before executing that interpreter. Refuse either location inside the candidate repository, including checkout aliases, parent-directory links and external links into the checkout. Execute the resolved external target. A legitimate external symlink remains supported; resolution failure refuses deferral.

Absolute-path validation alone reproduced the bypass. This small shell adaptation reuses host tools without adding a Python bootstrap, installed policy service or signature authority. The local caller and host tools remain trusted. Concurrent hostile filesystem replacement and a caller who edits the hook are outside that boundary. Exact-head hosted checks and the unchanged reviewed workflow pin remain mandatory. This safeguards the already approved local deferral, which is now stated consistently in CHANGE_ORDER. Revert these shell location checks to roll back this repair; doing so restores the reproduced bypass.


## Projection fixture host boundary (2026-10-19)

The actual candidate reports 31 FileNotFoundError cases in four Bash-launching projection tests. Running those same cases with a PATH without Bash reproduces all 31 failures locally; the private hosted missing filename remains unknown. Preserve these cases in an explicitly invoked host proof alongside existing mandatory host proofs. Keep the remaining 200 Python projection cases in ordinary unit discovery. Split private report and public diagnostic tests by behavior to satisfy the existing module-length check, and share only pure fixture helpers.

Reusing the existing host stage is the minimal adaptation. Skipping tests loses coverage; adding shell capability or custom infrastructure changes runtime trust assumptions. Neither is in scope. Preserve cases, decorators and assertions through the move, then separately document necessary fixture complexity and lint cleanup. All resulting files remain analyzer inputs. Exact-head independent timeout remains unresolved and no local pass substitutes for hosted acceptance. Rollback restores the original fixture ownership and removes the extra host invocation.


## Portable host path resolution (2026-10-19)

This section supersedes the native `realpath` command choice in the earlier external-interpreter guard. It preserves that guard's domain and both exclusions. Review 4312183015 and the full-hook control reproduce an otherwise eligible selection changing from DEFERRED exit zero to refusal when only `realpath` is unavailable. No new minimum macOS version is introduced.

The selected shape is one private Bash resolver, `_resolve_host_executable_path(absolute_path)`, used unconditionally. It emits the physical absolute executable target without a separator, or refuses. The existing caller keeps responsibility for the initial physical selected directory and final target being outside the candidate repository. It invokes the selected interpreter only after both checks, immutable commit/blob checks and the existing temporary checker preparation.

Resolve the physical parent at every symlink hop. Rebase relative link targets on that parent, preserve absolute targets, and use a bounded 40-hop traversal. Retain the existing initial regular-file/executable precondition and require a final executable regular file. Host directory resolution and `readlink -n` failures propagate as refusal. Capture path data and the helper result with successful terminal sentinels so shell command substitution cannot trim meaningful trailing newlines. The caller removes exactly its sentinel. No selected Python runs as its own location probe.

Three independent model sketches and an independent cross-judge selected the shell shape. A protected Perl/Cwd helper would reuse a native library but add unproven runtime availability and module-loading trust requirements. Retaining realpath, installing coreutils or adding a second resolver backend fails the bounded outcome. The Bash shape reuses existing host primitives and has one policy owner. The full-hook fixture already loads the helper.

The cross-judge observed that plain BSD readlink does not always append a new newline to an already newline-ending target. Removing a presumed separator corrupts such data. `readlink -n` plus sentinel capture avoids that ambiguity. Apple's historical file_cmds-321.100.11 manual documents that option: <https://raw.githubusercontent.com/apple-oss-distributions/file_cmds/file_cmds-321.100.11/stat/stat.1>, accessed 2026-10-19. The upstream macOS 12 report is <https://github.com/astral-sh/uv/issues/13807>. These sources and current-host primitive tests are not native macOS 11/12 execution acceptance.

Proof must exercise the complete existing hook with realpath absent, actual disposable Git indexes, legitimate external paths and links, physical directory aliases, exact pathname identity, and candidate-interpreter canaries. Keep policy, import, Git replacement and cleanup proofs. Current native stat preconditions accepted 32-link chains and rejected 33 on the measured Darwin host; the 40-hop helper bound does not narrow that observed domain. Supported-host limits and mandatory hosted checks remain acceptance work. No hostile concurrent filesystem containment, capsule runtime, dependency, workflow pin, timeout or authority change is claimed. Rollback restores the prior fail-closed missing-command refusal.
