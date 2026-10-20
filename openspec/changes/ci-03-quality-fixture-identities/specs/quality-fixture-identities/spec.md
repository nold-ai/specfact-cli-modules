## ADDED Requirements

### Requirement: Full suite selects the declared core baseline

The quality workflow SHALL retain the dynamic paired core for its existing integration checks and SHALL give only the existing full suite an independent immutable core 0.55.4 checkout. The baseline checkout SHALL occur after candidate formatting and lint gates. The workflow SHALL verify that checkout's commit and tree before use and SHALL retain the exact `hatch run test` command and unconditional declared dependency assertion.

#### Scenario: Full suite overrides the paired default

- **GIVEN** a quality job with a dynamically selected paired core
- **WHEN** the Full Test Suite step executes
- **THEN** its step-scoped dependency path selects verified core 0.55.4 and preceding paired checks retain the paired core path.

### Requirement: Installed smoke selects the reviewed modules fixture

The workflow SHALL read the paired core smoke fixture lock, require repository `nold-ai/specfact-cli-modules` and full commit/tree SHA identities, and check out the fixture into a clean sibling directory with credentials disabled. It SHALL verify commit, tree and clean status before the existing smoke command receives the absolute fixture path. The verified smoke checkout SHALL move outside the candidate workspace before candidate formatting and lint gates. All six launchers SHALL remain enabled.

#### Scenario: Valid lock supplies the smoke checkout

- **GIVEN** a paired core with a valid smoke fixture lock
- **WHEN** fixture preparation and smoke execution run
- **THEN** the checkout uses the lock commit and the smoke receives the verified relocated path outside the candidate workspace with direct, hatch-source, pip-editable, pipx, uv-run and uvx launchers.

#### Scenario: Invalid lock is rejected

- **GIVEN** malformed JSON, a wrong repository, a missing identity or a non-full commit/tree identity
- **WHEN** fixture identity is read
- **THEN** preparation fails before emitting checkout outputs.

#### Scenario: Unauthenticated fixture is rejected

- **GIVEN** a checkout with a wrong commit, wrong tree or dirty status
- **WHEN** fixture verification runs
- **THEN** verification fails before exporting a smoke fixture path.

### Requirement: Approved orchestrator candidates retain guarded local deferral

The local quality hook SHALL include `.github/workflows/pr-orchestrator.yml` in its existing candidate-path eligibility check for an explicitly approved local ARM64 Darwin feature-worktree review deferral. It SHALL preserve all existing guard conditions, every other Block 2 check and the DEFERRED warning. Mandatory blocking exact-head Linux candidate and independent signed review SHALL remain required before merge. Deferral eligibility SHALL require the indexed orchestrator to preserve the supported pull-request trigger, capsule path detection and output, mandatory reusable workflow call, and blocking quality prerequisite. Unsupported routing SHALL reject local deferral. Workflow-level defaults SHALL be absent from the supported contract, including run shell and working-directory overrides.

#### Scenario: Orchestrator-only candidate defers local review

- **GIVEN** an explicitly approved local ARM64 Darwin feature worktree with indexed blocking candidate and independent review jobs
- **WHEN** the staged candidate delta against origin/dev changes the orchestrator workflow with accompanying regression tests and change evidence
- **THEN** the hook reports DEFERRED, never PASS, and executes the remaining Block 2 checks, including contracts.

#### Scenario: Orchestrator eligibility preserves rejection guards

- **GIVEN** an orchestrator candidate in CI, on Linux, with invalid opt-in, or without indexed independent review, including an unstaged restoration
- **WHEN** the local deferral is requested
- **THEN** the hook rejects the deferral; an unrelated workflow candidate also remains ineligible even if origin/dev advanced.

#### Scenario: Indexed orchestration preserves mandatory review scheduling

