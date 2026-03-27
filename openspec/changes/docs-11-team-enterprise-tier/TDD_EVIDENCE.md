# TDD Evidence

## Verification Evidence

### 0. Failing evidence

Pre-implementation failing snapshot from the branch state before the `team-and-enterprise` pages existed.

Command intended for the missing-page state:

```bash
python3 -m pytest tests/unit/docs/test_docs_review.py::test_team_and_enterprise_pages_exist -q
```

Recorded failure excerpt:

```text
FAILED tests/unit/docs/test_docs_review.py::test_team_and_enterprise_pages_exist - AssertionError: Missing team-and-enterprise docs pages
1 failed in 0.12s
```

### 1. Command example verification

Acceptance coverage:
- Task 4.1 Verify all command examples match actual CLI

Command verification run on `2026-03-27T22:54:10+01:00`:

```bash
specfact init --help
specfact init ide --help
specfact project --help
specfact project init-personas --help
specfact project export --help
specfact project import --help
specfact project lock --help
specfact project locks --help
specfact project merge --help
specfact project sync bridge --help
specfact module --help
specfact module init --help
specfact module add-registry --help
specfact module list-registries --help
```

Verified command surface referenced by the new pages:

```text
specfact init --profile backlog-team
specfact init --profile enterprise-full-stack
specfact init ide --repo . --ide cursor
specfact project init-personas --bundle legacy-api --no-interactive
specfact project export --bundle legacy-api --repo .
specfact project import --bundle legacy-api --repo .
specfact project lock
specfact project locks
specfact project merge --repo . --source main --target release
specfact project sync bridge --repo .
specfact module init --scope project --repo .
specfact module add-registry <url> --id company --priority 10 --trust always
specfact module list-registries
```

Outcome:

```text
All referenced commands/options were present in the current CLI help output.
```

### 2. Team-and-enterprise page coverage

Acceptance coverage:
- Task 4.2 Verify team/enterprise docs describe migrated resources as bundle-owned rather than core-owned

Command run on `2026-03-27T22:54:10+01:00`:

```bash
python3 -m pytest tests/unit/docs/test_docs_review.py::test_team_and_enterprise_pages_exist tests/unit/docs/test_docs_review.py::test_team_and_enterprise_pages_use_bundle_owned_resource_language tests/unit/docs/test_docs_review.py::test_team_and_enterprise_index_links_exist -q
```

Passing excerpt:

```text
...                                                                      [100%]
3 passed in 0.68s
```

### 3. Internal-link validation

Acceptance coverage:
- Task 4.3 Verify all internal links resolve

Command run on `2026-03-27T22:54:10+01:00`:

```bash
python3 -m pytest tests/unit/docs/test_docs_review.py -q
```

Passing excerpt:

```text
tests/unit/docs/test_docs_review.py .................                    [100%]
======================== 17 passed, 2 warnings in 0.36s ========================
```

Notable details:

```text
The two warnings are the pre-existing repository-wide warnings already tolerated by the docs review suite:
- pre-existing docs files missing front matter
- pre-existing broken authored docs links outside the docs-11 scope
No new docs-11 failures or link-resolution regressions were introduced.
```

### 4. Jekyll build evidence

Acceptance coverage:
- Task 4.4 Run `bundle exec jekyll build` with zero warnings

Dependency bootstrap run on `2026-03-27T22:54:10+01:00`:

```bash
bundle install
```

Install excerpt:

```text
Bundle complete! 9 Gemfile dependencies, 41 gems now installed.
Bundled gems are installed into `./vendor/bundle`
```

Build command run on `2026-03-27T22:54:10+01:00`:

```bash
bundle exec jekyll build --destination ../_site
```

Build excerpt for acceptance item `4.4 Run bundle exec jekyll build with zero warnings`:

```text
Configuration file: /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-11-team-enterprise-tier/docs/_config.yml
            Source: /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-11-team-enterprise-tier/docs
       Destination: /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/docs-11-team-enterprise-tier/_site
 Incremental build: disabled. Enable with --incremental
      Generating...
       Jekyll Feed: Generating feed for posts
                    done in 1.51 seconds.
 Auto-regeneration: disabled. Use --watch to enable.
```

Verification statement:

```text
The build completed successfully and emitted no warning lines.
```

### 5. Code review gate

Acceptance coverage:
- Quality gate requirement: `specfact code review run` has 0 findings

Command run on `2026-03-27T22:57:30+01:00`:

```bash
specfact code review run tests/unit/docs/test_docs_review.py --no-tests
```

Passing excerpt:

```text
Code Review
Review completed with no findings.
Verdict: PASS | CI exit: 0 | Score: 120 | Reward delta: 40
```

### 6. Repository quality gates

Command sequence run after the docs-11 changes were in place:

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

Outcome summary:

```text
hatch run format -> All checks passed! 350 files left unchanged
hatch run type-check -> 0 errors, 0 warnings, 0 notes
hatch run lint -> All checks passed! / Your code has been rated at 10.00/10
hatch run yaml-lint -> Validated 6 manifests and registry/index.json
hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump -> Verified 6 module manifest(s).
hatch run contract-test -> 423 passed, 2 warnings in 39.56s
hatch run smart-test -> 423 passed, 2 warnings in 38.08s
hatch run test -> 423 passed, 2 warnings in 39.34s
```

Note:

```text
The repeated 2-warning count comes from the pre-existing docs review warnings already tolerated by the suite, not from the docs-11 additions.
```
