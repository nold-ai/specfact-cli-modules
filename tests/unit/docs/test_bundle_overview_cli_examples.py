"""Validate bundle overview quick examples against bundle Typer apps (`--help`).

Implements the bundle-overview-pages spec scenario: command examples stay aligned with
`specfact <command> --help`. The root `specfact` CLI may omit nested members in some dev
setups, so we invoke the same Typer apps the CLI mounts from each official bundle.
"""

from __future__ import annotations

import importlib
import logging
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
    "specfact spec sdd list --repo .": ["spec", "sdd", "list", "--help"],
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


def _route_backlog(t: list[str]) -> tuple[Any, list[str]] | None:
    if not t or t[0] != "backlog":
        return None
    if len(t) > 1 and t[1] == "policy":
        mod = importlib.import_module("specfact_backlog.policy_engine.commands")
        return mod.app, t[2:]
    mod = importlib.import_module("specfact_backlog.backlog.commands")
    return mod.app, t[1:]


_TOP_LEVEL_MODULE_BY_PREFIX: dict[str, str] = {
    "govern": "specfact_govern.govern.commands",
    "project": "specfact_project.project.commands",
    "plan": "specfact_project.plan.commands",
    "sync": "specfact_project.sync.commands",
    "migrate": "specfact_project.migrate.commands",
}


def _route_top_level(t: list[str]) -> tuple[Any, list[str]] | None:
    if not t:
        return None
    mod_path = _TOP_LEVEL_MODULE_BY_PREFIX.get(t[0])
    if mod_path is None:
        return None
    mod = importlib.import_module(mod_path)
    return mod.app, t[1:]


# Subcommand under `specfact code …` → Typer module. `review` keeps `review` in argv (nested subgroup).
_CODE_SUB_TO_MODULE: dict[str, tuple[str, bool]] = {
    "review": ("specfact_code_review.review.commands", True),
    "import": ("specfact_codebase.import_cmd.commands", False),
    "analyze": ("specfact_codebase.analyze.commands", False),
    "drift": ("specfact_codebase.drift.commands", False),
    "validate": ("specfact_codebase.validate.commands", False),
    "repro": ("specfact_codebase.repro.commands", False),
}


def _route_code(t: list[str]) -> tuple[Any, list[str]] | None:
    if len(t) < 2 or t[0] != "code":
        return None
    entry = _CODE_SUB_TO_MODULE.get(t[1])
    if entry is None:
        return None
    mod_path, keep_review_prefix = entry
    mod = importlib.import_module(mod_path)
    argv = t[1:] if keep_review_prefix else t[2:]
    return mod.app, argv


_SPEC_SUB_TO_MODULE = {
    "contract": "specfact_spec.contract.commands",
    "api": "specfact_spec.spec.commands",
    "sdd": "specfact_spec.sdd.commands",
    "generate": "specfact_spec.generate.commands",
}


def _route_spec(t: list[str]) -> tuple[Any, list[str]] | None:
    if not t or t[0] != "spec":
        return None
    if len(t) == 2 and t[1] == "--help":
        mod = importlib.import_module("specfact_cli.groups.spec_group")
        return mod.build_app(), ["--help"]
    if len(t) < 2:
        return None
    sub = t[1]
    mod_path = _SPEC_SUB_TO_MODULE.get(sub)
    if mod_path is None:
        logging.getLogger(__name__).warning("Unrecognized spec subcommand: %s - tokens: %s", sub, t)
        msg = f"Unrecognized spec subcommand: {sub!r} (tokens: {t!r})"
        raise ValueError(msg)
    mod = importlib.import_module(mod_path)
    return mod.app, t[2:]


def _route_to_bundle_app_and_argv(tokens: list[str]) -> tuple[Any, list[str]] | None:
    """Map `specfact …` tokens to (Typer app, argv for CliRunner)."""
    if len(tokens) < 2 or tokens[0] != "specfact":
        return None
    t = tokens[1:]
    if not t:
        return None
    for router in (_route_backlog, _route_top_level, _route_code, _route_spec):
        routed = router(t)
        if routed is not None:
            return routed
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
            # We only assert Typer accepted argv and exited 0; we do not diff full --help text or
            # every option name against the markdown (that would be brittle and duplicate Typer).
            # Optional smoke check below ensures something help-like was printed when --help is used.
            result = runner.invoke(app, argv, prog_name="specfact")
            if result.exit_code != 0:
                failures.append(f"{overview.relative_to(_REPO_ROOT)}: {raw_line.strip()!r} -> exit {result.exit_code}")
                continue
            if "--help" in argv:
                # CliRunner may expose only `output` (stdout+stderr) unless mix_stderr=False.
                combined = result.output or ""
                if "Usage" not in combined and "usage:" not in combined.lower():
                    failures.append(
                        f"{overview.relative_to(_REPO_ROOT)}: {raw_line.strip()!r} -> help output missing Usage banner"
                    )

    assert not failures, "Overview CLI --help mismatches:\n" + "\n".join(failures)
