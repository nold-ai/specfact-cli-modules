## ADDED Requirements

### Requirement: Cache refresh records hierarchy metadata

The system SHALL persist a local cache that records the repository identity, supported hierarchy issue data, a deterministic fingerprint, issue count, and the timestamp of the most recent successful GitHub synchronization.

#### Scenario: Unchanged hierarchy refresh renews freshness

- **WHEN** a GitHub hierarchy read succeeds and its fingerprint matches the existing cache for the same repository
- **THEN** the system SHALL retain the existing markdown hierarchy payload only when it is a non-symlink regular file whose contents, except the synchronization timestamp, match the expected rendered cache for the fetched Epic and Feature hierarchy
- **AND** SHALL update the state-file timestamp to the successful synchronization time
- **AND** SHALL report the cache as unchanged.

#### Scenario: Matching state does not trust malformed cache content

- **WHEN** the state file matches the repository and fingerprint but the markdown cache is missing, not a regular file, unreadable, or does not match the expected rendered hierarchy payload
- **THEN** the system SHALL regenerate the markdown cache
- **AND** when the cache path is any non-regular filesystem entry, SHALL preserve that entry at a unique sibling path before regenerating the cache
- **AND** SHALL report the cache as updated.

#### Scenario: Failed refresh preserves prior freshness

- **WHEN** the GitHub hierarchy read fails
- **THEN** the system SHALL return a failure
- **AND** SHALL NOT update the cache state timestamp.
