# SpecFact native macOS ARM64 execution component

These sources are compiled and ad-hoc signed by the maintainer artifact build.
They are never compiled or re-signed on a customer machine.

`build.sh` requires the macOS SDK only in the protected build environment. It
builds and signs the bootstrap first, derives its exact designated requirement,
then compiles that requirement into the broker. It also builds the small dynamic
PID verifier used before the controller resumes the broker. The capsule builder
supplies the already signed CPython requirement through
`SPECFACT_PYTHON_REQUIREMENT_FILE`; admitted direct-tool builds also supply the
Ruff, Semgrep Core and Node requirement files. Missing direct-tool requirements
compile to an impossible requirement and fail closed.
The resulting `build/component.json` records hashes and signing metadata for the
authenticated capsule manifest.

The versioned closed protocol binds fixed analyzer, tool-replay, preparation and
acquisition plans, plus broker-owned child launch operations. Project workers
cannot select arbitrary executables, PIDs, descriptors or broader grants.
The checked-in component is an implementation candidate. Physical CPython 3.11
proof executes all ten analyzers on selected pip/Hatch/uv/Poetry slices; the
complete supported OS/ABI, boundary and independent installation acceptance
remain required before production admission.