- **GIVEN** an otherwise eligible orchestrator or capsule-payload candidate
- **WHEN** indexed orchestration removes or disables the pull-request trigger, capsule filter/output, customer workflow call, or blocking quality prerequisite, or introduces workflow-level run defaults
- **THEN** the hook rejects deferral, including when an unstaged restoration repairs the working copy; only the indexed scheduling contract permits DEFERRED.

#### Scenario: Exact reviewed orchestration bytes authorize deferral

- **GIVEN** an otherwise eligible local worktree
- **WHEN** the indexed orchestrator differs by any byte from the reviewed workflow, including comments, quality containers, root or job environment, runners or defaults, or is absent
- **THEN** local deferral fails even if the working copy restores the reviewed bytes; a literal reviewed SHA-256 pin must be updated through review before any changed workflow is eligible.

### Requirement: Bash fixture proofs execute on the host

The default Hatch full test command SHALL explicitly execute the quality fixture identity host proof before the ordinary test suite. All seven lock validation cases and five checkout verification cases SHALL remain mandatory. Static workflow and host scheduling assertions SHALL remain in the unit suite. Capsule capabilities SHALL remain unchanged.

#### Scenario: Full tests retain the host proof

- **GIVEN** the default Hatch test entrypoint
- **WHEN** the quality fixture identity proofs run
- **THEN** the twelve Bash cases run on the host and the static unit assertion rejects removal of their explicit schedule.

### Requirement: Indexed schedule validation has capsule-safe coverage

The declared coverage sources SHALL include the qualified `scripts.validate_capsule_ci_schedule` module. Capsule-safe unit tests SHALL execute its byte validator and command entrypoint with the external Git read mocked. Reviewed bytes SHALL succeed; changed bytes and missing index entries SHALL return a refusal. Existing real Git index host proofs, coverage thresholds, exclusions and hosted review requirements SHALL remain intact.

#### Scenario: The native coverage adapter observes the schedule validator

- **GIVEN** the repository coverage policy and capsule-safe schedule unit tests
- **WHEN** pytest executes the tests and the portable coverage adapter evaluates the validator
- **THEN** coverage contains the validator and satisfies the existing per-source threshold without enabling subprocess capabilities.


### Requirement: Structured review failures retain bounded diagnostic observations

The independent review failure projector SHALL publish the existing allowlisted analyzer snapshot sides and CrossHair failure classes for complete structured reports as well as oversized reports. It SHALL derive these observations from the existing validated evidence source and preserve complete JSON validation, duplicate-key rejection, input bounds, private output handling, review status and exit behavior. It SHALL NOT publish raw messages, paths, tokens, command arguments or arbitrary analyzer identifiers.

#### Scenario: Structured contracts evidence identifies its incomplete side

- **GIVEN** a complete structured report with contracts error or UNKNOWN evidence
- **WHEN** the independent failure projector executes
- **THEN** it publishes only allowlisted incomplete snapshot sides and recognized CrossHair tool-error classes, with private canaries absent from stdout and stderr.

#### Scenario: Invalid or unrelated evidence cannot supply diagnostic classes

- **GIVEN** malformed or duplicate-key JSON, an unrelated tool or category, or an unknown failure message
- **WHEN** the independent failure projector executes
- **THEN** validation and allowlists prevent unsupported classifications and private output, while the existing oversized-report behavior remains bounded.


### Requirement: Local deferral executes caller-selected immutable policy

The existing local deferral hook SHALL require the trusted local caller to provide `SPECFACT_CODE_REVIEW_POLICY_COMMIT` as a full lowercase 40-character commit SHA and `SPECFACT_CODE_REVIEW_POLICY_PYTHON` as an absolute executable host Python path selected outside the candidate environment. It SHALL extract the existing schedule checker from that exact commit with Git replacement objects disabled, execute the nonempty blob from a private temporary directory with Python `-I -S`, preserve the candidate repository as working directory, and propagate refusal or execution failure. Missing or invalid selection, a non-commit object, unavailable checker blob, and Git or Python failure SHALL refuse deferral without falling back to candidate code, HEAD, repository configuration or candidate Hatch Python. The temporary directory SHALL be cleaned after execution.

