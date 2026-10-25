# Native-only scope ratchet

One JSON policy owns the execution direction, audit freeze revision, classified legacy path patterns and committed baseline mode/blob manifest. Default checking compares current classified files using Git checkout normalization and current index modes; it does not need the old feature commit after squash integration. Modified or added classified paths fail; removed paths are allowed. Working-tree checks include untracked classified paths. Historical read-only comparisons use explicit base/head revisions and Git name/status records with NUL separators and no rename inference.

The checker pins the reviewed policy bytes by SHA-256. A policy-only edit cannot move the baseline or remove a classified path. Changing the fingerprint is a change to the enforcement code and requires independent review like any other guard change. This binding prevents accidental configuration bypass; it does not authenticate a hostile candidate that also rewrites its checker. Resolve both comparison revisions with `git rev-parse --verify --end-of-options` before invoking Git diff. Only resolved commit identities enter that command.

Keep the policy and checker outside signed module payloads. Invoke the checker from the existing boundary command so pre-commit cannot silently omit it. A small separate CI workflow invokes the same Python command with complete Git history, read-only repository permissions and no capsule prerequisite. Existing capsule workflows and their failures remain untouched.

The ratchet deliberately freezes legacy surfaces rather than trying to infer whether an edit is a worthwhile capsule repair. Future approved native cutover may remove those files. If useful native code needs a currently frozen location, revise the migration ownership explicitly rather than adding an undocumented exception.

This is a regression guard against known scope drift, not hostile-code containment or proof of all possible future implementation semantics. The owner chose native execution already. No backend choice or runtime framework is introduced.
