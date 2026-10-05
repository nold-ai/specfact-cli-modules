# Project-driven native preparation

## Hatch matrix selection

When the caller selects a Hatch matrix root (including the built-in `hatch-test`),
the adapter uses Hatch's generated environment configurations and selects the
single member matching the admitted interpreter's major/minor version. It keeps
that member's workspace, dependency and installer configuration. A concrete
environment name is preserved. Multiple matching members require an explicit
configuration; no match reports an unsupported environment rather than
downloading another interpreter or using a host environment.

Hatch's local workspace members stay local. The confined description identifies
their names, relative paths and extras; the controller accepts only contained
project directories in the immutable snapshot, builds their wheels through
confined PEP 517 hooks, and acquires their external dependencies separately.
The authentic selected Hatch environment installs the original root and member
sources offline. Sanitized, identity-bound VCS metadata accompanies snapshots
for declared version backends; project Git operations use a packaged, broker-owned
network-denied child and cannot invoke host Git or execution hooks.

Workspace dependency resolution MUST receive all locally built member wheels as
explicit file candidates, preserving their names and versions instead of resolving
those names from an index. Source-root binding includes the root and every member.
Immutable transfer and writable hook preparation preserve executable status so
Git-backed versions distinguish actual source changes from copying artifacts.
Every native manager snapshot, including pip, retains captured sanitized VCS
context. Signature subprocess timeouts return structured incomplete evidence.
Partial clones do not require unavailable historical blobs solely for SCM
version queries. Export retains available bound objects and exact commit, tree,
tag and shallow identities without copying remotes or invoking transport.
All bound commit/tag/tree metadata and both the selected commit's source tree
and captured index tree must be complete locally. Missing required metadata or
current source bytes remain actionable incomplete evidence. Historical blob
omission does not authorize lazy fetching inside a worker.

Explicit root source paths do not hide editable workspace member paths. Member
builds retain their position under the sanitized repository root and execute
their hooks from the selected subdirectory, preserving ancestor-based SCM
discovery without exposing any directory outside the invocation snapshot.
Both immutable and uv writable copies retain executable status. When the caller
requires pip hashes, controller-built local wheel candidates carry their verified
hashes too; adding local candidates must not disable the caller's hash policy or
enable hash mode for otherwise unhashed dependency declarations.

Managed Python launches must preserve the reviewed manager probe forms: `-W
<filter>` and script input through `-`, in addition to `-c`, `-m` and scripts.
Warning filters apply before customer code, and stdin remains the broker-owned
pipe. These forms do not change executable identity, descriptor grants or
kernel confinement. Standard path-like subprocess arguments are converted to
bounded strings before the same executable and broker admission checks.
Unsupported interpreter startup flags remain explicit
limitations rather than an unrestricted host subprocess fallback.

Private virtual environments may alias the capsule's verified Python image.
The adapter admits an alias only inside the inherited writable roots, with a
regular `pyvenv.cfg` and a Python executable resolving to that exact capsule
image. The broker still executes the fixed capsule interpreter; a bounded,
canonical prefix selects that environment's own site-packages and installation
scheme. It cannot select another executable, grant or analyzer dependency root.
Missing or substituted aliases fail before launch. Manager probes requesting
UTF-8 may set `PYTHONUTF8=1`. PEP 517's private `PYTHONPATH` overlay is permitted
only when every directory is canonical and inside inherited worker grants.
Its site customization runs in the same confined child before the hook;
host paths, indirection and empty path entries are rejected.
Other Python startup overrides remain rejected.
Normal subprocess context exit closes stdin before waiting, so a child waiting
for EOF can complete. Inherited binary output is forwarded without strict text
decoding; output formatting failures must not retain terminal worker handles.
Build-worker import isolation retains its `__main__` module. Removing analyzer
imports must not invalidate the standard Python main-module contract used by
authentic managers and their environment creation libraries.
The admitted interpreter must expose relocatable installation paths. Native
startup binds its library/include metadata to the actual capsule Python root,
and private-environment startup preserves the requested alias, prefix and site
metadata across nested managed launches. Upstream build-host paths cannot be
used as installation locations or expanded filesystem grants.
Nested alias validation anchors to the fixed capsule image, excluding writable
private aliases from its reference set. Replacing an already registered venv
alias must fail admission rather than validate the substituted file against itself.