This is an explicit trusted-caller approval boundary, not protected-branch policy or hostile-code isolation. Caller edits or hook bypass are outside this local check; candidate hook/control changes still require independent review. Existing platform, worktree, branch, CI, eligible-path and blocking-job guards and mandatory hosted exact-head acceptance SHALL remain intact.

#### Scenario: Candidate policy cannot approve changed indexed orchestration

- **GIVEN** a caller-selected reviewed policy commit and external host Python
- **WHEN** the candidate changes indexed orchestration and updates its checker pin or replaces its working-copy checker with a successful canary, including an unstaged workflow restoration
- **THEN** immutable policy refuses the changed indexed bytes and the candidate checker never executes.

#### Scenario: Explicit immutable selection fails closed

- **GIVEN** an otherwise eligible local candidate
- **WHEN** the commit or Python selection is missing or invalid, the selected object is not a commit, the checker is absent or empty, or Git or Python fails
- **THEN** the hook refuses deferral without executing candidate policy; Git replacement objects cannot substitute an approving checker.

#### Scenario: Reviewed indexed bytes retain local deferral

- **GIVEN** exact reviewed indexed orchestration and explicit valid caller selections
- **WHEN** the existing local eligibility checks execute
- **THEN** the hook reports DEFERRED and retains contracts and all other checks, while cleaning its temporary checker.

#### Scenario: Candidate interpreter paths cannot bypass immutable policy

- **GIVEN** an otherwise eligible local candidate and explicit policy selection
- **WHEN** the interpreter path is inside the physical candidate repository, including a checkout alias or symlinked parent directory, or resolves through an external symlink into that repository
- **THEN** the hook refuses deferral before executing that interpreter; a legitimate external symlink to an external host interpreter remains eligible.

The hook SHALL canonicalize the repository, interpreter parent directory and interpreter target using host tools before executing the selected interpreter. Both the selected physical location and resolved target SHALL be outside the candidate repository. Resolution failures SHALL refuse deferral. This safeguards the already approved local deferral and grants no new policy authority.


#### Scenario: Existing Darwin eligibility does not depend on the realpath command

- **GIVEN** an otherwise eligible local Darwin ARM64 feature worktree with caller-reviewed immutable policy and an external host interpreter
- **WHEN** the host has no `realpath` command
- **THEN** host path canonicalization SHALL still qualify legitimate external direct paths and symlinks without executing the selected interpreter to establish its location
- **AND** candidate-owned selected locations or resolved targets SHALL still refuse deferral before interpreter execution
- **AND** resolution failures SHALL refuse deferral without a candidate fallback
- **AND** no minimum OS version, policy authority, workflow pin, capability, timeout or hosted-review gate changes.


#### Scenario: Successful external executable is not policy completion

- **GIVEN** a trusted caller selects the reviewed immutable checker and an external executable that exits zero without running Python or the checker
- **WHEN** local deferral evaluates the indexed orchestration
- **THEN** the hook SHALL refuse deferral without treating that exit status as completed policy validation
- **AND** a working external Python SHALL still execute the selected immutable checker and accept only its successful completion
- **AND** invalid indexed orchestration and checker execution errors SHALL still refuse deferral
- **AND** interpreter-location checks, isolation, immutable extraction, cleanup, workflow pin and hosted-review gates SHALL remain unchanged.


### Requirement: Shell projection checks execute in the mandatory host stage

