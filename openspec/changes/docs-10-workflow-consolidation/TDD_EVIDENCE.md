# TDD Evidence

## Verification Evidence

### 0. Failing evidence

N/A on this documentation consolidation branch. The failing state was the pre-existing legacy workflow-note stubs and fragmented brownfield pages that no longer matched the mounted CLI surface. The obsolete state was captured directly in the replaced files under `docs/guides/` before implementation on `feature/docs-10-workflow-consolidation`.

### 1. Command surface verification

Verified the command examples used in the new workflow pages against live `--help` output on 2026-03-27:

- `specfact spec --help`
- `specfact spec validate --help`
- `specfact backlog ceremony standup --help`
- `specfact backlog refine --help`
- `specfact backlog verify-readiness --help`
- `specfact code import --help`
- `specfact code analyze contracts --help`
- `specfact code review run --help`
- `specfact project sync bridge --help`
- `specfact govern enforce --help`
- `specfact govern enforce sdd --help`
- `specfact init ide --help`

### 2. Internal docs validation

Command run:

```bash
python3 -m pytest tests/unit/docs/test_docs_review.py -q
```

Result:

- `14 passed`
- only pre-existing repository warnings remained for unrelated docs front matter and legacy authored links

### 3. Legacy prompt/template path verification

Searched the new workflow-guide set for legacy core-owned prompt/template path patterns (`.cursor/`, `.claude/`, `.specify/`, `.github/prompts`, `.github/instructions`, `.specfact/prompts`).

Result:

- no legacy core-owned prompt or template paths were referenced in the new workflow docs

### 4. Acceptance item 5.4: `bundle exec jekyll build` with zero warnings

Verification statement:

- At `2026-03-27T22:27:11+01:00`, `bundle exec jekyll build --destination ../_site` completed successfully for this branch.
- The command output contained the normal Jekyll build summary and no warning lines on stdout/stderr.

Terminal excerpt:

```text
Configuration file: /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-10-workflow-consolidation/docs/_config.yml
            Source: /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-10-workflow-consolidation/docs
       Destination: /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-10-workflow-consolidation/_site
 Incremental build: disabled. Enable with --incremental
      Generating...
       Jekyll Feed: Generating feed for posts
                    done in 1.479 seconds.
 Auto-regeneration: disabled. Use --watch to enable.
```

### 5. `specfact code review run` clean pass

Command run:

```bash
specfact code review run \
  tests/unit/docs/test_missing_command_docs.py \
  tests/unit/docs/test_bundle_overview_cli_examples.py \
  --no-tests
```

Result:

- `Review completed with no findings.`
- `Verdict: PASS | CI exit: 0 | Score: 120 | Reward delta: 40`

### 6. Repository quality gates

Completed in repository order:

```bash
hatch run format
hatch run type-check
hatch run lint
hatch run yaml-lint
hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump
hatch run contract-test
hatch run smart-test
hatch run test
```

Result:

- all commands exited successfully on `feature/docs-10-workflow-consolidation`
- `contract-test`, `smart-test`, and `test` each passed the full `420` test cases
