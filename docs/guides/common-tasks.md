---
layout: default
title: Common Tasks Quick Reference
permalink: /common-tasks/
redirect_from:
  - /guides/common-tasks/
---

# Legacy Workflow Note

This page described older plan-generation, contract, and constitution workflows that are not part of the current public mounted CLI in this repository. The detailed command examples previously documented here were removed because they no longer match the command surface exposed by `specfact --help`.

Use the current mounted entrypoints instead:

- `specfact project --help`
- `specfact project sync --help`
- `specfact code --help`
- `specfact code review --help`
- `specfact spec --help`
- `specfact govern --help`
- `specfact backlog --help`
- `specfact module --help`

When you need exact syntax, verify against live help in the current release, for example:

```bash
specfact sync bridge --help
specfact code repro --help
specfact code validate sidecar --help
specfact spec validate --help
specfact govern enforce --help
```

This page needs a full rewrite around the mounted command groups before task-level workflow examples can be published again.
