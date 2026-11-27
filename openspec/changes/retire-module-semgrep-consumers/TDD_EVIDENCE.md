# Codebase Repro async analysis

Verification on 23 November 2026 used Python 3.12.13 and the exact analyzer
source from the verified core #799 merge `e90a4b57`.

- Before the fix on modules `2155370e`, five Repro cases failed. The
  explicit option was unavailable and legacy configuration still selected
  Semgrep. The unchanged no-request control passed.
- After the fix, all six Repro cases and 13 existing Codebase integration
  and unit cases passed. The suite invokes the actual Codebase command app and
  real core subprocess. It verifies structured results and exit codes,
  migration and missing-scanner diagnostics, and unchanged source.
- Signed external module acceptance remains pending under #516. This
  implements the Codebase Repro milestone of #523. The Project consumers
  and other retirement work remain open.

The first hosted run exposed six inherited host-fixture failures before the
Codebase tests could run. Four existing signed-install layout cases also
failed locally against the paired core's protected release cutoff. The
fixture-only follow-up reuses the reviewed repairs from #524, restores the
exact public-key and released-verifier inputs, and retains the invalid
signature and substituted archive rejection cases. Production workflows,
verification logic, and policies are unchanged.

## Native CI after merging the modules baseline

The signed update incorporates modules `dev` at `9f0de196`. The independent
review stops at CrossHair before it runs candidate tests. A separate local run
using the native candidate environment's released core 0.55.4 produced four
failures because that wheel predates the built-in analyzer. The paired-core
workflow regression also failed against the original workflow before the
checkout was added.

The updated workflow resolves the exact same-repository companion commit and
uses it for candidate tests only. It still installs and verifies the separate
signed controller first. The Repro, workflow, and independent-review regression
set passed 52 cases locally. The 42 focused Repro tests passed with branch
coverage of 81.53% for the command and 83.94% for the checker.

## Paired core provenance in targeted pytest

Review on #529 identified that the native bootstrap selected the paired checkout
but the clean environment discarded its path before targeted pytest. All three
workflow and handoff regression cases failed before the repair. The native
coordinator now maps the selected path into the pytest environment and retains
released-core behavior when no checkout is selected. The independent reviewer
still verifies its pinned released core before candidate setup. All 75 focused
cases passed, and the real registry provenance test passed with the exact
editable paired core and the environment supplied by the coordinator.

## Project OpenAPI example extraction

On 23 November 2026, both integration fixtures failed against modules
`4cf2747d`. Serial extraction omitted the asserted response example, and
the process worker launched the Semgrep sentinel. The same fixtures pass
with the Project-owned source converter. Both paths preserve the POST
request body and asserted HTTP 201 JSON response.

The Project suite passed 41 cases on Python 3.12.13 against released core
0.55.4 and the exact paired core source `41216d9`. Branch-inclusive coverage
was 82.64% for the converter and 92.59% for its source-name helpers. A legacy
test-pattern configuration emits migration guidance. Feature and quality
findings, Spec-Kit output, and signed installed acceptance remain open.

## OpenAPI review regressions

Five focused fixtures failed on signed #530 head `55d3a1ee`. The follow-up
replaces whole operation examples, binds context responses, extracts
assertions on inline requests, recognizes Flask test clients, and replaces
stale Python import aliases. All five fixtures and the unchanged Project
suite passed. Coverage is 88.85% for the converter and 94.59% for the source
helpers.

## Native review on protected modules dev

The signed #529 pull request passed the required checks before merge. Native
review of the subsequent protected dev push completed all contract targets,
then failed four Repro tests against released core 0.55.4, which lacked the
built-in scanner. See modules Actions run 45274139569, job 138041399412.

The workflow regression failed on commit `4cf2747d` because the candidate
resolver accepted only pull requests. It now accepts official protected dev
pushes and uses the exact commit resolved from core dev. All five resolver
and provenance cases passed on Python 3.12.13. The controller and its signed
reviewer retain their existing released inputs.

After all three quality jobs passed on #531 head `743cfccc`, GitHub still
blocked the PR. Native-review-only changes did not select the required
`sign-modules` pull request workflow. Verification-only dispatch run
45279879008 passed on the exact commit but its check contexts were absent
from the PR rollup. The new trigger regression failed on that head, then
passed after adding the exact workflow path to PR verification. The push
filter, verifier, and protected-main signing environment are unchanged.

## Project feature and quality evidence

The normal analyzer regression failed on `4cf2747d`: loading the feature
policy probed for Semgrep. The source-based replacement retains the HTTP
route and mutable-default finding on the appropriate feature, keeps the
healthy feature clear, and reports legacy configuration without probing
the tool. Fixtures cover authentication controls, normalized scanner
findings, scope, history, dependency graph, and incremental feature output.
On Python 3.12.13 with paired core `41216d9`, 75 focused cases passed.
Branch-inclusive coverage reached 80.94% for the
analyzer and 92.59% for the rule engine.

## Project analyzer review corrections

Five production-behavior fixtures failed on signed #532 head `5279c6ef`.
The follow-up uses source ranges, statically recognized Flask and FastAPI
receivers, resolved literal route parameters, known authentication
callables, scoped imports, and string initialization evidence. Tests also
require the expected parsed dependency names and validation tasks without
leaking TEST_MODE. After incorporating signed #530 head `685830f4`, all
85 focused Project tests passed. Coverage reached 81.41%
for the analyzer and 93.16% for source rules.

