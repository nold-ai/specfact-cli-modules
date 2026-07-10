# Design: docs-16 core documentation accountability sync

## Context

The core repository already owns `check-documentation-accountability.py`. It
derives official module packages and grouped roots from a supplied modules
checkout, then validates core catalogues, generated command artifacts, and
ownership handoffs. Modules must call that authority instead of maintaining a
second inventory or repeating core-catalogue rules.

The modules command overview is deterministic but its pre-commit routing only
runs generation for selected docs and prompt paths. It therefore needs broader
module/registry input routing plus inventory coverage that makes new or remapped
official records fail rather than pass with unchanged generated output.

## Decisions

1. **Use a subprocess wrapper, not a copied checker.** The wrapper resolves
   `SPECFACT_CLI_REPO`, then the matching paired worktree, then a sibling
   `specfact-cli` checkout. It invokes the core checker with the current modules root.
   Missing checkout or checker is a non-zero, actionable setup failure.
2. **Keep CI branch pairing deterministic.** Docs Review first uses a matching
   core branch name; if unavailable, it uses only `dev` or `main` from the PR
   base/ref fallback. Checkout and checker failures block the workflow.
3. **Run generated-artifact work for every module/registry change.** Local
   pre-commit regenerates and stages only deterministic changes after rejecting
   relevant unstaged inputs. CI runs check-only validation and never modifies
   artifacts. Unrelated implementation-only changes may produce identical
   generated files; freshness still proves that result.
4. **Make manifest/registry inventory authoritative for overview coverage.**
   The overview generator/checker must reject disagreement, omission, rename,
   or grouped-root remapping between official inventory records and command
   mounts. Adding a module therefore requires an explicit represented mount and
   regenerated artifacts.
5. **Make non-main signature repair staged-only and non-destructive.** Baseline
   verification still validates every payload checksum. When a non-required
   signature has no local public key, its cryptographic verification is skipped
   rather than treated as checksum drift. Automatic checksum/version repair is
   limited to module payloads staged for the pending commit; unrelated or
   pre-existing failures stop without rewriting manifests. Main keeps strict
   signature verification and no checksum-only auto-repair.

## Risks And Mitigations

- **Paired-core resolution drift** — Cover explicit, sibling, paired-worktree,
  and unavailable paths; document the required environment variable.
- **Accidental staging of unrelated generated output** — Refuse local
  auto-staging when relevant inputs have unstaged hunks.
- **Workflow filters omit a validation input** — Test Docs Review paths for
  manifests, registry, package source/resources/docs, tooling, workflow, and
  generated artifacts.
- **Signature repair mutates unrelated manifests** — Derive repair candidates
  from the staged index only, remove the failed-manifest fallback, and test that
  missing optional public keys do not start repair.

## Rollback

Revert the wrapper, gate wiring, and inventory/freshness checks together. No
data migration, registry publication, module signature, or runtime rollback is
required.
