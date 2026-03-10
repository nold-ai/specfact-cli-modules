# Cross-Check Analysis: AGENTS.md vs openspec/config.yaml vs .cursor/commands

**Date:** 2026-03-10  
**Purpose:** Identify mismatches and ambiguities between instruction sources that lead to confusion

---

## Summary of Findings

| Issue | Severity | Location | Description |
|-------|----------|----------|-------------|
| 1 | **High** | opsx-ff, opsx-apply | No Git Worktree Policy mention |
| 2 | **High** | opsx-ff, opsx-apply | No TDD evidence requirement |
| 3 | **Medium** | opsx-apply | No documentation research task mention |
| 4 | **Medium** | opsx-ff, opsx-apply | No module signing quality gate |
| 5 | **Low** | opsx-ff | Command syntax inconsistent (`/opsx:ff` vs `/opsx-ff`) |
| 6 | **Medium** | AGENTS.md vs config.yaml | AGENTS.md doesn't mention module signing |
| 7 | **High** | config.yaml tasks | Task format rules buried in long text blocks |
| 8 | **Medium** | All skills | No single source of truth for task structure |

---

## Detailed Findings

### 1. Git Worktree Policy: HIGH Severity

**AGENTS.md (lines 87-149):**
- Mandatory worktree policy with exact commands
- "Use git worktrees for parallel development branches only"
- "Never create a worktree for `dev` or `main`"
- Detailed operational rules and cleanup steps

**openspec/config.yaml (lines 102-103, 109-110):**
- Recently added: "Verify git workflow tasks are worktree-aware"
- "Verify: Worktree branch creation is first task..."
- "Verify: tasks include worktree bootstrap pre-flight"

**.cursor/commands/opsx-ff.md:**
- ❌ **NO mention** of Git Worktree Policy
- Only says "Create the change directory" with `openspec new change`
- No guidance on worktree creation before implementation

**.cursor/commands/opsx-apply.md:**
- ❌ **NO mention** of Git Worktree Policy
- Step 6: "Implement tasks (loop until done or blocked)" - no mention of WHERE to implement
- No reminder to work from worktree, not primary checkout

**.cursor/commands/wf-create-change-from-plan.md (line 27):**
- ✅ Has "CRITICAL Git Workflow" mentioning worktrees
- "Always add tasks to create a git branch in a dedicated worktree"

**.cursor/commands/wf-validate-change.md (lines 102-103, 109-110):**
- ✅ Validates worktree compliance explicitly

**Mismatch Impact:**
- User runs `/opsx:ff`, creates change, then `/opsx:apply` - neither mentions worktrees
- AI assistant may implement directly in primary checkout, violating AGENTS.md
- Only `wf-create-change-from-plan` and `wf-validate-change` catch this

**Recommendation:**
- Add worktree requirement to `opsx-ff.md` Step 4 (artifact creation)
- Add worktree check to `opsx-apply.md` Step 1 (before implementation)
- Reference: `git worktree add ../specfact-cli-worktrees/<type>/<slug> -b <branch> origin/dev`

---

### 2. TDD/SDD Evidence Requirement: HIGH Severity

**AGENTS.md (Hard Gate section):**
- "Required evidence: Create/update `openspec/changes/<change-id>/TDD_EVIDENCE.md`"
- Strict TDD order enforced

**openspec/config.yaml (lines 53-60, 108, 111, 131-133):**
- "Evidence required—record failing-before and passing-after test runs"
- "TDD evidence is mandatory: each behavior change must include TDD_EVIDENCE.md"
- Per-artifact tasks rules repeat this requirement

**.cursor/commands/opsx-ff.md:**
- ❌ **NO mention** of TDD evidence requirement
- Creates artifacts but doesn't mention TDD_EVIDENCE.md

**.cursor/commands/opsx-apply.md:**
- ❌ **NO mention** of TDD evidence when implementing
- Step 6: "Implement tasks" - no mention of recording failing tests first

**.cursor/commands/wf-create-change-from-plan.md (line 28):**
- ✅ Has "CRITICAL TDD" mentioning test tasks

**Mismatch Impact:**
- AI assistant may skip TDD evidence recording
- User has no visibility into TDD requirement from skill prompts
- Validation only catches this in `wf-validate-change`

**Recommendation:**
- Add TDD_EVIDENCE.md requirement to `opsx-ff.md` output section
- Add TDD step to `opsx-apply.md` Step 6: "Record failing test in TDD_EVIDENCE.md before implementing"

---

### 3. Documentation Research Task: MEDIUM Severity

**openspec/config.yaml (lines 115-124):**
- Explicit requirement: "Documentation research and review (required for every change)"
- Specific 3-step process for identifying and updating docs

**AGENTS.md:**
- Mentions documentation in general terms
- No specific task format requirement

**.cursor/commands/opsx-ff.md, opsx-apply.md:**
- ❌ **NO mention** of documentation research task

**Mismatch Impact:**
- Documentation updates may be skipped
- Skills don't enforce this config.yaml requirement

