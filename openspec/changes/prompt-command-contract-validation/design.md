# Overview

The existing docs validator already discovers mounted bundle command paths from Typer apps. This change extends that idea to shipped bundle prompts, because prompt resources are executable guidance consumed by AI IDEs and should fail fast when their command examples no longer match the installed CLI.

## Design

- Add `scripts/check-prompt-commands.py` as the prompt-specific validator.
- Reuse or mirror the command-discovery shape from `scripts/check-docs-commands.py`: import bundle app modules, convert Typer apps to Click commands, collect command paths, and inspect Click parameters for accepted options.
- Scan only `packages/*/resources/prompts/**/*.md`; `.github/prompts` is intentionally excluded.
- Extract command references from fenced shell blocks, inline backticks, slash prompt examples, and parameter/option prose. Resolve placeholders such as `<path>`, `[<bundle-name>]`, `[OPTIONS]`, line continuations, and comments without executing commands.
- Treat unknown command paths and unknown options as blocking findings with `path:line: [category] message` output.
- Require each executable prompt file to include a standard CLI reality-check/self-healing instruction. The current `_validate_cli_reality_check_guidance` implementation in `scripts/check-prompt-commands.py` enforces this independently for every prompt file and does not resolve companion prompt includes; companion include resolution is deferred until the validator has explicit include tracking.
- Add a Hatch script `validate-prompt-commands`.
- Wire `run_prompt_command_validation_gate` into `scripts/pre-commit-quality-checks.sh` before `check_safe_change` so prompt-only Markdown edits are still validated.
- Add CI execution to `.github/workflows/docs-review.yml` and include prompt resource paths in workflow triggers.
- Update `openspec/config.yaml` rules so future prompt-resource changes remember this validation surface.

## Prompt Updates

Prompt text should say:

- Prompt instructions are operating guidance for SpecFact CLI, not the source of truth for the installed CLI.
- Before running a command, inspect the current command help when unsure.
- If a command or option from the prompt fails, inspect the nearest valid parent command with `--help`, correct the invocation when the mapping is obvious, and ask the user when no safe correction is clear.

## Compatibility

This change does not add runtime CLI commands for end users. It adds repository validation tooling and prompt resource edits. Because prompt resources are signed bundle payloads, implementation must account for module version/signature enforcement before finalization.