The Hatch adapter treats the manager's exact local root-project reference as a
confined build input, never an index acquisition request. Other direct source
references require separately admitted build handling and remain incomplete.
The Hatch adapter uses the pinned upstream manager's environment model and
preparation lifecycle in the network-denied project worker. It selects the
requested environment, preserves inherited configuration and lock behavior,
and obtains dependency/features/groups from Hatch rather than reimplementing
its TOML semantics. Acquisition consumes only bounded validated declarations.
The installation phase receives verified wheels and backend dependencies,
including requirements returned by the confined PEP 660 editable-build hook
when the selected manager environment uses development installation,
uses private data/cache/config directories and returns an inventoried project
site. Unsupported native installers, shells or SDK builds remain incomplete;
none may be removed from the mandatory corpus to claim support.

Approved revision: 2026-10-04, Europe/Berlin. This supersedes the requirement for
a publisher acquisition catalog entry for each customer project. Historical
signed corpus bundles remain optional explicit import fixtures.

The controller snapshots the selected project and preserves its discovered or
explicit configuration.
Source and snapshot directory roots are canonicalized before internal link
validation. Platform aliases such as macOS `/var` and `/private/var` must not
make a repository-internal link appear to escape its root. External, recursive
and excluded-environment links remain rejected.
Project inputs determine a local cache identity; only
the SpecFact capsule requires a publisher identity. No signing key is available
to the controller, managers, hooks or project workers.

For pip, the sealed pinned manager first resolves compatible binary wheels in a
network-enabled acquisition domain containing only bounded, validated dependency
declarations. It cannot receive source directories, pip command-line options,
VCS requirements, sdists or arbitrary local files as install targets. This
initial wheel-only resolution must never execute project metadata or build hooks.
An offline installation worker runs the same pinned pip against the verified
wheel bytes with dependency resolution and bytecode compilation disabled.
Standard wheel installation layouts are handled by pip rather than by a custom
extractor. Artifact digests are rechecked between acquisition and installation.
Coverage/import roots follow explicit project configuration. Otherwise, root
wheel Python files may establish an unambiguous import root only when their
bytes match the disposable source snapshot. Workers validate relative roots
inside their immutable project grant. Recorded member dependency graphs pin the
analyzer entry points and their admitted fallback imports; compatible project
dependencies retain their actual versions. Unrelated analyzer packages and cached
modules cannot substitute for missing project dependencies. Inventory and marker
evaluation use the prepared target interpreter, not the controller ABI.
Native BasedPyright receives verified source roots as well as the project site.
Contract analysis retains its declared source/test distinction even when pytest
or coverage policy projection fails. A policy failure must not make CrossHair
import test-support modules as production contract inputs.
Native interpreter selection uses native artifact patch versions, never copies
the Linux interpreter lock. Unknown native versions remain unavailable. The
prepared target's full Python version must match its native selection metadata
before admitting project evidence. Acquisition failures yield structured
incomplete reports instead of escaping into CLI parameter errors.
For non-editable uv installation, unambiguous matching Python file bytes in the
installed site may bind source roots to the disposable snapshot. Unrelated
dependencies and mismatched files cannot establish those roots; the same bounded
comparison budget applies. Explicit configured roots retain precedence.
An editable manager environment must not create false unknown-import findings
merely because its private preparation prefix has been retired.
The controller builds a fresh, read-only member view from verified capsule bytes,
containing only that member's admitted imports and metadata. File-based analysis
such as Astroid must see the same restricted view; a Python import hook alone is
insufficient. The `project-origin-v1` pytest graph may legitimately receive an
empty sealed view when every dependency comes from the project. This must not
expose unrelated analyzer packages or change protected-review restrictions.
Sealed analyzer code is never taken from a customer environment cache.
Source-only stdlib projects receive an ephemeral empty project site and actual
target-interpreter graphs, without package acquisition or invented project metadata.
Installed-wheel execution must not silently substitute coverage of
different files for the selected source snapshot.
Source matching indexes inputs once and has a cumulative comparison budget;
exceeding it requests explicit roots instead of unbounded controller work.
Malformed failure receipts preserve incomplete preparation evidence using a
bounded fallback diagnostic; they cannot abort independent analyzer reporting.

