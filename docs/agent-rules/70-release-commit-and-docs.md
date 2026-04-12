---
layout: default
title: Agent release, commit, and docs rules
permalink: /contributing/agent-rules/release-commit-and-docs/
description: Versioning, registry consistency, documentation, and commit rules preserved from the previous AGENTS.md.
keywords: [agents, versioning, registry, docs, commits]
audience: [team, enterprise]
expertise_level: [advanced]
doc_owner: specfact-cli-modules
tracks:
  - AGENTS.md
  - README.md
  - docs/**
  - registry/index.json
  - packages/**/module-package.yaml
last_reviewed: 2026-04-12
exempt: false
exempt_reason: ""
id: agent-rules-release-commit-and-docs
always_load: false
applies_when:
  - finalization
  - release
  - documentation-update
priority: 70
blocking: false
user_interaction_required: true
stop_conditions:
  - version bump requested without confirmation
depends_on:
  - agent-rules-index
  - agent-rules-quality-gates-and-review
---

# Agent release, commit, and docs rules

## Versioning

- Apply semver in `packages/<bundle>/module-package.yaml`: `patch` for bug fixes, `minor` for additive command or API work, `major` for breaking changes.
- When a bundle requires a newer `specfact-cli`, update `core_compatibility` in the bundle manifest and the registry metadata when carried there.
- Treat version bumps and registry updates as one release surface, not independent edits.

## Registry and publish flow

1. Branch from `origin/dev` into a feature or hotfix branch.
2. Bump the bundle version in `packages/<bundle>/module-package.yaml`.
3. Run `python scripts/publish-module.py --bundle <bundle>` as the publish pre-check.
4. Publish with the project tooling wrapper when release work is actually intended.
5. Update `registry/index.json` with `latest_version`, artifact URL, and checksum.

## Commits

- Use Conventional Commits.
- If signed commits fail in a non-interactive shell, stage files and hand the exact `git commit -S -m "<message>"` command to the user instead of bypassing signing.

## Documentation

- Keep docs current with every user-facing bundle, registry, or workflow change.
- Preserve Jekyll frontmatter on docs edits.
- Update navigation when adding or moving pages.
- Keep cross-links between `docs.specfact.io` and `modules.specfact.io` honest.
