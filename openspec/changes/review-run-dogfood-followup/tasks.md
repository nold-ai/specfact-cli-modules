# Tasks: review-run dogfood follow-up

## 1. Setup and reproduction

- [x] 1.1 Create branch `bugfix/review-run-dogfood-followup` from `dev`
- [x] 1.2 Run `specfact code review run` against representative modules-repo Python sources and capture the failure mode

## 2. TDD follow-up

- [x] 2.1 Add or update a targeted regression test that reproduces the dogfood failure
- [x] 2.2 Record failing evidence in `TDD_EVIDENCE.md`

## 3. Fix the runtime gap

- [x] 3.1 Implement the minimal `specfact-code-review` fix required by the repo dogfood run
- [x] 3.2 Align `--json` help and behavior with file-based output conventions
- [x] 3.3 Add a repo-local helper for linking a dev module into a runtime validation shadow root
- [x] 3.4 Re-run the targeted regression test and the repo dogfood command successfully

## 4. Evidence

- [x] 4.1 Record passing evidence in `TDD_EVIDENCE.md`
- [x] 4.2 Run targeted validation for the touched review-run paths

## 5. Second-layer dogfooding follow-up

- [x] 5.1 Add configurable suppression for known low-signal review noise
- [x] 5.2 Add interactive prompting for whether tests should be included in review scope
- [x] 5.3 Update the bundled code-review skill to ask whether tests should be included
- [x] 5.4 Add focused tests and validation evidence for the new behavior

## 6. Review progress feedback

- [x] 6.1 Add live progress feedback for long-running review execution
- [x] 6.2 Validate that progress feedback preserves the existing stdout contract

## 7. Untracked file review scope

- [x] 7.1 Include untracked Python files in auto-detected review scope
- [x] 7.2 Validate that untracked AI-generated files are reviewed before staging
- [x] 7.3 Clean the newly exposed script/test review debt and revalidate the review flow
