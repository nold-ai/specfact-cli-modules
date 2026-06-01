---
description: Manage project bundles - create, add features/stories, and update plan metadata.
---

# SpecFact Plan Management Command

## CLI Reality Check

Prompt instructions are operating guidance for SpecFact CLI, not the source of truth. Current CLI help is authoritative. If a command or option fails, inspect the nearest valid `--help`, correct the invocation when the mapping is obvious, and ask the user when no safe correction is clear.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Manage project bundles: initialize, add features/stories, update metadata (idea/features/stories).

**When to use:** Creating bundles, adding features/stories, updating metadata.

**Quick:** `/specfact.02-plan init legacy-api` or `/specfact.02-plan add-feature --key FEATURE-001 --title "User Auth"`

## Parameters

### Target/Input

- `--bundle NAME` - Project bundle name (optional, defaults to explicit bundle name)
- `--key KEY` - Feature/story key (e.g., FEATURE-001, STORY-001)
- `--feature KEY` - Parent feature key (for story operations)

### Output/Results

- (No output-specific parameters for plan management)

### Behavior/Options

- `--interactive/--no-interactive` - Interactive mode. Default: True (interactive)
- `--scaffold/--no-scaffold` - Create directory structure. Default: True (scaffold enabled)

### Advanced/Configuration

- `--title TEXT` - Feature/story title
- `--outcomes TEXT` - Expected outcomes (comma-separated)
- `--acceptance TEXT` - Acceptance criteria (comma-separated)
- `--constraints TEXT` - Constraints (comma-separated)
- `--confidence FLOAT` - Confidence score (0.0-1.0)
- `--draft/--no-draft` - Mark as draft

## Workflow

### Step 1: Parse Arguments

- Determine operation: `init`, `add-feature`, `add-story`, `update-idea`, `update-feature`, `update-story`
- Extract parameters (bundle name defaults to active plan if not specified, keys, etc.)

### Step 2: Execute CLI

```bash
specfact code import from-code --repo . <bundle-name>
specfact code import from-code --repo . <bundle-name>
specfact code import from-code --repo . <bundle-name>
specfact code import from-code --repo . <bundle-name>
specfact code import from-code --repo . <bundle-name>
specfact code import from-code --repo . <bundle-name>
# --bundle defaults to active plan if not specified
```

### Step 3: Present Results

- Display bundle location
- Show created/updated features/stories
- Present summary of changes

## CLI Enforcement

**CRITICAL**: Always use SpecFact CLI commands. See [CLI Enforcement Rules](./shared/cli-enforcement.md) for details.

**Rules:**

- Execute CLI first - never create artifacts directly
- Use `--no-interactive` flag in CI/CD environments
- Never modify `.specfact/` directly
- Use CLI output as grounding for validation
- Code generation requires LLM (only via AI IDE slash prompts, not CLI-only)

## Dual-Stack Workflow (Copilot Mode)

When in copilot mode, follow this three-phase workflow:

### Phase 1: CLI Grounding (REQUIRED)

```bash
# Execute CLI to get structured output
specfact code import from-code --repo . <bundle-name>
```

**Capture**:

- CLI-generated artifacts (plan bundles, features, stories)
- Metadata (timestamps, confidence scores)
- Telemetry (execution time, file counts)

### Phase 2: LLM Enrichment (OPTIONAL, Copilot Only)

**Purpose**: Add semantic understanding to CLI output

**What to do**:

- Read CLI-generated artifacts (use file reading tools for display only)
- Use CLI artifacts as the source of truth for keys/structure/metadata
- Scan codebase only if asked to align the plan with implementation or to add missing features
- When scanning, compare findings against CLI artifacts and propose updates via CLI commands
- Identify missing features/stories
- Suggest confidence adjustments
- Extract business context

**What NOT to do**:

- ❌ Create YAML/JSON artifacts directly
- ❌ Modify CLI artifacts directly (use CLI commands to update)
- ❌ Bypass CLI validation
- ❌ Write to `.specfact/` folder directly (always use CLI)
- ❌ Use direct file manipulation tools for writing (use CLI commands)

**Output**: Generate enrichment report (Markdown) or use `--batch-updates` JSON/YAML file

### Phase 3: CLI Artifact Creation (REQUIRED)

```bash
# Use enrichment to update plan via CLI
specfact code import from-code --repo . <bundle-name>
# Or use batch updates:
specfact code import from-code --repo . <bundle-name>
```

**Result**: Final artifacts are CLI-generated with validated enrichments

**Note**: If code generation is needed, use the validation loop pattern (see [CLI Enforcement Rules](./shared/cli-enforcement.md#standard-validation-loop-pattern-for-llm-generated-code))

## Expected Output

## Success (Init)

```text
✓ Project bundle created: .specfact/projects/legacy-api/
✓ Bundle initialized with scaffold structure
```

## Success (Add Feature)

```text
✓ Feature 'FEATURE-001' added successfully
Feature: User Authentication
Outcomes: Secure login, Session management
```

## Error (Missing Bundle)

```text
✗ Project bundle name is required (or set explicit bundle name)
Usage: specfact code import from-code --repo . <bundle-name>
```

## Common Patterns

```bash
/specfact.02-plan init legacy-api
/specfact.02-plan add-feature --key FEATURE-001 --title "User Auth" --outcomes "Secure login" --acceptance "Users can log in"
/specfact.02-plan add-story --feature FEATURE-001 --key STORY-001 --title "Login API" --acceptance "API returns JWT"
/specfact.02-plan update-feature --key FEATURE-001 --title "Updated Title" --confidence 0.9
/specfact.02-plan update-idea --target-users "Developers, DevOps" --value-hypothesis "Reduce technical debt"
# --bundle defaults to active plan if not specified
```

## Context

{ARGS}
