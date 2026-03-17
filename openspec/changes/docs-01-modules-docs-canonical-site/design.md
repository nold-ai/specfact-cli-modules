# Design: Modules Docs Canonical Site And Publishing Contract

## Context

The modules repository already owns the content that best represents official bundle workflows, but the public site identity is still weak:

- the site currently targets `https://nold-ai.github.io/specfact-cli-modules/`
- many overlapping bundle pages are still available in `specfact-cli`
- navigation is not yet coordinated with a canonical docs entry point

This repository should become the canonical origin for module-specific deep docs without depending on a combined build with the core docs repository.

## Goals

- Give the modules docs site a first-class public identity suitable for `modules.specfact.io`
- Make site navigation explicitly interoperable with the core docs portal model
- Support independent publishing of module-only docs changes

## Non-Goals

- Implement Cloudflare routing in this repository
- Move every duplicated page out of `specfact-cli` in the same change
- Replace Jekyll or GitHub Pages

## Publication Model

Target public topology:

```text
docs.specfact.io      -> canonical docs entry point and core docs origin
modules.specfact.io   -> modules docs origin
```

This repo is responsible for the `modules.specfact.io` side of the contract:

- site copy and metadata must present it as the canonical home for official bundle docs
- navigation must include routes back to docs home and core docs
- internal sidebar focus should remain module-specific rather than trying to mirror the entire core docs tree

## Navigation Contract

Shared top-level labels:

- `Docs Home`
- `Core CLI`
- `Modules`

The modules site should use these labels in its top nav while keeping the local sidebar focused on:

- bundle guides
- official modules
- publishing and signing
- reference

## Validation Strategy

Implementation should add lightweight checks for:

- canonical site identity in landing page/configuration
- shared top-level navigation labels
- avoidance of wording that presents the GitHub Pages project URL as the long-term canonical home

Those checks are sufficient because the change is about site identity and publication contract, not runtime behavior.

## Discovery Notes

The current modules docs set substantially overlaps with the `specfact-cli` docs tree. Shared files currently include:

- landing/config/layout assets (`index.md`, `_config.yml`, `_layouts/default.html`, `assets/main.scss`)
- module-focused guide families (`guides/installing-modules.md`, `guides/module-marketplace.md`, `guides/module-development.md`, `guides/publishing-modules.md`, `guides/module-signing-and-key-rotation.md`)
- adapter and backlog workflow guides (`adapters/*.md`, `guides/backlog-*.md`, `guides/devops-adapter-integration.md`)
- module/reference material (`reference/module-*.md`, `reference/bridge-registry.md`, `reference/commands.md`)

The canonical module-owned destinations for this change are the modules site landing page, top navigation, and the bundle/module deep-guidance sections listed above. This change does not migrate or delete the duplicate pages from `specfact-cli`; it makes the ownership contract explicit here so the follow-on core-docs cleanup can point readers back to this site.

## Cutover Assumptions

- `docs.specfact.io` remains the canonical entry point for the overall docs experience and the core docs origin.
- `modules.specfact.io` is the intended canonical modules docs origin once GitHub Pages and Cloudflare are wired.
- Until DNS/routing is live, site copy must describe the modules subdomain as the intended public address and treat GitHub Pages as preview infrastructure rather than the long-term canonical identity.