Project build backends run in a distinct, network-denied worker on a disposable
copy. Backend dependencies are acquired as wheels and installed separately.
Additional requirements returned by hooks are validated before acquisition.
The controller invokes separate discovery and wheel-build phases. A hook may
write only within its disposable copy/output/temporary grants. Backend paths
must remain in that copy; returned wheel names cannot escape the output root.
The root project wheel and its Requires-Dist metadata join dependency preparation
without importing the backend into the acquisition or analyzer process.
Even a package declaring an empty dependency list follows its declared or default
build backend and installs the resulting root wheel; it is not an empty runtime.
Wheel metadata inspection runs in a separate sealed worker, never in the backend
process. Hook responses are untrusted bounded JSON objects. Build environments
exclude preloaded analyzer distributions as well as their import paths. A
requirements-only build-system declaration uses pip's default setuptools backend.
Resolution includes the locally built root wheel so self-referential extras do
not select a published copy. Unsupported managers are rejected before acquisition
or execution of hooks, until their authentic integration is admitted.
Unsupported spawning, compilation or dependency sources produce actionable
incomplete evidence and cannot authorize host execution or a PASS verdict.
Optional acquisition archives are bounded while headers are enumerated, before
complete archive traversal or extraction. Header count, metadata allocation,
paths, member types and cumulative declared payload sizes must stop oversized
input immediately; archive rejection must not publish a partial project cache.
Native local pytest evidence remains `project-origin-v1`. It preserves the
project's doctest collection option and coverage exclusion expressions within
the confined worker. These options cannot gain protected-review authority;
the existing protected pytest/coverage policy continues to reject them.
Local coverage exclusions read from INI files must preserve every nonempty
expression as an indented continuation line, including section-like text;
projection must not create additional configuration sections or keys from
either INI strings or TOML list elements. Additive `exclude_also` and
`partial_also` retain Coverage defaults unless the project explicitly replaces
them with `exclude_lines` or `partial_branches`. A TOML regex containing
embedded newlines is projected through TOML so its regex grouping is preserved,
while all INI continuation values are indented against section injection. Coverage
plugins remain unsupported in both modes. Report-only `.coveragerc` files
are discovered with standard Coverage section names, so their policy is never
silently discarded. Local compatibility is admitted only
for worktree, full, explicit-files, index and range-preview assurance.
BasedPyright whole-file diagnostics without a source range, such as import
cycles, are retained at line 1. Malformed explicit ranges remain incomplete
evidence rather than being discarded.

Hatch, uv and Poetry must retain their authentic pinned manager semantics. A pip
implementation cannot stand in for their acceptance suites. Until their managed
launch integration passes, they report the specific missing capability without
requesting a publisher entry for the project.

The acquisition policy is a separate versioned capability, not a general network
grant to existing analyzer or project plans. Startup ownership, direct-fork
denial, resource enforcement, cancellation and broker-death cleanup continue to
apply. Completed workers may leave pytest temporary-directory aliases. Before
reusing invocation scratch, the controller may unlink owner-owned symlinks
without following them, pruning directory aliases from traversal. It must
never normalize or mutate link targets. Receipts remain regular-file-only;
a substituted receipt link is removed and its missing evidence remains
UNKNOWN. Hardlinks, special files and foreign ownership remain rejected.

