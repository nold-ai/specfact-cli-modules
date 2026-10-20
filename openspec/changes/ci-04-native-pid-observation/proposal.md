# Native PID observation maintenance

## Why

Maintainers running the existing native controller-loss proof can observe the self-test PID marker after its exclusive creation but before its separate write. Both active Python readers currently parse that legitimate empty state immediately. Issue [#520](https://github.com/nold-ai/specfact-cli-modules/issues/520), under Feature #163, owns this bounded repair. The owner delegated necessary guideline-compliant corrections; the root selected the existing proof-module design on 20 October 2026 (Europe/Berlin).

## What Changes

- Await one complete positive ASCII decimal PID record ending in newline, within the existing five-second deadline.
- Share the fixed reader in the existing proof module and retain the sibling `_worker_pid` entry point through an import alias.
- Add portable real-file regressions for both consumers, including actual create-then-write publication, framing, deadline and I/O failures.

## Impact

The actual user is a maintainer running delivered native proof. The concrete outcome is that `_hold_worker` waits through empty or incomplete publication and then emits the same JSON, exact WAIT request and `WAIT_SENT`; the sibling observes the same positive PID. The PID is observational and grants no signaling authority. Trust remains an invocation-owned private directory and the existing producer. No hostile concurrent-writer integrity claim is made.

Only the two Python reader owners, the portable boundary tests and this maintenance specification are implementation scope. Native C, signed assets, manifests, versions, dependencies, cleanup identity and deadlines, 100 repetitions, nine physical matrix cells, workflow selectors and frozen historical proof files remain unchanged. Rejected issue #460 is not reopened or implementation authority. There is no runtime release, new platform, native build, CI retry, waiver or merge permission.

The first milestone is strict specification, portable tests and genuine old-reader RED, before source changes. Local GREEN, mandatory quality gates and existing hosted/native acceptance remain separate obligations. No elapsed-time or monetary estimate has been measured. Rollback reverts this isolated maintenance change and restores the known publication race.