The default Hatch test command SHALL execute all four shell projection regression functions and their 31 parameter cases in an explicit host proof before ordinary unit discovery. The remaining 200 projection cases SHALL retain ordinary unit discovery. Fixture partitioning SHALL preserve assertions, review exit codes, privacy checks and isolation checks without changing runtime capabilities, analyzer gates or budgets. The same existing mandatory host selection SHALL also own all 152 native snapshot diagnostic cases, retaining their names, parameter identities, exact legacy assertions and real isolated `-I` invocation. Ordinary discovery SHALL retain all original 85 projection cases and SHALL NOT duplicate the moved corpus. Both groups SHALL pass ordinary complexity and nesting gates without suppression. The original 31 host cases and indexed orchestrator SHALL remain unchanged.

#### Scenario: Default suite retains shell projection coverage

- **GIVEN** the default Hatch test command
- **WHEN** its mandatory host stage runs
- **THEN** all 31 shell projection cases execute alongside existing host proofs and fail the command on failure.


### Requirement: Failure diagnostics associate contracts reasons with snapshot sides

Both existing inline failure projectors SHALL optionally publish `snapshot_diagnostic_observations` as at most two records in base then head order. Each record SHALL contain exactly `analyzer` with literal value `contracts`, `side` with literal value `base` or `head`, and `reason` from the closed vocabulary below. Candidate output SHALL append one JSONL envelope containing this value. Independent output SHALL add the same value to its existing summary. Both SHALL omit the field or envelope when the observation list is empty.

The new observation SHALL require analyzer_evidence to be a list with at most ten entries and exactly one object row whose id equals contracts. Repeated contracts rows, including identical duplicates, and lists over ten entries SHALL produce no new observation. A side SHALL qualify only when it is an object and execution_state equals error or evidence_outcome equals UNKNOWN. A missing, nonobject or complete side SHALL contribute no record.

For a qualifying side, reason SHALL be the canonical value matching the exact diagnostic token before its first colon. Classification SHALL accept only strings of at most 4096 Unicode code points, without coercion, trimming, case changes or suffix search. Missing, nonstring, empty, unknown and longer diagnostics SHALL yield literal `unclassified`. The closed vocabulary SHALL be `analyzer_reported_incomplete_execution`, `analyzer_output_invalid`, `capsule_request_failed`, `linux_bubblewrap_identity_missing`, `namespace_unavailable`, `sandbox_filesystem_error`, `analyzer_process_error`, `sandbox_launch_failed`, `reserved_import_catalog_unavailable`, `reserved_import_collision`, `bubblewrap_identity_mismatch`, `trace_helper_failed`, `pre_namespace_observation_unsupported`, `pre_namespace_observation_requires_single_thread`, `pre_namespace_exec_stop_missing`, `pre_namespace_observation_failed`, `pre_namespace_executable_missing`, `pre_namespace_executable_ambiguous`, `pre_namespace_host_object`, and `unclassified`.

Only complete reports accepted by the existing duplicate-safe readers SHALL supply observations. Complete reports above 2 MiB and at most 32 MiB MAY supply diagnostics through the existing header path while existing unavailable acceptance remains unchanged. Malformed, truncated, trailing-garbage, duplicate-key and over-32-MiB reports SHALL supply no new observations. Existing report-byte bounds, output fields and lines, legacy substring observations, finding handling, assurance, verdicts, original review exits, privacy, import isolation and protected gates SHALL remain unchanged. Parent diagnostics, findings, logs and unrelated analyzer diagnostics SHALL NOT supply a snapshot reason. No raw suffix, private path, token, argument or source fragment SHALL be published.

#### Scenario: Distinct reasons retain their snapshot association

- **GIVEN** one contracts row with incomplete base and head objects and distinct recognized leading reasons
- **WHEN** either actual failure projector reads a complete small or diagnostic-size report
- **THEN** two ordered records identify each side's own reason, and swapping diagnostics swaps reasons while preserving the side identities
- **AND** removing the new field or envelope leaves every legacy output unchanged, including unavailable assurance for diagnostic-size reports.

#### Scenario: Finite reasons reject private suffix promotion

