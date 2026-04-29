## Design
The command registry loads bundle command groups from `module-package.yaml` `commands`. `plan` exists as implemented runtime surface, but without manifest declaration it is not registered for delegation.

The fix is manifest-first and docs alignment, with a regression test that inspects bundle metadata.
