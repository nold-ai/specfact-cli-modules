# macOS ARM64 feasibility gate

## Status and decision rule

Planned, 2026-09-30 Europe/Berlin. No native prototype, runtime test, backend approval or support claim is recorded here. This document is the execution contract for the next milestone.

Run harmless fixtures on native ARM64 macOS under an ordinary user. Compare a minimal signed Seatbelt helper and an App Sandbox alternative. Record exact OS build, hardware/process architecture, Python ABI, core/module/runtime/artifact/policy identities, command, expected outcome, observed outcome and diagnostic. Negative cases require a successful positive control; parser/startup failure is not confinement proof.

CPython 3.11–3.13 is the candidate matrix. Enumerate available macOS builds before execution; advertise only the tested combinations. Include a physical-Mac smoke and distinguish CI virtualization from application dependence on a VM. No Rosetta or emulated interpreter/library satisfies native acceptance.

## Required proof groups

| Group | Positive control | Negative/adverse cases | Required decision evidence |
|---|---|---|---|
| Launch and loading | Signed helper starts native interpreter and admitted extension | Missing helper, x64-only binary, dyld injection, pre-confinement initializer, inherited FD/IPC access | Confinement active before untrusted code; explicit Apple system-library allowance and actual load origins |
| Filesystem and network | Declared input read and private output write succeed | Host secret canaries, writes outside roots, symlink redirection, outbound/listening sockets, inherited sockets and undeclared IPC | Denial attributable to policy; source and sealed payload unchanged |
| Lifecycle and bounds | Normal worker/child completes | Timeout, cancel, controller death, fork/setsid descendants, resource exhaustion | Independent survivor detection, measured cleanup bounds and enforced numeric limits |
| Project preparation | Pinned pip/pip-tools, Hatch, uv and Poetry projects build/test with plugins and coverage | Build hook host access, credential access, undeclared downloads, incompatible extensions | Separate acquisition/build/analysis policies and preserved project pins |
| Native closure | ARM64 extension and declared dylibs load | Missing or wrong-slice dependency, unsafe rpath, substituted dylib, prohibited Node package | Complete policy-admitted Mach-O/Python closure and loader behavior |
| Cache and integrity | Cold install and verified offline warm use | Corrupt, stale, unbound, mixed, interrupted and concurrent caches; verification-to-use swaps | Atomic publication, no partial reuse, race-resistant launch and policy-bound identities |
| Customer distribution | Fresh signed install through documented CLI | Quarantine, signing/notarization failure, third-party extension rejection, paths with spaces/Unicode, case-insensitive APFS and permissions | Actual delivery route works without sudo, signature bypasses or disabling protections |
| Review and regression | Full required analyzer set and real external test slices | Deliberate defects, skipped/empty required evidence, unsupported consumer | Expected released verdicts, honest OS-specific outcomes and passing Linux regression matrix |

## Admission and production approval checklist

- Resolve BasedPyright's direct prohibited Node distribution dependency and the complete native closure; audit replacement metadata, provenance, licenses and build inputs.
- Identify any concrete report/runtime consumer incompatibility and the bounded paired change needed. C15 is not a blanket prerequisite.
- Freeze the backend and profile version, exact supported macOS/ABI matrix, runtime sources, Apple signing/distribution method, trust boundaries, observation limits and numeric lifecycle/resource bounds.
- Record all group results and outstanding failures. A required failure or unresolved capability means no production approval; retain evidence and propose a reviewed correction.
- Approve a bounded production design only after required feasibility groups pass. Final analyzer corpus and public signed-installation acceptance must be repeated on the production candidate/publication.
- Use current-run results and concise notes. Planned requirements inspection is not executable proof, and no historical RED ledger or optional seal is required.
