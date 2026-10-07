# Bounded reviewer bootstrap

Confirmed outcome: an independently installed authenticated reviewer can select
explicit portable tests and avoid repeated computation of immutable similarity
windows without changing findings. The owner approved a separate preparation PR;
merge/publication remain manual. Parent issue #460 is Todo, parent #163, required
labels/project present and predecessor #459 closed; current hierarchy cache is read
before implementation.

Reuse: retain upstream Pylint and the existing trusted wrapper. A native jobs
increase is unsuitable because fork policy and output parity are unproven. A
vendored checker fork adds maintenance cost. Select a minimal per-invocation
functools LRU around the pinned hash function. Upstream LineSet objects remain
unchanged during pair comparisons, and the checker copies mutable line limits
before processing them. Bound to 256 keys and restore/clear in finally.

Validate meaningful RED→GREEN selection tests, same-object duplicate groups and
locations, disabled-line callbacks/options/minima, eviction and exceptional
teardown. Actual full-range sealed timing is a promotion check; host timings and
hash-call counts alone do not establish #498 acceptance. Preserve every required
analyzer, project policy and incomplete-evidence failure. Rollback is a corrective
module release; preserve immutable historical artifacts and Linux support.

Release metadata: prepare 0.51.1 from released dev 0.51.0. The registry continues
to advertise the actual released 0.51.0 until separately authorized artifact
publication updates the catalog through existing tooling. Do not invent archive
URLs/checksums or access local private signing keys. CI provides a signature-only
follow-up. Native PR #498 must rebase and use 0.51.2 after human promotion; its
current unpublished 0.51.1 is not promoted alongside this small bootstrap. The
previously approved local Darwin review deferral remains DEFERRED to blocking
exact-head GitHub Linux, with every other normal hook required.
