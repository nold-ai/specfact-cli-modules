#!/usr/bin/env python3
# ruff: noqa: N999
"""Enforce bundle import boundaries for specfact-cli-modules."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

PACKAGE_DIRS: dict[str, Path] = {
    "specfact_project": ROOT / "packages/specfact-project/src/specfact_project",
    "specfact_backlog": ROOT / "packages/specfact-backlog/src/specfact_backlog",
    "specfact_codebase": ROOT / "packages/specfact-codebase/src/specfact_codebase",
    "specfact_spec": ROOT / "packages/specfact-spec/src/specfact_spec",
    "specfact_govern": ROOT / "packages/specfact-govern/src/specfact_govern",
}

ALLOWED_SPECFACT_CLI_EXACT: set[str] = {
    "specfact_cli",
    "specfact_cli.utils",
}

ALLOWED_SPECFACT_CLI_PREFIXES: tuple[str, ...] = (
    "specfact_cli.adapters.registry",
    "specfact_cli.cli",
    "specfact_cli.common",
    "specfact_cli.contracts.module_interface",
    "specfact_cli.integrations.specmatic",
    "specfact_cli.models",
    "specfact_cli.modes",
    "specfact_cli.modules",
    "specfact_cli.registry.registry",
    "specfact_cli.runtime",
    "specfact_cli.telemetry",
    "specfact_cli.utils.bundle_converters",
    "specfact_cli.utils.bundle_loader",
    "specfact_cli.utils.env_manager",
    "specfact_cli.utils.git",
    "specfact_cli.utils.ide_setup",
    "specfact_cli.utils.optional_deps",
    "specfact_cli.utils.performance",
    "specfact_cli.utils.progress",
    "specfact_cli.utils.sdd_discovery",
    "specfact_cli.utils.structure",
    "specfact_cli.utils.structured_io",
    "specfact_cli.utils.terminal",
    "specfact_cli.validators.contract_validator",
    "specfact_cli.validators.schema",
    "specfact_cli.versioning",
)

ALLOWED_CROSS_BUNDLE_IMPORTS: dict[str, set[str]] = {
    "specfact_project": set(),
    "specfact_backlog": set(),
    "specfact_codebase": {"specfact_project"},
    "specfact_spec": {"specfact_project"},
    "specfact_govern": {"specfact_project"},
}


@dataclass(frozen=True)
class Violation:
    """Single import boundary violation."""

    file_path: Path
    line: int
    import_name: str
    message: str


def _is_allowed_prefix(module_name: str, allowed_prefixes: tuple[str, ...]) -> bool:
    if module_name in ALLOWED_SPECFACT_CLI_EXACT:
        return True
    return any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in allowed_prefixes)


def _extract_imported_modules(tree: ast.AST) -> list[tuple[int, str]]:
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, node.module))
    return imports


def _scan_python_file(bundle_name: str, file_path: Path) -> list[Violation]:
    violations: list[Violation] = []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except SyntaxError as exc:
        violations.append(
            Violation(
                file_path=file_path,
                line=exc.lineno or 1,
                import_name="<syntax-error>",
                message=f"Could not parse file: {exc.msg}",
            )
        )
        return violations

    for line, module_name in _extract_imported_modules(tree):
        if module_name.startswith("specfact_cli.") and not _is_allowed_prefix(
            module_name, ALLOWED_SPECFACT_CLI_PREFIXES
        ):
            violations.append(
                Violation(
                    file_path=file_path,
                    line=line,
                    import_name=module_name,
                    message="Forbidden MIGRATE-tier import from specfact_cli.*",
                )
            )
            continue

        for other_bundle in PACKAGE_DIRS:
            if other_bundle == bundle_name:
                continue
            if module_name == other_bundle or module_name.startswith(other_bundle + "."):
                if other_bundle not in ALLOWED_CROSS_BUNDLE_IMPORTS.get(bundle_name, set()):
                    violations.append(
                        Violation(
                            file_path=file_path,
                            line=line,
                            import_name=module_name,
                            message=f"Forbidden cross-bundle import: {bundle_name} -> {other_bundle}",
                        )
                    )
                break

    return violations


def main() -> int:
    violations: list[Violation] = []

    for bundle_name, package_dir in PACKAGE_DIRS.items():
        if not package_dir.exists():
            continue
        for file_path in package_dir.rglob("*.py"):
            violations.extend(_scan_python_file(bundle_name, file_path))

    if not violations:
        print("Import boundary check passed.")
        return 0

    print("Import boundary violations found:")
    for violation in sorted(violations, key=lambda v: (str(v.file_path), v.line, v.import_name)):
        rel_path = violation.file_path.relative_to(ROOT)
        print(f"- {rel_path}:{violation.line} [{violation.import_name}] {violation.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
