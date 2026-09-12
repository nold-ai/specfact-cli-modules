# Design: Customer Capsule Execution Correction

## Delivery boundary and baseline

This is planning only, based on modules `a6bac86ec529715b9122a7a670ee4886a749d9f6` and Code Review 0.49.77. Preserve the installed-payload layout correction and existing core compatibility. Revalidate the released baseline before implementation; freeze exact module/core versions and artifact identities in reproduction evidence. Read the paired core #680 proposal before changing handoff assumptions. No core source changes are included here.

## Customer reproduction

Use a dedicated workflow in this repository on `ubuntu-24.04`, x86-64, with Python 3.11/3.12/3.13 and fail-fast disabled. Each job records runner image/kernel, host UID/GID, Python patch version, core/module versions, launcher identity, namespace policy observations, cache state, and signed artifact identities. Host execution must be non-root; UID remapping inside a user namespace is not host privilege elevation.

Install released core and the official signed module via documented customer commands into fresh user-owned locations. Resolve the released stable versions once per reproduction campaign and bind all jobs to those identities. Keep publisher tokens, saved registry login, development links, unsigned overrides, source PYTHONPATH, and prefetched OCI caches out of customer acquisition and review steps. GitHub artifact upload credentials must not enter analyzer processes.

Execute the installed CLI from an independent temporary Git repository with controlled clean and defective tracked Python files and a nonempty selected scope. Include a deterministic blocking finding and expected clean outcome. Ensure required analyzers actually execute; exercise conditional project-runtime/test members with their existing valid attestation inputs rather than treating absent prerequisites as success. Exercise range snapshots/configuration mounts and an installed-CLI run against this modules repository. Record existing repository findings honestly; this dogfood run need not be artificially clean, but must complete its expected analyzer coverage.

Capture unmodified baseline failures first. If host policy denies the actual signed launcher, record that negative result separately; document the narrowly scoped administrator prerequisite and then rerun as non-root under an explicitly provisioned compatible policy. Do not count a denied-policy run as positive execution evidence. Do not silently change host security settings or run review with sudo. Retain a negative namespace-policy test as well as positive execution coverage.

## Acquisition and integrity

Exercise the production downloader anonymously from an empty cache, including its authentication challenge and allowed redirect path. Anonymous registry-issued bearer tokens are compatible with anonymous access; publisher/account credentials are not required. Repeat with a verified warm cache and prohibit acquisition network use for that repeat. Keep the base/toolchain identity stable across cache locations; compare composition identities only with equivalent bound inputs.

Identify whether a failure is the OCI manifest, config/layer bytes or size, uncompressed layer, wheel closure, installed filesystem content/mode manifest, module signature, or post-base composition. Report stage, ABI, expected and observed identities where available, and sanitized failure details. Never accept an observed hash merely because a run produced it. Compare cp312 root entries under explicit umasks 022 and 077 and non-root ownership; use a privileged run only as optional diagnostic evidence, never as customer acceptance. Fix determinism or publish corrected signed artifacts only after the exact mismatch is proven.

## Namespace and filesystem boundary

The capability probe must exercise the verified static Bubblewrap executable with the same descriptor execution, namespace flags, and observation/tracing constraints used by real materialization and review. An installed distro `bwrap` command succeeding is insufficient. Distinguish host policy denial from payload identity, filesystem setup, and analyzer execution failures. Keep UNKNOWN and failing exit behavior through existing reports; do not introduce a new command or public schema merely for diagnostics.

Capture the reported `/var/opt/specfact/...` failure's exact argv, path, process, errno/syscall and stderr before selecting its repair. The observed read-only-root-before-directory-creation sequence is a hypothesis for the customer error, not a proven match. Materialization writes occur in user-owned staging; analyzer state belongs in per-process declared writable mounts.

Establish every required mount destination before the relevant composition is sealed. Cover snapshot, numbered configuration roots, output, temporary state, Radon control, project runtime, and plugin preflight variants, plus proc/dev/tmp prerequisites. Any placeholder introduced after base verification belongs in the authenticated post-base composition; any base payload change requires a new signed base identity. Preserve the immutable base digest and update current composition bindings as appropriate, without editing installed signed files or historical checkpoint evidence to evade validation. Validate destinations against symlink/path escape and unexpected payload collisions. Keep analyzer code and dependencies read-only and route home/cache/temp/state through declared private writable roots. Verify cleanup after failure as well as success.

## Interfaces and release

Preserve CLI syntax, core/module discovery and handoff, canonical source mounts, signature verification, and existing assurance/exit semantics. Extend diagnostic detail within current fields; do not collapse infrastructure failure into an empty review or analyzer PASS. A known blocking finding may retain FAIL even when other evidence is incomplete; uncertainty must remain visible. Local or range-candidate evidence cannot claim protected pr_range authority.

Future changes are limited to proven capsule causes and the customer validation path. Run the customer matrix against candidate artifacts in a separately identified development lane, then against the actual signed public release as acceptance. The candidate lane cannot substitute for released installation. Publish immutable assets first through canonical tooling, update patch version/locks/resource identities/signatures/registry consistently, and preserve recoverable prior releases. Keep the bug open until released validation passes; archive via OpenSpec only after implementation, merge, and acceptance.

## Risks, costs and rollback

- Host policy can deny user namespaces or descriptor/tracing behavior: retain a diagnostic negative test and prove an explicitly supported non-root host configuration.
- Root manifests may depend on install modes or ambient state: compare exact entry manifests under controlled umasks and separate content from metadata drift.
- A smoke test can pass without real review: assert nonempty scope, exact required analyzer coverage, known clean/defective outcomes, and signed released installation.

Compressed runtime layer totals are 263599655, 258372661, and 255962422 bytes for cp311/cp312/cp313: 777934738 bytes total, approximately 0.78 GB decimal per full cold matrix, excluding installation dependencies. Disk use is larger after extraction; duration is unmeasured. Rollback uses reviewed revert plus canonical signed publication and registry correction, never edits to published immutable payloads. If the old release remains affected, record that limitation instead of claiming rollback restores working customer execution.

## Implementation checkpoint — 2026-09-12

The owner authorized implementation and integration into modules dogfooding CI. The existing dedicated worktree and PR now carry the implementation; earlier planning validation remains historical evidence. Static inspection also found that default materialization requests cache-only acquisition and that all GitHub Actions environments select candidate payload provenance, even for installed customer modules. Add regressions before correcting these paths.

Authenticated post-base composition will contain fixed mount anchors. Numbered configuration destinations are constructed inside a private tmpfs mounted at the authenticated config anchor, bound to the existing invocation context's exact mount list, and remounted read-only before analyzer execution. This prevents creation beneath a read-only parent without modifying sealed base bytes or exposing writable configuration at execution.