- **GIVEN** eligible contracts sides with any allowed reason or missing, nonstring, unknown, whitespace-prefixed, embedded or over-bound diagnostics
- **WHEN** either actual failure projector classifies those sides
- **THEN** only canonical exact leading reasons or unclassified appear, 4096 Unicode code points are accepted, 4097 are rejected, and private canaries remain absent.

#### Scenario: Ambiguous or invalid evidence cannot invent association

- **GIVEN** duplicate contracts rows, an over-ten-entry list, absent or invalid sides, unrelated analyzers, duplicate JSON keys, truncated or over-bound reports
- **WHEN** either actual failure projector executes
- **THEN** no unsupported snapshot record is emitted, an empty field is omitted, and existing outputs and review exits remain intact.


### Requirement: Unclassified snapshot diagnostics expose only finite fallback facts

For each existing eligible contracts snapshot observation whose reason is unclassified, both actual failure projectors SHALL optionally publish `snapshot_diagnostic_facts`. At most two records SHALL retain base then head order. Each record SHALL contain exactly analyzer=contracts, side=base/head, shape=missing/non_string/string, length_bucket=not_string/empty/within_bound/over_bound and recognized_leading_token as a JSON boolean. Missing and present null diagnostics SHALL remain distinguishable. String lengths SHALL use Unicode code points with the existing 4096 boundary. Recognized membership SHALL inspect at most 49 code points against the unchanged 20-token vocabulary, without normalization or suffix search. A known oversized leading token MAY be recognized while its old reason remains unclassified.

No classified side SHALL produce these fallback facts. Empty results SHALL omit the field or envelope. Eligibility, complete duplicate-safe parsing, ten-row cap, 2-MiB/32-MiB bounds, existing reason records, legacy output, review exits, assurance, verdicts and privacy SHALL remain unchanged. Exact lengths, unknown tokens, private suffixes, paths, arguments and source SHALL NOT be published. These are diagnostic observations and SHALL NOT authenticate a producer, establish executed source identity, change runtime behavior or provide acceptance.

#### Scenario: Fallback shapes remain finite without promoting private text

- **GIVEN** incomplete contracts sides with missing, nonstring, empty, unknown or over-bound diagnostics
- **WHEN** either actual isolated failure program runs
- **THEN** only the closed shape, length bucket and membership facts appear, with the existing reason remaining unclassified
- **AND** removing only the validated additive field preserves every prior output, while invalid, ambiguous or complete evidence supplies no new fact.


### Requirement: Installed controller source observations remain bounded and non-authoritative

The independent-review job SHALL observe the installed controller sources separately for preparation and review, after the existing imports and before entering the subject directory. It SHALL retain the original process results, arguments, isolation, reports, findings, assurance, acceptance, capabilities, installation pins and deadlines. The candidate job SHALL NOT receive this installed-controller observation.

The observer SHALL use only installed USER_MODULES_ROOT/specfact-code-review and its fixed module-package.yaml, src/specfact_code_review/run/runner.py and src/specfact_code_review/run/sandbox.py. Metadata SHALL pass the installed ModulePackageMetadata.model_validate and name nold-ai/specfact-code-review. The native core 0.55.4 verify_module_artifact API SHALL receive that package and metadata, allow_unsigned=False, require_integrity=True, require_signature=True and explicit bundled PEM. Only a true verification result permits observation. The observer SHALL NOT duplicate the install version pin or accept environment keys, candidate registries or report-selected paths.

Both already loaded modules SHALL have absolute string __file__ and __spec__.origin paths identifying their exact fixed contained sources. A non-null callable sandbox.execute_launch_plan SHALL be identical to runner.execute_launch_plan. Missing attributes, shared noncallables, alternative bindings, missing specs, relative or mismatched origins SHALL yield unavailable. No cache-absence predicate, reload or alternate module import SHALL be added.

