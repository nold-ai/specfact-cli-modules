# Project-aware local code review architecture

## Problem and confirmed outcome

Customers need the ordinary CLI to review their Python repositories without adopting SpecFact's development dependencies or coding standards. The owner approved a hard cut from capsules and explicitly selected trusted local execution on 2026-10-16, Europe/Berlin. Dependency installation, build hooks, imports and configured checks may execute on the customer's machine. Hostile-code containment is excluded.

This artifact records future architecture. No local-runtime capability, supported installation cell, failing test or release is established by planning validation.

## Usage from the caller's view

The persistent installation routes are `pipx install specfact-cli` and `uv tool install specfact-cli`. The ephemeral route uses `uvx --from specfact-cli specfact`. Signed modules remain installed through the existing module commands in user scope, outside customer dependencies. Exact installation behavior is an acceptance obligation in change 20, including repeated fresh uvx invocations. After provisioning valid locally verified signed modules, the project environment and selected tools, local review must run without network access using the locally available invocation route/cache. Missing prerequisites remain preparation failures; cold offline bootstrap is not promised.

```console
specfact code review runtime inspect --json
specfact code review runtime prepare --project-config /path/outside/repo/review.toml --json
specfact code review run --scope worktree --json --out /path/outside/repo/review.json
specfact code review run tests/checks.py --project-config /path/outside/repo/review.toml
specfact code review run --scope range --base-ref BASE --head-ref HEAD
```

`runtime inspect` does not install or import project setup code. `runtime prepare` initializes the selected external sidecar context. Normal review automatically prepares missing context. Ambiguous environments return candidates rather than a guessed environment. Keep the existing descriptor meaning of `--project-runtime`; unsupported old descriptors receive a migration diagnostic. An interpreter is selected through the project configuration's Python selection, not by silently repurposing that flag.

The first complete bootstrap workflow uses the existing detached Hatch fixture twice, with an existing selected environment and a cold environment. Use different CLI and project Python versions. Demonstrate dependency imports, an entrypoint, the native pytest plugin, project lint configuration and a controlled defect through the new project execution boundary. Public ordinary review still uses the old dispatcher until change 19. Change 17 proves the bootstrap slice, not a released replacement reviewer. The complete ordinary CLI review is proved at change 19 and exact installed acceptance at change 20. Later acceptance adds a native dependency and actual icontract violation in explicit fixtures. No reconstructed fixture proves the inaccessible original customer repository fixed.

## Shape and ownership

| Owner | Knowledge and responsibility |
| --- | --- |
| `specfact_codebase.project_runtime` | Project inspection, interpreter selection, native manager preparation, owned external state and project command execution. |
| `specfact_code_review.run` | Scope selection, customer standards, check scheduling, findings and report assembly. |
| Existing review tool adapters | Tool-specific argv construction and output parsing. |
| Existing scope and differential helpers | Source identities, snapshots, finding continuity and suppression comparison. |
| Core CLI | Module command discovery and ordinary report consumers. |

Code Review already depends on Codebase. Framework/OpenAPI sidecar validation reuses the runtime service while retaining its own explicit workflow. It no longer maintains a competing generic dependency installer. Do not move framework extraction into runtime setup or introduce a reverse Codebase-to-Review dependency.

The public boundary hides manager orchestration and subprocess mechanics. Its sketch belongs in documentation until implementation starts.

```python
@dataclass(frozen=True)
class ProjectSelection:
    python: str | None
    manager: str | None
    environment: str | None
    groups: tuple[str, ...]
    extras: tuple[str, ...]


@dataclass(frozen=True)
class ProjectCommand:
    argv: tuple[str, ...]
    cwd: Path
    env_overrides: Mapping[str, str]


@dataclass(frozen=True)
class ProjectPlan:
    root: Path
    selection: ProjectSelection
    dependency_inputs: tuple[Path, ...]
    configuration_inputs: tuple[Path, ...]
    source_identity: SourceIdentity


class PreparedProject:
    root: Path
    python: Path
    environment_identity: EnvironmentIdentity

    def run(self, command: ProjectCommand, *, timeout: float) -> ProcessResult:
        raise NotImplementedError


def inspect_project(root: Path, selection: ProjectSelection) -> ProjectPlan:
    raise NotImplementedError


def prepare_project(plan: ProjectPlan, workspace: Path) -> PreparedProject | PreparationFailure:
    raise NotImplementedError


def review(project: PreparedProject | PreparationFailure, request: ReviewRequest) -> LocalReviewReport:
    raise NotImplementedError
```

