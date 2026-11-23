"""Source-only Python feature and quality evidence for brownfield analysis."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

from beartype import beartype
from icontract import ensure, require

from specfact_project.analyzers.python_source import import_aliases, qualified_name


class PatternMatch(NamedTuple):
    rule: str
    node: ast.stmt | ast.expr | ast.ExceptHandler
    message: str = ""
    metadata: dict[str, str] | None = None
    function_name: str = ""


CRUD = {
    "create": "create",
    "add": "create",
    "insert": "create",
    "get": "read",
    "find": "read",
    "fetch": "read",
    "retrieve": "read",
    "update": "update",
    "modify": "update",
    "edit": "update",
    "delete": "delete",
    "remove": "delete",
    "destroy": "delete",
}
HTTP_METHODS = frozenset({"get", "post", "put", "delete", "patch", "head", "options", "trace"})
CHECKED_MODELS = {
    "BaseModel": "pydantic",
    "pydantic.BaseModel": "pydantic",
    "Base": "sqlalchemy",
    "DeclarativeBase": "sqlalchemy",
    "sqlalchemy.orm.DeclarativeBase": "sqlalchemy",
    "db.Model": "sqlalchemy",
    "Model": "django",
    "models.Model": "django",
    "django.db.models.Model": "django",
    "tortoise.models.Model": "tortoise-orm",
    "peewee.Model": "peewee",
}
CALL_RULES = {
    "structlog.get_logger": "structlog-usage",
    "structlog.configure": "structlog-usage",
    "logging.getLogger": "logger-instantiation",
    "os.getenv": "env-variable-access",
    "os.environ.get": "env-variable-access",
    "load_dotenv": "dotenv-usage",
    "dotenv.load_dotenv": "dotenv-usage",
    "asyncio.gather": "asyncio-gather-pattern",
    "mock.patch": "unittest-mock-usage",
    "mock.Mock": "unittest-mock-usage",
    "unittest.mock.patch": "unittest-mock-usage",
    "unittest.mock.Mock": "unittest-mock-usage",
}
QUALITY_CALLS = {
    "eval": ("unsafe-eval-usage", "Unsafe evaluation of Python code"),
    "exec": ("unsafe-eval-usage", "Unsafe execution of Python code"),
    "compile": ("unsafe-eval-usage", "Review dynamic compilation of Python code"),
    "pickle.load": ("unsafe-pickle-deserialization", "Do not deserialize untrusted pickle data"),
    "pickle.loads": ("unsafe-pickle-deserialization", "Do not deserialize untrusted pickle data"),
    "os.system": ("command-injection-risk", "Avoid invoking a shell to run a command"),
    "hashlib.md5": ("weak-cryptographic-hash", "MD5 is unsuitable for cryptographic security"),
    "hashlib.sha1": ("weak-cryptographic-hash", "SHA-1 is unsuitable for cryptographic security"),
    "random.random": ("insecure-random", "Use secrets for security-sensitive randomness"),
    "random.randint": ("insecure-random", "Use secrets for security-sensitive randomness"),
}


ROUTER_CONSTRUCTORS = {
    "fastapi.FastAPI": "fastapi",
    "fastapi.APIRouter": "fastapi",
    "flask.Flask": "flask",
    "flask.Blueprint": "flask",
}
SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
SourceValues = dict[str, list[tuple[int, ast.expr]]]


class _SourceScope(NamedTuple):
    aliases: dict[str, str]
    assignments: SourceValues

    @ensure(lambda result: result is None or isinstance(result, ast.expr), "A binding has a source expression")
    def before(self, name: str, line: int) -> ast.expr | None:
        return next((value for at, value in reversed(self.assignments.get(name, [])) if at < line), None)


def _literal_string(node: ast.AST | None) -> str:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""


def _keyword(call: ast.Call, *names: str) -> ast.expr | None:
    return next((item.value for item in call.keywords if item.arg in names), None)


def _route_framework(node: ast.Call, scope: _SourceScope) -> str:
    if not isinstance(node.func, ast.Attribute):
        return ""
    receiver = node.func.value
    constructor = scope.before(receiver.id, node.lineno) if isinstance(receiver, ast.Name) else receiver
    if isinstance(constructor, ast.Call):
        return ROUTER_CONSTRUCTORS.get(qualified_name(constructor.func, scope.aliases), "")
    return ""


def _decorated_route(node: ast.Call, framework: str) -> Iterator[tuple[str, str]]:
    if not isinstance(node.func, ast.Attribute):
        return
    method = node.func.attr
    path = _literal_string(node.args[0] if node.args else _keyword(node, "path", "rule"))
    if not path:
        return
    if method in HTTP_METHODS:
        yield method.upper(), path
    if method == "route" and framework == "flask":
        for verb in _configured_route_methods(node):
            if verb.lower() in HTTP_METHODS:
                yield verb.upper(), path


def _configured_route_methods(node: ast.Call) -> Iterator[str]:
    configured = _keyword(node, "methods")
    if isinstance(configured, (ast.List, ast.Tuple)):
        yield from map(_literal_string, configured.elts)
    elif configured is None:
        yield "GET"


DECORATOR_RULES = {
    "beartype": "beartype-decorator-detection",
    "require": "icontract-decorator-detection",
    "ensure": "icontract-decorator-detection",
    "contextmanager": "contextlib-contextmanager",
    "middleware": "middleware-detection",
    "pytest.fixture": "pytest-fixture-detection",
    "pytest.mark.parametrize": "pytest-parametrize",
}


AUTH_DEPENDENCY_NAMES = frozenset({"require_auth", "require_permission", "get_current_user", "get_current_active_user"})


def _is_auth_dependency(call: ast.Call, aliases: dict[str, str]) -> bool:
    function = qualified_name(call.func, aliases)
    if function not in {"Depends", "fastapi.Depends", "Security", "fastapi.Security"}:
        return False
    dependency = call.args[0] if call.args else _keyword(call, "dependency")
    if dependency is None:
        return False
    name = qualified_name(dependency.func if isinstance(dependency, ast.Call) else dependency, aliases)
    return name.startswith("fastapi.security.") or name.rsplit(".", 1)[-1] in AUTH_DEPENDENCY_NAMES


def _annotated_dependencies(argument: ast.arg, aliases: dict[str, str]) -> tuple[ast.expr, ...]:
    annotation = argument.annotation
    if not isinstance(annotation, ast.Subscript) or not isinstance(annotation.slice, ast.Tuple):
        return ()
    if qualified_name(annotation.value, aliases) not in {
        "Annotated",
        "typing.Annotated",
        "typing_extensions.Annotated",
    }:
        return ()
    return tuple(annotation.slice.elts[1:])


def _parameter_dependencies(args: ast.arguments, aliases: dict[str, str]) -> Iterator[ast.expr]:
    yield from args.defaults
    yield from (value for value in args.kw_defaults if value is not None)
    for argument in (*args.posonlyargs, *args.args, *args.kwonlyargs):
        yield from _annotated_dependencies(argument, aliases)


def _requires_auth_dependency(node: ast.Call, args: ast.arguments, aliases: dict[str, str]) -> bool:
    values = list(_parameter_dependencies(args, aliases))
    configured = _keyword(node, "dependencies")
    if configured is not None:
        values.append(configured)
    return any(
        _is_auth_dependency(item, aliases) for value in values for item in ast.walk(value) if isinstance(item, ast.Call)
    )


def _route_patterns(node: ast.Call, args: ast.arguments, scope: _SourceScope) -> Iterator[PatternMatch]:
    framework = _route_framework(node, scope)
    if not framework:
        return
    routes = tuple(_decorated_route(node, framework))
    for method, path in routes:
        yield PatternMatch(f"{framework}-route-detection", node, metadata={"method": method, "path": path})
    if routes and framework == "fastapi" and _requires_auth_dependency(node, args, scope.aliases):
        yield PatternMatch("fastapi-dependency-auth-detection", node)


def _decorator_patterns(
    function: ast.FunctionDef | ast.AsyncFunctionDef, scope: _SourceScope
) -> Iterator[PatternMatch]:
    for node in function.decorator_list:
        name = qualified_name(node.func if isinstance(node, ast.Call) else node, scope.aliases)
        suffix = name.rsplit(".", 1)[-1]
        if isinstance(node, ast.Call):
            yield from _route_patterns(node, function.args, scope)
        if suffix in {"require_auth", "require_permission", "login_required"}:
            permission = _literal_string(node.args[0]) if isinstance(node, ast.Call) and node.args else ""
            yield PatternMatch("auth-decorator-detection", node, metadata={"permission": permission})
        if rule := DECORATOR_RULES.get(name) or DECORATOR_RULES.get(suffix):
            yield PatternMatch(rule, node)


def _function_patterns(node: ast.FunctionDef | ast.AsyncFunctionDef, scope: _SourceScope) -> Iterator[PatternMatch]:
    yield from _decorator_patterns(node, scope)
    prefix, _, entity = node.name.partition("_")
    operation = CRUD.get(prefix)
    if operation and entity:
        yield PatternMatch(
            f"crud-{operation}-operation", node, metadata={"operation": operation}, function_name=node.name
        )
    if node.name.startswith("test_"):
        yield PatternMatch("pytest-test-detection", node)
        if node.args.args and node.args.args[0].arg == "self":
            yield PatternMatch("unittest-test-detection", node)
    if isinstance(node, ast.AsyncFunctionDef):
        yield PatternMatch("async-function-detection", node)
    if node.returns is not None:
        yield PatternMatch("type-annotations-detection", node)
    if any(
        isinstance(default, (ast.List, ast.Dict, ast.Set)) for default in (*node.args.defaults, *node.args.kw_defaults)
    ):
        yield PatternMatch("mutable-default-argument", node, "Mutable default argument")


def _class_base_patterns(node: ast.ClassDef, bases: set[str]) -> Iterator[PatternMatch]:
    for model in sorted({CHECKED_MODELS[base] for base in bases if base in CHECKED_MODELS}):
        yield PatternMatch(f"{model}-model-detection", node, metadata={"model": node.name})
    if any(base.endswith("BaseSettings") for base in bases):
        yield PatternMatch("pydantic-settings-detection", node)
    if any(base.endswith("Exception") for base in bases):
        yield PatternMatch("custom-exception-class", node)


def _class_shape_patterns(
    node: ast.ClassDef, bases: set[str], methods: set[str], decorators: set[str]
) -> Iterator[PatternMatch]:
    if {"__enter__", "__exit__"} <= methods:
        yield PatternMatch("context-manager-class", node)
    for family in ("Service", "Repository"):
        if ("__init__" in methods and node.name.endswith(family)) or family in bases:
            rule = "service-class-detection" if family == "Service" else "repository-pattern-detection"
            yield PatternMatch(rule, node)
    if "dataclass" in decorators:
        yield PatternMatch("dataclass-usage", node)
    elif len(methods) >= 20:
        yield PatternMatch("god-class-detection", node, "Potential God Class with at least 20 methods")
    if "invariant" in decorators:
        yield PatternMatch("icontract-decorator-detection", node)


def _class_patterns(node: ast.ClassDef, aliases: dict[str, str]) -> Iterator[PatternMatch]:
    bases = {qualified_name(base, aliases) for base in node.bases}
    methods = {item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
    decorators = {
        qualified_name(item.func if isinstance(item, ast.Call) else item, aliases).rsplit(".", 1)[-1]
        for item in node.decorator_list
    }
    yield from _class_base_patterns(node, bases)
    yield from _class_shape_patterns(node, bases, methods, decorators)


def _call_patterns(node: ast.Call, aliases: dict[str, str]) -> Iterator[PatternMatch]:
    name = qualified_name(node.func, aliases)
    if rule := CALL_RULES.get(name):
        yield PatternMatch(rule, node)
    if quality := QUALITY_CALLS.get(name):
        yield PatternMatch(quality[0], node, quality[1])
    if name in {"subprocess.run", "subprocess.call", "subprocess.Popen"} and any(
        item.arg == "shell" and isinstance(item.value, ast.Constant) and item.value.value is True
        for item in node.keywords
    ):
        yield PatternMatch("command-injection-risk", node, "Shell subprocess invocation")


def _assignment_patterns(node: ast.Assign) -> Iterator[PatternMatch]:
    names = {target.id for target in node.targets if isinstance(target, ast.Name)}
    value = node.value
    if "__all__" in names and isinstance(value, ast.List):
        yield PatternMatch("__all__-declaration", node)
    if (
        isinstance(value, ast.Constant)
        and isinstance(value.value, str)
        and (names & {"API_KEY", "PASSWORD"} or value.value.lower().startswith(("api_key:", "password:", "secret:")))
    ):
        yield PatternMatch("hardcoded-secret", node, "Literal credential assigned in source")
    if isinstance(value, ast.Lambda):
        yield PatternMatch("lambda-assignment-antipattern", node, "Use a named function in place of an assigned lambda")
    if isinstance(value, ast.ListComp):
        yield PatternMatch("list-comprehension-usage", node)
    if isinstance(value, ast.GeneratorExp):
        yield PatternMatch("generator-expression", node)


def _import_patterns(node: ast.Import | ast.ImportFrom) -> Iterator[PatternMatch]:
    modules = {name.name.split(".", 1)[0] for name in node.names} if isinstance(node, ast.Import) else {node.module}
    deprecated = {
        "imp": "deprecated-imp-module",
        "optparse": "deprecated-optparse-module",
        "urllib2": "deprecated-urllib-usage",
    }
    for name in sorted(item for item in modules if item):
        if rule := deprecated.get(name):
            yield PatternMatch(rule, node, f"Deprecated Python module {name}")
        if name in {"structlog", "dotenv"}:
            yield PatternMatch("structlog-usage" if name == "structlog" else "dotenv-usage", node)


def _repeated_additions(node: ast.For | ast.AsyncFor, scope: _SourceScope) -> Iterator[ast.Assign]:
    assignments = (statement for statement in node.body if isinstance(statement, ast.Assign))
    for statement in assignments:
        value = statement.value
        if (
            not isinstance(value, ast.BinOp)
            or not isinstance(value.op, ast.Add)
            or not isinstance(value.left, ast.Name)
        ):
            continue
        targets = {target.id for target in statement.targets if isinstance(target, ast.Name)}
        if value.left.id in targets:
            initial = scope.before(value.left.id, node.lineno)
            if isinstance(initial, ast.Constant) and isinstance(initial.value, str):
                yield statement


def _definition_evidence(node: ast.AST, scope: _SourceScope) -> Iterator[PatternMatch]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _function_patterns(node, scope)
    if isinstance(node, ast.ClassDef):
        return _class_patterns(node, scope.aliases)
    if isinstance(node, ast.Call):
        return _call_patterns(node, scope.aliases)
    if isinstance(node, ast.Assign):
        return _assignment_patterns(node)
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return _import_patterns(node)
    return iter(())


def _statement_evidence(node: ast.AST, scope: _SourceScope) -> Iterator[PatternMatch]:
    if isinstance(node, ast.ExceptHandler) and node.type is None:
        yield PatternMatch("bare-except-antipattern", node, "Use a specific exception instead of bare except")
    if isinstance(node, (ast.Try, ast.TryStar)) and node.finalbody:
        yield PatternMatch("finally-block-usage", node)
    if isinstance(node, ast.AnnAssign):
        yield PatternMatch("type-annotations-detection", node)
    if isinstance(node, ast.Subscript) and qualified_name(node.value, scope.aliases) == "os.environ":
        yield PatternMatch("env-variable-access", node)
    if isinstance(node, (ast.For, ast.AsyncFor)):
        for statement in _repeated_additions(node, scope):
            yield PatternMatch("string-concatenation-loop", statement, "Review repeated concatenation in a loop")


def _owned_nodes(root: ast.AST) -> Iterator[ast.AST]:
    pending = list(reversed(list(ast.iter_child_nodes(root))))
    while pending:
        node = pending.pop()
        yield node
        if not isinstance(node, SCOPE_NODES):
            pending.extend(reversed(list(ast.iter_child_nodes(node))))


def _assignment_values(nodes: list[ast.AST]) -> SourceValues:
    values: SourceValues = {}
    for node in nodes:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if node.value is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                values.setdefault(target.id, []).append((node.lineno, node.value))
    return values


def _source_matches(tree: ast.AST, inherited: _SourceScope) -> Iterator[PatternMatch]:
    nodes = list(_owned_nodes(tree))
    scope = _SourceScope(inherited.aliases | import_aliases(nodes), inherited.assignments | _assignment_values(nodes))
    enclosing = inherited if isinstance(tree, ast.ClassDef) else scope
    for node in nodes:
        yield from _definition_evidence(node, scope)
        yield from _statement_evidence(node, scope)
        if isinstance(node, SCOPE_NODES):
            yield from _source_matches(node, enclosing)


@beartype
@require(lambda tree: isinstance(tree, ast.Module), "Pattern evidence requires a parsed Python module")
def feature_patterns(tree: ast.Module, file_path: Path) -> list[dict[str, Any]]:
    """Normalize source matches to the existing brownfield evidence fields."""
    return [
        {
            "check_id": match.rule,
            "path": str(file_path),
            "start": {"line": match.node.lineno},
            "message": match.message,
            "extra": {"metadata": match.metadata or {}, "message": match.function_name},
        }
        for match in _source_matches(tree, _SourceScope({}, {}))
    ]