**Recommendation:**
- Add documentation research task to `opsx-ff.md` artifact creation guidelines
- Include in default tasks.md template

---

### 4. Module Signing Quality Gate: MEDIUM Severity

**openspec/config.yaml (lines 136-141):**
- "Module signing quality gate (required before PR)"
- Specific 4-step process for signature verification

**AGENTS.md:**
- ❌ **NO mention** of module signing

**.cursor/commands/opsx-apply.md:**
- ❌ **NO mention** of module signing in PR creation

**Mismatch Impact:**
- PRs may be created without signed modules
- CI/CD may fail on signature check

**Recommendation:**
- Add module signing task to `opsx-apply.md` PR creation step
- Consider adding to AGENTS.md quality gates section

---

### 5. Command Syntax Inconsistency: LOW Severity

**.cursor/commands/opsx-ff.md:**
- File name: `opsx-ff.md`
- Header: `name: /opsx-ff`
- But skill uses `/opsx:ff` format in examples

**.cursor/commands/wf-validate-change.md (line 557):**
- "OPSX commands: `/opsx:new`, `/opsx:ff`, `/opsx:continue`..."

**Actual invocation:**
- User said: `/opsx:ff` (with colon)
- But file is named `opsx-ff.md` (with dash)

**Ambiguity:**
- Is the command `/opsx-ff` or `/opsx:ff`?
- Different files use different formats

**Recommendation:**
- Standardize on `/opsx:ff` format (with colon) in all documentation
- Update file names to match if needed

---

### 6. AGENTS.md vs config.yaml Gap: MEDIUM Severity

**Module Signing:**
- config.yaml: Required quality gate
- AGENTS.md: Not mentioned

**TDD Evidence:**
- config.yaml: Mandatory per-artifact rule
- AGENTS.md: Mentioned in Hard Gate, but not in workflow sections

**Documentation Research:**
- config.yaml: Explicit task requirement
- AGENTS.md: Not mentioned

**Recommendation:**
- Update AGENTS.md to include all quality gates from config.yaml
- Or: Make config.yaml the authoritative source, AGENTS.md high-level only

---

### 7. Task Format Rules Buried: HIGH Severity

**openspec/config.yaml (lines 98-103, 109-111):**
- Task format rules embedded in long text blocks
- "Check section headers: Must use hierarchical numbered format"
- "Check task format: Must use `- [ ] 1.1 [Description]`"
- Difficult to extract and follow

**.cursor/commands/opsx-ff.md:**
- No task format guidance
- Creates tasks.md without format validation

**Result:**
- Inconsistent task formatting across changes
- Validation catches errors late (in wf-validate-change)

**Recommendation:**
- Create explicit task template in `opsx-ff.md`
- Add validation step to ensure task format compliance

---

### 8. No Single Source of Truth: MEDIUM Severity

**Problem:**
- AGENTS.md has workflow philosophy
- openspec/config.yaml has per-artifact rules
- .cursor/commands have skill-specific instructions
- No unified reference for "how to create a change"

**Result:**
- AI assistant must check 3+ files to understand requirements
- Easy to miss critical constraints (like worktrees)

**Recommendation:**
- Create unified workflow guide linking all sources
- Or: Make `.cursor/commands/opsx-ff.md` the canonical entry point with links to other sources

---

## Recommended Fixes

### Applied Fix (2026-03-10)

**Updated `.cursorrules`** to add AGENTS.md authority and pre-execution checklist:

- **AGENTS.md Authority Section**: Explicitly states AGENTS.md OVERRIDES any skill/command instructions
- **Pre-Execution Checklist**: Mandatory self-check before ANY workflow command (`/opsx:ff`, `/opsx:apply`, etc.)
- **OPSX Workflow Gap-Filling Section**: Specific templates and verification steps for each OPSX command

This fix ensures AI assistants fill OPSX gaps without modifying OpenSpec-delivered commands.

### Remaining (Cannot Fix - OpenSpec Delivered)

The following cannot be modified (delivered by OpenSpec CLI):
- `opsx-ff.md` - Cannot add Step 0 directly
- `opsx-apply.md` - Cannot modify implementation loop
- `opsx-continue.md` - Cannot add worktree verification

**Mitigation**: `.cursorrules` now requires explicit gap-filling for these.

### Optional Enhancements

1. **Update AGENTS.md** (if desired):
   - Add module signing quality gate reference
   - Add documentation research task reference

2. **Standardize command syntax**:
   - Use `/opsx:ff` consistently (with colon) in all internal docs

3. **Unified workflow guide** (long-term):
   - Single document linking all sources
   - Clear hierarchy: `.cursorrules` (entry) → AGENTS.md (authority) → config.yaml (rules) → skills (execution)

---

## Rules Applied

- `.cursorrules` (Git Worktree Policy section added today)
- `AGENTS.md` (Git Worktree Policy section)
- `openspec/config.yaml` (per-artifact rules, especially tasks)
- `.cursor/commands/*.md` (OPSX workflow skills)

**AI Provider/Model:** kimi-k2.5