Preparation failure retains the plan/root so independent source-only checks can run and produce an explicitly partial report. It never supplies a usable interpreter for required dynamic checks. The result model distinguishes completed checks, not applicable checks, unavailable checks, execution failures and timeouts. Findings are separate from execution state. Only serialization knows report wire fields.

Explicit configuration and provider contributions are parsed once at the boundary. A project command uses argv rather than newly introduced shell text. Existing native manager scripts retain the manager's documented semantics. Persist no credentials. Subprocess diagnostics and outputs are bounded. Cancellation and timeout terminate owned processes through ordinary platform process management, without claiming a hostile-process security boundary.

## Project fidelity and bootstrap

For an existing environment, probe the selected executable's real version, prefix and relevant package/import context. Never derive customer Python from the CLI's `sys.prefix`. Reuse the environment for execution. If it needs synchronization, prepare a separate owned environment instead of installing into it.

For a cold project, select the declared compatible Python and manager. Honor the manager's environment, default groups and requested extras. Preserve local/VCS origins, markers, editable installation, generated artifacts and build hooks. Do not translate every manager to pip or introduce `--no-editable` universally. A lock is immutable input. A deliberately unlocked project may resolve its declarations, but stores the observed resolution externally. Missing Python produces a remedy; do not automatically download an interpreter or silently use the controller. Native manager provisioning already requested by the customer's manager configuration remains visible as part of that manager's execution.

| Manager | Preparation contract |
| --- | --- |
| pip or pip-tools | Create an external venv with selected Python. Install the selected requirements/includes and constraints, project package and extras as declared. Keep compiled pins where supplied. |
| Hatch | Select the named native environment and honor its dependencies, scripts and editable behavior. Redirect owned preparation with `HATCH_ENV_TYPE_VIRTUAL_PATH`; use the selected project interpreter. |
| uv | Redirect with `UV_PROJECT_ENVIRONMENT`. Use locked synchronization when `uv.lock` exists. Existing execution avoids implicit synchronization; stale locks fail without an unlocked retry. |
| Poetry | Select project Python and groups/extras. Redirect environment storage through supported Poetry settings and consume the existing lock. Do not replace Poetry with an export/split/pip approximation. |

Existing manager versions and installed tool versions are facts to record, not a requirement to reproduce a sealed publisher closure. The adapter must diagnose unsupported manager features. Existing custom setups can select an explicit compatible environment/profile. An unfamiliar manager never triggers a guessed pip fallback.

Store selection, matching source/configuration identities, and completed environment facts in per-project external state. Use separate invocation workspaces for preparations and atomic completion publication. Native manager/package caches provide reuse. Do not create a daemon, distributed cache, signed project catalog, OCI materializer or generalized environment broker.

Source and configuration fingerprints determine reuse. Environment identity includes interpreter/platform, the selected dependency closure, groups/extras, exact package versions and local/VCS origins/build inputs. Unrelated packages in an existing environment are recorded as incidental inventory for no-mutation checking, not silently promoted to the project's declared dependency closure. If an import analyzer cannot reconstruct the relevant context faithfully, it is unavailable.

## Customer standards and profile extension

Selection precedence is explicit invocation/configuration, then an explicitly selected organizational profile, then native project discovery. Native tool config discovery and plugin semantics remain native. A provider contributes configuration references and named checks; it does not create runtimes or issue findings.

The single extension route is `specfact.project_profiles`. Only an explicitly selected compatible provider installed in the CLI's external installation is loaded. Native pytest and linter plugins stay in their native environments and do not need SpecFact provider wrappers. The existing module registry discovers command applications, not project-profile contributions; do not introduce a second competing module registry.

```python
class ProjectProfileProvider(Protocol):
    def discover(self, root: Path) -> ProfileContribution:
        raise NotImplementedError
```

`ProfileContribution` has a supported contribution version, selection preferences, native configuration references and named command declarations. It is declarative data validated by the controller. It never carries objects to import inside a different Python interpreter. A missing provider, unsupported contribution or unresolved profile conflict is an actionable failure.

Project-defined checks run with project-selected tools and plugins. Source-only supplemental analyzers run in separate tool environments. Import-dependent analyzers prefer a compatible project-installed tool. Their fallback is a separately prepared environment with the exact selected project graph and origins plus compatible analyzer requirements. A conflict is an unavailable check, never a package upgrade, path splice or changed customer constraint. Tools offering an explicit target-interpreter option may use it through a verified adapter instead of rebuilding dependencies.

