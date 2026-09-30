# Native ARM64 XPC execution-boundary experiment

This is a bounded feasibility experiment for #460. It does not enable a production
capsule or run arbitrary customer commands. Build and run on a physical ARM64 Mac
with Command Line Tools. No administrator installation or service registration is
performed. Application-scoped XPC launches the embedded service. Signing is local
ad-hoc signing, not Developer ID or notarization.

```sh
python scripts/macos_execution_boundary/run.py /private/tmp/specfact-xpc-new-run --diagnose
```

The output directory must not exist. The runner builds a fresh application and
service, records source/profile/executable digests, then writes `report.json` and
per-case JSONL logs. Keep these outputs outside Git or in an ignored directory.
`--diagnose` runs each fault once even after a failure; it never admits a backend.
Without it, the first failure stops the experiment. `--repetitions 100` is required
for a successful stress-test result, which still requires a mechanism review.
`--unsandboxed-control` is an explicitly labelled diagnostic baseline, never an
accepted capsule boundary.

The host observer measures a five-second cleanup bound after fault injection.
It checks native process birth times and executable paths, and takes a host
process-table census to find unreported workers from this unique test bundle.
Only matching fixture identities are signalled during emergency cleanup. Workers
also have a bounded lifetime. PID checks and polling are experimental observation
and rescue, not atomic production process ownership.

A survivor, startup failure, missing readiness or emergency cleanup rejects the
candidate. A passing individual fixture does not imply complete containment.
All receipts keep `production_eligible=false`. The test does not enable Rosetta,
Homebrew fallback, privileged services, remote uploads or registry publication.

The native lifecycle gate precedes Python/project-runtime integration, concurrent
run acceptance, complete filesystem/network/IPC checks, signing/distribution
acceptance and production backend selection. If it fails, preserve the failure
and stop admission; do not weaken the subprocess contract to obtain a green run.
