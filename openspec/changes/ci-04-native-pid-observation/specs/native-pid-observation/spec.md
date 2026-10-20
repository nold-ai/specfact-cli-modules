## ADDED Requirements

### Requirement: Complete positive records remain observable
A complete positive ASCII decimal PID plus one final newline, at most 31 bytes total, SHALL be accepted without a pending-publication sleep.

#### Scenario: complete-pid-record
- **WHEN** an immediately complete valid marker is read
- **THEN** both existing consumers observe its integer value, and the controller retains exact JSON, WAIT payload and WAIT_SENT

### Requirement: Creation does not imply publication
Both active readers SHALL await complete publication when a real marker is empty or contains only an incomplete ASCII numeric prefix.

#### Scenario: publication-completeness
- **WHEN** the producer exclusively creates its real marker and publishes the remaining actual PID bytes and newline after the first pending poll
- **THEN** both consumers observe the complete actual PID and never prematurely parse the empty or partial record

### Requirement: Pending publication uses one five-second deadline
Absent, empty and newline-free numeric markers SHALL remain pending under one fixed five-second monotonic deadline, with positive sleeps at most 10 ms capped by remaining time.

#### Scenario: single-deadline
- **WHEN** publication remains absent, empty or incomplete
- **THEN** both consumers raise AssertionError by the same deadline without PID output or WAIT

### Requirement: Invalid publication fails before observation
Readers SHALL reject oversize, non-ASCII, signed, whitespace, zero, empty-line, multiline and trailing-byte records with ValueError before PID output or WAIT.

#### Scenario: strict-framing
- **WHEN** a marker contains an invalid record
- **THEN** both consumers fail immediately without polling or observable PID output

### Requirement: Late observations do not become ready
Readers SHALL recheck the same deadline after observation and reject a ready record observed at or after that deadline.

#### Scenario: late-observation
- **WHEN** a real valid record is read but the final monotonic observation reaches the deadline
- **THEN** both consumers raise AssertionError without PID output or WAIT

### Requirement: Only regular non-symlink markers are admitted
Readers SHALL reject symlinks, directories and FIFOs promptly without a blocking read or retry.

#### Scenario: regular-marker
- **WHEN** the marker pathname is a symlink, directory or FIFO
- **THEN** both consumers fail immediately before PID output or WAIT

### Requirement: Ordinary I/O failures retain their identity
Readers SHALL propagate ordinary OSError unchanged and SHALL retry only FileNotFoundError from opening an absent marker.

#### Scenario: io-failure
- **WHEN** the marker open or read encounters an ordinary I/O error
- **THEN** the same exception reaches the caller without polling, PID output or WAIT