Retain all customer-selected diagnostics and their original identifiers. Unknown structured rule families do not disappear. Custom checks without a structured adapter retain exit status and bounded output without invented line attribution. Supplemental security, defect and quality findings have separate origin/policy attribution. They do not enable extra customer lint families behind the customer's back.

Remove the universal 80-percent customer coverage floor and missing-icontract requirement. Customer coverage policy remains effective. This repository retains its own configured quality/coverage obligations. Initial contract analysis checks existing icontract contracts through CrossHair. No contracts means not applicable. Requested unsupported contract mechanisms and failed imports are incomplete. Do not synthesize contracts or promise proof for arbitrary uncontracted code.

## Source and report contracts

Keep stable scope selection, source identities, differential matching, multiplicity, source attribution and suppression comparison where compatible. For worktree checks, verify relevant source identity before and after execution. For index/range, prepare dependencies and generated artifacts against each materialized snapshot. Never run an editable installation of another checkout and label that result snapshot-bound. Bind configuration and check identities when comparing base/head; incompatible policies or tool identities remain unknown.

Report schema 2.0 records local execution facts, actual tools/configuration, source/dependency identity and completion. A failed assertion is a completed check with a finding. Missing required evidence, preparation failure, malformed output and timeout remain incomplete. Shadow may exit zero while preserving adverse truth. Scores and autofix availability cannot turn incomplete execution into acceptance. C15 calibration and exception authority stay separately owned.

Version dispatch is explicit. Existing module and pre-commit helpers classify any major greater than one as at least 1.6. The cutover updates these consumers and the paired core consumer instead of changing only the version label. Historical 1.6 evidence retains its original interpretation. Any report version without an explicitly supported contract is nonaccepting, including unknown minor versions within a known major. Do not fill capsule fields with dummy values.

A signed module, immutable source range or caller PR context does not grant protected `pr_range`. Core #680 keeps its separate protected contract. Schema 2.0 local reports cannot satisfy that old capsule contract without a separately reviewed protected workflow. C15 #417/core #679 retain active owners and status; this planning delivery adds a coordination note only.

## Synthesis decision and alternatives

The architect panel compared a combined project/tool environment, a static-only cold-project fallback, and a shared project runtime with separate analyzers. Candidates used gpt-6-astra, gpt-6.1-sol and gpt-6-luna. An independent gpt-6-astra cross-judge preferred the shared-runtime design. This records design judgment, not executed capability.

Use the Astra candidate as the base for faithful cold bootstrap and source binding. Adopt Sol's narrow command representation and explicit selection precedence. Adopt Luna's per-check tool provenance. Reject repurposing `--project-runtime`, project `sys.path` splicing and a static-only cold workflow.

| Alternative | Decision |
| --- | --- |
| Reuse the existing framework sidecar installer unchanged | Reject. It uses controller-Python and incomplete manager approximations and mixes tool/project dependencies. |
| Adapt discovery and native manager knowledge behind one shared service | Select. It preserves useful project knowledge while removing capsule execution assumptions. |
| Install SpecFact and every analyzer in the project environment | Reject. It changes customer dependency resolution and cannot handle arbitrary valid conflicts. |
| Require customers to prepare every environment themselves | Reject as the default. It does not satisfy automatic cold sidecar bootstrap. |
| Build another custom broker/catalog/backend framework | Reject. It recreates the maintenance cost the owner explicitly removed. |

Laziness Protocol determines the single runner and small service. Subtract Before You Add determines capsule deletion at public cutover. Boundary Discipline keeps native output parsing at adapters. Prove It Works determines installed customer-workflow acceptance instead of component-only success.

## Delivery sequence and reconciliation

Changes 17, 18, 19, paired core adoption, then 20 form the runtime delivery sequence. All current implementation tasks remain unchecked. During implementation, bind scenario-derived tests into the requirement mappings with executable selectors before RED and require the Requirements evidence gate to verify actual results at implementation maturity before GREEN; planning inspection is insufficient. Change 17 proves one complete existing/cold Hatch workflow before expanding managers. Change 18 establishes project standards and analyzer fidelity. Change 19 emits local evidence and performs one public cutover, deleting both obsolete execution routes. Core adopts ordinary consumption. Change 20 proves installations, replaces capsule-only CI and prepares the coordinated breaking release.