Fixed components SHALL reject symlinks. Final reads SHALL use nonblocking no-follow opens and require regular files, with limit-plus-one reads and byte limits of 4 MiB per source, 256 KiB manifest, 64 KiB PEM and 4096 bytes per receipt. Source and manifest bytes and file identity SHALL remain consistent across native verification. These are bounded checks under the existing fresh ordinary-user job trust, not an atomic snapshot against hostile same-user mutation. Ordinary observer and receipt-write exceptions SHALL leave the original operation unchanged. BaseException and original operation failures SHALL retain their behavior.

Each invocation SHALL atomically replace its own complete private JSON receipt beside reviewer.py, using controller-source-preparation.private.json or controller-source-review.private.json. Receipt location SHALL derive from the generated script directory, without a caller-selected path. Observed records SHALL have exactly phase, invocation, status, identity_kind, runner_sha256 and sandbox_sha256, with phase installed_controller_source, invocation preparation or review, status observed, identity_kind authenticated_source_and_loaded_origins and lowercase 64-character SHA-256 hex digests of checked source bytes. Unavailable SHALL contain exactly phase, invocation and status unavailable.

One subsequent always() step SHALL publish exactly two reconstructed JSON lines, preparation then review. It SHALL use the trusted interpreter with -I when available and standard-library-only projection. Missing root, interpreter, earlier installation, bootstrap or receipt SHALL produce the corresponding unavailable records. The shell SHALL buffer complete projector stdout and discard it on nonzero exit before printing two literal unavailable records. Observation failures SHALL return zero from the publisher while preserving the earlier command result. Runner termination is outside this later-step guarantee.

The publisher SHALL reject symlinks, nonregular or oversized receipts, invalid UTF-8, malformed or trailing JSON, duplicate keys, nonobject roots, wrong or extra keys, wrong fixed labels and invalid digests. It SHALL reconstruct each result independently and never echo raw bytes, private errors, paths, tokens or unknown keys. Unavailable SHALL contain no hashes, identity kind or reason.

These records SHALL describe authenticated source and loaded-origin observations only. They SHALL NOT identify literal executed bytes, caches, worker or capsule-child imports, candidate source, historical producers or root cause. They SHALL NOT influence runtime behavior or acceptance.

#### Scenario: Complete loaded source predicates produce separate receipts before subject entry

- **GIVEN** synthetic installed modules with fixed regular sources, valid metadata, strict verifier success, matching loaded origins and one shared callable
- **WHEN** each complete real reviewer dispatch enters the subject
- **THEN** its own complete observed receipt already exists and its source hashes match independently calculated fixture bytes
- **AND** different invocation fixtures remain distinct, a different metadata version is permitted, and a present cache does not invalidate source-only observation.

#### Scenario: Unusable source identity does not change the original operation

- **GIVEN** failed verification, invalid metadata or key, origin or binding mismatch, symlink, nonregular or oversized file, consistency drift or ordinary receipt-write failure
- **WHEN** the complete reviewer executes preparation or review
- **THEN** it retains the original dispatch, cleanup and exit and supplies unavailable or absent evidence without private public output.

#### Scenario: Separate publication preserves command success and failure

- **GIVEN** successful preparation, no governed impact, failed preparation, failed bootstrap, or review exit 0, 2, 7, 17 or 124
- **WHEN** the original command recipe and separate always publisher execute
- **THEN** the original command result and public output remain unchanged and publication emits exactly two ordered source records
- **AND** early setup failure, missing interpreter and projector failure after partial stdout yield two unavailable records without a public traceback.

#### Scenario: Receipt projection reconstructs only the two exact public variants

- **GIVEN** valid, missing, malformed, duplicate, oversized, nonregular or privacy-canary receipts
- **WHEN** the actual complete isolated publisher recipe executes
- **THEN** each valid record round-trips through an exact allowed shape and each invalid record becomes its own three-key unavailable result
- **AND** no raw receipt text, canary, path or partial projector stdout reaches public output.


