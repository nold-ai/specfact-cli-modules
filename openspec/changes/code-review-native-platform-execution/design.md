# Design: Native Local Code Review Across macOS Linux and Windows

## Product boundary

The developer or agent invokes the normal CLI in its native project environment on macOS, Linux, or Windows. Local invocation does not require GitHub, an agent vendor, Docker, WSL, a Linux VM, or OS/CPU emulation. An ordinary virtual environment is permitted; it does not abstract away the host OS. OS-native isolation is allowed.

Target architecture coverage is x64 and ARM64 for each OS. Before implementation, publish a matrix of OS versions, Python ABIs, analyzers, runtime artifacts, and isolation capabilities. Missing native dependency coverage is an explicit unresolved requirement, never permission to substitute emulation or claim support. Exact minimum OS versions and production backends are deliberately unapproved until prerequisite baseline reassessment.

## Current coupling and feasibility evidence

C14 hardcodes Linux x86-64 environment IDs, native Bubblewrap descriptors, /proc mapping/file-descriptor observation, Linux ptrace, and capsule/project-runtime paths. The runner, toolchain, sandbox, locks, project-runtime provenance, and protected consumers must be assessed together; merely allowing another platform name is insufficient.

PyPI metadata checked 2026-09-06 shows native macOS ARM64 and Windows x64 wheels for Semgrep 1.144.0, CrossHair 0.0.109, Z3 5.1.0.0, and Node 24.16.0. This proves artifact availability only. CrossHair 0.0.109 lacks Linux ARM64 wheels; Z3 5.1.0.0 uses manylinux_2_38 for Linux ARM64. Recheck the complete dependency closure and build provenance after baseline release.

Primary references: [Semgrep native platforms](https://semgrep.dev/blog/2025/five-considerations-when-building-cross-platform-tools-for-windows-and-macos/), [CrossHair artifacts](https://pypi.org/project/crosshair-tool/0.0.109/#files), [Z3 artifacts](https://pypi.org/project/z3-solver/5.1.0.0/#files), and [platform tag meaning](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/). Accessed 2026-09-06.

## Architecture decisions deferred to the released baseline

Keep Git scope, policy selection, differential classification, C15 enforcement/waiver semantics, and machine-readable output portable. Define a bounded backend interface for capabilities, verified provisioning, launch, observation, cleanup, and result identity. Package platform-specific Python/native analyzer runtimes with signed manifests and offline reuse after provisioning; never use ambient dependencies as an unreported substitute for pinned evidence.

Evaluate Linux Bubblewrap, a signed native macOS sandbox helper, and Windows AppContainer/process lifecycle controls with harmless conformance fixtures. These are candidates, not approved implementations. [Apple App Sandbox](https://developer.apple.com/documentation/security/protecting-user-data-with-app-sandbox) and [Microsoft AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation) describe native primitives; neither establishes parity with C14's Linux-specific contract by itself. Accessed 2026-09-06.

Approve a common behavioral capability contract and platform-specific attestation details after native prototypes prove filesystem/network policy, process-tree cleanup, resource bounds, load-path integrity, and unattended operation. Record limits honestly; sanitized environment variables alone are not OS isolation. No unsupported capability or omitted required analyzer can become PASS through fallback.

## Baseline gate and evidence lifecycle

Implementation is deferred until #459 is corrected, #434 is published with install readback, and core #679 has adopted the released C15 module #417. Pin exact core/module versions, commits, signed artifacts, policy/profile, and available preflight/checkpoint/conformance identities. Reassess this proposal using that baseline, refine material scope/interfaces with user review, and obtain the required current approval/seal before production edits.

Before implementation, map requirements and risks to native tests and record failing evidence. During implementation, use the released checkpoint surface and record every meaningful change. At completion, use final conformance and native OS/architecture runners, then verify published installation. A changed baseline or release artifact invalidates affected evidence.

## Compatibility and release

Do not rewrite historical C14 schemas, profiles, or checkpoint digests. Any new portable profile/report/runtime identity contract must be explicitly versioned and paired with core consumer scope before coding. Preserve C15 authoritative status/exit semantics and the distinction between local evidence and protected CI promotion.

A future release requires verified native artifacts, complete dependency identities, appropriate semver/core compatibility, canonical signing/registry publication, and install readback. Roll out only proven platform combinations; unproven combinations remain open acceptance gaps. Withhold or revert a faulty platform publication without relabeling historical Linux evidence. No runtime, schema, version, registry, or support claim changes in this planning PR.
