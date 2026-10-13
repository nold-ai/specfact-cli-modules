## Confirmed workflow

An operator runs the complete configured pytest suite through the existing Linux signed reviewer, selecting an explicit bounded budget when necessary. The project cannot grant itself an unlimited budget. Legacy invocations retain300seconds.

## Minimal adaptation

Reuse existing ReviewOptions and CLI request routing, passing the selected budget only to targeted-pytest-coverage. Bound integer admission to1..600seconds (booleans reject). Other members keep300seconds and Pylint's internal30-second limit. Record requested/effective provenance; no cached result may claim another budget. Darwin default behavior remains unchanged; a nondefault Linux override returns unsupported UNKNOWN rather than silently ignoring it.

## Non-goals and acceptance

No runner/account changes, test/file/coverage reduction, host fallback, unsigned adoption, global interpreter tuning, release or merge. Synthetic contract tests prove admission/routing/timeout/output compatibility; supported Linux full-scope regression and trusted signed candidate are required before consumer adoption. Rollback restores legacy options while retained reports keep their explicit provenance.

The explicit nondefault Linux pytest budget travels through the existing read-only sealed JSON request. Exact member-specific integer admission precedes path projection. A ContextVar with token restoration bounds the nonportable subprocess per invocation, without mutating global defaults or shared cache identities. The existing portable inner limit remains unchanged. Native report scope evidence states both inner policies and the selected outer deadline; incomplete execution retains UNKNOWN. Matching run/review/ledger command-test controls preserve complete native corresponding-test selection.
