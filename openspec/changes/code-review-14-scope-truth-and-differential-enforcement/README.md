# Code Review 14: Scope Truth and Differential Enforcement

This change makes review scope an explicit evidence fact and compares base/head analyzer results instead of treating worktree changed lines as PR introduction evidence.

Planning only: no review package, tests, registry, version, signature, prompts, or generated docs change on this branch.

The approved immutable compatibility target is core lightweight tag `v0.55.1` at commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` and tree `47984be5434d7ae65ed6908bf525a32053290337`, advertised only as `===0.55.1` after the prescribed smoke passes.
