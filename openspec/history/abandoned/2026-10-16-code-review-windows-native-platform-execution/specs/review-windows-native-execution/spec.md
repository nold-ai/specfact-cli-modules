## ADDED Requirements

### Requirement: Project-driven Windows preparation
Native Windows x86-64 review SHALL use the shared ProjectPlan configuration and
on-demand preparation contract, without a publisher catalog entry for customer
projects or changes to their checkout or active environment.

#### Scenario: Unfamiliar configured project
- **WHEN** a supported dependency-bearing repository has no acquisition catalog entry
- **THEN** the verified native runtime SHALL prepare it using its authentic selected manager in disposable domains
- **AND** ambiguous discovery SHALL return candidate setups and actionable required configuration.

### Requirement: Proven Windows execution boundary
The Windows backend SHALL prove startup ownership, managed process confinement,
network/filesystem/descriptor restrictions, enforced resources and cleanup
against the final native artifact before advertising support.

#### Scenario: Preparation or boundary capability is unavailable
- **WHEN** a required preparation or kernel capability is missing
- **THEN** review SHALL preserve independent findings and return incomplete required evidence
- **AND** it SHALL NOT fall back to host execution or produce PASS.

### Requirement: Equivalent physical and VM acceptance
Acceptance SHALL depend on guest OS, CPU architecture, ABI and required
capabilities, with no hardware-brand or hypervisor requirement.

#### Scenario: Clean matching-architecture Windows VM
- **WHEN** a full Windows x86-64 VM runs the final capsule as an ordinary user with normal protections
- **THEN** it SHALL be eligible for the same complete installation and runtime acceptance as a physical Windows x86-64 computer
- **AND** VM status SHALL NOT weaken isolation or cause rejection.

#### Scenario: Translated applications on ARM64 Windows
- **WHEN** an ARM64 Windows guest translates x86-64 applications
- **THEN** its results SHALL remain supplemental evidence and SHALL NOT establish native Windows x86-64 acceptance.
