# Design: Native Local Code Review Across macOS Linux and Windows

## Product boundary

The developer or agent invokes the normal CLI in its native project environment on macOS, Linux, or Windows. Local invocation does not require GitHub, an agent vendor, Docker, WSL, a Linux VM, or OS/CPU emulation. An ordinary virtual environment is permitted; it does not abstract away the host OS. OS-native isolation is allowed.

Target architecture coverage is x64 and ARM64 for each OS. Before implementation, publish a matrix of OS versions, Python ABIs, analyzers, runtime artifacts, and isolation capabilities. Missing native dependency coverage is an explicit unresolved requirement, never permission to substitute emulation or claim support. Exact minimum OS versions and production backends are deliberately unapproved until prerequisite baseline reassessment.

## Current coupling and feasibility evidence

C14 hardcodes Linux x86-64 environment IDs, native Bubblewrap descriptors, /proc mapping/file-descriptor observation, Linux ptrace, and capsule/project-runtime paths. The runner, toolchain, sandbox, locks, project-runtime provenance, and protected consumers must be assessed together; merely allowing another platform name is insufficient.

PyPI metadata checked 2026-09-06 shows native macOS ARM64 and Windows x64 wheels for Semgrep 1.144.0, CrossHair 0.0.109, and Z3 5.1.0.0. This proves artifact availability only, not dependency-policy admission. CrossHair 0.0.109 lacks Linux ARM64 wheels; Z3 5.1.0.0 uses manylinux_2_38 for Linux ARM64. Recheck the complete dependency closure and build provenance after baseline release.

The `nodejs-wheel-binaries` 24.16.0 PyPI distribution also has macOS ARM64 and Windows x64 wheels, but it is **rejected feasibility evidence**, not an admissible native dependency source. The wheel evidence describes that distribution only; it does not establish approval of upstream Node.js release archives or any replacement.

Primary references: [Semgrep native platforms](https://semgrep.dev/blog/2025/five-considerations-when-building-cross-platform-tools-for-windows-and-macos/), [CrossHair artifacts](https://pypi.org/project/crosshair-tool/0.0.109/#files), [Z3 artifacts](https://pypi.org/project/z3-solver/5.1.0.0/#files), [Rejected Node binary wheel artifacts](https://pypi.org/project/nodejs-wheel-binaries/24.16.0/#files), and [platform tag meaning](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/). Accessed 2026-09-06.

## Dependency source admission

Core's [dependency policy at released commit d579970](https://github.com/nold-ai/specfact-cli/blob/d579970565530c3fd7b98bad4de90cf874c2a99d/scripts/check_dependency_trust_exceptions.py) explicitly prohibits `nodejs-wheel-binaries` in the dependency-trust register and frozen locks; an ordinary trust exception cannot authorize it. Checked 2026-09-06. The shipped modules C14 specification nevertheless names it in the isolated signed analyzer lock. The core check does not establish enforcement over that separate module lock, and its historical inclusion does not grandfather admission into the future native closure.

Exclude this package from the proposed native closure. Before approving implementation, reassess the released core/module dependency policies, audit the complete native dependency closure, and select a policy-admissible native Node distribution or build source with verified provenance. No replacement source is approved by this plan. If a proposed source requires changing a prohibition, a separate explicit policy change must be reviewed and accepted first; signing or adding an exception record cannot bypass the prohibition. An unresolved policy conflict blocks native design approval and production implementation.

The future native contract SHALL enforce dependency-source admission independently of artifact integrity, both during provisioning and before launch/offline reuse against the selected approved policy identity. A correctly signed but prohibited dependency fails closed before analyzer execution. Reconcile the inherited C14 lock requirement through explicitly versioned native contracts and coordinated core scope after baseline reassessment; any replacement requires fresh artifact/closure/cache identities and conformance evidence. This planning PR does not rewrite the shipped C14 specification, signed lock, or core policy and does not claim to remediate the historical discrepancy.

## Architecture decisions deferred to the released baseline

Keep Git scope, policy selection, differential classification, C15 enforcement/waiver semantics, and machine-readable output portable. Define a bounded backend interface for capabilities, verified provisioning, launch, observation, cleanup, and result identity. Preserve the existing full-module-directory checksum/signature boundary for native files shipped in the module. Separately provisioned runtime caches require an approved signed lock/manifest binding every artifact digest, applicable layer digest, installed payload/root manifest, OS/architecture/Python ABI, dependency closure, and cache identity. Verify the artifact and extracted payload against those bindings during provisioning and revalidate the selected installed payload/root before every launch, including offline reuse. Reject unbound, stale, partial, mixed-version, or platform/ABI-mismatched caches; successful module verification alone does not authorize an external cached binary. Exact descriptor formats and backend mechanisms remain subject to released-baseline design approval. Never use ambient dependencies as an unreported substitute for pinned evidence.

Evaluate Linux Bubblewrap, a signed native macOS sandbox helper, and Windows AppContainer/process lifecycle controls with harmless conformance fixtures. These are candidates, not approved implementations. [Apple App Sandbox](https://developer.apple.com/documentation/security/protecting-user-data-with-app-sandbox) and [Microsoft AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation) describe native primitives; neither establishes parity with C14's Linux-specific contract by itself. Accessed 2026-09-06.

Approve a common behavioral capability contract and platform-specific attestation details after native prototypes prove filesystem/network policy, process-tree cleanup, resource bounds, load-path integrity, and unattended operation. Record limits honestly; sanitized environment variables alone are not OS isolation. No unsupported capability or omitted required analyzer can become PASS through fallback.

## Baseline gate and evidence lifecycle

Implementation is deferred until #459 is corrected, #434 is published with install readback, and core #679 has adopted the released C15 module #417. Pin exact core/module versions, commits, signed artifacts, policy/profile, and available preflight/checkpoint/conformance identities. Reassess this proposal using that baseline, refine material scope/interfaces with user review, and obtain the required current approval/seal before production edits.

Before implementation, map requirements and risks to native tests and record failing evidence. During implementation, use the released checkpoint surface and record every meaningful change. At completion, use final conformance and native OS/architecture runners, then verify published installation. A changed baseline or release artifact invalidates affected evidence.

## Compatibility and release

Do not rewrite historical C14 schemas, profiles, or checkpoint digests. Any new portable profile/report/runtime identity contract must be explicitly versioned and paired with core consumer scope before coding. Preserve C15 authoritative status/exit semantics and the distinction between local evidence and protected CI promotion.

A future release requires verified native artifacts, complete dependency identities, appropriate semver/core compatibility, canonical signing/registry publication, and install readback. Roll out only proven platform combinations; unproven combinations remain open acceptance gaps. Withhold or revert a faulty platform publication without relabeling historical Linux evidence. No runtime, schema, version, registry, or support claim changes in this planning PR.
