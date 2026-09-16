## ADDED Requirements

### Requirement: Validate the exact staged snapshot before running unchanged hooks
The transport SHALL bind an allowlisted regular-file patch to its SHA256, immutable base and resulting tree, and SHALL reject changes to hooks, workflows or trust controls. The only permitted dependency input change is the reviewed replacement of this repository's Pylint and basedpyright ranges with its signed toolchain entry versions.

#### Scenario: Valid snapshot
- **GIVEN** a clean checkout and an allowlisted patch with matching base, digest and tree
- **WHEN** native hook transport prepares the snapshot
- **THEN** its staged tree equals the requested tree and the original hooks remain unchanged

#### Scenario: Untrusted or corrupt snapshot
- **GIVEN** a digest, base, tree, path, size or file-mode violation
- **WHEN** the transport validates the request
- **THEN** it fails before executing hooks

### Requirement: Preserve real execution authority and hook outcome
The transport SHALL execute every unchanged pre-commit stage in a credential-free child, retain real outer Actions identity and propagate nonzero exits or tracked and non-ignored untracked source mutation. Its receipt SHALL identify local explicit-file evidence and SHALL NOT grant protected PR range or customer release authority.

#### Scenario: Failure and credentials
- **GIVEN** caller credentials and real Actions context
- **WHEN** a hook fails
- **THEN** the child receives only the explicit environment allowlist, the receipt retains actual outer identity and the failure is propagated

#### Scenario: Default workflow
- **GIVEN** an ordinary workflow invocation without the transport request
- **WHEN** the workflow selects jobs
- **THEN** the original customer corpus runs and the transport does not

#### Scenario: Native manager activation and decorated CLI output
- **GIVEN** the repository's default Hatch environment and ordinary CLI startup output
- **WHEN** the transport prepares the project runtime before unchanged hooks
- **THEN** it invokes genuine Hatch activation and retains raw output plus exactly one complete typed local runtime descriptor
- **AND** missing, malformed or ambiguous descriptors fail before hook execution

#### Scenario: Preparation uses reviewed workspace command modules
- **GIVEN** an installed signed baseline and the reviewed workspace source
- **WHEN** preparation selects its command implementation
- **THEN** it mirrors the unchanged hook's explicit owned bundle roots and Python source paths
- **AND** arbitrary inherited module paths, credentials and publisher context remain excluded

#### Scenario: Bounded development dependency alignment
- **GIVEN** the exact reviewed Pylint and basedpyright declarations in the immutable base
- **WHEN** a snapshot updates pyproject.toml
- **THEN** only those two approved pin replacements are accepted, and any other byte change fails before preparation or hooks

#### Scenario: Inventory the actual hook interpreter after preparation
- **GIVEN** Hatch preparation may synchronize declared development dependencies
- **WHEN** preparation succeeds and unchanged hooks are about to run
- **THEN** the transport records a fresh inventory from the actual hook interpreter and binds its digest in the receipt, retaining the earlier installation inventory separately

#### Scenario: Hooks create untracked source

- **WHEN** a successful hook creates a non-ignored source file without staging it
- **THEN** the transport rejects the changed worktree even when its staged tree is unchanged
- **AND** ordinary ignored cache and report artifacts remain permitted
