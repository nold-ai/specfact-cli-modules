# Source-link exclusion fix

Finding: PR #474 comment 4005446099, verified against the candidate on 2026-09-14. A committed alias to excluded repository-local `.env`, virtual-environment contents, or `.git/config` was dereferenced into the disposable builder. Network-enabled dependency hooks could read those copied bytes. Synthetic reproductions confirmed availability, without using real secrets or attempting exfiltration.

The shared source-link validator now rejects excluded resolved path components. Source copying preserves links and normalizes valid targets into the copied tree. It verifies the complete copied identity before build hooks execute. The original source identity is checked before and after copying/building. This closes the alias route at discovery and acquisition, preserving ordinary included files and directory links. Tests cover excluded files, directories, descendants, Git configuration, absolute links, and parent-traversing relative links.

A fresh read-only investigator independently reproduced four alias classes. A separate fresh patch reviewer found one compatibility regression: valid `../source/app.py` links needed rebasing too. Its failing regression was recorded and fixed. The reviewer also exercised deterministic link replacements after the copy callback; destination validation rejected them before execution. No surviving symlink disclosure was found.

Focused validation: `hatch run pytest tests/unit/specfact_code_review/run/test_runtime_builder.py tests/unit/specfact_code_review/run/test_runtime_discovery.py -q` passes. Whole-repository lint/type and final publication gates are recorded separately in TDD_EVIDENCE.md; this document does not grant release acceptance.

Boundary limitation: hardlinks are ordinary source files and are not preserved by Git. A local process able to create hardlinks to local secrets is outside the committed-symlink trigger addressed here. Private staging must remain inaccessible to untrusted processes; same-user host compromise is outside the capsule's source-isolation claim.