## Project source provenance

On signed pull request head `f114bba4`, five regression cases failed.
Nested findings reached the outer feature, ordinary bases counted as ORM
models, named security dependencies lost their authentication evidence,
ambiguous string initializers reported string concatenation, and a later
import erased an earlier route. Two confidence and route controls passed.

With the corrections, 92 Project tests passed on Python 3.12.13.
Branch-inclusive coverage was 81.48% for the analyzer and 90.56% for
the source-pattern engine. Separate otherwise equivalent feature fixtures
verify the 0.10 route bonus and 0.05 mutable-default penalty.

## Loop writes and lexical shadowing

Eight regression cases failed on signed pull request head `2aba6b08`.
The scanner treated list or ambiguous loop writes as string concatenation,
reported a replaced import after a function definition, or attributed an
imported callable to a shadowing parameter. The default-expression control
also checks that the declaration still sees its enclosing scope.
All 100 focused Project tests passed with the corrected scanner.

## Conditional loop additions

Two cases failed on signed pull request head `6186a5a0`: a conditional
addition with a definite string went unreported, and the same pattern in
a nested loop was missed. The corrected scanner assigns each finding to
its innermost loop and keeps the negative control for a possible list
write. All 102 focused Project tests passed.

## Loop-carried assignments

The pre-signing review of `927c16a2` identified list assignments carried
into later iterations. The direct and nested-loop fixtures reproduced
the false positive. A third regression demonstrated why a `continue`
must preserve the state at that path. The analyzer uses bindings
known both at entry and across repeat paths, and still reports a
concatenation when the current iteration establishes a string.
All 106 focused Project tests passed.

## Unpacked loop targets

Three tests failed on `023e08b4`: tuple targets, nested list and starred
targets, and an unpacking assignment inside the loop retained a stale
string binding. All 109 focused Project tests passed after forgetting
each name bound by unpacking. A separate accumulator still reports
string concatenation in the same loop.

## Binding evaluation order

Five cases failed on `7f0f7501`: a plain, unpacked, annotated, or augmented
assignment and a loop iterable each lost a callable alias before the
old binding was used. The scanner now inspects the evaluated value first.
It still discards the old binding for subsequent statements and the
loop body. All 114 focused Project tests passed.

## Spec-Kit import artifacts

On modules dev `c8859ae2`, the Project handler attempted to generate a
Semgrep preset and advertised it in the command output. On Typer 0.27.0, the
public `code import from-bridge` route separately consumed the subcommand as
the parent bundle argument and rejected its options.

The mapped public-command regression now imports a minimal Spec-Kit project,
loads the generated protocol with an empty transition list, parses the
GitHub Actions workflow, and checks its Project health check. It verifies
that neither the filesystem, the command, nor the report advertises a
Semgrep preset. The native test selection passed 217 tests using the reviewed
core source `58f6a2af`. The focused suite also passed on released core
0.55.4 and Typer 0.27.0.

The starting branch coverage was 17.75% for the shared Project import file.
The added tests exercise real import and enrichment runs, recovery from saved
checkpoints, generated and cached contracts, source tracking, and adapter
diagnostics. The local native test selection passed 256 tests with 80.83%
branch-inclusive coverage for the Project import file and 85.96% for the
Codebase import route against the unchanged 80% requirement. The staged
Requirements, Code Review, contract tests, and repository lint also passed.
Protected signing run 46065268836 signed Codebase 0.42.4 and Project
0.41.34. Both signatures match the approved payloads and pass the strict
module verifier. Hosted checks and installed-artifact acceptance remain
pending.

### Independent native contract review

Run 46068014936 stopped before pytest because the pinned Semgrep parser
rejected a keyword-only lambda in an import test. The named confirmation
fixture passed in isolation and both Semgrep checks completed on the next
signed head. CodeRabbit also found a test that depended on import runtime
patches having run earlier. The standalone case failed with a missing
`repo` key and passed after the test initialized those patches before
injecting its I/O failure.

Run 46068467669 retained two incomplete CrossHair results. The pinned
solver crashed on Typer's `Literal` annotation and the Spec-Kit converter
exceeded 120 seconds while the solver was still reaching additional
contracts. The compatibility patch enumerates literal values and escapes
line breaks in diagnostics, preserving the signed parser's one-record-per-line
format. Native review gives each source 480 seconds of wall-clock time
with the same 10-second per-path budget. The signed AST checks and result
parser remain in use, and crashes or incomplete evidence still block.
All 48 native-review unit tests passed after four new targeted cases failed
against the previous driver. The signed Codebase and Project payloads are
byte-identical to signing run 46065268836.

Run 46070279491 completed all independent analyzers. Pytest then found
nine brownfield cases failing at startup because the unpaired candidate
fixture resolved a Typer version that lacked a helper used by released
core. The native bootstrap now uses the existing controller Typer
constraint for that released-core fixture. A shell-level regression
failed for the unpaired branch and passed after the change. The paired
branch retained its existing setup in both runs. All nine affected cases
passed locally with released core 0.55.4 and Typer 0.27.0.
