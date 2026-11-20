# Post-rotation quality CI

## Before

The dev push at `c8e5178` failed with four Ruff SIM102 diagnostics and `Smoke fixture identity does not match the reviewed commit`. Running Ruff 0.17.6 on the exact module and paired core files reproduced all four diagnostics. Calling the core smoke script with the dev modules checkout reproduced the commit mismatch.

The workflow regression run failed five cases because Ruff was unbounded and the quality job did not read or check out the reviewed fixture. The paired core lock specifies Ruff 0.16.0. With that version, both dev trees pass Ruff lint and formatting at the reproduced revisions.
