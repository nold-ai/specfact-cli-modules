## REMOVED Requirements

### Requirement: Sign packages manifests on PR approval

**Reason**: Review events run against PR refs outside the protected replacement signing environment.

**Migration**: PRs use public signature verification. The protected signing environment retains key preflight, reproducibility, and the paused publisher.

### Requirement: Manifest discovery covers packages directory

**Reason**: The PR approval workflow no longer discovers or signs manifests.

**Migration**: The public verifier and protected reproducibility check discover manifests under `packages/`.
