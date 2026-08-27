## 1. Scope and specification

- [x] 1.1 Create an isolated bugfix worktree from current `origin/dev`.
- [x] 1.2 Verify the current GitHub Security records against repository code and
  identify the shared workflow trigger/check-out boundary.
- [x] 1.3 Define the manual-trigger removal, compatibility limit, and rollback
  before workflow edits.
- [x] 1.4 Strictly validate this OpenSpec change.

## 2. Test-first evidence

- [x] 2.1 Update focused workflow contracts to require trigger isolation while
  preserving pull-request/push matching-branch behavior.
- [x] 2.2 Run the focused suite before workflow edits and record the expected
  failure in `TDD_EVIDENCE.md`.

## 3. Minimal implementation

- [x] 3.1 Remove `workflow_dispatch` and dead manual checkout steps from all
  three mixed-trust workflows.
- [x] 3.2 Confirm module packages, manifests, registry data, dependency files,
  signatures, and release artifacts remain unchanged.

## 4. Verification and review

- [x] 4.1 Run focused workflow tests, `actionlint`, YAML lint, and strict
  OpenSpec validation; record passing evidence.
- [x] 4.2 Run format, type, lint, bundle-import, signature/version, contract,
  smart-test, test, and changed-scope SpecFact code-review gates.
- [x] 4.3 Run one independent bypass/regression review and resolve every
  source-backed finding within scope.
- [x] 4.4 Ensure `.specfact/code-review.json` is fresh and records a passing
  changed-scope review with `--bug-hunt`.

## 5. Delivery

- [x] 5.1 Commit the bounded change with a signed Conventional Commit.
- [x] 5.2 Push the bugfix branch and open a sanitized PR to `dev`.
- [ ] 5.3 Confirm required PR checks, including Actions CodeQL analysis, pass;
  inspect the private GitHub Security records for closure.
- [ ] 5.4 After merge, archive only with
  `openspec archive ci-02-codeql-cache-scope-isolation`.
