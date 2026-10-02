# Parallel native compatibility implementation

Owner authorized 2026-10-02: advance native dependency packaging and controlled
analyzer compatibility in parallel with boundary investigation. This extends the
managed-process plan without admitting a production backend or relaxing its gates.

## Mach-O inventory

A maintainer inventory tool SHALL inspect a supplied local payload without loading
or executing its binaries. It SHALL report Mach-O architecture slices, dylib load
commands and rpaths using absolute system inspection tools. It SHALL reject missing
ARM64 slices, malformed inspection output, unresolved load tokens, dependencies
outside the payload other than Apple system libraries, and unsafe path/symlink
escapes. It SHALL distinguish library IDs from load dependencies. The output is
inventory evidence, never a signature, sandbox or production admission receipt.

### Scenario: ARM64 closure inspected

Given a payload with an ARM64 executable and an internal dylib, inventory reports
its exact relative paths, hashes, architectures and dependencies without execution.
Universal binaries are accepted only if an ARM64 slice is present; each load
resolution is evaluated for that slice and executable context.

### Scenario: ambient or incompatible load rejected

An x86-only image, missing internal dylib, external symlink, Homebrew dependency,
unsafe rpath or unrecognized required load command produces actionable failure.
Apple shared-cache libraries may be recognized without requiring a disk file.

## Controlled analyzer compatibility

A maintainer-only smoke tool SHALL run repository-authored clean and defective
fixtures on native ARM64 macOS using explicit configured interpreter/tool paths.
It SHALL exercise the real analyzer adapters where applicable, check expected
findings/status, and record tool versions and actual OS/architecture. It SHALL
never be a fallback from the production review command or accept a customer
repository as an implicitly trusted target. Missing tools, skips, unexpected exit
codes or missing expected findings SHALL fail the compatibility check.

### Scenario: native findings verified

Fixed clean and defective fixtures exercise required analyzer members, including
pytest/coverage and contracts when their dependencies are present. Each member
records independent success/failure, expected diagnostic and observed result.
An overall compatibility pass requires all required members, not just installed
members. These are compatibility results only; signed capsule, real-project corpus
and managed-process acceptance remain separate and mandatory.

### Scenario: compatibility is not capsule approval

Every receipt SHALL identify controlled maintainer execution, sandbox_verified=false,
production_eligible=false, and native architecture. It SHALL reject non-ARM64 or
non-macOS execution for native evidence. No caller flag may promote this result to
protected review evidence or native production acceptance.

## Native Node package

The existing NATIVE_NODE_CONTRACT.md governs the offline BasedPyright/Node packager.
Run its fixed clean/defective fixtures as explicit maintainer compatibility tests
only. Pin matching is separate from upstream publisher-signature verification,
policy admission and final signed artifact acceptance.

## Explicit downstream Z3 wheel preparation

A maintainer tool MAY derive a distinctly versioned `5.1.0.0+specfact.1` ARM64
wheel from the exact pinned upstream Z3 5.1.0.0 wheel when metadata/tag defects
are confirmed. It SHALL authenticate the input digest, retain every native/source
payload byte and license, change only explicitly documented wheel metadata and
its dist-info directory/RECORD, and regenerate a valid RECORD. Target platform is
macosx_14_0_arm64 (not 13.0); native load minimum and architecture require separate
inventory validation. No installer or input code runs during repack.

### Scenario: deterministic correction with provenance

Two repacks of the same approved input produce identical output bytes. A sidecar
binds upstream URL/digest, all metadata corrections and output digest, and marks
production_eligible=false and dependency_admitted=false. Normal dependency
resolution and pip check must succeed before compatibility testing; disabling
resolution or hiding the upstream mismatch is not an acceptable remedy.

### Scenario: unsafe wheel rejected

Changed digest, unsafe ZIP paths/links/duplicates, excessive expansion, unexpected
upstream metadata or altered native content is rejected before any final output.
The tool never overwrites existing user files. Downstream namespace and provenance
must remain visible; the result cannot impersonate an upstream release.

## Candidate analyzer dependency locks

Maintainer candidate inputs SHALL keep BasedPyright/Node outside the Python graph,
use the explicit downstream Z3 version, and pin the released analyzer baseline
except Semgrep 1.175.0/MCP 1.29.0, selected to satisfy the paired core security
floor. Generated CPython-specific Darwin ARM64 locks SHALL include all resolved
transitive requirements and artifact hashes. Installation SHALL use normal
dependency resolution, explicit local wheel input and hash checking; pip check
must pass. These locks do not constitute policy or signed runtime admission.
