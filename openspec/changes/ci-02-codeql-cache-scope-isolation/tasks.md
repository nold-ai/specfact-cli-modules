## 1. Scope and specification

- [x] 1.1 Create an isolated bugfix worktree from current `origin/dev`.
- [x] 1.2 Verify the current GitHub Security records against repository code and
  identify the shared workflow trigger/check-out boundary.
- [x] 1.3 Define the manual-trigger removal, compatibility limit, and rollback
  before workflow edits.
- [x] 1.4 Strictly validate this OpenSpec change.
- [x] 1.5 Confirm the exact-only metadata is a runtime installer boundary and
  define evidence-backed range semantics.

## 2. Test-first evidence

- [x] 2.1 Update focused workflow contracts to require trigger isolation while
  preserving pull-request/push matching-branch behavior.
- [x] 2.2 Run the focused suite before workflow edits and record the expected
  failure in `TDD_EVIDENCE.md`.
- [x] 2.3 Add focused contracts for the minimum, later compatible versions, and
  immutable minimum-version CI evidence.
- [x] 2.4 Run those contracts before manifest/workflow implementation and
  record the expected failures.

## 3. Minimal implementation

- [x] 3.1 Remove `workflow_dispatch` and dead manual checkout steps from all
  three mixed-trust workflows.
- [x] 3.2 Confirm module packages, manifests, registry data, dependency files,
  signatures, and release artifacts remain unchanged.
- [x] 3.3 Replace the exact-only runtime constraint with the dependency-bounded
  `>=0.55.1,<1.0.0` range and apply the required patch
  version/checksum/signature flow.
- [x] 3.4 Reframe the immutable 0.55.1 workflow as minimum-version evidence and
  keep current paired-core marketplace validation.
- [x] 3.5 Correct active change-order guidance without rewriting historical C14
  evidence or frozen provenance identities.

## 4. Verification and review

- [x] 4.1 Run focused workflow tests, `actionlint`, YAML lint, and strict
  OpenSpec validation; record passing evidence.
- [x] 4.2 Run format, type, lint, bundle-import, signature/version, contract,
  smart-test, test, and changed-scope SpecFact code-review gates.
- [x] 4.3 Run one independent bypass/regression review and resolve every
  source-backed finding within scope.
- [x] 4.4 Ensure `.specfact/code-review.json` is fresh and records a passing
  changed-scope review with `--bug-hunt`.
- [x] 4.5 Run focused compatibility tests, strict OpenSpec validation, publish
  precheck, and the required quality sequence.
- [x] 4.6 Run independent pre-patch and post-patch fix reviews and resolve every
  source-backed finding in scope.
- [x] 4.7 Address PR review findings with specification-first updates, focused
  failing/passing evidence, and refreshed signature verification.

## 5. Delivery

- [x] 5.1 Commit the bounded change with a signed Conventional Commit.
- [x] 5.2 Push the bugfix branch and open a sanitized PR to `dev`.
- [ ] 5.3 Confirm required PR checks, including Actions CodeQL analysis, pass;
  inspect the private GitHub Security records for closure.
- [ ] 5.4 After merge, archive only with
  `openspec archive ci-02-codeql-cache-scope-isolation`; if C14 remains active,
  record this change as the later compatibility authority and require C14's
  eventual archive to preserve or be followed by this supersession.
- [ ] 5.5 Confirm the signing bot updates the PR manifest and the post-merge
  publisher opens the immutable registry publication PR.
