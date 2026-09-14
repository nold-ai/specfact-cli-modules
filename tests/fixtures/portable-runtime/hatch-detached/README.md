# Reconstructed #472 conditions

This controlled fixture models the reported detached Hatch environment, `src/` layout,
additional source root, explicit asyncio plugin, importlib mode, third-party dependency,
and native `pyodbc` import. It is not the original customer repository or a claim that
its underlying PR has been reproduced. No network request or database connection occurs.

Select Hatch environment `review` and declare `libodbc.so.2` in the external runtime
configuration. The deliberately incompatible default pytest constraint must not leak
into the detached review environment. Validation runs both the native host tests and
capsule review, with the configuration stored outside the fixture source.
