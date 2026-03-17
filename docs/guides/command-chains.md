---
layout: default
title: Command Chains Reference
permalink: /guides/command-chains/
---

# Legacy Workflow Note

This page described older SpecFact CLI - v0.42.1

⏱️  Started: 2026-03-18 00:18:23
Command 'plan' is not installed.
Install workflow bundles with specfact init --profile <profile> or specfact 
module install <bundle>.

✓ Finished: 2026-03-18 00:18:23 | Duration: 0.03s, SpecFact CLI - v0.42.1

⏱️  Started: 2026-03-18 00:18:33
Command 'generate' is not installed.
Install workflow bundles with specfact init --profile <profile> or specfact 
module install <bundle>.

✓ Finished: 2026-03-18 00:18:33 | Duration: 0.03s, SpecFact CLI - v0.42.1

⏱️  Started: 2026-03-18 00:18:44
Command 'contract' is not installed.
Install workflow bundles with specfact init --profile <profile> or specfact 
module install <bundle>.

✓ Finished: 2026-03-18 00:18:44 | Duration: 0.03s, or SpecFact CLI - v0.42.1

⏱️  Started: 2026-03-18 00:18:55
Command 'sdd' is not installed.
Install workflow bundles with specfact init --profile <profile> or specfact 
module install <bundle>.

✓ Finished: 2026-03-18 00:18:55 | Duration: 0.02s workflows that are not part of the current public mounted CLI in this repository. The detailed command examples previously documented here were removed because they no longer match the command surface exposed by                                                                                 
 Usage: specfact [OPTIONS] COMMAND [ARGS]...                                    
                                                                                
 SpecFact CLI - Spec → Contract → Sentinel for Contract-Driven Development      
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --version          -v                                       Show version and │
│                                                             exit             │
│ --banner                                                    Show ASCII art   │
│                                                             banner (hidden   │
│                                                             by default,      │
│                                                             shown on first   │
│                                                             run)             │
│ --mode                                         TEXT         Operational      │
│                                                             mode: cicd       │
│                                                             (fast,           │
│                                                             deterministic)   │
│                                                             or copilot       │
│                                                             (enhanced,       │
│                                                             interactive)     │
│ --debug                                                     Enable debug     │
│                                                             output: console  │
│                                                             diagnostics and  │
│                                                             log file at      │
│                                                             ~/.specfact/log… │
│                                                             (operation       │
│                                                             metadata for     │
│                                                             file I/O and API │
│                                                             calls)           │
│ --skip-checks                                               Skip startup     │
│                                                             checks (template │
│                                                             validation and   │
│                                                             version check) - │
│                                                             useful for CI/CD │
│ --input-format                                 [yaml|json]  Default          │
│                                                             structured input │
│                                                             format (yaml or  │
│                                                             json)            │
│                                                             [default: yaml]  │
│ --output-format                                [yaml|json]  Default          │
│                                                             structured       │
│                                                             output format    │
│                                                             for generated    │
│                                                             files (yaml or   │
│                                                             json)            │
│                                                             [default: yaml]  │
│ --interactive              --no-interactive                 Force            │
│                                                             interaction mode │
│                                                             (default auto    │
│                                                             based on         │
│                                                             terminal/CI      │
│                                                             detection)       │
│ --install-comple…                                           Install          │
│                                                             completion for   │
│                                                             the current      │
│                                                             shell.           │
│ --show-completion                                           Show completion  │
│                                                             for the current  │
│                                                             shell, to copy   │
│                                                             it or customize  │
│                                                             the              │
│                                                             installation.    │
│ --help,--help-ad…  -h,-ha                                   Show this        │
│                                                             message and      │
│                                                             exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ init      Bootstrap SpecFact and manage module lifecycle (use `init ide` for │
│           IDE setup)                                                         │
│ module    Manage marketplace modules (install, uninstall, search, list,      │
│           show, upgrade)                                                     │
│ upgrade   Check for and install SpecFact CLI updates                         │
│ backlog   Module package: nold-ai/specfact-backlog                           │
│ code      Module package: nold-ai/specfact-codebase                          │
│ govern    Module package: nold-ai/specfact-govern                            │
│ project   Module package: nold-ai/specfact-project                           │
│ spec      Module package: nold-ai/specfact-spec                              │
╰──────────────────────────────────────────────────────────────────────────────╯.

Use the current mounted entrypoints instead:

