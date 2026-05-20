---
layout: default
title: Official SpecFact Modules Docs
nav_order: 1
permalink: /
keywords: [specfact, modules, bundles, documentation, home]
audience: [solo, team, enterprise]
expertise_level: [beginner, intermediate, advanced]
---

# Official SpecFact Modules Docs

Canonical documentation for official nold-ai bundles and module-specific workflows.

The modules site owns all bundle-specific deep guidance. Core CLI platform docs remain at [docs.specfact.io](https://docs.specfact.io).

**New here?** Start with [Choose Your Modules]({{ '/getting-started/choose-your-modules/' | relative_url }}) — a quick guide to what each module does, which ones you need, and how they work together.

**New in Code Review:** `ai_bloat` advisories flag bloated shapes common in AI-assisted code and feed `/specfact.08-simplify` for per-change confirmed cleanup. Start with the [AI bloat quickstart]({{ '/quickstart-ai-bloat/' | relative_url }}).

## Find Your Path

<div class="path-cards">
<div class="path-card">
<h3>Solo Developer</h3>
<p>Get started quickly with SpecFact modules on your own projects.</p>
<ul>
<li><a href="{{ '/getting-started/choose-your-modules/' | relative_url }}">Choose Your Modules</a></li>
<li><a href="{{ '/getting-started/installation/' | relative_url }}">Installation</a></li>
<li><a href="{{ '/getting-started/first-steps/' | relative_url }}">First Steps</a></li>
<li><a href="{{ '/getting-started/tutorial-backlog-quickstart-demo/' | relative_url }}">Backlog Quickstart Demo</a></li>
</ul>
</div>
<div class="path-card">
<h3>Small Team / Startup</h3>
<p>Set up SpecFact for your team with shared configuration and agile workflows.</p>
<ul>
<li><a href="{{ '/team-and-enterprise/team-collaboration/' | relative_url }}">Team Collaboration Setup</a></li>
<li><a href="{{ '/team-and-enterprise/agile-scrum-setup/' | relative_url }}">Agile &amp; Scrum Setup</a></li>
<li><a href="{{ '/guides/cross-module-chains/' | relative_url }}">Cross-Module Workflows</a></li>
<li><a href="{{ '/guides/daily-devops-routine/' | relative_url }}">Daily DevOps Routine</a></li>
</ul>
</div>
<div class="path-card">
<h3>Corporate Team</h3>
<p>Scale SpecFact across multiple repos with CI/CD integration and governance.</p>
<ul>
<li><a href="{{ '/team-and-enterprise/multi-repo/' | relative_url }}">Multi-Repo Setup</a></li>
<li><a href="{{ '/guides/ci-cd-pipeline/' | relative_url }}">CI/CD Pipeline Integration</a></li>
<li><a href="{{ '/bundles/govern/overview/' | relative_url }}">Govern Bundle Overview</a></li>
<li><a href="{{ '/bundles/code-review/overview/' | relative_url }}">Code Review Bundle Overview</a></li>
</ul>
</div>
<div class="path-card">
<h3>Enterprise</h3>
<p>Enterprise-grade configuration, security, custom registries and module authoring.</p>
<ul>
<li><a href="{{ '/team-and-enterprise/enterprise-config/' | relative_url }}">Enterprise Configuration</a></li>
<li><a href="{{ '/authoring/module-signing/' | relative_url }}">Module Signing</a></li>
<li><a href="{{ '/authoring/custom-registries/' | relative_url }}">Custom Registries</a></li>
<li><a href="{{ '/reference/module-security/' | relative_url }}">Module Security</a></li>
</ul>
</div>
</div>

## Official Bundles

| Bundle | Overview | Deep Dives |
|--------|----------|------------|
| Backlog | [Overview](bundles/backlog/overview/) | [Refinement](bundles/backlog/refinement/), [Delta](bundles/backlog/delta/), [Policy Engine](bundles/backlog/policy-engine/), [Dependency Analysis](bundles/backlog/dependency-analysis/) |
| Project | [Overview](bundles/project/overview/) | [DevOps Flow](bundles/project/devops-flow/), [Import & Migration](bundles/project/import-migration/) |
| Codebase | [Overview](bundles/codebase/overview/) | [Sidecar Validation](bundles/codebase/sidecar-validation/), [Analyze](bundles/codebase/analyze/), [Drift](bundles/codebase/drift/), [Repro](bundles/codebase/repro/) |
| Spec | [Overview](bundles/spec/overview/) | [Validate](bundles/spec/validate/), [Generate Tests](bundles/spec/generate-tests/), [Mock](bundles/spec/mock/) |
| Govern | [Overview](bundles/govern/overview/) | [Enforce](bundles/govern/enforce/), [Patch](bundles/govern/patch/) |
| Code Review | [Overview](bundles/code-review/overview/) | [Run](bundles/code-review/run/), [Ledger](bundles/code-review/ledger/), [Rules](bundles/code-review/rules/) |

## Getting Started

- [Choose Your Modules](getting-started/choose-your-modules/) — which module for what, side-by-side comparison
- [Installation](getting-started/installation/)
- [First Steps](getting-started/first-steps/)
- [Module Bootstrap Checklist](getting-started/module-bootstrap-checklist/)
- [Tutorial: Backlog Quickstart Demo](getting-started/tutorial-backlog-quickstart-demo/)

## Workflows

- [Cross-Module Chains](guides/cross-module-chains/)
- [Daily DevOps Routine](guides/daily-devops-routine/)
- [CI/CD Pipeline](guides/ci-cd-pipeline/)
- [Backlog Refinement](bundles/backlog/refinement/)
- [Project DevOps Flow](bundles/project/devops-flow/)
- [DevOps Adapter Integration](integrations/devops-adapter-overview/)

## Team and Enterprise

- [Team Collaboration Setup](team-and-enterprise/team-collaboration/)
- [Agile and Scrum Team Setup](team-and-enterprise/agile-scrum-setup/)
- [Multi-Repo Setup](team-and-enterprise/multi-repo/)
- [Enterprise Configuration](team-and-enterprise/enterprise-config/)

## Authoring

- [Module Development](authoring/module-development/)
- [Publishing Modules](authoring/publishing-modules/)
- [Module Signing](authoring/module-signing/)
- [Custom Registries](authoring/custom-registries/)

## Reference

- [Command Reference](reference/commands/)
- [Module Contracts](reference/module-contracts/)
- [Module Security](reference/module-security/)
- [Architecture](architecture/)
