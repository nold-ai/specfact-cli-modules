"""Source-only Python feature and quality evidence for brownfield analysis."""

from __future__ import annotations

import ast
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from beartype import beartype
from icontract import require

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
    "sqlalchemy.orm.DeclarativeBase": "sqlalchemy",
    "sqlalchemy.orm.declarative_base": "sqlalchemy",
    "sqlalchemy.ext.declarative.declarative_base": "sqlalchemy",
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
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
SCOPE_NODES = (*FUNCTION_NODES, ast.ClassDef)
FOR_NODES = (ast.For, ast.AsyncFor)
_Definition = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
_SourceRoot = ast.Module | _Definition


class _SourceScope(NamedTuple):
    aliases: dict[str, str]
    origins: dict[str, str]
    strings: set[str]


def _source_origin(node: ast.expr, scope: _SourceScope) -> str:
    if isinstance(node, ast.Name) and node.id in scope.origins:
        return scope.origins[node.id]
    if isinstance(node, ast.Call):
        return qualified_name(node.func, scope.aliases)
    return qualified_name(node, scope.aliases)


def _literal_string(node: ast.AST | None) -> str:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""


def _keyword(call: ast.Call, *names: str) -> ast.expr | None:
    return next((item.value for item in call.keywords if item.arg in names), None)


def _route_framework(node: ast.Call, scope: _SourceScope) -> str:
    if not isinstance(node.func, ast.Attribute):
        return ""
    receiver = node.func.value
    if isinstance(receiver, ast.Name):
        return ROUTER_CONSTRUCTORS.get(scope.origins.get(receiver.id, ""), "")
    if isinstance(receiver, ast.Call):
        return ROUTER_CONSTRUCTORS.get(_source_origin(receiver, scope), "")
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


def _is_auth_dependency(call: ast.Call, scope: _SourceScope) -> bool:
    function = qualified_name(call.func, scope.aliases)
    if function not in {"Depends", "fastapi.Depends", "Security", "fastapi.Security"}:
        return False
    dependency = call.args[0] if call.args else _keyword(call, "dependency")
    if dependency is None:
        return False
    name = _source_origin(dependency, scope)
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


def _requires_auth_dependency(node: ast.Call, args: ast.arguments, scope: _SourceScope) -> bool:
    values = list(_parameter_dependencies(args, scope.aliases))
    configured = _keyword(node, "dependencies")
    if configured is not None:
        values.append(configured)
    return any(
        _is_auth_dependency(item, scope) for value in values for item in ast.walk(value) if isinstance(item, ast.Call)
    )


def _route_patterns(node: ast.Call, args: ast.arguments, scope: _SourceScope) -> Iterator[PatternMatch]:
    framework = _route_framework(node, scope)
    if not framework:
        return
    routes = tuple(_decorated_route(node, framework))
    for method, path in routes:
        yield PatternMatch(f"{framework}-route-detection", node, metadata={"method": method, "path": path})
    if routes and framework == "fastapi" and _requires_auth_dependency(node, args, scope):
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


