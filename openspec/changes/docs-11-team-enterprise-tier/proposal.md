# Change: Create Team And Enterprise Documentation Tier

## Why

All existing docs assume individual developer usage. There is no guidance for team leads setting up SpecFact for a team, configuring shared profiles, managing multi-repo setups, or applying enterprise-level configuration. This gap prevents adoption beyond solo developers.

## What Changes

- Expand team-collaboration-workflow.md into a full team setup guide covering onboarding, shared config, and role-based workflows
- Expand agile-scrum-workflows.md into a team onboarding playbook for Scrum and Kanban teams
- Write new multi-repo setup guide for teams working across multiple repositories
- Write new enterprise configuration guide covering custom profiles, domain overlays, and central config management
- Document how teams manage bundle-owned prompts/templates through installed module versions and shared bootstrap flows after `packaging-01-bundle-resource-payloads`

## Capabilities

### New Capabilities

- `team-setup-docs`: guides for team leads setting up SpecFact for small-medium teams
- `enterprise-config-docs`: guides for enterprise environments with custom profiles and central configuration

## Impact

- Expanded files: `team-and-enterprise/team-collaboration.md`, `team-and-enterprise/agile-scrum-setup.md`
- New files: `team-and-enterprise/multi-repo.md`, `team-and-enterprise/enterprise-config.md`
- Aligns with: `packaging-01-bundle-resource-payloads` for team-facing prompt/template ownership and rollout guidance
- Depends on: `docs-06-modules-site-ia-restructure`

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #99
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/99
- **Last Synced Status**: synced
- **Sanitized**: true
