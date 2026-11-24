"""Resolve names in Python source without importing project code."""

from __future__ import annotations

import ast
from collections.abc import Sequence

from beartype import beartype
from icontract import ensure


@beartype
@ensure(lambda result: isinstance(result, str), "Qualified names must be text")
def qualified_name(node: ast.AST, aliases: dict[str, str]) -> str:
    """Resolve a syntactically qualified name through known imports."""
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return f"{qualified_name(node.value, aliases)}.{node.attr}"
    return ""


@beartype
@ensure(lambda result: isinstance(result, dict), "Aliases must be a mapping")
def import_aliases(nodes: Sequence[ast.AST]) -> dict[str, str]:
    """Map aliases to imported Python names without loading modules."""
    aliases: dict[str, str] = {}
    for node in nodes:
        if isinstance(node, ast.Import):
            for name in node.names:
                bound_name = name.name.partition(".")[0]
                aliases[name.asname or bound_name] = name.name if name.asname else bound_name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            aliases.update({name.asname or name.name: f"{node.module}.{name.name}" for name in node.names})
    return aliases
