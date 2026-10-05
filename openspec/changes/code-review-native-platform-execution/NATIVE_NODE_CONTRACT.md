# Experimental native BasedPyright input contract

Status: experimental, not policy-admitted and not production-eligible. Authorized
bounded implementation on 2026-10-01 (Europe/Berlin); aggregate capsule proof is
owned by the main implementation. Historical Linux artifacts, global development
dependencies and shipped runtime platform acceptance are outside this change.

## Bounded independent preparation

The initial input-lock preparation is now extended by the owner-authorized
parallel compatibility implementation on 2026-10-02. It includes the offline
`scripts/native_node_package.py` packager, exact npm lock and focused tests.
The npm policy disables lifecycle scripts and omits optional packages. fsevents
remains in the resolved lock for provenance, but is not installed.

Upstream Node input:
`https://nodejs.org/dist/v24.16.0/node-v24.16.0-darwin-arm64.tar.gz`, SHA-256
`39189dab4eeb15706c424af0ac08a3044c9e48f7db12a7d77f6b7aafc7dd5df6`.
The exact archive and upstream signed checksum list were verified on 2026-10-02;
see the [verification runbook](../../../scripts/native_node_inputs/README.md).
Native clean/defective one-shot tests pass. These results establish bounded input
and analyzer compatibility, not dependency-policy admission or capsule acceptance.
See [current compatibility evidence](NATIVE_COMPATIBILITY_RESULTS.md).

## Requirement: locked inputs without executable installation

The offline packager SHALL consume explicit local archive paths for upstream
BasedPyright npm 1.39.10 and upstream Node 24.16.0 Darwin ARM64. Committed npm
integrity and Node release SHA-256 identities SHALL authenticate the exact input
bytes against reviewed HTTPS upstream metadata. This is content authentication
against committed pins, not independent publisher-signature or policy admission.
The packager SHALL perform no download, npm lifecycle script, Python installation,
Node execution or ambient PATH lookup. It SHALL reject tampered archives before
writing output and SHALL never overwrite an existing output directory.

### Scenario: exact native inputs packaged offline

GIVEN the pinned archives and an unused output directory
WHEN the packager prepares native inputs
THEN only Node bin/node and its license plus the locked BasedPyright package are
materialized; Node is a Mach-O ARM64 executable, the manifest binds every emitted
payload file by SHA-256 and mode, and the explicit absolute execution argv names
the packaged Node and packaged index.js without consulting ambient Node.
AND the receipt records experimental=true, dependency_admitted=false and
production_eligible=false regardless of packaging success.

### Scenario: unsafe or inconsistent input rejected

GIVEN changed bytes, unsafe/duplicate archive paths, links or special files in
selected payloads, oversized input, wrong Node architecture, inconsistent npm
name/version/entrypoint/dependency metadata or a pre-existing output
WHEN packaging is requested
THEN it fails without executing input and leaves no partial output directory.
A failure SHALL NOT overwrite or remove pre-existing user content.

## Requirement: optional dependency audit

BasedPyright 1.39.10 declares no mandatory npm dependencies and optionally requests
fsevents ~2.3.3. The npm lock SHALL retain fsevents 2.3.3 provenance/integrity and
its install-script fact for review, but the one-shot packaging path SHALL omit
fsevents entirely. Its native addon and node-gyp install/build scripts SHALL NOT
run or enter the payload. Watch/language-server behavior is not supported by this
bounded packaging path. Any newly required or changed optional dependency SHALL
fail closed pending contract and lock review. nodejs-wheel-binaries and the PyPI
BasedPyright wheel SHALL NOT be input components or fallback providers.

### Scenario: no installer, optional addon or ambient runtime

GIVEN an empty or hostile PATH and local pinned archives
WHEN packaging runs
THEN it succeeds without npm, pip, Docker, fsevents or ambient Node, and emitted
execution argv uses explicit packaged paths. Archive-provided scripts remain
inert data; no postinstall/build hook is invoked.

## Requirement: one-shot behavior parity

### Scenario: native clean and defective project diagnostics

GIVEN the final packaged Node/BasedPyright payload on physical Darwin ARM64
WHEN invoked explicitly with --project <config> --outputjson on a clean fixture
and an assignment-type-error fixture with fsevents omitted
THEN version is 1.39.10; clean exit is 0 with no errors; defective exit is 1 with
the expected structured assignment-type diagnostic and file/line identity.
This verifies bounded one-shot parity only, not the aggregate capsule boundary.

## Remaining admission

Final assembled-artifact verification, full Node/Mach-O/dylib and build-input audit,
license/security review, signed native capsule publication, boundary integration
and aggregate acceptance/customer-install proof remain mandatory. The receipt
MUST NOT represent pin matching as any of these approvals.

## Sources

Read 2026-10-01 (Europe/Berlin):
- https://registry.npmjs.org/basedpyright/1.39.10
- https://registry.npmjs.org/fsevents/2.3.3
- https://nodejs.org/dist/v24.16.0/SHASUMS256.txt
