# Post-rotation quality CI

## Before

The dev push at `c8e5178` failed with four Ruff SIM102 diagnostics and `Smoke fixture identity does not match the reviewed commit`. Running Ruff 0.17.6 on the exact module and paired core files reproduced all four diagnostics. Calling the core smoke script with the dev modules checkout reproduced the commit mismatch.

The workflow regression run failed five cases because Ruff was unbounded and the quality job did not read or check out the reviewed fixture. The paired core lock specifies Ruff 0.16.0. With that version, both dev trees pass Ruff lint and formatting at the reproduced revisions.

## After

The five new workflow cases and the 12 existing workflow cases pass. Ruff 0.16.0 and actionlint pass for the modules checkout. The paired core dependency-trust check and locked cache warmup pass.

The unchanged core verifier authenticates fixture commit `046d366`, verifies its tree, and builds a scratch registry from all seven 0.55.4 cutoff archives. Strict signature and version verification also passes for all seven source manifests in a clean modules checkout.

The local six-launcher run reached the frozen wheel download after fixture verification and the offline child dependency sync. The download hit the existing 180-second timeout before the first launcher completed. This is partial execution evidence.
