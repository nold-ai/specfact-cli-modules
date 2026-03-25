"""Validate bundle overview quick examples against bundle Typer apps (`--help`).

Implements the bundle-overview-pages spec scenario: command examples stay aligned with
`specfact <command> --help`. The root `specfact` CLI may omit nested members in some dev
setups, so we invoke the same Typer apps the CLI mounts from each official bundle.
"""

from __future__ import annotations

import importlib
import re
import shlex
from pathlib import Path
from typing import Any

from typer.testing import CliRunner


_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUNDLE_OVERVIEWS = sorted(_REPO_ROOT.glob("docs/bundles/*/overview.md"))

# Runnable examples (not plain `--help`); map exact line → tokens after `specfact`.
_OVERVIEW_LINE_TO_TOKENS_AFTER_SPECFACT: dict[str, list[str]] = {
    "specfact code validate sidecar init my-bundle /path/to/repo": [
        "code",
        "validate",
        "sidecar",
        "init",
        "--help",
    ],
    "specfact code repro --verbose --repo .": ["code", "repro", "--help"],
    "specfact project link-backlog --adapter github --project-id owner/repo --bundle my-bundle --repo .": [
        "project",
        "link-backlog",
        "--help",
    ],
    "specfact migrate artifacts --repo .": ["migrate", "artifacts", "--help"],
    "specfact backlog refine github --preview --labels feature": [
        "backlog",
        "refine",
        "github",
        "--help",
    ],
    "specfact backlog daily github --state open --limit 20": ["backlog", "daily", "--help"],
    "specfact spec sdd list --repo .": ["spec", "sdd", "list", "--repo", ".", "--help"],
}

_BASH_FENCE_RE = re.compile(r"^```(?:bash)?\s*$")


def _iter_bash_block_lines(markdown: str) -> list[str]:
    lines_out: list[str] = []
    in_bash = False
    for raw in markdown.splitlines():
        if _BASH_FENCE_RE.match(raw.strip()):
            in_bash = not in_bash
            continue
        if in_bash:
            lines_out.append(raw.rstrip("\n"))
    return lines_out


def _tokens_for_specfact_line(line: str) -> list[str] | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if "&&" in s or "|" in s:
        return None
    if s in _OVERVIEW_LINE_TO_TOKENS_AFTER_SPECFACT:
        return ["specfact", *_OVERVIEW_LINE_TO_TOKENS_AFTER_SPECFACT[s]]
    try:
        tokens = shlex.split(s)
    except ValueError:
        return None
    if not tokens or tokens[0] != "specfact":
        return None
    return tokens


def _route_to_bundle_app_and_argv(tokens: list[str]) -> tuple[Any, list[str]] | None:
    """Map `specfact …` tokens to (Typer app, argv for CliRunner)."""
    if len(tokens) < 2 or tokens[0] != "specfact":
        return None
    t = tokens[1:]

    if t[0] == "backlog" and len(t) > 1 and t[1] == "policy":
        mod = importlib.import_module("specfact_backlog.policy_engine.commands")
        return mod.app, t[2:]

    if t[0] == "backlog":
        mod = importlib.import_module("specfact_backlog.backlog.commands")
        return mod.app, t[1:]

    if t[0] == "govern":
        mod = importlib.import_module("specfact_govern.govern.commands")
        return mod.app, t[1:]

    if t[0] == "project":
        mod = importlib.import_module("specfact_project.project.commands")
        return mod.app, t[1:]

    if t[0] == "plan":
        mod = importlib.import_module("specfact_project.plan.commands")
        return mod.app, t[1:]

    if t[0] == "sync":
        mod = importlib.import_module("specfact_project.sync.commands")
        return mod.app, t[1:]

    if t[0] == "migrate":
        mod = importlib.import_module("specfact_project.migrate.commands")
        return mod.app, t[1:]

    if t[0] == "code" and len(t) > 1:
        if t[1] == "review":
            mod = importlib.import_module("specfact_code_review.review.commands")
            # `review.commands.app` mounts the nested `review` subgroup at name `review`.
            return mod.app, t[1:]
        if t[1] == "import":
            mod = importlib.import_module("specfact_codebase.import_cmd.commands")
            return mod.app, t[2:]
        if t[1] == "analyze":
            mod = importlib.import_module("specfact_codebase.analyze.commands")
            return mod.app, t[2:]
        if t[1] == "drift":
            mod = importlib.import_module("specfact_codebase.drift.commands")
            return mod.app, t[2:]
        if t[1] == "validate":
            mod = importlib.import_module("specfact_codebase.validate.commands")
            return mod.app, t[2:]
        if t[1] == "repro":
            mod = importlib.import_module("specfact_codebase.repro.commands")
            return mod.app, t[2:]

    if t[0] == "spec" and len(t) == 2 and t[1] == "--help":
        mod = importlib.import_module("specfact_cli.groups.spec_group")
        return mod.build_app(), ["--help"]

    if t[0] == "spec" and len(t) > 1:
        sub = t[1]
        if sub == "contract":
            mod = importlib.import_module("specfact_spec.contract.commands")
        elif sub == "api":
            mod = importlib.import_module("specfact_spec.spec.commands")
        elif sub == "sdd":
            mod = importlib.import_module("specfact_spec.sdd.commands")
        elif sub == "generate":
            mod = importlib.import_module("specfact_spec.generate.commands")
        else:
            return None
        return mod.app, t[2:]

    return None


def test_validate_bundle_overview_cli_help_examples() -> None:
    """Invoke bundle Typer apps with argv derived from each overview quick-example line."""
    runner = CliRunner()
    seen: set[str] = set()
    failures: list[str] = []

    for overview in _BUNDLE_OVERVIEWS:
        text = overview.read_text(encoding="utf-8")
        for raw_line in _iter_bash_block_lines(text):
            tokens = _tokens_for_specfact_line(raw_line)
            if tokens is None:
                continue
            if "--help" not in tokens:
                failures.append(
                    f"{overview.relative_to(_REPO_ROOT)}: {raw_line.strip()!r} "
                    "(add --help to the example or an entry in _OVERVIEW_LINE_TO_TOKENS_AFTER_SPECFACT)"
                )
                continue

            key = " ".join(tokens)
            if key in seen:
                continue
            seen.add(key)

            routed = _route_to_bundle_app_and_argv(tokens)
            if routed is None:
                failures.append(f"{overview.relative_to(_REPO_ROOT)}: no route for {key!r}")
                continue
            app, argv = routed
            result = runner.invoke(app, argv, prog_name="specfact")
            if result.exit_code != 0:
                failures.append(f"{overview.relative_to(_REPO_ROOT)}: {raw_line.strip()!r} -> exit {result.exit_code}")

    assert not failures, "Overview CLI --help mismatches:\n" + "\n".join(failures)
