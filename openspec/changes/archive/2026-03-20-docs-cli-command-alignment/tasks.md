## 1. Audit

- [x] 1.1 Capture the current mounted command surface from `hatch run specfact --help` and relevant subcommand help
- [x] 1.2 Compare central reference and install docs against the mounted command surface and module manifests

## 2. Docs Updates

- [x] 2.1 Update command-reference pages to use current mounted command groups
- [x] 2.2 Update installation and module-management guides to use official `nold-ai/...` package ids
- [x] 2.3 Update getting-started pages that still advertise removed or unmapped command paths
- [x] 2.4 Add an OpenSpec delta requiring docs command examples to match the mounted CLI surface

## 3. Verification

- [x] 3.1 Re-run focused `specfact --help` checks for every command family documented in the edited pages
- [x] 3.2 Re-run targeted repo searches for stale command prefixes in the edited pages
- [x] 3.3 Record verification evidence in `TDD_EVIDENCE.md`
