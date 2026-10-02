# Managed boundary implementation checkpoint

Recorded 2026-10-02 (Europe/Berlin). **Production integration remains blocked.**
The local fixed-fixture startup and confinement prototype is implemented; see
[STARTUP_BOUNDARY_RESULTS.md](STARTUP_BOUNDARY_RESULTS.md). The owner-approved managed-process scope is retained; no requirement
for isolation, integrity or lifecycle has been relaxed and no native support
release is claimed. Apple distribution requirements were explicitly deferred.

## Distribution-signing split — 2026-10-02 (Europe/Berlin)

This owner-approved revision supersedes the earlier Developer-ID-first milestone.
Optional [#488](https://github.com/nold-ai/specfact-cli-modules/issues/488) /
[`code-review-macos-developer-id-distribution`](../code-review-macos-developer-id-distribution/proposal.md)
is blocked by #460; it does not block this change, shipment or publication.
"Signed runtime" in this change means native signatures plus an authenticated
SpecFact payload manifest, not a mandatory Apple publisher identity. Preserve
historical experiments as evidence, without treating their old signing policy as
current acceptance. Sandbox, dependency, lifecycle and real-installation gates
remain mandatory. Apple credentials do not solve the startup ownership gap.

## Optional Apple prerequisite utility

`scripts/macos_managed_boundary/preflight.py` checks explicit maintainer signing
configuration, valid Developer ID Application identity and notarization profile
authentication. It never builds or executes a candidate. A successful result still
sets `signed_boundary_verified` and `production_approved` to false. See the
[maintainer runbook](../../../scripts/macos_managed_boundary/README.md).

Parallel dependency packaging and all-ten-analyzer compatibility now have actual
native results on CPython 3.11–3.13; see
[NATIVE_COMPATIBILITY_RESULTS.md](NATIVE_COMPATIBILITY_RESULTS.md). They are not
an admitted runtime. No module payload, version, signature or registry identity
was changed.

## Historical startup ownership gap found during implementation review

The proposed sequence `spawn -> bootstrap PT_TRACE_ME -> confinement -> project
exec` does not itself establish cleanup ownership from process creation. A child
created but not yet traced can remain alive when its broker dies. Starting the
bootstrap suspended makes the counterexample deterministic at the mechanism level:
there is neither a live broker to resume it nor an established trace relationship
to kill it. Preventing project code from running is necessary but does not satisfy
the separate five-second survivor requirement.

Apple's published `proc_exit` kills children marked `P_LTRACED`; untraced children
are reparented. `PT_TRACE_ME` sets that flag only when the child executes the
syscall and passes its checks. These are source-derived findings, not observations
from a signed runtime on the advertised OS matrix. Sources inspected 2026-10-02:
[XNU parent exit](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_exit.c#L2188)
and [tracing setup](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/mach_process.c#L161).

Reviewed alternatives do not establish the missing ownership:

- Spawn suspended followed by parent attachment leaves the same creation-to-attach
  interval.
- Apple's published public `vfork()` implementation calls the fork wrapper; it
  cannot be assumed to hold the parent until bootstrap exec/exit.
- The reviewed spawn path releases the child to userspace before returning, with
  no wait for its bootstrap to establish tracing.

Sources: [Apple Libc fork implementation](https://github.com/apple-oss-distributions/Libc/blob/main/sys/fork.c#L51)
and [XNU 11417.140.69 spawn ordering](https://github.com/apple-oss-distributions/xnu/blob/xnu-11417.140.69/bsd/kern/kern_exec.c#L4066).
The moving source branches are not mapped here to every supported shipping OS;
that remains required before any positive admission. The conclusion is rejection
of this sequence as sufficient proof, not proof that every native architecture is
impossible.

## Original conditions for resuming boundary implementation

1. Identify an execution/cleanup ownership mechanism covering the interval from
   worker creation through tracing, including broker death before bootstrap code
   runs. A parent check, handshake, child timer, polling loop or repeated ordinary
   success cannot alone prove removal of an unscheduled/suspended worker.
2. Keep the pre-trace broker-death case mandatory in independent survivor testing.
   A source review is not a substitute for the required signed execution proof.
3. Verify the exact initial-distribution native signatures, hardened-runtime
   settings and narrow entitlements against final payload bytes. Apple credentials
   and notarization belong to optional #488; they do not block this milestone.
4. Pass the complete boundary suite, five-second limit and 100 repetitions of each
   lifecycle race before integrating adapters, analyzers or runtime provisioning.

Ad-hoc signed initial-distribution builds are admitted only after the complete
boundary suite passes; unsigned execution never substitutes for valid signatures. No production broker, managed
adapter, automatic runtime downloader or signed macOS artifact is implemented in
this checkpoint. The completed capability still requires its minor version bump,
manifest/signature/registry changes, full acceptance and PR review loop. This
checkpoint must not be presented as that delivery or archived as complete.

## Startup-only follow-up: now measured on the physical host

A source/documentation check on 2026-10-02 identified an alternative to investigate,
not an approved mechanism: an invocation-scoped user launchd job may own cleanup
of the trusted bootstrap before tracing is established. Both this host's
`launchd.plist(5)` and [Apple's published manual](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5)
document cleanup of remaining processes sharing the job's process-group ID unless
AbandonProcessGroup is enabled. This is not the previously rejected claim that
process groups contain arbitrary project descendants.

The hypothesis requires every pre-trace bootstrap to remain in that group and
execute only fixed trusted code; after admission, the existing tracing/confinement
contract must still hold. It also requires proof of ordinary-user registration,
no unwanted restart or persistent job, authenticated CLI connection, cleanup
within five seconds and all initial-distribution startup races on each supported OS. The manual
does not guarantee that bound or establish those properties. The follow-up has now been executed with temporary jobs and independent
positive/negative controls: 100 repetitions of each of six startup stages pass on
macOS 27.0.1 build 26A434. See [the results and limits](STARTUP_BOUNDARY_RESULTS.md).
Full boundary admission and production integration remain incomplete.

## Executable control and sealed analyzer checkpoint — 2026-10-03

The physical-host startup subset resolves the original creation-to-tracing
counterexample for fixed trusted bootstraps. The authenticated broker control
fixture now implements launch, wait, signal, cancel and event-driven connection
loss; [CONTROL_BOUNDARY_CONTRACT.md](CONTROL_BOUNDARY_CONTRACT.md) preserves measured
results, review corrections and limits. The kernel-traced deny-default bootstrap
also executes the actual pinned Semgrep core with both rule packs on clean and
defective fixtures. See [SEALED_ANALYZER_CONTRACT.md](SEALED_ANALYZER_CONTRACT.md).
Neither is a production backend, complete artifact, supported matrix, project
manager adapter or independent-Mac installation proof. These successful subsets
do not enable the public native command or approve publication. Paid Apple
identity remains optional; OS-specific private Seatbelt compatibility requires
measured acceptance, not a new blanket prerequisite that Apple publish the API.
