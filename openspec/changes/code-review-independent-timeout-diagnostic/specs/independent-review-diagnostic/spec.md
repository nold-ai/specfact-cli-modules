## ADDED Requirements

### Requirement: Preserve required review authority
The workflow SHALL schedule diagnostics only after a failed attempted PR independent review and SHALL preserve its command, environment, full analyzer selection, deadline and failure result.

#### Scenario: Any diagnostic outcome
- **WHEN** the replay completes, fails, times out or cannot start
- **THEN** its result is non-accepting and the original required review remains failed

### Requirement: Authenticate before observation
The helper SHALL verify core version, installed module signatures with the established key, installed reviewer payload, immutable registry reference and fixed staged subject before subject execution.

#### Scenario: Unverified identity
- **WHEN** any binding fails verification
- **THEN** no diagnostic subject process starts and only a static unavailable result is public

### Requirement: Restrict public projection
The helper SHALL emit only bounded numbers, static codes and verified installed symbol identifiers. Raw stacks, paths, process identities, argv, environment and errors SHALL remain private.

#### Scenario: Untrusted profile content
- **WHEN** a profile contains foreign same-suffix files, subject functions, secret markers, changed installed files, malformed data or oversized data
- **THEN** no unverified text is emitted

### Requirement: Own observation processes
The helper SHALL bind processes by start identity and ancestry, clean up owned descendants on completion, cancellation and timeout, and report missing joins and coverage as gaps.

#### Scenario: Incomplete process evidence
- **WHEN** a PID is reused, a request join is missing or a descendant is unsampled
- **THEN** attribution stays unknown and the result is partial or unavailable
