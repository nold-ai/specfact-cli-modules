---
layout: default
title: Enterprise Configuration
permalink: /team-and-enterprise/enterprise-config/
---

# Enterprise Configuration

This guide covers the configuration levers most relevant to enterprise rollouts: profiles, central registry policy, project-scoped bootstrap, and domain-specific overlays managed in repository configuration.

## 1. Start from an enterprise profile

```bash
specfact init --profile enterprise-full-stack
specfact init ide --repo . --ide cursor
```

This profile installs the broadest official command surface for teams that need project, backlog, code, spec, and govern flows together.

## 2. Manage registries centrally

Use custom registries when teams consume an internal mirror or approved company modules:

```bash
specfact module add-registry https://company.example.com/specfact/registry/index.json --id company --priority 10 --trust always
specfact module list-registries
```

Combine this with project or workstation provisioning so teams see the same registry ordering and trust policy.

## 3. Use project-scoped bootstrap for domain overlays

Enterprise teams often need repository-local overlays on top of the shared company baseline. The supported approach is to keep shared module versions central while letting individual repositories bootstrap their own module root and IDE exports:

```bash
specfact module init --scope project --repo .
specfact init ide --repo . --ide cursor --force
```

Treat those repo-local artifacts as the domain overlay layer for a given service or business unit.

## 4. Keep bundle-owned resources versioned

Prompts and workspace templates ship from installed bundles. Enterprise rollout should therefore version the bundles, not copied prompt files:

- approve bundle versions centrally
- upgrade with `specfact module upgrade`
- refresh project-facing exports with `specfact init ide --force`

## 5. Non-official publisher policy

If the enterprise uses private or third-party registries, make the trust model explicit in automation and workstation setup. For non-official publishers, use the documented trust controls rather than bypassing the module lifecycle.

## Related

- [Multi-Repo Setup](/team-and-enterprise/multi-repo/)
- [Custom registries](/authoring/custom-registries/)
- [Module marketplace](/guides/module-marketplace/)
