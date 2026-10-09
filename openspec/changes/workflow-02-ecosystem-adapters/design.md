# Design: Integrate released validation with Spec Kit and GitHub

## Ownership and public boundary

Modules owns thin extension/Actions packaging, producer projection and summaries. #483 owns execution/budgets; core #742 owns contributor adoption. Native JSON remains authoritative.

Use existing Bridge Adapter, plugin registration and requirement/evidence extension surfaces. Keep producer-original records separate from normalized presentation. Parsing and digest evaluation are side-effect free; runtime adapters own invocation, filesystem snapshots and explicitly selected external access. No new graph engine, hosted service or unrestricted shell runner is introduced.

## Decisions

### Thin upstream and CI invocation adapters

The modules repository SHALL provide an optional Spec Kit extension using documented pinned upstream extension hooks and a GitHub Actions integration invoking released SpecFact commands. Authoring, clarification and task generation SHALL remain upstream-owned. The integration SHALL verify compatible signed module/core identities and preserve producer exit codes and complete native reports. Hooks SHALL be documented as invocation assistance; protected CI SHALL remain the enforcement boundary. The first certified execution path SHALL use structured pytest runner identity, version and configuration, not unrestricted opaque command strings.

### Loss-aware summaries and SARIF projection

GitHub summaries SHALL show independent producer statuses, exact candidate identity, missing mappings, unavailable checks and native-report links. SARIF 2.1.0 projection SHALL include only suitable located findings and SHALL preserve stable rule identity, original rule/severity, producer identity and original report references. Unlocated obligations and unsupported evidence SHALL remain visible in summaries and authoritative native JSON. Projection SHALL NOT turn advisory convergence into acceptance, fabricate locations or overwrite failed test/security outcomes.

### Least-privilege portable integration

Integration defaults SHALL support local/offline native output without external writes or paid model calls. GitHub publication SHALL require only the scoped permissions needed for selected summary/artifact/code-scanning operations, with third-party actions pinned to immutable revisions. Pull-request execution SHALL NOT execute untrusted candidate code with write credentials through pull_request_target. Unsupported reviewer report formats SHALL be explicit; no universal CodeRabbit/Copilot SARIF contract SHALL be assumed. Native JSON SHALL remain available when code-scanning upload is unavailable.

## Dependencies and rollout

Current-run workflow integration waits for signed #483, which waits for #481. Spec Kit hook profile acceptance waits for paired compatibility follow-ups. Standalone summary/SARIF fixture work can proceed independently. Optional #433 and #169/#170/#171 are not blanket blockers.

Start additive behavior in shadow/advisory mode where appropriate. Preserve independent required checks. Review exact core/module version and signed payload identities before adoption. Roll back by disabling optional context/hooks/projection or restoring the prior compatible signed pair; retain reports with their original schema, statuses and limitations.

## Verification boundaries

Every spec scenario becomes an independently meaningful fixture or integration assertion before behavior changes. Test negative identities, missing/ambiguous input and source preservation rather than merely mirroring data classes. Reports of planning inspection do not claim execution. Use pytest structured identities first and declare unsupported platforms/producers explicitly.
