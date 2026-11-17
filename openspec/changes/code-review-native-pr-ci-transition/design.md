# Native CI review owner

The workflow installs the signed released reviewer separately from candidate dependencies. An isolated controller imports that installation before entering the subject. Candidate reviewer modules cannot replace the controller. Project dependencies remain in the repository Hatch environment. Independent analyzer tools use a separate controller environment constrained by the existing reviewed analyzer versions. Signing secrets are absent and checkout credentials are not persisted.

The input is the exact event head, merge-base, staged head tree, trusted reviewer identity and rule/configuration identities. The output is a CI receipt with one completed outcome per required member, raw findings and the ordinary changed-enforcement result. It is ordinary job evidence, not a protected report or a new customer report schema.

Reuse the signed tool adapters for Ruff, Radon, Semgrep clean and bugs, AI-bloat AST, AST clean code, basedpyright, pylint and contracts/CrossHair. Require the signed rule packs and explicit trusted configuration. Capture each member before filtering. Tool errors, UNKNOWN, skipped or malformed execution block regardless of line or severity. Run native project tests with coverage and retain their actual result. Test applicability must be explicit rather than inferred from an empty result.

Validate source identity before and after execution. Bind the receipt and artifact to the event head. The quality matrix requires successful independent review, native Hatch acceptance, migration scope and signatures. A skipped, cancelled, stale or incomplete prerequisite cannot pass.

One writer implements this bounded adapter. Source analysis compared a static supplement with full signed-engine reuse. Full reuse preserves existing ownership with less duplicated policy. The critical probe demonstrated engine callability and exposed its missing completeness barrier. Independent implementation review and exact-head Linux execution remain required before removing the old prerequisite.

## CI prerequisite input repair on 2026-11-17

The signature job owns event interpretation and supplies the verifier's existing explicit file input. With both key secrets absent, it selects the exact event PR base SHA or pre-push SHA, validates that nonzero commit identity, extracts the existing PEM into runner temporary storage, and invokes the unchanged verifier. Configured keys retain precedence. Whitespace-only configured keys fail explicitly because the verifier strips whitespace before its normal fallback lookup. Trust selection never uses the version comparator's HEAD~1 fallback or a candidate working-tree key. Missing authority fails closed.

The independent controller receives one temporary compatibility constraint containing typer==0.27.0 before its first install. Both controller installs consume that file. The analyzer install also retains its existing trusted-base constraints. Installed-version assertions retain core 0.55.4 and add Typer 0.27.0 before immutable registry checks. The signed marketplace reviewer remains 0.51.2 and Semgrep remains separate.

Three read-only design passes compared minimal workflow wiring, immutable key fingerprint/revision policy, a general resolver/bootstrap wrapper, and reuse of the complete docs constraints. Independent judgment selected workflow wiring with a single-purpose controller constraint. A new wrapper adds an unnecessary interface. A fingerprint adds key-rotation policy. The complete candidate docs constraints expand candidate influence into the independent controller and include unrelated dependencies. No new public API or trust service is needed.

Independent security/correctness review, real signature negative controls, a fresh released-controller install and the full exact-head hosted workflow are required before merge readiness. Rollback is a reviewed revert of the workflow and regression changes.
