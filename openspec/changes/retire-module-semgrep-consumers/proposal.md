# Retire Semgrep from remaining module entry points

## Why

The trusted-local Code Review reset owns the 18 supplemental review rules and deletes the capsule review backend. Project analysis, Project import and Codebase `repro` still have their own scanner calls, outputs and configuration. An externally installed module set must not retain those Semgrep execution paths once the replacement ships.

## What changes

Replace the Project feature/quality scanner and Codebase repro async check using the same proved rule semantics as their core counterparts where applicable. Inventory third-party configuration and historical serialized fields before choosing the migration. Preserve supported findings, diagnostics and expected source effects, including truthful handling of requested fixes. Remove active module scanner discovery, tool install instructions, presets, repo-development dependencies and commands that provision or invoke Semgrep.

Project import also invokes Semgrep to select tests for OpenAPI example extraction and can write a Semgrep preset during Spec-Kit import. Compare the existing AST extractor with the configured path using request, response and status-code fixtures before routing both OpenAPI import modes through it. Retire the Spec-Kit scanner preset and verify the protocol and GitHub Actions generation still run.

A local source-only probe on 22 November 2026 extracted a POST request from a selected test with `response = client.post(...)` but omitted both `assert response.status_code == 201` and the asserted `response.json()` body. Keep this fixture when comparing the AST and configured paths. Core also carries an OpenAPI test converter. Coordinate the expected example semantics with core #797 before replacing either path.

## Dependencies and impact

Module #514 owns review-rule replacement, #515 owns review cutover, and #516 owns signed installed acceptance. These entry points have independent fixture work. Align shared rule semantics with the paired core change `retire-core-semgrep` before removing a duplicate path. Historical artifacts remain immutable. Any affected signed module is versioned and signed through normal release gates.

## Source tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- GitHub Issue: #523
- Issue URL: <https://github.com/nold-ai/specfact-cli-modules/issues/523>
- Parent: #163

## Codebase Repro milestone

A developer runs `specfact code repro --repo PATH --async-checks` from the installed CLI
against a project they control. Existing projects with the standard legacy policy continue
to select async analysis automatically. The analyzer reads Python source in an isolated
child interpreter. Other Repro checks keep their existing tool and environment selection.

The core analyzer from #797 owns the rules, legacy-policy recognition, exit codes and
JSON output. Codebase owns the Repro check lifecycle and YAML report. Reuse the installed
scanner script and its existing CLI rather than copying rules into the bundle or routing
through the deprecated core Repro checker and duplicating the whole check suite. An older
core remains compatible with normal Repro when async analysis is not requested. An async
request on that core fails with upgrade guidance. The supported replacement is report-only
and states when remediation must be done manually. Project import, Project analysis,
the trusted-local review cutover and publication are outside this milestone.
