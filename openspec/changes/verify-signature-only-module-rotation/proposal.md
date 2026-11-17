## Why

A publisher key rotation can replace a source manifest signature over unchanged module bytes. The current version check rejects this change even when the checksum and version remain valid.

## What Changes

- Allow full verification to accept a same-version source manifest update when the Git diff changes only its signature and the replacement key verifies the unchanged payload.
- Preserve the release cutoff, published archives, and the version requirement for any other bundle change.
