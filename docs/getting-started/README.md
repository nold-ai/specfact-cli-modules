# Getting Started with SpecFact Modules

Welcome to the **modules** getting-started guide. This section covers installing and using official bundles. For core CLI platform setup, see [docs.specfact.io](https://docs.specfact.io).

## Installation

Choose your preferred installation method:

- **[Installation Guide](installation.md)** - All installation options (uvx, pip, Docker, GitHub Actions)
- **[Installation Guide](installation.md)** - Optional dependencies for graph-based analysis (pyan3, syft, bearer, graphviz)

## Quick Start

### Module System Note

SpecFact runs on a lifecycle-managed module system.

- Core runtime manages lifecycle, registry, contracts, and orchestration.
- Feature behavior is implemented in module-local command implementations.
- This allows feature modules to evolve independently without repeatedly rewiring CLI core logic.

### Your First Command

**For Legacy Code Modernization** (Recommended):

```bash
# CLI-only mode (works with uvx, no installation needed)
uvx specfact-cli@latest code import --repo . my-project

# Interactive AI Assistant mode (requires pip install + specfact init)
# See First Steps guide for IDE integration setup
```

**For New Projects**:

```bash
# Install a project-oriented bundle first, then inspect the mounted workflow surface
specfact module install nold-ai/specfact-project
specfact project --help
```

**Note**: Interactive AI Assistant mode provides better feature detection and semantic understanding, but requires `pip install specfact-cli` and IDE setup. CLI-only mode works immediately with `uvx` but may show 0 features for simple test cases.

### Migration Note (0.40.0)

Flat root commands were removed. Use the mounted grouped command forms:

- `specfact validate ...` -> `specfact code validate ...`
- `specfact code repro ...` -> `specfact code repro ...`
- `specfact sync ...` -> `specfact project sync ...`
- `specfact govern enforce ...` -> `specfact govern enforce ...`
- `specfact policy ...` -> `specfact backlog policy ...`

First-run bundle selection examples:

```bash
specfact init --profile solo-developer
specfact init --install backlog,codebase
specfact init --install all
```

Marketplace bundle install examples:

```bash
specfact module install nold-ai/specfact-codebase
specfact module install nold-ai/specfact-backlog
```

Official bundles are published in the `nold-ai/specfact-cli-modules` registry and verified as `official` tier during install.
Some bundles install dependencies automatically:

- `nold-ai/specfact-spec` -> pulls `nold-ai/specfact-project`
- `nold-ai/specfact-govern` -> pulls `nold-ai/specfact-project`

### Modernizing Legacy Code?

**New to brownfield modernization?** See our **[Brownfield Engineer Guide](../guides/brownfield-engineer.md)** for a complete walkthrough of modernizing legacy Python code with SpecFact CLI.

## Next Steps

- [Installation Guide](installation.md) - Install SpecFact CLI
- [First Steps](first-steps.md) - Step-by-step first commands
- [Module Bootstrap Checklist](module-bootstrap-checklist.md) - Verify bundled modules are installed in user/project scope
- [Tutorial: Using SpecFact with OpenSpec or Spec-Kit](tutorial-openspec-speckit.md) - Complete beginner-friendly tutorial
- [DevOps Adapter Integration](../integrations/devops-adapter-overview.md) - Integrate SpecFact into agile DevOps workflows
- [Backlog Refinement](../bundles/backlog/refinement.md) - AI-assisted template-driven refinement for standardizing work items
- [Tutorial: Backlog Quickstart Demo (GitHub + ADO)](tutorial-backlog-quickstart-demo.md) - Short end-to-end demo
- [Tutorial: Backlog Refine with AI IDE](tutorial-backlog-refine-ai-ide.md) - End-to-end for agile DevOps teams
- [Tutorial: Daily Standup and Sprint Review](tutorial-daily-standup-sprint-review.md) - End-to-end daily standup
- [Use Cases](../guides/use-cases.md) - See real-world examples
- [Command Reference](../reference/commands.md) - Learn all available commands

## Need Help?

- [GitHub Discussions](https://github.com/nold-ai/specfact-cli/discussions)
- [GitHub Issues](https://github.com/nold-ai/specfact-cli/issues)
- [hello@noldai.com](mailto:hello@noldai.com)