- 
⏱️  Started: 2026-03-18 00:19:19
                                                                                
 Usage: specfact project [OPTIONS] COMMAND [ARGS]...                            
                                                                                
 Manage project bundles with persona workflows                                  
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion                  Install completion for the current     │
│                                       shell.                                 │
│ --show-completion                     Show completion for the current shell, │
│                                       to copy it or customize the            │
│                                       installation.                          │
│ --help-advanced,--help  -ha,-h        Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ link-backlog       Link a project bundle to a backlog provider               │
│                    configuration.                                            │
│ health-check       Run project-level health checks including backlog graph   │
│                    health.                                                   │
│ devops-flow        Run integrated DevOps stage actions for a project bundle. │
│ snapshot           Save current linked backlog graph as baseline snapshot.   │
│ regenerate         Re-derive plan state from current bundle and linked       │
│                    backlog graph.                                            │
│ export-roadmap     Export roadmap milestones from backlog dependency         │
│                    critical path.                                            │
│ export             Export persona-owned sections from project bundle to      │
│                    Markdown.                                                 │
│ import             Import persona-edited Markdown file back into project     │
│                    bundle.                                                   │
│ lock               Lock a section for a persona.                             │
│ unlock             Unlock a section.                                         │
│ locks              List all section locks.                                   │
│ init-personas      Initialize personas in project bundle manifest.           │
│ merge              Merge project bundles using three-way merge with          │
│                    persona-aware conflict resolution.                        │
│ resolve-conflict   Resolve a specific conflict in a project bundle.          │
│ version            Manage project bundle versions                            │
│ sync               Synchronize external tool artifacts and repository        │
│                    changes (Spec-Kit, OpenSpec, GitHub, Linear, Jira, etc.). │
│                    See 'specfact backlog refine' for template-driven backlog │
│                    refinement.                                               │
╰──────────────────────────────────────────────────────────────────────────────╯



✓ Finished: 2026-03-18 00:19:19 | Duration: 0.39s
- 
⏱️  Started: 2026-03-18 00:19:30
                                                                                
 Usage: specfact project sync [OPTIONS] COMMAND [ARGS]...                       
                                                                                
 Synchronize external tool artifacts and repository changes (Spec-Kit,          
 OpenSpec, GitHub, Linear, Jira, etc.). See 'specfact backlog refine' for       
 template-driven backlog refinement.                                            
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help,--help-advanced  -h,-ha        Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ bridge        Sync changes between external tool artifacts and SpecFact      │
│               using bridge architecture.                                     │
│ repository    Sync code changes to SpecFact artifacts.                       │
│ intelligent   Continuous intelligent bidirectional sync with conflict        │
│               resolution.                                                    │
╰──────────────────────────────────────────────────────────────────────────────╯


✓ Finished: 2026-03-18 00:19:31 | Duration: 0.31s
- 
⏱️  Started: 2026-03-18 00:19:43
                                                                                
 Usage: specfact code [OPTIONS] COMMAND [ARGS]...                               
                                                                                
 Code command extensions for structured review workflows.                       
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion                  Install completion for the current     │
│                                       shell.                                 │
│ --show-completion                     Show completion for the current shell, │
│                                       to copy it or customize the            │
│                                       installation.                          │
│ --help-advanced,--help  -h,-ha        Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ review     Governed code review workflows.                                   │
│ import     Import codebases and related external inputs into SpecFact        │
│            project bundles.                                                  │
│ analyze    Analyze codebase for contract coverage and quality                │
│ drift      Detect drift between code and specifications                      │
│ validate   Validation commands                                               │
│ repro      Run validation suite for reproducibility                          │
╰──────────────────────────────────────────────────────────────────────────────╯



✓ Finished: 2026-03-18 00:19:45 | Duration: 1.16s
- 
⏱️  Started: 2026-03-18 00:19:55
                                                                                
 Usage: specfact code review [OPTIONS] COMMAND [ARGS]...                        
                                                                                
 Governed code review workflows.                                                
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help-advanced,--help  -h,-ha        Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ run      Execute code review runs.                                           │
│ ledger   Persist and inspect review reward history.                          │
│ rules    Manage the code-review house-rules skill.                           │
╰──────────────────────────────────────────────────────────────────────────────╯


✓ Finished: 2026-03-18 00:19:56 | Duration: 0.64s
- 
⏱️  Started: 2026-03-18 00:20:05
                                                                                
 Usage: specfact spec [OPTIONS] COMMAND [ARGS]...                               
                                                                                
 Specmatic integration for API contract testing (OpenAPI/AsyncAPI validation,   
 backward compatibility, mock servers)                                          
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion                  Install completion for the current     │
│                                       shell.                                 │
│ --show-completion                     Show completion for the current shell, │
│                                       to copy it or customize the            │
│                                       installation.                          │
│ --help-advanced,--help  -h,-ha        Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ validate          Validate OpenAPI/AsyncAPI specification using Specmatic.   │
│ backward-compat   Check backward compatibility between two spec versions.    │
│ generate-tests    Generate Specmatic test suite from specification.          │
│ mock              Launch Specmatic mock server from specification.           │
╰──────────────────────────────────────────────────────────────────────────────╯



