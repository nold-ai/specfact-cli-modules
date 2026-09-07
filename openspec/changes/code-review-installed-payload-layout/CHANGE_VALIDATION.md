# Change Validation

## Current lifecycle (2026-09-07, Europe/Berlin)

Implementation PR [#462](https://github.com/nold-ai/specfact-cli-modules/pull/462)
merged to `dev` at `2cf1899e3ac502bb7a5ddc9eae57899152c9d08d` on
2026-09-07 at 15:23:57 CEST. Registry publication PR
[#463](https://github.com/nold-ai/specfact-cli-modules/pull/463) merged at
`cd7fa371c79da69782bcd14accbd64e15c40a93d` at 16:36:39 CEST.
Code Review 0.49.77 is published with archive SHA-256
`e1da8dc6774e965e0a05c96febcf96ff62bf872b14b579dc3be894c9f4723718`.
The archive and matching `.tar.gz.sha256` sidecar are under `registry/modules/`;
the detached signature is `registry/signatures/specfact-code-review-0.49.77.tar.sig`.

Runtime tests and release evidence are in [TDD_EVIDENCE.md](TDD_EVIDENCE.md).
Issue #459 remains open for final acceptance; main promotion is PR #464.
Canonical archival awaits that acceptance and uses `openspec archive`.
Historical planned-maturity Requirements reports below are not retrospectively
promoted to verified lifecycle evidence.

## Historical planning validation (PR #461)

- Checked: 2026-09-06T22:17:24+02:00 (Europe/Berlin).
- Planning base: modules origin/dev commit 5772621922d0913cc8685e8bfddb7fa0c6364bcc.
- Issue: nold-ai/specfact-cli-modules#459; open and Todo.
- Delivery maturity: planned. Implementation evidence: not-yet-available.

## Verified planning checks

- `openspec validate code-review-installed-payload-layout --strict`: passed.
- `markdownlint --disable MD013 MD060 -- <changed Markdown files>`: passed.
  Line-length and table-layout style rules are omitted to match existing OpenSpec
  prose/table formatting; structural Markdown rules are checked.
- Staged `scripts/requirements_evidence_gate.py --required-maturity planned`:
  two sources passed, zero failed/skipped, observed maturity planned.
  The report is ignored local evidence under .specfact/reports/.
- `hatch run ruff check .` and `hatch run ruff format . --check`: passed;
  no Python files changed.
- `hatch run yaml-lint` and `hatch run check-bundle-imports`: passed.
- `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump --version-check-base origin/dev --public-key-file <installed-core-official-public-key>`:
  all seven manifests passed. The first invocation lacked a configured public
  key; rerunning with the installed core's bundled official verification key
  resolved that environment setup issue without bypassing verification.
- `scripts/pre_commit_code_review.py <staged paths>`: repository helper returned
  zero and explicitly skipped analyzer review because no .py/.pyi targets exist.
  No analyzer PASS or synthetic code-review JSON is claimed.
- `git diff --cached --check`: passed.

## Metadata and dependency review

Both issues have assignee djm81, parent feature #163, required labels, the
SpecFact CLI project, Todo status, and no milestone. Issue #459 has type Bug;
issue #460 has type User Story.

Native dependencies read back from GitHub: core #680 is blocked by #459
alongside its existing modules #431 prerequisite; #460 is blocked by
modules #459, modules #434, and core #679. Issue #459 has no open prerequisites.
No existing edges were removed. The added edges do not create a cycle.

## Historical planning acceptance boundary (PR `#461`)

This validates proposal structure, planned evidence, metadata, and artifact
integrity only. Runtime tests, native isolation prototypes, code changes, module
versioning/publication, and implementation PRs remain future unchecked tasks.
No runtime source, tests, runtime schemas, payload manifests, signatures, or
module registry files changed. The OpenSpec change order adds these two planning
proposals and updates the active-tree count from 20 to 22.

The planning PR uses Refs, leaves both issues open, and does not archive either
change. Native implementation awaits the released prerequisite/C15 baseline;
the layout correction remains upstream of core C14 adoption.

## PR review follow-up

Reviewed PR #461 at 9d99bb91ac9486c3905583a5e0b77285d5911c06;
follow-up checked 2026-09-06T22:34:17+02:00 (Europe/Berlin).

- Review 3945174715: clarified that runtime/module artifacts are unchanged while
  the OpenSpec change order is intentionally updated from 20 to 22 entries.
- Review 3945174727: restricted this capability to the installed-payload fix;
  native execution remains a separate dependency-linked proposal.
- Review 3945174726: preserved the existing no-follow/regular-file behavior and
  made root-bound copy-time checks explicit in the design and spec. Added two
  planned scenarios for entry-type and ancestor substitutions, with inspection
  cases and future test tasks. This does not claim a reproduced runtime exploit
  or an implemented copy-path fix.

Strict OpenSpec validation, structural Markdown checks, staged planned-maturity
Requirements evidence (two sources passed), and diff whitespace checks passed
for the revised contracts. Runtime tests remain unexecuted and all future
implementation tasks remain unchecked. No issue dependencies changed.
