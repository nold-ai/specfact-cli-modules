# Reconstructed #472 conditions

This controlled fixture models the reported detached Hatch environment, `src/` layout,
additional source root, explicit asyncio plugin, importlib mode, third-party dependency,
and native `pyodbc` import. It is not the original customer repository or a claim that
its underlying PR has been reproduced. No network request or database connection occurs.

Select Hatch environment `review` and declare `libodbc.so.2` in the external runtime
configuration. The deliberately incompatible default pytest constraint must not leak
into the detached review environment. Validation runs both the native host tests and
capsule review, with the configuration stored outside the fixture source.

The same test slice also launches real nested `sys.executable` processes. It checks
inherited environment values, explicit additions/overrides/removals (including `HOME`),
a minimal environment without runtime markers, attached Python/native imports with
`env={}`, relative helpers and data under pytest's `tmp_path`, and caller-owned open
temporary files in both the default location and explicit `/tmp`. The detached fixture
does not install its source package, so the empty-environment child explicitly adds the
source directory before importing it, just as a native Python caller must. Children must
share the caller's working directory and temporary filesystem while retaining the capsule's existing
isolation. These assertions run unchanged in host, cold capsule, and offline warm
capsule validation; local host execution alone does not establish capsule acceptance.