✓ Finished: 2026-03-18 00:20:06 | Duration: 0.35s
- 
⏱️  Started: 2026-03-18 00:20:16
                                                                                
 Usage: specfact govern [OPTIONS] COMMAND [ARGS]...                             
                                                                                
 Governance and quality gates: enforce, patch.                                  
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion                  Install completion for the current     │
│                                       shell.                                 │
│ --show-completion                     Show completion for the current shell, │
│                                       to copy it or customize the            │
│                                       installation.                          │
│ --help,--help-advanced  -h,-ha        Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ enforce   Configure quality gates and enforcement modes                      │
│ patch     Preview and apply patches (local or upstream with --write).        │
╰──────────────────────────────────────────────────────────────────────────────╯



✓ Finished: 2026-03-18 00:20:17 | Duration: 0.55s
- 
⏱️  Started: 2026-03-18 00:20:29
                                                                                
 Usage: specfact backlog [OPTIONS] COMMAND [ARGS]...                            
                                                                                
 Backlog refinement and template management                                     
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion                  Install completion for the current     │
│                                       shell.                                 │
│ --show-completion                     Show completion for the current shell, │
│                                       to copy it or customize the            │
│                                       installation.                          │
│ --help,--help-advanced  -ha,-h        Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ ceremony           Ceremony-oriented backlog workflows                       │
│ delta              Backlog delta analysis and impact tracking                │
│ auth               Authenticate backlog providers                            │
│ sync               Sync current backlog graph with stored baseline and       │
│                    export delta outputs.                                     │
│ verify-readiness   Verify release readiness for selected backlog items.      │
│ analyze-deps       Analyze backlog dependencies for a project.               │
│ diff               Show changes since baseline sync.                         │
│ promote            Validate promotion impact for an item and print promotion │
│                    intent.                                                   │
│ refine             Refine backlog items using AI-assisted template matching. │
│ daily              Show daily standup view: list my/filtered backlog items   │
│                    with status and last activity.                            │
│ init-config        Scaffold `.specfact/backlog-config.yaml` with default     │
│                    backlog provider config structure.                        │
│ map-fields         Interactive command to map ADO fields to canonical field  │
│                    names.                                                    │
│ add                Create a backlog item with optional parent hierarchy      │
│                    validation and DoR checks.                                │
╰──────────────────────────────────────────────────────────────────────────────╯



✓ Finished: 2026-03-18 00:20:30 | Duration: 1.56s
- 
⏱️  Started: 2026-03-18 00:20:42
                                                                                
 Usage: specfact module [OPTIONS] COMMAND [ARGS]...                             
                                                                                
 Manage marketplace modules                                                     
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion                  Install completion for the current     │
│                                       shell.                                 │
│ --show-completion                     Show completion for the current shell, │
│                                       to copy it or customize the            │
│                                       installation.                          │
│ --help,--help-advanced  -h,-ha        Show this message and exit.            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ init              Bootstrap shipped module artifacts into user or project    │
│                   module root.                                               │
│ install           Install a module from bundled artifacts or marketplace     │
│                   registry.                                                  │
│ uninstall         Uninstall a marketplace module.                            │
│ add-registry      Add a custom registry to the config.                       │
│ list-registries   List all configured registries (official + custom).        │
│ remove-registry   Remove a custom registry from the config.                  │
│ enable            Enable modules in lifecycle state registry.                │
│ disable           Disable modules in lifecycle state registry.               │
│ search            Search marketplace and installed modules by                │
│                   id/description/tags.                                       │
│ list              List installed modules with trust labels and optional      │
│                   origin details.                                            │
│ show              Show detailed metadata for an installed module.            │
│ upgrade           Upgrade marketplace module(s) to latest available          │
│                   versions.                                                  │
│ alias             Manage command aliases (map name to namespaced module)     │
╰──────────────────────────────────────────────────────────────────────────────╯



✓ Finished: 2026-03-18 00:20:42 | Duration: 0.47s

When you need exact syntax, verify against live help in the current release, for example:



This page needs a full rewrite around the mounted command groups before task-level workflow examples can be published again.
