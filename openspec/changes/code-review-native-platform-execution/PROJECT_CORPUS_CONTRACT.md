# Native macOS project-corpus acceptance contract

Status: maintainer acceptance candidate; production eligibility remains false.

This slice binds the existing portable-runtime corpus to bounded native macOS
manager plans. It does not enable the production runner or publish a capsule.

## Corpus authority

`tests/fixtures/portable-runtime/corpus.json` is the only project-selection
authority. The harness accepts its pinned pip, Hatch, uv and Poetry entries and
the local Hatch reconstruction. Unknown managers, mutable repository identities,
absolute paths, path traversal and project-supplied commands fail closed.

The harness derives commands from a versioned trusted plan. A project may select
only the manager, groups, environment and test paths already declared in the
corpus. It cannot add argv, environment variables, executables or descriptors.
No plan resolves Homebrew, an ambient host executable, Docker or a shell.

## Execution domains

Each project has distinct preparation and execution directories and requests:

- `project-preparation-v1` admits the selected manager's fixed offline plan and
  build-hook policy. It has no analysis authority or acquisition credentials.
- `project-execution-v1` admits the fixed Python observer plan. It has no network
  or package-manager authority and may only consume the sealed preparation
  descriptor and declared project inputs.

Both requests travel through `ManagedRun` and require a broker-verified response
for the same plan, domain and corpus identity. Direct process creation remains
kernel denied. An adapter request for unsupported spawning, daemonization,
`preexec_fn`, arbitrary descriptors or an unbound executable produces actionable
`INCOMPLETE` evidence containing `no host fallback`; it can never produce PASS.

## Required execution evidence

Complete evidence contains one preparation and one execution record for every
pip, Hatch, uv and Poetry corpus member. At least one real managed execution must
also prove all of the following:

- pytest collected and executed the declared test slice;
- an explicitly admitted pytest plugin loaded;
- coverage recorded at least one declared project source;
- a compatible generic ARM64 Mach-O Python extension imported from the sealed
  native payload, with its recorded dependency closure admitted;
- preparation and project execution used separate declared domains; and
- neither domain used network, host executables or undeclared child processes.

Missing or incompatible native extensions, plugin failures, absent coverage,
manager/build-hook incompatibility and unsupported child-process requests are
incomplete required evidence. Independent static analyzer findings remain valid,
but aggregate project-runtime acceptance cannot PASS.

## Physical-Mac evidence

The optional physical test consumes an already verified analyzer candidate. It
executes the trusted observer through `python_analyzers.execute`; it never runs a
candidate executable directly from the harness. Raw paths, output and native
receipts remain private. Public results contain only aggregate counts, manager
names, ABI, signing mode and the production-false flag.

Passing the prepared-project observer does not by itself approve all manager
preparation hooks. Complete release acceptance still requires the pinned upstream
corpus to run through every fixed manager plan on the supported macOS/ABI matrix.

## Fixed offline manager adapters

The preparation plan binds one executable identity and one exact command shape:

- pip uses sealed CPython and the sealed `pip` module with `--no-index`,
  `--require-hashes` and a private target directory;
- Hatch uses the sealed SpecFact Hatch adapter, the selected corpus environment
  and offline dependency inputs;
- uv uses the sealed native uv adapter with `sync --offline --frozen`;
- Poetry uses the sealed SpecFact Poetry adapter with `--offline`,
  `--no-interaction` and the selected dependency groups.

Each adapter requires its manager lock/config files and every selected artifact
to be present in the authenticated payload or declared project source. Missing
manager executables, lock files, wheels, native libraries, build backends or
compatible ARM64 extensions produce an exact `INCOMPLETE` blocker. No adapter
searches `PATH`, invokes a shell, accesses a registry or resolves a host tool.

Build hooks run only inside the preparation domain. Pure-Python hooks and hooks
whose complete toolchain is separately admitted may execute. Requests for an
external SDK, compiler, linker, CMake, Meson, Rust, Homebrew or Xcode toolchain
produce `external SDK/toolchain required; no host fallback` and do not execute.

## Trusted acquisition and generated offline input

The pinned upstream repository is not required to contain a SpecFact-specific
`requirements.lock`, `hatch.lock` or other generated lock. A distinct trusted
acquisition domain fetches only the corpus URL and exact 40-character commit,
verifies the commit and Git tree through an authenticated Git checkout or the
GitHub commit/archive route, and binds that evidence to the source archive digest
and deterministic extracted source-tree inventory. A caller-supplied observed
commit string alone is insufficient. Dependency resolution/download completes
before any project code or build hook can execute.

Acquisition emits an authenticated `specfact-macos-project-acquisition-v1`
descriptor, a content-addressed source archive, a private wheelhouse and a
generated fixed-manager lock. The signed payload binds the corpus identity,
source URL and commit, source archive and tree digests, ABI, manager and exact
manager version, and every dependency's normalized name, version, filename,
kind, URL, size, SHA-256 and wheel tags. Only HTTPS package artifacts from the
declared trusted repository hosts are admitted. Redirected URLs, local paths,
filename or tag substitutions, duplicate filenames, mutable versions and
unrecorded bytes fail closed.

Archive extraction rejects absolute paths, traversal, links, devices and
duplicate output paths. It checks each member size before opening its output,
creates output files with exclusive no-follow semantics, and streams bounded
chunks while hashing. The resulting signed descriptor binds the authenticated
fetch method, requested source and archive URLs, commit, Git tree, archive hash,
extracted tree hash and file inventory.

The acquisition domain may use network and narrowly scoped read-only registry
credentials. It may not import the project, run a package manager, execute a
build backend or invoke any project-controlled program. The descriptor is
installed atomically only after its complete content closure verifies. A missing
completion marker, temporary directory, changed archive, changed wheel, changed
mode or interrupted install is rejected and never reused offline.

The preparation domain has no network or acquisition credentials. It consumes
only the authenticated descriptor, its exact wheelhouse and source bytes, plus a
sealed fixed adapter for pip 26.2.1, Hatch 1.18.0, uv 0.12.13 or Poetry 2.4.3.
The adapter rejects project-provided argv, environment, URLs and host tools.
Build hooks execute only in this managed preparation domain. Compatible generic
ARM64 wheels and admitted native extensions are valid inputs; a dependency that
requires an unavailable external SDK or native toolchain produces actionable
`INCOMPLETE` evidence.

The execution domain receives only the sealed prepared output and its bound
preparation descriptor. It receives neither the acquisition wheelhouse nor
network credentials.

## Sealed preparation handoff

Successful preparation produces a deterministic inventory of ordinary files:
canonical relative path, byte length, mode and SHA-256. Symlinks, devices,
sockets, path escapes and writable executable substitution are rejected. The
descriptor binds the corpus identity, source identity, manager plan, preparation
domain, execution domain and inventory digest.

The trusted controller verifies the inventory, copies it to the declared
execution input directory without following links, verifies the copied bytes and
then binds the descriptor digest into the execution request. A descriptor from a
different project, preparation domain or execution domain is rejected. Mutation
before or after copy prevents project execution and yields incomplete evidence.
