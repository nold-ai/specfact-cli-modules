# TDD Evidence

## Discovery

- Inventory of duplicated docs paths found `86` files shared between `specfact-cli-modules/docs` and `specfact-cli/docs`.
- The canonical module-owned destinations for this change were documented in `design.md`: landing/config/layout plus module-specific guides, adapter workflows, publishing/signing, and module reference pages.
- Public-domain cutover assumptions were documented in `design.md`: `docs.specfact.io` remains the entry point and core docs origin, and `modules.specfact.io` becomes the canonical modules origin once GitHub Pages and Cloudflare routing are enabled.

## Red Phase

Command:

```bash
hatch run pytest tests/unit/test_modules_docs_site_contract.py -q
```

Result:

- `4` tests collected
- `4` failed
- Failures covered the expected gaps:
  - `_config.yml` still targeted the GitHub Pages project URL instead of the modules public domain contract
  - `docs/index.md` did not yet state canonical ownership for module-specific deep guidance
  - `docs/_layouts/default.html` did not expose `Docs Home`, `Core CLI`, and `Modules`
  - the sidebar remained broad/core-oriented instead of module-focused

## Green Phase

Command:

```bash
hatch run pytest tests/unit/test_modules_docs_site_contract.py -q
```

Result:

- `4` tests collected
- `4` passed

## Validation

Command:

```bash
openspec validate docs-01-modules-docs-canonical-site --strict
```

Result:

- Change validated successfully in strict mode

Command:

```bash
hatch run test -- tests/unit/test_modules_docs_site_contract.py -q
```

Result:

- The repo `test` script ignored the narrow file selection and executed the broader test suite
- Full result: `389 passed in 45.42s`
