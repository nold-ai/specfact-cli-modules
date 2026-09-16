# PR #478: BasedPyright Node distribution ownership

On 2026-09-16, the canonical scenario `BasedPyright preserves its actual sealed
Node distribution` preceded the regression tests and production correction.

## Dependency evidence

BasedPyright 1.39.10's actual wheel metadata declares
`Requires-Dist: nodejs-wheel-binaries>=20.13.1`; its `run_node.py` imports
`nodejs_wheel.executable`. The exact wheel was read from the
[PyPI release metadata](https://pypi.org/pypi/basedpyright/1.39.10/json)
(accessed 2026-09-16), SHA-256
`cbd75d83c0be841329bcfef2d2f1182f152a6d975b8eb199e75cf5b8e9a3de78`.
The signed toolchain selects `nodejs-wheel-binaries==24.16.0`; the observed
project inventory selected 24.19.0.

An isolated host reproduction used the real wheel metadata and import code with
production dependency-graph, mount-selection, and verified-finder APIs. Before
the correction, the graph chose project ownership, omitted `nodejs_wheel` from
the member mount, and the actual import raised
`project_worker_analyzer_origin_mismatch:nodejs_wheel`. This independently proves
the domain defect; it does not prove the cause of a prior native run without
that run's raw diagnostic. It does not claim Linux namespace execution.

## Failing-first and passing evidence

The regression command was:

```sh
SPECFACT_CLI_REPO=/private/tmp/specfact-473-core .venv/bin/python -m pytest \
  tests/unit/specfact_code_review/run/test_runtime_compatibility.py \
  -k 'node_' -q --tb=short
```

Before the production edit, `PR478_NODE_DOMAIN_RED.txt` records two genuine
failures: the missing explicit version-conflict diagnostic and the matching
version's failed verified import. Two preservation controls passed: no project
Node and an unrelated project distribution named `nodejs-wheel`.

Only the member distribution name changed in production, from `nodejs-wheel`
to `nodejs-wheel-binaries`. A different project version now gets an explicit
member incompatibility; no project version is silently substituted. Matching
and absent project versions retain the sealed package and metadata mount.

The compatibility, runtime-domain, and target-launch test files subsequently
passed together: **87 passed in 11.66 seconds**, macOS, Python 3.14.7,
pytest 9.1.1. Ruff check and format check passed. New test/helper complexity is
at most nine. The real Linux native review remains an integration gate owned
by the parent task; these focused checks are not a capsule acceptance claim.
