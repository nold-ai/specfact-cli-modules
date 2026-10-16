# GitHub alignment for the local review reset

The owner approved these artifact and issue dispositions on 2026-10-16, Europe/Berlin. Planning artifacts do not implement the runtime. Live write/readback results are appended under Execution verification after the replacement package is validated.

## Replacement stories

| Change | Public issue | Parent | Status | Direct blockers |
| --- | --- | --- | --- | --- |
| code-review-17-project-runtime-bootstrap | [modules #513](https://github.com/nold-ai/specfact-cli-modules/issues/513) | #163 under #162 | Todo / User Story | None. |
| code-review-18-project-standards-and-checks | [modules #514](https://github.com/nold-ai/specfact-cli-modules/issues/514) | #163 under #162 | Todo / User Story | #513. |
| code-review-19-local-report-and-cutover | [modules #515](https://github.com/nold-ai/specfact-cli-modules/issues/515) | #163 under #162 | Todo / User Story | #513 and #514. |
| code-review-local-report-adoption | [core #769](https://github.com/nold-ai/specfact-cli/issues/769) | #375 under #285 | Todo / User Story | modules #515. |
| code-review-20-external-installation-acceptance | [modules #516](https://github.com/nold-ai/specfact-cli-modules/issues/516) | #163 under #162 | Todo / User Story | #515 and core #769. |

All five use Project SpecFact CLI, assignee djm81, and existing enhancement/architecture/codebase/openspec/change-proposal labels. Direct dependencies are native GitHub blocked-by relationships. They must be rechecked before implementation.

## Approved predecessor dispositions

| Item | Disposition and retained responsibility |
| --- | --- |
| modules #460 | Close Not Planned as superseded remaining native capsule delivery. Preserve delivered code and experimental evidence; new implementation later removes production capsule paths. |
| modules #488 | Close Not Planned. Retain never-delivered optional Apple distribution proposal under abandoned history; no specification promotion. |
| modules #495 | Close Not Planned. Retain never-delivered Windows capsule proposal under abandoned history; ordinary Windows local acceptance belongs to #516. |
| modules #512 | Close Not Planned. Retire capsule prerequisites; preserve receipt coverage attribution, complete explicit selection, cold preparation/review phase accounting and other relevant behavior as replacement acceptance. |
| PR #506 | Close unmerged as superseded capsule promotion. Do not publish or alter its historical artifacts. |
| PR #509 | Close unmerged as superseded native repairs. Preserve actual fix/review records; reusable diagnostics/path/source cases become replacement tests. |
| PR #510 | Close unmerged as superseded Linux capsule execution budgets. Keep timeout/incomplete-outcome and per-invocation budget isolation cases in replacement testing. |
| code-review-portable-reviewer-bootstrap | Retire remaining capsule-only tasks in place and preserve shipped selection/tool fixes. |
| branch-only code-review-baseline-receipt-coverage and code-review-linux-pytest-execution-budget | Do not import discontinued capsule implementation tracks. Existing issue/PR evidence remains history and relevant behavior is retained in the new acceptance requirements. |
| modules #480 | Keep open, current owner/status. Add a native blocker from replacement #514 and its explicit-file scenarios; close only after actual execution proof. |
| modules #417 and core #679 | Preserve active ownership/status and acceptance. Add only a local-schema compatibility coordination note. |
| core #680 | Preserve protected assurance scope and status. Note that schema 2.0 local evidence cannot satisfy its current capsule contract automatically. |
| closed modules #416/#459/#466/#472/#473 | Keep closed and preserve immutable releases/evidence. This reset does not reopen, relabel as new delivery, or archive them. |
| modules #511; core #718/#719 | Preserve independent module signing/security work, status and gates. |
| preflight #431/#432/#434, architecture #164/#230 and requirement-context #491 | Future consumers of context/reports. No new blanket blocking edge, runtime ownership or implementation claim. |

## Reusable acceptance from the discontinued queue

Retain explicit tests even when source basenames collide; pytest collection/execution/configuration failures; actual generated-source and canonical-path attribution; bounded output and malformed-report handling; no shared invocation-budget leakage; and source/checker coverage measurement tied to the actual Python source. Preserve all applicable assertions when a case remains relevant. A test whose sole contract is a removed containment mechanism is retired through the owning implementation spec delta, not reclassified as passing.

Current repository security, signing and review gates remain effective throughout this artifact delivery. Future capsule gate replacement is explicit scope in #515/#516 and paired core #769. This planning work does not waive or rewrite those runtime gates.

## Execution verification

Live GitHub readback completed on 2026-10-16, Europe/Berlin. All five replacement stories are open User Stories with the documented parents, labels, assignee, SpecFact CLI/Todo project status and exact native direct blockers.

- Modules #460/#488/#495/#512 are CLOSED with state reason NOT_PLANNED and project status Rejected.
- PR #506/#509/#510 are closed and unmerged. Their recorded head commit identities match the pre-disposition snapshot. No branch deletion or publication was requested.
- Modules #480 remains open with #514 as its native implementation blocker.
- Modules #417/#511 and core #679/#680 retain their original status, type, assignees, labels, parent, project fields and blocker relationships. Coordination comments do not change their implementation authority.
- The canonical architecture and each new change's requirement scenarios are also published on the corresponding issue. Relative artifact references there are repository paths rather than links to unpublished branches.

The before/after public-state snapshots are included in the committed [validation receipt](../../../.audit/code-review-reset-validation.json). The five-source Requirements validator reports planned maturity, proposal-only delivery and no implementation evidence. Structural verification covers 23 requirements, 55 inspection cases and 90 unchecked implementation tasks after review refinements. Neither actual local runtime support nor a completed OpenSpec change is claimed.

Repository artifacts use modules branch `codex/code-review-reset-planning` and core branch `codex/code-review-local-report-planning`, each targeting `dev` in a separate planning pull request. The internal wiki source, C14/C15 compatibility notes, index and native graph were aligned on 2026-10-16 and refreshed for review clarifications. Unrelated dirty wiki source pages were preserved. Its initial strict health check had 59 pre-existing errors; the review follow-up observes 58 and no new errors. No merge or runtime release is claimed.

Both branches were signed with the owner's existing GitHub-verified key and pushed on 2026-10-16. Ready planning PRs are [modules #517](https://github.com/nold-ai/specfact-cli-modules/pull/517) and [core #770](https://github.com/nold-ai/specfact-cli/pull/770), both targeting `dev`. GitHub readback confirms open, non-draft state and valid commit signatures. Their file lists contain planning/history, audit evidence and a repaired documentation link. All 90 implementation tasks remain unchecked. Opening these PRs does not authorize merging or runtime implementation.
