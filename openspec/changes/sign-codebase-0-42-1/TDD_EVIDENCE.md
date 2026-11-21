# Signing-only workflow evidence

The approved source is the staged PR #524 integration tree
`07fcd2443b89f5fd492b9b397f964364362cd3c4`. The SHA-256 of the 5,068-byte
module payload is `a826c75ef57409191711f1af03dd13877d56d48769ba3a2e29d1929e16ce9909`.
The Git-tracked review copy has one terminal newline, which the workflow removes
before verifying the checksum.

Before implementation the five signer cases failed because the checked-out
workflow and payload were absent. During integration the final protected-dev
trigger test also failed with `KeyError: 'push'` while the draft still used
manual dispatch. GitHub requires a manually dispatched workflow to exist on
the default branch. The preflight workflow exists only on dev, so the
reviewed payload entering dev is the trigger for the approval job.

The five signer cases and eight existing signature-hardening cases pass with
an encrypted ephemeral key under OpenSSL 3. The actual shell verifies and
emits the expected detached signature and rejects three different mismatches.
Actionlint and strict OpenSpec validation pass. The protected key was never
used in local testing.
