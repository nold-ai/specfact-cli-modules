---
layout: default
title: "The Journey: From Spec-Kit to SpecFact"
permalink: /guides/speckit-journey/
---

# The Journey: From Spec-Kit to SpecFact

This guide tracks the current public Spec-Kit workflow and shows where SpecFact fits in after a feature is specified.

## Current Spec-Kit Flow

The current Spec-Kit public workflow follows this order:

1. `/constitution`
2. `/specify`
3. `/clarify`
4. `/plan`
5. `/tasks`
6. `/analyze`
7. `/implement`

`/clarify` is no longer optional documentation drift in our site copy. It is part of the normal path before `/plan` unless you intentionally skip it. `/analyze` also belongs before `/implement`, after `/tasks`, to catch cross-artifact gaps.

## Initialize a Project

Use the current `specify` CLI to bootstrap Spec-Kit:

```bash
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
specify --version
specify init my-project --ai copilot
```

You can also initialize for other supported agents such as Claude, Cursor, or Gemini.

## Typical Feature Loop

Inside the initialized project, the expected feature loop is:

```text
/constitution -> /specify -> /clarify -> /plan -> /tasks -> /analyze -> /implement
```

Use `/clarify` to resolve underspecified behavior before architecture work. Use `/analyze` to check consistency and coverage across the generated artifacts before implementation starts.

## Hand Off to SpecFact

SpecFact complements this flow in two common ways.

### 1. Convert a Spec-Kit feature into an OpenSpec change

Use this when you want SpecFact change tracking, backlog sync, or downstream governance on top of an existing Spec-Kit feature:

```bash
specfact sync bridge --adapter speckit --repo . --mode change-proposal --feature 001-auth-sync
```

To convert every untracked feature in the repository:

```bash
specfact sync bridge --adapter speckit --repo . --mode change-proposal --all
```

### 2. Add SpecFact enforcement after specification work

Once the feature exists in SpecFact or OpenSpec form, continue with the current mounted entrypoints:

```bash
specfact project --help
specfact code --help
specfact code review --help
specfact spec --help
specfact govern --help
specfact backlog --help
```

## What Changed From Older Docs

Older copies of this page and related guides drifted in two ways:

- they referred to slash commands like `/speckit.specify` instead of the current `/specify` style
- they skipped `/clarify` and `/analyze` in the primary workflow order

Those older sequences should be treated as outdated.
