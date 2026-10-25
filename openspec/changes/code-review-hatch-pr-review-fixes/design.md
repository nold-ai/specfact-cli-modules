# Bounded review corrections

Project provenance keeps the current physical traversal and adds each nonignored directory link's relative path and link text to both identity digests. Existing physical target configuration files remain content-fingerprinted. Traversing arbitrary aliases would change the read closure, cycle handling and cost; rejecting aliases would add admission restrictions. Neither is part of this correction.

The scope policy remains the one owner of classified surfaces and reviewed state. A committed manifest stores each baseline path's Git mode and blob identity; the existing policy SHA binding covers it. Default checking compares current classified entries with those records and accepts missing entries as retirement. It never needs the old freeze commit. Explicit historical comparisons retain safe revision resolution and Git diff semantics. Modes preserve chmod/type detection; symlinks use link text, not target content. This is an accidental-drift guard, not hostile-candidate authentication.

Alternatives are retaining/fetching a new remote ref, which adds operational setup and retention dependencies, or using dev as the baseline, which loses already approved feature-branch state. A committed manifest preserves the existing baseline without either dependency. Independent design review is `/private/tmp/513-babysit-design-review.md`.

The decisive portability test copies only a final tree to a new Git repository with a single root commit. The old freeze object is absent. Unchanged/native/deletion cases must pass; repaired/new/mode-changed classified files must fail. Historical recurrence evidence remains honest about which original bytes or excerpts it preserves.

Test decomposition retains collected selectors and assertions wherever possible. Static complexity is measured by the existing Radon analyzer, with no new runtime abstraction or acceptance threshold.
