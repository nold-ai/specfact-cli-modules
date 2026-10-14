# Diagnostic recovery evidence

2026-10-14 (Europe/Berlin). This is an incomplete diagnostic preview, not an accepted reviewer or release.

Initial test collection failed because the new producer module did not exist. This weak availability check did not execute behavioral assertions. The first implementation then passed ten focused tests. No claim of scenario-level pre-implementation failure is made for those ten tests. Three additional source-identity, false-completeness and unknown-tool tests then failed with actual assertions against that implementation; their focused corrections produced thirteen passes. A post-implementation mutation copying private report text into the sidecar was detected by an actual assertion failure, then restored.

Workflow tests failed before the opt-in mode existed and then passed after its declaration. Full privacy/authority, signature and independent affected review remain required. Native review is explicitly DEFERRED under the approved ARM64 feature-worktree route, never PASS. All other applicable gates remain mandatory. Hosted native producer acceptance remains required before any future merge/completion and is not satisfied by the supplementary diagnostic execution.

The unchanged CI signing workflow must sign the preview before strict installation or execution. Local checksum preparation is source preflight only. No unsigned preview is executed.

Independent affected review identified three additional gaps: missing outcomes could permit completeness, same-location findings could borrow introduced identity, and independently valid member/tool/rule tokens could form invalid combinations. Five regression assertions failed before their corrections (13 other cases passed). A partial edit first caused eight errors; that failed result is retained separately. Corrected production code then passed all 20 focused tests. Internal message/severity/blocking identity is used only for correspondence and is never serialized.

Local source gates completed: formatting, type checking, lint, manifest YAML, bundle imports, 28 contract tests and seven-module checksum verification with the established public key. The new producer remains locally checksum-only until the unchanged CI signer signs it. Strict verification of the existing official signed baseline passed; signature and payload mutations were rejected. These controls do not authenticate the new preview before CI signing.
