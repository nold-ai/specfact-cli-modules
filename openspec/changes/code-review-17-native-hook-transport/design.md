# Design

Checkout the transport controls and the immutable supplied source base separately. Decode a size-limited gzip/base64 patch, verify its SHA256, validate all changed paths against the reviewed allowlist before application, apply to a clean Git index and require the expected Git tree. Reject nonregular modes, deletions, renames and any modified hook/control inputs.

Run the unchanged complete pre-commit hook implementation in a credential-free child environment with explicitly recorded environment names. The outer receipt retains the real Actions workflow/ref/run identity. Preserve the hook exit, exact tree before/after, control hashes and logs; source mutation or incomplete execution fails the job. The child represents local explicit-file developer review, not protected publisher provenance.

The host can accept only a successful exact-tree receipt from the reviewed workflow commit, then GPG-sign the same tree normally. No signing material enters the runner. A separate native customer matrix and CI module signing remain mandatory.

Timeout: ninety minutes. Rollback: remove the opt-in transport in a reviewed follow-up; no immutable release is changed.
