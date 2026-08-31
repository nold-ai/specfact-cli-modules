## MODIFIED Requirements

### Requirement: Cache refresh records hierarchy metadata

The system SHALL persist a local cache that records the repository identity, supported hierarchy issue data, a deterministic fingerprint, issue count, and the timestamp of the most recent successful GitHub synchronization.

#### Scenario: Unchanged hierarchy refresh renews freshness

- **WHEN** a GitHub hierarchy read succeeds and its fingerprint matches the existing cache for the same repository
- **THEN** the system SHALL retain the existing markdown hierarchy payload
- **AND** SHALL update the state-file timestamp to the successful synchronization time
- **AND** SHALL report the cache as unchanged.

#### Scenario: Failed refresh preserves prior freshness

- **WHEN** the GitHub hierarchy read fails
- **THEN** the system SHALL return a failure
- **AND** SHALL NOT update the cache state timestamp.
