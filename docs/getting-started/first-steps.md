---
layout: default
title: Your First Steps with SpecFact CLI
permalink: /getting-started/first-steps/
keywords: [getting-started, first-steps, quickstart, tutorial, beginner, install, first command]
audience: [solo, team, enterprise]
expertise_level: [beginner]
---

# Your First Steps with SpecFact CLI

This guide walks you through your first commands after installing SpecFact CLI. If you haven't installed yet, start with the [Installation guide]({{ '/getting-started/installation/' | relative_url }}).

Not sure which modules to install? See [Choose Your Modules]({{ '/getting-started/choose-your-modules/' | relative_url }}).

## 1. Verify Your Installation

```bash
specfact --version
specfact --help
```

You should see the CLI version and the top-level command groups. The available commands depend on which modules you have installed.

## 2. Install Your First Modules

Pick a profile or install modules individually:

```bash
# Option A: Use a profile (installs a curated set)
specfact init --profile solo-developer

# Option B: Install specific modules
specfact module install nold-ai/specfact-backlog
specfact module install nold-ai/specfact-code-review
```

Verify what's installed:

```bash
specfact module list
```

## 3. Explore the Command Surface

Each module mounts its commands under a top-level group. After installing, explore what's available:

```bash
# Backlog management
specfact backlog --help

# Code review
specfact code review --help

# Project management (if installed)
specfact project --help

# Spec validation (if installed)
specfact spec --help

# Governance enforcement (if installed)
specfact govern --help
```

## 4. Run Your First Code Review

The simplest way to see SpecFact in action — run a governed code review on your current project:

```bash
cd your-project/
specfact code review run
```

This analyzes your code with Ruff, Semgrep, Pylint, BasedPyright, Radon, and CrossHair, then produces a quality score. No configuration needed.

To review only changed files:

```bash
specfact code review run --scope changed
```

Check your quality ledger over time:

```bash
specfact code review ledger status
```

## 5. Connect Your Backlog

If you installed the Backlog module, connect it to your issue tracker:

**GitHub Issues:**

```bash
specfact backlog auth github
specfact backlog daily
```

**Azure DevOps:**

```bash
specfact backlog auth azure-devops
specfact backlog daily
```

The `daily` command generates a standup summary from your backlog — what moved, what's blocked, what needs attention.

## 6. Run Backlog Refinement

The CLI provides deterministic template detection and validation:

```bash
specfact backlog refine
```

This detects the story type (user story, defect, spike, enabler), scores completeness confidence, and checks Definition of Ready criteria. The output is structured data — no AI is involved at this step.

**Want AI-powered refinement?** Install IDE slash prompts (see step 7), then use the `/specfact.backlog-refine` slash command in your IDE. The AI reads the CLI output and interactively helps you improve story quality, fix underspecification, and split oversized stories.

## 7. Install IDE Slash Prompts (Optional)

SpecFact CLI itself is fully deterministic — no AI built in. AI-assisted workflows are delivered via **slash prompts** that you install into your IDE. The prompts call CLI commands under the hood and let your IDE's AI interpret and act on the results.

```bash
# Auto-detects your IDE and installs all available slash prompts
specfact init ide

# Or specify your IDE explicitly
specfact init ide --ide cursor
specfact init ide --ide claude
specfact init ide --ide vscode
```

**Supported IDEs:** Cursor, Claude Code, VS Code / GitHub Copilot, Windsurf, Gemini CLI, Qwen Code, opencode, Kilo Code, Auggie, Roo Code, CodeBuddy, Amp, Amazon Q Developer.

After installation, you get slash commands like:

| Slash command | What it does |
|---|---|
| `/specfact.01-import` | Import codebase → extract routes, schemas, contracts; AI enriches context |
| `/specfact.02-plan` | Create and manage project plans with AI assistance |
| `/specfact.03-review` | Review plan quality, identify gaps, promote stages |
| `/specfact.backlog-refine` | Interactive AI refinement of backlog items |
| `/specfact.backlog-daily` | AI-enhanced daily standup from backlog data |
| `/specfact.07-contracts` | Analyze contract coverage, generate and apply contracts |
| `/specfact.validate` | Run validation suite with AI interpretation |

Each prompt calls SpecFact CLI commands and feeds the structured output to your IDE's AI for interactive analysis.

For detailed setup: [AI IDE Workflow Guide]({{ '/ai-ide-workflow/' | relative_url }})

## 8. Set Up House Rules (Optional)

House rules enforce consistent quality standards in your AI IDE's code generation:

```bash
# Initialize rules for your IDE
specfact code review rules init

# View current rules
specfact code review rules show
```

These rules are checked during governed code reviews (`specfact code review run`) and are also available as context for AI IDEs after `specfact init ide`.

## What's Next?

Depending on your role and goals:

- **Want deeper backlog workflows?** → [Backlog Quickstart Demo]({{ '/getting-started/tutorial-backlog-quickstart-demo/' | relative_url }})
- **Need contract validation?** → [Spec Bundle Overview]({{ '/bundles/spec/overview/' | relative_url }})
- **Working with legacy code?** → [Import & Migration]({{ '/bundles/project/import-migration/' | relative_url }})
- **Setting up for a team?** → [Team Collaboration]({{ '/team-and-enterprise/team-collaboration/' | relative_url }})
- **Want CI/CD integration?** → [CI/CD Pipeline Guide]({{ '/guides/ci-cd-pipeline/' | relative_url }})
- **Full module comparison** → [Choose Your Modules]({{ '/getting-started/choose-your-modules/' | relative_url }})
