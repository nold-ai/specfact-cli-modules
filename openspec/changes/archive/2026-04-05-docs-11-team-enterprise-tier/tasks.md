## 1. Change Setup

- [x] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-11-team-enterprise-tier` entry
- [x] 1.2 Add `team-setup-docs` and `enterprise-config-docs` capability specs

## 2. Expand Existing Guides

- [x] 2.1 Expand team-collaboration-workflow into `team-and-enterprise/team-collaboration.md`: onboarding, shared config, roles
- [x] 2.2 Expand agile-scrum-workflows into `team-and-enterprise/agile-scrum-setup.md`: Scrum + Kanban team playbooks

## 3. New Enterprise Guides

- [x] 3.1 Write `team-and-enterprise/multi-repo.md`: multi-repo setups with shared bundles
- [x] 3.2 Write `team-and-enterprise/enterprise-config.md`: custom profiles, domain overlays, central config
- [x] 3.3 Document team rollout/versioning guidance for bundle-owned prompts and workspace templates

## 4. Verification

- [x] 4.1 Verify all command examples match actual CLI
- [x] 4.2 Verify team/enterprise docs describe migrated resources as bundle-owned rather than core-owned
- [x] 4.3 Verify all internal links resolve (`TDD_EVIDENCE.md`, section 3)
- [x] 4.4 Run `bundle exec jekyll build` with zero warnings (`TDD_EVIDENCE.md`, section 4)