### Requirement: Contracts snapshot producer categories remain sparse and non-authoritative

Both actual failure projectors SHALL optionally publish snapshot_producer_categories using only existing eligible contracts observations whose reason is unclassified. Each of at most two records SHALL contain exactly analyzer=contracts, side=base/head and category=project_analyzer_dependency_incompatible/project_runtime_required, ordered base then head. Candidate SHALL append one envelope containing only this field after its existing facts. Independent SHALL add only this property to its existing summary. Empty results SHALL omit the field or envelope.

Only a nonempty string of at most 4096 Unicode code points whose exact token before the first colon equals one of those two families SHALL confirm a category. Bare family strings SHALL qualify. No coercion, trimming, case normalization, substring match or suffix search SHALL occur. Missing, non-string, empty and oversized diagnostics SHALL remain unavailable to classification. Other bounded strings SHALL remain other internally. Neither internal outcome SHALL be published. Existing five-key fallback facts SHALL retain negative shape information, with old reason unclassified and recognized_leading_token false for these families. Absence alone SHALL NOT establish a negative observation without the corresponding existing facts and known deployed contract support.

The existing at-most-ten-entry, unique contracts row, object side and error-or-UNKNOWN eligibility rules SHALL remain unchanged. Existing complete duplicate-safe report parsing and 2-MiB/32-MiB bounds SHALL apply. A valid whitespace-padded report exactly 32 MiB MAY supply categories without restoring assurance; cap plus one SHALL NOT. Parent, finding, log and unrelated analyzer text SHALL NOT supply categories. Candidate dictionaries without findings SHALL retain their existing eligibility, while independent invalid report shapes SHALL remain rejected.

Removing only the validated new field or dedicated envelope SHALL leave every old output unchanged. The twenty old reason values, three-key observations, five-key facts, original exits, private bytes, import isolation, observer, publisher, complete orchestrator, selection, dependencies, signatures, budgets, gates and authority SHALL remain unchanged. No raw token, suffix, path, argument or source SHALL be published. These categories SHALL NOT authenticate producers, identify packages or versions, prove historical cause, change runtime behavior or provide acceptance.

#### Scenario: Exact producer families retain their eligible snapshot association

- **GIVEN** eligible contracts base and head diagnostics with bare or colon-suffixed exact producer families
- **WHEN** either complete actual failure program executes
- **THEN** only the exact ordered three-key positive records appear, including swapped families and both error-or-UNKNOWN eligibility routes
- **AND** all legacy outputs remain identical after removing only the validated addition.

#### Scenario: Other or unavailable diagnostics retain finite existing facts

- **GIVEN** missing, non-string, empty, unknown, normalized-looking, embedded or oversized diagnostic values
- **WHEN** either complete actual failure program executes
- **THEN** it emits no invented category and retains the exact existing reason and shape facts
- **AND** Unicode lengths 4096 and 4097, mixed classified sides, invalid or ambiguous evidence and rejected complete reports retain their existing boundaries.

#### Scenario: Report acceptance and owner asymmetry remain unchanged

- **GIVEN** the same positive family evidence in small, above-2-MiB, exactly-32-MiB or over-cap reports, or a dictionary without findings
- **WHEN** the candidate and independent programs execute
- **THEN** only accepted diagnostic evidence supplies categories, oversized assurance remains unavailable, and the dictionary without findings confirms only for candidate
- **AND** private canaries remain absent and report bytes remain unchanged.

#### Scenario: Positive publication preserves the original candidate failure

- **GIVEN** the actual candidate failure tail and a controlled prior exit of 17 or 124
- **WHEN** its unchanged guard, isolated interpreter invocation, complete heredoc and final exit execute under native Python
- **THEN** the original exit is preserved, exact two-family categories appear, public and private stderr are empty and report bytes remain unchanged
- **AND** this native synthetic proof does not claim to reproduce the original review command or hosted interpreter.