Cross-machine installation and full supported OS/ABI acceptance remain
required for shipment.

Managed children use inherited private request/reply pipes. The worker requests
only an admitted program identifier, bounded arguments/environment and a working
directory within its current grants. The broker derives every child grant and
resource budget from the registered parent; workers cannot supply host PIDs or
broader paths. Initial live admission covers the capsule's exact Python image.
Manager virtualenv PATH overlays are accepted only as the admitted
private prefix's bin directory followed by the unchanged parent PATH. PATH is
then removed from the child request; executable identity always selects the
verified image. Runtime `Popen[bytes]` annotations remain importable while
process creation continues through the broker. No host PATH override is admitted.
Output reads, standard input, polling, wait, timeout and termination use owned
handles; no raw broker descriptors or host-process handles are returned. A
non-isolated managed Python launch includes the admitted working directory for
`-c`, `-m` and stdin, or the admitted script directory for a file launch.
`-I` applies throughout supported startup options, excluding warning-filter
values and arguments after the execution selector. Isolated launches exclude
these directories and inherited Python overlays regardless of option order.
An ignored `PYTHONPATH` must not prevent an isolated launch; its contents never
enter the broker request or child import paths.
A parent’s exit terminates its logical children; controller EOF terminates the
whole invocation. Unsupported descriptors, shells and startup overrides remain
explicit managed-process limitations.

The unsandboxed broker must anchor child stream allocation and cleanup to held
directory descriptors, including mutable parent temporary trees. Reaped records
must never cause a signal to an old PID. Child admission and service time count
against the parent's monotonic deadline. Successful Popen context exit waits for
normal completion; exceptional cancellation remains bounded. Wait and communicate
retire completed handles while preserving unread bounded streams. Managed Python
children inherit the caller's admitted cwd/environment, return available partial
stream data and honor accepted buffering flags.

Compatible universal2 project libraries are admitted only when bounded Mach-O
inspection finds the native ARM64 slice and validates that slice's load paths.
An x86-only or malformed image remains incomplete evidence; Rosetta is not used.

## Native project pytest plugin discovery — 2026-10-05

The confined pytest worker loads pytest11 entry points only from the verified
project site's installed distributions. Ambient controller/capsule entry-point
discovery remains disabled. The sealed coverage plugin is supplied exactly
once; project plugins run with project-origin-v1 authority and the same kernel
process, filesystem and network restrictions. Discovery is bounded and rejects
ambiguous duplicate plugin names. It must never import project plugins in the
controller or sealed analyzer worker. Authentic xdist requests use the existing
managed Python subprocess route and retain actionable incomplete evidence when
requested spawning exceeds that route's capabilities.

Native xdist topology discovery may read exactly `hw.logicalcpu` and
`hw.physicalcpu`, alongside the existing count sysctls. These read-only
counts do not grant arbitrary sysctl access, change process admission limits
or represent a hard resource guarantee. Writes and all undeclared names
remain denied; launched workers still belong to the broker registry.

Projected TOML preserves supplementary Unicode without surrogate escapes and
retains configured coverage thresholds in the runner's enforcement reader.
Named project plugin registration retains verified distribution metadata so
pytest's `required_plugins` version checks work before executing tests.

Managed Python launches omit non-existent `sys.path` entries, matching normal
Python import behavior. Existing import paths remain canonical and within the
parent worker grants; no request may broaden those grants. Repository pytest
configuration may add relative import paths that do not exist from the worker
cwd, and those inert entries must not make an otherwise valid child launch fail.

Managed subprocess binary streams preserve the standard file interface: any
public `.buffer` is a readable/writable stream, never internal storage. This
allows execnet's byte-channel selection without exposing descriptors or PIDs.
The internal pending bytes remain bounded by the existing output budget.

