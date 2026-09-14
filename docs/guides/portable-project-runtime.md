---
layout: default
title: Review external Python projects
permalink: /guides/portable-project-runtime/
description: Prepare repository dependencies in an isolated sidecar runtime for capsule review.
keywords: [capsule, review, Python, pip, Hatch, uv, Poetry]
audience: [users, developers]
expertise_level: [intermediate]
doc_owner: specfact-cli-modules
tracks:
  - packages/specfact-code-review/**
last_reviewed: 2026-09-14
exempt: false
exempt_reason: ""
---

# Review external Python projects

Portable project runtimes let the code review capsule use a repository's own dependencies and test configuration. Runtime acquisition runs in a disposable builder; analysis runs offline in separate target workers. The signed supervisor keeps its own dependencies. Analyzer-owned imports follow the recorded member graph and resolve from the verified analyzer installation before project paths or startup imports are considered; project-owned dependencies keep their selected versions. Member startup preserves ordinary editable hooks, restores analyzer lookup precedence afterward, and reports hooks that remove protected import machinery or add paths outside the copied runtime. These startup checks do not sandbox arbitrary Python code within one interpreter. A namespace shared between analyzer-owned and project-owned portions is not currently combined; that configuration reports an origin mismatch and incomplete analysis.

Execution requires Linux x86-64 with the capsule's supported Python 3.11, 3.12, or 3.13 ABI and working unprivileged user namespaces. A local descriptor does not grant protected pull-request authority.

Windows and macOS host-to-worker setup is not implemented or validated by this change. Runtime inspection reads project metadata, but automatic preparation and capsule execution require the Linux environment above. A future container or VM handoff must validate source transfer, architecture, native dependencies, and returned evidence. Linux execution cannot establish Windows- or macOS-specific test behavior.

## Inspect and review

From the repository root, inspect the selected manager and input identities without installing dependencies:

```bash
specfact code review runtime inspect --json
```

Existing review commands prepare the target runtime automatically before dependency-sensitive analysis:

```bash
specfact code review run src/example.py tests/test_example.py --bug-hunt --json --out /tmp/review.json
```

A single declared test dependency group or test extra is selected automatically. Explicit groups and extras suppress automatic selection of the other category; competing choices require configuration. Hatchling alone is a build backend, so it does not imply a Hatch environment. Competing environment choices produce a diagnostic; select the intended environment explicitly. Discovery validates the metadata tables it consumes before choosing an environment, including when a manager is explicitly selected; malformed tables identify the source file and section.

## Select an environment

Store selection outside the reviewed source when possible. For a detached Hatch environment:

```toml
manager = "hatch"
environment = "review"
```

For a uv project with a test group:

```toml
manager = "uv"
groups = ["tests"]
```

For a Hatch test matrix, `environment = "hatch-test"` selects its unique native environment matching the selected Python version. Multiple matching matrix entries require a concrete name such as `hatch-test.py3.12-feature`. Selection uses Hatch's exported configuration.

The `python` setting overrides `.python-version`; both are checked against `requires-python` and the exact signed interpreter version. A root `.python-version` also activates automatic preparation for source-only projects without packaging metadata. A compatible controller ABI is reused; an incompatible controller does not force that ABI onto the project. Base and head reviews select their workers independently.

Poetry Python constraints are intersected with project `requires-python` before choosing a worker. PEP 440 ranges are supported; Poetry caret, tilde, union and table syntax currently produce an explicit unsupported-constraint diagnostic. Express the declaration as an equivalent PEP 440 range to proceed.

Supported manager names are `pip`, `hatch`, `uv`, and `poetry`. Optional fields are `python`, `groups`, `extras`, `requirements`, `constraints`, `source_roots`, and `native_libraries`. Explicit `requirements` and `constraints` fields apply to `pip`; other managers reject these fields with a diagnostic rather than ignore them. Paths are repository-relative. Native libraries use ELF names such as `libodbc.so.2`; unavailable libraries are named in the preparation diagnostic. Hatch extras and dependencies belong in the selected native Hatch environment.

```bash
specfact code review runtime prepare --project-config /tmp/review-runtime.toml --json
specfact code review run src/example.py tests/test_example.py --project-config /tmp/review-runtime.toml
```

Plain package-index dependencies do not require Git. Preparation stages available Git capabilities; a dependency that actually needs a missing Git executable or HTTP transport fails with a preparation diagnostic and installation remedy. A newly initialized repository without a first commit has no VCS version context; ordinary dependency discovery can still proceed. Missing requested revisions or corrupt Git state remain errors.

Preparation returns the path to `project-runtime.json`. Generated environments, resolutions, and inventories stay in the private cache, outside customer source. Keep descriptors private: they contain project dependency and path metadata. Index credentials are excluded from published descriptor inventory; private failed-build logs are owner-readable.

## Reuse and attach

```bash
specfact code review runtime prepare --project-config /tmp/review-runtime.toml --offline --json
specfact code review run src/example.py tests/test_example.py --project-config /tmp/review-runtime.toml --project-runtime /path/from/prepare/project-runtime.json
```

Attachment verifies the payload, project inputs, ABI, and analyzer worker identity. Changed workspace source invalidates built project packages as well as changed dependency files. Git commits, tags, and shallow-history boundaries also participate in cache identity for dynamically versioned packages. Staged reviews bind the captured Git tree separately from its HEAD commit, so private build copies retain the staged index and sanitized VCS metadata even if the live index later changes. Private Git metadata contains only the object closure recorded by the selected commit, staged tree, tags, and shallow boundary; unrelated branch refs and unreachable objects are excluded. A corrupt cache is rejected; remove only the identified invalid artifact and prepare again. Interrupted preparations do not publish partial descriptors.

## Interpret incomplete evidence

Runtime failure preserves independent static findings. Affected analyzers reference the preparation diagnostic and remain incomplete. A real missing import after successful preparation remains a finding. A report can contain real failures while still showing incomplete required evidence.

Runtime attachment adds import roots only when declared through pytest `pythonpath` or explicit review `source_roots`. It does not infer `src/` or repository-root overrides from layout: installed packages, build-generated contents, editable hooks, and native pytest import modes retain their normal precedence.

Pytest configuration and selection controls remain active. Deselected tests are recorded separately from the selected execution inventory; distributed deselection visibility is labelled as controller-observed. Quoted pytest paths and file patterns preserve spaces using native argument rules. Malformed tables, invalid path/pattern value shapes, and unclosed quotes identify the section or option and configuration file. The report records collection, execution, setup and internal errors, configured options, versions, and coverage. Distribution-owned commands are available inside target workers. Localhost coordination for plugins stays inside the offline namespace. Collection-only runs, early stopping that leaves collected tests unexecuted, and absent required coverage do not become successful test evidence.

## Compatibility evidence

The checked-in corpus pins Requests, Hatch, Flask, and Poetry commits and their initial source/test slices. The customer workflow exercises supported Python ABIs, records host tests separately, checks cold preparation and offline attachment, and injects controlled defects. Untouched upstream acceptance requires completed applicable analysis; it does not require zero findings.

Track release acceptance in [User Story #473](https://github.com/nold-ai/specfact-cli-modules/issues/473) and the original [customer bug #472](https://github.com/nold-ai/specfact-cli-modules/issues/472). The reconstructed Hatch fixture is not proof that the inaccessible original customer reproduction is resolved.

Python subprocess options `-I`, `-E`, and `-S` disable the startup mechanism used to attach the selected runtime. The worker rejects these exact options with `project_python_option_unsupported` rather than running without project dependencies. Ordinary `-c`, `-m`, `-u`, and script invocations retain native Python argument handling.

Source aliases must resolve to included repository content. Aliases into excluded `.env`, virtual environments, or Git metadata are rejected before dependency building. Valid internal links are preserved in the private source copy, including absolute links rebased into that copy; the copied bytes are verified before build hooks execute.

Pip discovery recognizes `requirements.txt`, pip-tools `requirements.in`, and `pylock.toml`. Multiple lock/requirements alternatives require explicit selection. Standard lock handling is delegated to pip; pip 26.2.1 documents `pylock.toml` support as experimental ([pip install reference](https://pip.pypa.io/en/stable/cli/pip_install/), accessed 2026-09-14). Static `setup.cfg` Python constraints are imported when PEP 621 metadata does not provide them.

Portable analysis uses a verified private source copy with local environments and excluded secret files removed. The corpus records artifact bytes and Linux host-interface transfer counters; those counters include concurrent host traffic and are not exact package download sizes. Its warm preparation and attachment commands additionally run in a non-root network namespace, independently of the offline option.
