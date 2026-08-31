## Context

Cache freshness is governed by the state file. Fingerprint equality indicates unchanged hierarchy content, not an unsuccessful refresh.

## Decision

On a successful unchanged sync, keep the markdown file byte-stable and rewrite only state metadata with the current UTC timestamp. A failed GitHub read remains an exception path before any write.

## Risks

Timestamp-only state writes are intentional local cache churn. The cache remains ignored and is not a release artifact.
