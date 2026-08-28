## Context

The stable module owns one canonical workflow. This change maps that workflow into three first-party/companion installation shapes without turning any harness package into a second validation engine.

Current primary-source observations reviewed on 2026-08-25:

- OpenSpec publishes one command intent under different harness-native forms, including skill-based Codex invocation: <https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md>
- ECC is skills-first, uses command shims only when legacy slash compatibility is required, and treats root AGENTS.md plus SKILL.md as cross-tool surfaces: <https://github.com/affaan-m/everything-claude-code/blob/main/.agents/skills/everything-claude-code/SKILL.md> and <https://github.com/affaan-m/everything-claude-code>
- hatch3r 1.9 documents canonical bundled content, generated Claude Code/Cursor/GitHub Copilot adapters, and no user-repository `.agents/` materialization: <https://github.com/hatch3r/hatch3r>

These are integration inputs, not permanent assumptions. Each adapter must declare and test the harness versions it actually supports.

## Goals / Non-Goals

**Goals:**

- Provide plug-and-play install, invoke, upgrade, drift-check, and uninstall behavior.
- Preserve one canonical workflow and one deterministic CLI/JSON contract.
- Keep generated AGENTS/OpenSpec/Spec Kit references small and valid after install.
- Make external contributions reviewable independently of core validator behavior.

**Non-Goals:**

- Add hooks or autonomous implementation triggers.
- Duplicate workflow semantics in three repositories.
- Claim support for untested harness versions or removed hatch3r adapters.

## Decisions

### 1. Shared adapter descriptor

Every adapter consumes a descriptor containing the exact SpecFact module version, artifact digest, authorized signature/trust-root identity, registry identity, compatible core identity, canonical workflow identity/digest, supported harness and version range, native invocation form, asset mapping, instruction markers, install scope, and uninstall inventory. It consumes the official installer's verified result when that interface owns verification. Invalid, untrusted, unsupported, or mismatched identities fail closed before installation, upgrade, invocation, or packaging.

### 2. Codex plugin is an installation shell

The Codex plugin packages the canonical skill and any minimal discovery metadata needed by Codex. It exposes Codex's native skill invocation and references the installed SpecFact CLI. It does not include validators, generated seals, or a second copy of the workflow source.

### 3. ECC integration is skills-first

The ECC companion maps the canonical workflow to its skill layout. A `commands/` shim is added only if the supported ECC/Claude Code path requires explicit legacy slash compatibility. Root AGENTS.md changes are limited to the generated gate reference owned by #253.

### 4. hatch3r distribution is an explicit upstream prerequisite

hatch3r 1.9.0 exposes no documented third-party pack or inventory-registration API. The SpecFact adapter therefore ships only after a selected hatch3r release documents a supported distribution/extension surface or a separately authorized upstream contribution adds and accepts one. Until then, hatch3r remains a blocked target: implementation must not write internal inventory data, depend on private package layout, reintroduce removed adapters, or materialize `.agents/` content contrary to the supported release.

### 5. Contract tests compare semantics, not file sameness

Adapters may have different native files and invocation spellings. Tests compare descriptor identity, phase ordering, CLI arguments, stop/approval semantics, assurance-limit text, and installed asset inventory. All determinate findings still come from the SpecFact JSON result.

### 6. External writes are separately authorized

Implementation in SpecFact may prepare adapter packages and tests. Opening issues or PRs in ECC/hatch3r or publishing a Codex plugin happens only in their dedicated accepted sessions with explicit repository authority.

## Risks / Trade-offs

- **Harness churn:** Pin tested versions and make unsupported layouts fail with upgrade guidance.
- **Workflow drift:** Compare installed workflow digest to the signed module identity.
- **Duplicate commands/hooks:** Use inventory-based idempotency and do not register hooks for the MVP.
- **Uninstall damage:** Remove only descriptor-owned files whose current digest matches the installed record.

## Migration and Rollback

Installations are opt-in. Upgrade replaces only adapter-owned assets after drift checks. Uninstall removes only recorded assets and generated instruction sections owned by the adapter. Rollback pins the last verified adapter/module identity and removes a failed external distribution from its marketplace or pack index.

## Open Questions Deferred to Implementation

- Exact Codex marketplace/distribution channel available when the adapter work begins.
- Whether ECC needs a command shim for every supported target or only Claude Code compatibility.
- Whether a selected hatch3r release has gained a documented extension surface or an upstream contribution has been accepted; absence of either outcome blocks hatch3r packaging.