def _class_patterns(node: ast.ClassDef, scope: _SourceScope) -> Iterator[PatternMatch]:
    bases = {_source_origin(base, scope) for base in node.bases}
    methods = {item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
    decorators = {
        qualified_name(item.func if isinstance(item, ast.Call) else item, scope.aliases).rsplit(".", 1)[-1]
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


def _repeats_string_addition(node: ast.Assign, strings: set[str]) -> bool:
    value = node.value
    if not isinstance(value, ast.BinOp) or not isinstance(value.op, ast.Add) or not isinstance(value.left, ast.Name):
        return False
    return value.left.id in strings and any(
        isinstance(target, ast.Name) and target.id == value.left.id for target in node.targets
    )


def _track_loop_write(statement: ast.AST, scope: _SourceScope, definite: bool) -> None:
    if isinstance(statement, ast.Assign) and _repeats_string_addition(statement, scope.strings):
        return
    _track_source_bindings(statement, scope, definite)


def _loop_entry_scope(
    node: ast.For | ast.AsyncFor, scope: _SourceScope, body_nodes: Sequence[ast.AST], owned_nodes: frozenset[ast.AST]
) -> _SourceScope:
    direct_statements = frozenset(node.body)
    after_iteration = _SourceScope(scope.aliases.copy(), scope.origins.copy(), scope.strings.copy())
    _forget_target_names(node.target, after_iteration)
    entry_strings = after_iteration.strings.copy()
    for statement in body_nodes:
        if isinstance(statement, ast.Continue) and statement in owned_nodes:
            entry_strings.intersection_update(after_iteration.strings)
        _track_loop_write(statement, after_iteration, statement in direct_statements)

    # The loop can repeat under either its initial bindings or bindings carried from an earlier iteration.
    return _SourceScope(scope.aliases.copy(), scope.origins.copy(), entry_strings & after_iteration.strings)


def _additions_at_statement(statement: ast.AST, scope: _SourceScope) -> Iterator[ast.Assign]:
    if isinstance(statement, FOR_NODES):
        yield from _repeated_additions(statement, scope)
    if isinstance(statement, ast.Assign) and _repeats_string_addition(statement, scope.strings):
        yield statement


def _repeated_additions(node: ast.For | ast.AsyncFor, scope: _SourceScope) -> Iterator[ast.Assign]:
    body_nodes = list(_owned_nodes(node.body))
    owned_nodes = frozenset(_owned_nodes(node.body, boundaries=(*SCOPE_NODES, *FOR_NODES)))
    loop_scope = _loop_entry_scope(node, scope, body_nodes, owned_nodes)
    direct_statements = frozenset(node.body)
    for statement in body_nodes:
        if statement in owned_nodes:
            yield from _additions_at_statement(statement, loop_scope)
        _track_loop_write(statement, loop_scope, statement in direct_statements)


def _definition_evidence(node: ast.AST, scope: _SourceScope) -> Iterator[PatternMatch]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _function_patterns(node, scope)
    if isinstance(node, ast.ClassDef):
        return _class_patterns(node, scope)
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


def _binding_value(node: ast.AST) -> ast.expr | None:
    if isinstance(node, FOR_NODES):
        return node.iter
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        return node.value
    return None


def _owned_nodes(nodes: Sequence[ast.AST], *, boundaries: tuple[type[ast.AST], ...] = SCOPE_NODES) -> Iterator[ast.AST]:
    pending = list(reversed(nodes))
    while pending:
        node = pending.pop()
        value = _binding_value(node)
        if value is not None:
            yield from _owned_nodes((value,), boundaries=boundaries)
        yield node
        if not isinstance(node, boundaries):
            children = reversed(list(ast.iter_child_nodes(node)))
            pending.extend(child for child in children if child is not value)


def _track_origin(name: str, origin: str, scope: _SourceScope, definite: bool) -> None:
    scope.aliases.pop(name, None)
    if definite and origin:
        scope.origins[name] = origin
    elif origin != scope.origins.get(name):
        scope.origins.pop(name, None)


def _track_binding(target: ast.expr, value: ast.expr | None, scope: _SourceScope, definite: bool) -> None:
    if not isinstance(target, ast.Name):
        _forget_target_names(target, scope)
        return
    name = target.id
    origin = _source_origin(value, scope) if isinstance(value, ast.Call) else ""
    _track_origin(name, origin, scope, definite)
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        if definite:
            scope.strings.add(name)
    else:
        scope.strings.discard(name)


def _track_type_binding(node: ast.ClassDef, scope: _SourceScope, definite: bool) -> None:
    bases = (_source_origin(base, scope) for base in node.bases)
    origin = next((base for base in bases if CHECKED_MODELS.get(base) == "sqlalchemy"), "")
    _track_origin(node.name, origin, scope, definite)
    scope.strings.discard(node.name)


def _forget_name(name: str, scope: _SourceScope) -> None:
    scope.aliases.pop(name, None)
    scope.origins.pop(name, None)
    scope.strings.discard(name)


def _forget_target_names(target: ast.expr, scope: _SourceScope) -> None:
    if isinstance(target, ast.Name):
        _forget_name(target.id, scope)
    if isinstance(target, ast.Starred):
        _forget_target_names(target.value, scope)
    if isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            _forget_target_names(element, scope)


def _track_imports(node: ast.Import | ast.ImportFrom, scope: _SourceScope, definite: bool) -> None:
    for name, imported in import_aliases([node]).items():
        scope.strings.discard(name)
        scope.origins.pop(name, None)
        if definite or scope.aliases.get(name) == imported:
            scope.aliases[name] = imported
        else:
            scope.aliases.pop(name, None)


def _track_source_bindings(node: ast.AST, scope: _SourceScope, definite: bool) -> None:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        _track_imports(node, scope, definite)
        return
    if isinstance(node, ast.Assign):
        for target in node.targets:
            _track_binding(target, node.value, scope, definite)
        return
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        _track_binding(node.target, node.value, scope, definite)
    if isinstance(node, ast.AugAssign):
        _track_binding(node.target, None, scope, definite)
    if isinstance(node, ast.ClassDef):
        _track_type_binding(node, scope, definite)
    if isinstance(node, FUNCTION_NODES):
        _forget_name(node.name, scope)
    if isinstance(node, FOR_NODES):
        _forget_target_names(node.target, scope)


def _loop_evidence(node: ast.For | ast.AsyncFor, scope: _SourceScope) -> Iterator[PatternMatch]:
    for statement in _repeated_additions(node, scope):
        yield PatternMatch("string-concatenation-loop", statement, "Review repeated concatenation in a loop")


def _definition_header_evidence(node: _Definition, scope: _SourceScope) -> Iterator[PatternMatch]:
    body = frozenset(node.body)
    header = [child for child in ast.iter_child_nodes(node) if child not in body]
    for expression in _owned_nodes(header):
        yield from _definition_evidence(expression, scope)
        yield from _statement_evidence(expression, scope)


def _source_matches(tree: _SourceRoot, inherited: _SourceScope) -> Iterator[PatternMatch]:
    scope = _SourceScope(inherited.aliases.copy(), inherited.origins.copy(), set())
    if isinstance(tree, FUNCTION_NODES):
        for parameter in ast.iter_child_nodes(tree.args):
            if isinstance(parameter, ast.arg):
                _forget_name(parameter.arg, scope)
    enclosing = inherited if isinstance(tree, ast.ClassDef) else scope
    direct_statements = frozenset(tree.body)
    outer_nodes = frozenset(_owned_nodes(tree.body, boundaries=(*SCOPE_NODES, *FOR_NODES)))
    for node in _owned_nodes(tree.body):
        yield from _definition_evidence(node, scope)
        yield from _statement_evidence(node, scope)
        if isinstance(node, FOR_NODES) and node in outer_nodes:
            yield from _loop_evidence(node, scope)
        if isinstance(node, SCOPE_NODES):
            yield from _definition_header_evidence(node, scope)
        if isinstance(node, ast.ClassDef):
            yield from _source_matches(node, enclosing)
        _track_source_bindings(node, scope, node in direct_statements)
        if isinstance(node, FUNCTION_NODES):
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
        for match in _source_matches(tree, _SourceScope({}, {}, set()))
    ]
