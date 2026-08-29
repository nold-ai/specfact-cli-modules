## 1. Governance and Scope

- [x] 1.1 Create bug issue #452 with Bug type, labels, assignee, parent Epic #162, project assignment, In Progress status, and explicit no-blocker metadata.
- [x] 1.2 Cross-link paired core bug nold-ai/specfact-cli#699 and confirm no active change owns this corrective scope.
- [x] 1.3 Add and strictly validate the paired OpenSpec change before behavior edits.
- [x] 1.4 Keep the internal wiki source mirror aligned with both active public changes.

## 2. Tests Before Implementation

- [x] 2.1 Add a failing regression test for non-destructive development-bootstrap guidance.
- [x] 2.2 Add a failing regression test for non-destructive repository rule guidance.
- [x] 2.3 Rename the local import-isolation test so it does not imply filesystem uninstall behavior.
- [x] 2.4 Record the failing-before command and result in `TDD_EVIDENCE.md` before production edits.

## 3. Implementation

- [x] 3.1 Update the development bootstrap docstring to preserve shadowed user installations.
- [x] 3.2 Update repository context guidance to explain workspace-local precedence and no-action behavior.
- [x] 3.3 Keep registry, manifests, signed module payloads, and explicit uninstall behavior unchanged.

## 4. Evidence and Delivery

- [x] 4.1 Run focused passing tests and record passing-after evidence.
- [x] 4.2 Run format, type-check, lint, yaml-lint, bundle-import, contract, smart-test, full test, and applicable signature gates; document reproducible `origin/dev` baseline failures.
- [x] 4.3 Run SpecFact changed-scope bug-hunt review, resolve every finding, and record fresh JSON evidence.
- [ ] 4.4 Commit with a signed Conventional Commit, push the bugfix branch, and open a PR to `dev` cross-linked to both issues and the paired core PR.
