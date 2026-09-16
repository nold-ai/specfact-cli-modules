# Design

Checkout the transport controls and the immutable supplied source base separately. Decode a size-limited gzip/base64 patch, verify its SHA256, validate all changed paths against the reviewed allowlist before application, apply to a clean Git index and require the expected Git tree. Reject nonregular modes, deletions, renames and any modified hook/control inputs.

Run the unchanged complete pre-commit hook implementation in a credential-free child environment with explicitly recorded environment names. The outer receipt retains the real Actions workflow/ref/run identity. Preserve the hook exit, exact tree before/after, control hashes and logs; source mutation or incomplete execution fails the job. The child represents local explicit-file developer review, not protected publisher provenance.

The host can accept only a successful exact-tree receipt from the reviewed workflow commit, then GPG-sign the same tree normally. No signing material enters the runner. A separate native customer matrix and CI module signing remain mandatory.

Timeout: ninety minutes. Rollback: remove the opt-in transport in a reviewed follow-up; no immutable release is changed.

An optional basedpyright diagnostic runs only after hook failure and explicit selection. It reconstructs the same staged snapshot and verifies the original report's project, runtime, environment and bound capsule identities against an offline cache. A trusted controller argv inside the verified outer sandbox calls the unchanged signed nested target worker. It retains native portable arguments, source configuration and raw replay streams. A mismatch refuses execution; the pre-hook preparation descriptor cannot substitute for the runtime actually reviewed. Genuine Hatch activation resolves the same selected environment. Replay is bounded and diagnostic-only; it never changes the hook exit. Process tracing is excluded because it conflicts with the capsule's own ptrace startup verification.