At cutover, delete native macOS broker/worker and Linux OCI/Bubblewrap acquisition, capsule admission/descriptors/catalogs, sealed import policing, dependency/native-library copying and the parallel legacy host orchestrator after useful helpers move. No permanent runtime backend switch remains. Distribution cleanup removes residual native builds and capsule-only release/support configuration. Preserve cryptographic module verification and independent security work.

Approved dispositions and actual execution state are recorded in [GitHub alignment](GITHUB_ALIGNMENT.md). Never-delivered abandoned proposals belong in non-canonical history. Partially delivered lineage is marked superseded in place; shipped fixes/evidence remain historical. Do not archive abandoned work or promote unimplemented specs. Native OpenSpec archival remains required for completed changes.

During follow-up implementation, update this design for an accepted contract deviation before handing it to another worker. Record acceptance source and update usage, types and responsibility assignments together. No implementation deviations are accepted or hidden by this planning delivery.

## Acceptance and risks

| Evidence | Required observation |
| --- | --- |
| First existing/cold detached Hatch workflow | Different controller/project Python, real imports/entrypoint/plugin/lint and seeded defect, no SpecFact dependency injection. |
| Four native manager adapters | Selected groups/extras, pins, markers, local/VCS packages, generated sources and manager entrypoints retain native behavior. |
| Customer standard fixtures | Rules/exclusions/versions/coverage differ deliberately from SpecFact defaults and remain effective. |
| Analyzer and contract fixtures | Actual defect and icontract violation, no-contract applicability, tool conflict, malformed output and timeout remain distinct. |
| Immutable scopes and reports | Source-bound base/head execution, explicit supported-contract dispatch with unsupported same-major/major rejection, no protected local authority. |
| Exact installed distribution | pipx, uv tool and repeated uvx, user-scoped module discovery, Linux/macOS/Windows and supported CLI Python cells. |
| No-pollution evidence | Project declarations/locks and existing environment package inventory match before/after; ordinary trusted hook outputs are identified separately. |

The current CLI test matrix is Python 3.11, 3.12 and 3.13. Target interpreters are independent; include a manager-admitted version outside that matrix in acceptance and publish only cells actually proved. Neither ABI catalogs nor all-ten-analyzer completion on every possible graph is a blanket prerequisite for running the CLI. Required selected checks remain nonaccepting when unavailable. Optional checks disclose limitations.

Largest risks are wrong-environment execution, dependency reconstruction drift and overstated source/assurance evidence. Interpreter probes, origin-aware graph records, snapshot binding and explicit consumer tests mitigate them. Trusted hooks can write ordinary build outputs; no sandbox guarantee is asserted. The service itself does not rewrite customer declarations, locks or install its tools into their environment.

This spans two modules and paired core consumers. Duration and cold-download cost need the first workflow measurement. No paid service or publisher membership is required. Follow-up release uses a breaking Code Review major, appropriate Codebase/core compatibility updates, normal signatures and canonical publication. Rollback pins the previous immutable compatible CLI/module pair, without a second production runner.

Confidence is Medium. Ownership, observed code coupling and live issue lineage are grounded. Runtime fidelity, supported installation cells and release acceptance remain unverified until implementation.

## Primary references

- [Published modules baseline](https://github.com/nold-ai/specfact-cli-modules/commit/209b4ed835187ea857d1fa847abdd351f6f6232a) and [candidate baseline](https://github.com/nold-ai/specfact-cli-modules/commit/593656f675eaf4954b609aca51aa6504367dc02e), inspected 2026-10-16.
- [uv tool isolation](https://docs.astral.sh/uv/concepts/tools/) and [pipx](https://pipx.pypa.io/stable/), accessed 2026-10-16.
- [uv project environment configuration](https://docs.astral.sh/uv/concepts/projects/config/) and [locked synchronization](https://docs.astral.sh/uv/concepts/projects/sync/), accessed 2026-10-16.
- [Hatch virtual environment options](https://hatch.pypa.io/latest/plugins/environment/virtual/) and [Poetry configuration](https://python-poetry.org/docs/configuration/), accessed 2026-10-16.
- [BasedPyright target-interpreter option](https://docs.basedpyright.com/latest/configuration/command-line/) and [CrossHair contracts](https://crosshair.readthedocs.io/en/latest/contracts.html), accessed 2026-10-16.
