## 1. Specification and regression setup

- [x] 1.1 Create the command-overview compatibility delta and design.
- [x] 1.2 Add focused Typer 0.27 option and argument regression coverage.
- [x] 1.3 Run the new test before production edits and record failing evidence.

## 2. Implementation and artifacts

- [x] 2.1 Update command-parameter classification for the supported Typer
  runtime without changing public command behavior.
- [x] 2.2 Regenerate `llms.txt` and command-reference artifacts under the Docs
  Review dependency set.
- [x] 2.3 Record passing evidence in `TDD_EVIDENCE.md`.

## 3. Verification and review

- [x] 3.1 Run strict OpenSpec validation and the focused Docs Review tests.
- [x] 3.2 Run applicable formatting, lint, docs, and generated-artifact gates.
- [x] 3.3 Run changed-line SpecFact code review with `--bug-hunt`, resolve all
  findings, and record the result.
