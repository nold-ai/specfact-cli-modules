## 1. Specification and scope

- [x] 1.1 Create an isolated worktree from merged `origin/dev`.
- [x] 1.2 Define the manual-dispatch paired-core trust boundary and explicit
  non-goals before workflow edits.
- [x] 1.3 Record the `SECURITY.md` exception to public issue tracking; keep
  alert-specific evidence in private GitHub Security records.
- [x] 1.4 Strictly validate the OpenSpec change.

## 2. Test-first evidence

- [x] 2.1 Add focused contract tests for non-manual matching-branch behavior and
  literal manual `main`/`dev` checkout behavior in all three workflows.
- [x] 2.2 Run the focused tests before workflow edits and record the expected
  failure in `TDD_EVIDENCE.md`.

## 3. Bounded implementation

- [x] 3.1 Guard each dynamic core-ref resolver and checkout from manual events.
- [x] 3.2 Add mutually exclusive literal `main` and `dev` paired-core checkout
  steps for manual events.
- [x] 3.3 Confirm module packages, manifests, registry data, dependency files,
  and C14 release artifacts remain unchanged.

## 4. Verification and review

- [x] 4.1 Run focused tests, workflow/YAML lint, and strict OpenSpec validation.
- [x] 4.2 Record passing and quality evidence in `TDD_EVIDENCE.md`.
- [x] 4.3 Run fresh SpecFact changed-scope and final review evidence; resolve all
  findings or document an approved exception.
- [x] 4.4 Open a narrowly scoped PR to `dev` without public alert details.
- [x] 4.5 After merge, archive with
  `openspec archive ci-01-workflow-dispatch-core-ref-trust`.
