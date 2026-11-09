## Why

The owner authorized focused native Semgrep migration preparation on 5 November 2026. The selected Python Semgrep package requires MCP and OpenTelemetry versions whose original risk windows expired. Native Semgrep retains the tested constant-propagation finding without starting the Python CLI.

## What Changes

Migrate existing scanner callers to the unmodified upstream `osemgrep scan --experimental` executable. Remove the Python Semgrep dependency only from inputs whose migrated tool installation can supply the reviewed native executable. Preserve logical Semgrep findings, rule bytes, result consumers, timeouts and fail-closed delivery gates. Existing CI must capture JSON stdout because native `--output` does not create the requested file.

## Recoverable analyzer diagnostics, 8 November 2026

Replace three silent broad-failure handlers with fixed debug diagnostics through the standard module logger. Preserve all partial results, recovery boundaries and fallback behavior. Do not log source, exceptions, tracebacks or paths, and do not configure logging. This focused review correction changes no public signature, native execution or authenticated resource. The independently accepted v8 candidate signatures remain tied to their frozen bytes and do not authorize this changed source.

## Unused private analyzer plumbing, 8 November 2026

Remove four unused parameters from three internal extraction methods and migrate every internal call in the same unit. Remove two private forwarding wrappers that have no production or test callers. Keep the stateful async wrapper because it uses its file path to update module state. Public methods and signatures stay fixed. This is a mechanical refactor characterized by the existing 336 passing cases; four existing unused-argument findings provide the quality baseline. No compatibility shim, new API, argument sink or native runtime change is introduced.

## Dependency recovery diagnostic, 9 November 2026

Replace the redundant final return at the existing SyntaxError and UnicodeDecodeError boundary with one fixed debug diagnostic. Keep graph state, catch scope, public signatures and all unrelated failures unchanged. Do not include source text, paths, exception details or a traceback. This extends the accepted diagnostic approach without changing logging configuration, native execution or trust behavior.

## Capabilities

### New Capabilities

- `native-semgrep-cli`: native executable discovery and scanning without the Python CLI dependency.

## Impact

Paired core and official code-review module preparation. No signature, module adoption, CI dispatch, exception renewal, protected authority, release or merge is granted. Original M69 and consumed proof/signing runs remain immutable. Official module main 209b4ed8 is not adopted because its sealed toolchain retains vulnerable dependencies. Parser 3.11 remains provisional pending fresh supply-chain classification and compatibility. User-facing installation guidance and existing scan commands must be updated before finalization. Rollback during preparation is the isolated branch; no public PR head changes occur.

## Approved project callers

On 6 November 2026 the owner explicitly included the two reachable project scanner owners, their existing manifest and required tests. They retain command lists, copied environment mappings and existing JSON result consumers. No shared launcher, new public API or additional runtime/admission behavior is introduced. Original project version/signatures remain unfinalized until the existing legitimate CI workflow can produce them.

## Existing provider and license boundary

Retain the existing isolated Pylint and npm BasedPyright providers while removing conflicting pip declarations from code-review. Preserve both logical tools and their existing runners. Populate the existing canonical companion Python license map from exact package metadata. Keep native binary attribution and future CI coverage as separate delivery checks. No new provider, exception, framework or installation API is introduced.

## Approved Codebase repro owner

On 6 November 2026 the owner explicitly included the existing Codebase repro validator, direct certifi manifest declaration and one focused test file. Preserve this scanner's managed prefix, optional status, timeout, autofix behavior and logical Semgrep findings. Correct the migrated core missing-tool report at its existing executable boundary. The existing environment probe retains its public signature and logical tool names. Native probing supplies native argv and child-local CA/private-library inputs; it does not alias Python Semgrep. Other module owners remain outside this preparation scope.

## Native Hatch CA ownership

Use immutable, byte-exact selected certifi data and its notice for existing native Hatch commands. A bounded data-only preflight checks the default before direct native execution. Existing explicit SSL_CERT_FILE values stay authoritative, and other commands retain their environment. Exact-path Git attributes prevent byte conversion. This adds no launcher, helper alias, private environment marker, plugin, writable CA cache or new runtime API. Windows native execution and complete bootstrap remain delivery checks.

## Current official module integration, 8 November 2026

The owner authorized autonomous focused resolution and PR786 update on 8 November 2026. Continue this preparation against official module dev `430e3ccbf9fbd6a6177b033662a76235a8bd6cc8`, preserving its current versions, authenticated resources, immutable rule identities, result reconciliation and sealed execution boundaries. Earlier M69 preparation remains a historical isolated artifact and cannot replace the newer payload.

Host-only native executable discovery and command adaptation belong at existing owners. Managed Linux and native capsule requests retain their existing logical Semgrep argv, including `--disable-nosem`, their immutable trust inputs and admitted tool paths. No new helper, launcher, public API or authority map is introduced. The existing direct host UTF-8, CA/default and timeout contracts remain.

The actual Windows vendor diagnostic proved a certificate-chain rejection with the frozen Native TLS backend. Pinned Windows CA loading bypasses `SSL_CERT_FILE`; the optional OpenSSL binding is absent. This preparation supplies no Windows success or complete delivery credit. A corrected eligible upstream payload remains required; trust additions, fallback, patched engines, deadline increases and skipped negative controls are excluded. The sealed toolchain's older Python Semgrep closure, legitimate new versions, three publisher signatures, a new immutable fixture and full review/readiness checks remain explicit delivery holds.

## Private Repro text parsing, 9 November 2026

Move only ANSI cleanup and the five existing tool-text parsers to one private sibling inside Codebase. Keep all public definitions, the dispatcher, serialization recovery, execution, environment imports and metadata in their existing owner. This removes a mixed responsibility without changing supported parser output or adding a launcher, public API, factory or compatibility framework. The independent architecture comparison selected this first unit over analyzer mixins. Every new source path enters actual review, typing, source/checksum and packaging scopes. Earlier CodeRabbit upload authority does not include the new path. Moved private function globals and traceback locations change; unsupported external owner-global rebinding is not promised. All current review, signature, Windows, security and readiness holds remain.

The five parsers are explicit exports from a private module, bound under their existing private owner names. The helper module and local record types stay private, with no package re-export or supported new public API. Function names, qualified names, defining modules and diagnostic identification may change as private metadata. Existing owner alias replacement and dispatcher behavior remain required. All five helper exports enter actual contract discovery; no policy, waiver, filter or skip changes.
