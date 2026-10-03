# Native npm input preparation: bounded TDD evidence

Historical input-preparation record: 2026-10-01 (Europe/Berlin).
This section predates the implemented packager; see the dated addendum below. Baseline: modules origin/dev
`37b6000227ba4be353a4f1769e39e92073b1fced`.

## Scope and authority

The agent verified #460 OPEN/Todo, required labels/project, parent #163,
closed blocker #459 and refreshed the hierarchy before implementation. The main agent
reported unresolved native lifecycle feasibility and bounded independent progress
to a specification, exact npm lock and focused dependency tests. This records input
preparation only: **experimental, dependency admission pending, no production
eligibility**. No PR, commit, push, native packager or shipped runtime change.

## Spec -> RED -> inputs -> GREEN

1. Wrote NATIVE_NODE_CONTRACT.md before tests. Existing change passed
   `openspec validate code-review-native-platform-execution --strict`.
2. Initial broader packager tests returned 19 missing-implementation errors.
   No packager was implemented. Those tests were replaced to bound independent progress while the backend
   remained unresolved; they are not current acceptance evidence.
3. Wrote five focused tests in `tests/unit/test_native_node_inputs.py`, covering
   private/exact root dependency, closed dependency membership, npm artifact
   integrity and entrypoint, optional fsevents provenance/install-script fact,
   and install policy that disables scripts and omits optional dependencies.
4. RED command (before creating npm inputs):

   ```sh
   python3 -m unittest discover -s tests/unit -p test_native_node_inputs.py -v
   ```

   Result: **5 errors**, all FileNotFoundError for the absent input package.json.
   Raw local transcript: `/tmp/native-node-pins-red.txt` (ephemeral).
5. Added `scripts/native_node_inputs/package.json` and `.npmrc`, then generated
   the lock with host npm 11.19.1, without installing packages or running hooks:

   ```sh
   npm install --package-lock-only --ignore-scripts --omit=optional --no-audit --no-fund --cache /tmp/specfact-native-node-npm-cache --prefix scripts/native_node_inputs
   ```

6. GREEN: the same focused unittest command reports **5 passed**. Stdlib tests
   run under host CPython 3.14.7; no Hatch environment or global dependency change
   was needed. Final Ruff lint and format checks pass using the existing sibling
   worktree's Ruff binary, without changing that environment.

## Disposable install proof

Copied package.json, package-lock.json and .npmrc into a temporary directory and
ran `/opt/homebrew/bin/npm ci --ignore-scripts --omit=optional --no-audit
--no-fund --cache /tmp/specfact-native-node-npm-cache` there. Result: **added 1
package**. Independent assertions confirmed installed BasedPyright 1.39.10,
absence of fsevents and nodejs-wheel-binaries, and unchanged lock bytes. The
scratch installation was removed automatically. No analyzer was executed.
Host Node 26.10.0/npm were preparation tools, not the proposed authenticated
Darwin ARM64 Node 24.16.0 customer runtime.

Upstream HTTPS metadata for BasedPyright 1.39.10 and fsevents 2.3.3 was read on
2026-10-01. The generated lock matches the published sha512 integrity values.
BasedPyright has no mandatory npm dependencies; optional fsevents ~2.3.3 resolves
to 2.3.3 (MIT, Darwin, install script). Omitting it avoids installing its native
addon or node-gyp hook. This does not prove watch/language-server behavior.

## Limits and next owner action

Only focused tests, disposable npm installation, Ruff and strict OpenSpec
validation were run. Full repository/release gates were not run: this is an
explicitly bounded handoff, not merge-ready production evidence.

No historical Linux lock/artifact, module manifest/version/signature, global
Python dependency, runtime acceptance or lifecycle source was changed. Native
Node archive/publisher authentication, Mach-O/dylib closure, security/license
admission, native one-shot behavior parity, final signed capsule proof and
customer-install acceptance remain open. The contract's packager/native parity
scenarios remain planned; they must not be reported as green.

Historical input-only rollback: the six files below covered the initial
preparation. The implemented packager extends this list in the addendum.

- openspec/changes/code-review-native-platform-execution/NATIVE_NODE_CONTRACT.md
- openspec/changes/code-review-native-platform-execution/NATIVE_NODE_TDD.md
- scripts/native_node_inputs/package.json
- scripts/native_node_inputs/package-lock.json
- scripts/native_node_inputs/.npmrc
- tests/unit/test_native_node_inputs.py

## Packager implementation addendum — 2026-10-03 (Europe/Berlin)

The owner-authorized 2026-10-02 compatibility checkpoint implemented
`scripts/native_node_package.py` and its test suite. The preceding no-packager
and planned-scenario statements describe the historical input-only handoff,
not the current branch. The offline packaging and bounded native one-shot
scenarios in NATIVE_NODE_CONTRACT.md are implemented with passing evidence;
no runtime shipment or dependency-policy admission is claimed.

NATIVE_COMPATIBILITY_RESULTS.md records 23 missing-implementation RED tests,
the initial passing implementation and subsequent negative-test expansion to
32 packager tests. The five npm-input tests are additional. Two actual offline
builds produced the same 5,421-file manifest and passed clean/defective native
BasedPyright behavior. Final-artifact boundary, installation and production
eligibility remain unresolved.

Rollback of this complete experimental checkpoint also removes:

- scripts/native_node_package.py
- tests/unit/test_native_node_package.py
- scripts/native_node_inputs/README.md

Preserve the historical Linux runtime and all unrelated artifacts.
