---
layout: default
title: Module Publishing Guide
permalink: /module-publishing-guide/
---

# Module Publishing Guide

This legacy note predates the current authoring IA. For the maintained publishing workflow, use
[Publishing modules](/authoring/publishing-modules/).

The checklist below remains a useful quick reference for the registry data you need to prepare.

## Prerequisites

- A module package with `module-package.yaml`
- A release tarball
- SHA-256 checksum for the tarball

## Registry Entry Template

Add a module entry to `registry/index.json` with the following fields:

- `id` (namespace/name)
- `namespace`
- `name`
- `description`
- `latest_version`
- `core_compatibility`
- `download_url`
- `checksum_sha256`

## Validation Checklist

- Verify module id format (`namespace/name`)
- Verify checksum matches uploaded tarball
- Verify `core_compatibility` uses PEP 440 specifier syntax
