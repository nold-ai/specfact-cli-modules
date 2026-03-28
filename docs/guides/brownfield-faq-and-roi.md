---
layout: default
title: Brownfield FAQ and ROI
permalink: /guides/brownfield-faq-and-roi/
keywords: [brownfield, faq, roi, planning, investment]
audience: [solo, team]
expertise_level: [intermediate]
---

# Brownfield FAQ and ROI

This page merges the brownfield FAQ and ROI guidance into one planning reference.

## What is the minimum safe starting point?

Start with a project bundle plus IDE resource bootstrap:

```bash
specfact init --profile solo-developer
specfact init ide --repo . --ide cursor
specfact code import legacy-api --repo .
```

That gives you a repeatable baseline without needing to modernize the whole codebase at once.

## How should teams estimate the effort?

A practical sequence is:

1. Import the repo into a bundle.
2. Analyze current contract coverage.
3. Validate the contracts you already have.
4. Add enforcement only when the bundle state is stable enough for promotion.

The commands that anchor those phases are:

```bash
specfact code analyze contracts --repo . --bundle legacy-api
specfact spec validate --bundle legacy-api
specfact govern enforce sdd legacy-api --no-interactive
```

## Where does the ROI usually appear first?

The earliest gains usually come from:

- faster understanding of legacy structure after `code import`
- less manual contract drift checking once `spec validate` is in the loop
- fewer late-stage release surprises when `govern enforce sdd` becomes part of promotion

## How do teams avoid drift between CLI and IDE resources?

Refresh exported IDE assets from the installed bundles instead of storing copied prompt files:

```bash
specfact init ide --repo . --ide cursor --force
```

## When is the workflow worth formalizing in CI?

Once the team is repeatedly running local validation and enforcement, move the same sequence into CI so release checks are deterministic.

See [CI/CD pipeline](/guides/ci-cd-pipeline/) for the repository gate order.

## Related

- [Brownfield modernization](/guides/brownfield-modernization/)
- [Brownfield examples](/guides/brownfield-examples/)
- [Daily DevOps routine](/guides/daily-devops-routine/)
