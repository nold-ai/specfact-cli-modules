# Planning Validation

- Checked: 2026-09-06T22:17:24+02:00 (Europe/Berlin).
- Planning base: modules origin/dev commit 5772621922d0913cc8685e8bfddb7fa0c6364bcc.
- Issue: nold-ai/specfact-cli-modules#460; open and Todo.
- Delivery maturity: planned. Implementation evidence: not-yet-available.

## Verified planning checks

- `openspec validate code-review-native-platform-execution --strict`: passed.
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

## Acceptance boundary

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

- Reviews 3945174732 and 3945174737: distinguished full-module verification from
  separately provisioned native runtimes. Specified signed artifact/root,
  platform/ABI, dependency, and cache bindings before launch/offline reuse.
  Added five planned integrity scenarios and matching inspection cases.
- Review 3945174730: rechecked PyPI metadata for nodejs-wheel-binaries 24.16.0;
  native macOS ARM64 and Windows x64 wheels exist. Clarified the exact package
  name and cited its artifacts. The suggestion to replace this wheel evidence
  with upstream Node.js archives was not adopted because it changes the source
  of the verified evidence.
- Removed the shared generic capability wording so this proposal covers native
  execution and keeps the installed-payload correction as a prerequisite.

Strict OpenSpec validation, structural Markdown checks, staged planned-maturity
Requirements evidence (two sources passed), and diff whitespace checks passed
for the revised contracts. Runtime tests remain unexecuted and all future
implementation tasks remain unchecked. No issue dependencies changed.
