# Change: Privacy And GDPR EU Module

## Why

The five-pillar plan requires a dedicated runtime surface for PII detection, GDPR-oriented checks, and EU data-governance rules. Without a specialized module, privacy findings stay theoretical and cannot participate in the same review, evidence, and policy workflows as the other governance pillars.

## What Changes

- **NEW**: Add a `specfact-pii-gdpr` bundle with a `privacy` command focused on PII detection and GDPR/EU rule execution.
- **NEW**: Package detectors and rule resources that classify prompt/log/data findings into the paired core privacy and GDPR finding categories.
- **NEW**: Add EU-specific residency and lawful-basis checks that can be enabled through the shared policy-pack mechanism rather than ad hoc flags.
- **NEW**: Define redaction-safe evidence and reporting surfaces so privacy reviews can feed downstream knowledge/enterprise flows without leaking sensitive payloads.
- **EXTEND**: Reserve manifest, registry, docs, and signing work for a first-party privacy bundle.

## Capabilities

### New Capabilities

- `privacy-gdpr-module`: Runtime bundle, command surface, detectors, and redaction-safe reporting for PII and GDPR/EU governance.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-pii-gdpr/`, detector adapters, and GDPR rule resources.
- Affected docs: bundle overview and command-reference documentation for `privacy`.
- Dependencies: paired core changes `security-01-unified-findings-model` and `security-02-eu-gdpr-baseline`.
- Release impact: introduces a new signed official bundle and registry entry.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#218](https://github.com/nold-ai/specfact-cli-modules/issues/218)
- **GitHub Issue**: [#229](https://github.com/nold-ai/specfact-cli-modules/issues/229)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/229>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