Native pytest supplies xdist's documented automatic-worker preference of four
through `PYTEST_XDIST_AUTO_NUM_WORKERS`. This bounds `-n auto` and `-n logical`
within the broker's unchanged eight-worker capacity while leaving room for
control and nested work. Explicit worker counts and project hooks still face
that kernel/broker capacity and can return incomplete evidence; no limit is
raised and no test is deselected. Explicit serial or lower counts are retained.

Broker-owned pytest children retain the parent's selected project plugin set,
including pytest-cov, named registration and distribution version metadata.
The child installs this compatibility only inside the confined dispatch of
pytest-origin launches; manager probes and isolated Python launches do not
load these plugins. `PYTEST_DISABLE_PLUGIN_AUTOLOAD` remains enabled. Registry
discovery examines only the admitted project's prepared site, and ambient
entry points are never enabled. Every fresh pytest configuration receives the
same bounded registrations, including execnet's `_prepareconfig` entry point.

Child plugin imports are deferred until pytest creates its configuration,
after execnet has established its byte-channel bootstrap. Plugin import-time
output must not precede or corrupt that protocol. The compatibility context
itself must not load project plugins.

Pytest compatibility is lazy: a test's ordinary child or private venv may run
without pytest installed. Only importing `_pytest.config` activates the config
factory adapter, using the existing import finders and grants. Explicit plugins
supplied to `pytest.main` or `_prepareconfig` must not be registered twice;
selected distribution metadata still accompanies those plugins.

The reviewed pytest-rerunfailures 14.0 adapter replaces only its localhost
failure-count transport with a bounded invocation-private SQLite store. The
upstream rerun selection, count and reporting hooks remain active. Master and
managed children exchange an opaque relative store token in the existing xdist
workerinput field; they cannot select host paths. Updates are transactional,
concurrent increments are preserved, and unknown plugin versions remain
actionable incomplete evidence. Network policy and selected tests are unchanged.

Managed executable discovery exposes the verified capsule uv image just as it
exposes packaged Git. `shutil.which("uv")` does not consult the host PATH; an
absent, mutable, substituted or foreign image returns no result. Discovery
does not enable direct spawning or broaden the admitted uv launch operations.

## Managed-worker validation structure

Refactoring worker startup, launch validation and stream handling must retain
their ordering and every admission predicate. Separate bounded argument,
environment, executable and import checks by responsibility; no helper may
relax inherited grants or execute before confinement. Standard subprocess
interfaces remain compatible even where their fixed public signatures exceed
internal style limits. Existing behavioral and negative admission tests are
the authority, alongside the actual confined native quality findings.

## Controller installation and minor-specific pure wheels

The installed module SHALL declare cryptography as a controller dependency for
authenticated native acquisition and capsule verification. Ordinary Linux and
macOS reviews SHALL not depend on an undeclared developer-environment library.
Analyzer dependencies remain sealed, and signature verification remains required.

Authenticated wheel admission SHALL accept `py311-none`, `py312-none` and
`py313-none` for their corresponding selected CPython ABI, for `any` or supported
macOS ARM64/universal2 platforms. Minor-specific tags do not waive ABI,
architecture, host minimum-version, digest or signature checks. Newer or
noncanonical Python tags and native ABI claims on pure wheels SHALL reject
before output creation.

Scenarios: an ordinary module installer provisions the controller's cryptography
requirement; each supported minor-specific pure wheel preserves authenticated
payload bytes; foreign architecture, future Python, native ABI and future macOS
minimum-version pure-wheel claims reject.

## Complete snapshot and test-only failure attribution

Complete pytest snapshots SHALL retain ordinary project data while excluding
the same generated/environment directories as source-only captures. Local
`.venv`, version-control internals and caches are not project test inputs.

A native review selecting only tests SHALL preserve reconciled pytest failure
findings at a selected test file. Coverage source selection remains unchanged;
test files SHALL NOT become production coverage inputs to obtain an anchor.
Findings outside selected inputs remain rejected.

Directory exclusions SHALL apply to directories and directory aliases, not
regular project data files with the same name. Complete captures retain such
files and internal regular-file aliases under the existing path/integrity checks.
