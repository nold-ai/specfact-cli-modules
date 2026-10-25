# Native CI review owner

The workflow installs the signed released reviewer separately from candidate dependencies. An isolated controller imports that installation before entering the subject. Candidate reviewer modules cannot replace the controller. Project dependencies remain in the repository Hatch environment. Independent analyzer tools use a separate controller environment constrained by the existing reviewed analyzer versions. Signing secrets are absent and checkout credentials are not persisted.

The input is the exact event head, merge-base, staged head tree, trusted reviewer identity and rule/configuration identities. The output is a CI receipt with one completed outcome per required member, raw findings and the ordinary changed-enforcement result. It is ordinary job evidence, not a protected report or a new customer report schema.

Reuse the signed tool adapters for Ruff, Radon, Semgrep clean and bugs, AI-bloat AST, AST clean code, basedpyright, pylint and contracts/CrossHair. Require the signed rule packs and explicit trusted configuration. Capture each member before filtering. Tool errors, UNKNOWN, skipped or malformed execution block regardless of line or severity. Run native project tests with coverage and retain their actual result. Test applicability must be explicit rather than inferred from an empty result.

Validate source identity before and after execution. Bind the receipt and artifact to the event head. The quality matrix requires successful independent review, native Hatch acceptance, migration scope and signatures. A skipped, cancelled, stale or incomplete prerequisite cannot pass.

One writer implements this bounded adapter. Source analysis compared a static supplement with full signed-engine reuse. Full reuse preserves existing ownership with less duplicated policy. The critical probe demonstrated engine callability and exposed its missing completeness barrier. Independent implementation review and exact-head Linux execution remain required before removing the old prerequisite.
