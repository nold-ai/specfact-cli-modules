"""Resolve review inputs without trusting the caller's mutable worktree.

This module is the sole Git-discovery boundary for Code Review scope.  Later
pipeline stages consume :class:`ScopeResolution`; they do not rediscover paths.
"""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import tomllib
from collections.abc import Callable, Iterable, Sequence
from contextlib import ExitStack
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Literal, cast

from icontract import ensure, require


ScopeKind = Literal["worktree", "index", "range", "full", "explicit_files"]
ScopeStatus = Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
AssuranceKind = Literal["worktree", "index", "range_preview", "range_candidate", "pr_range", "full", "explicit_files"]
EnforcementKind = Literal["full", "changed", "shadow"]

_REGULAR_GIT_MODES = frozenset({"100644", "100755"})
_PYTHON_SUFFIXES = frozenset({".py", ".pyi"})
_GIT_LOCAL_ENV_VARS = frozenset(
    {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PREFIX",
        "GIT_WORK_TREE",
    }
)
GOVERNED_POLICY_PATHS_V1 = frozenset(
    {
        ".coveragerc",
        ".coveragerc.toml",
        ".pylintrc",
        ".pylintrc.toml",
        ".pytest.ini",
        ".pytest.toml",
        ".ruff.toml",
        ".semgrep/bugs.yaml",
        ".semgrep/clean_code.yaml",
        "basedpyrightconfig.json",
        "mypy.ini",
        "pylintrc",
        "pylintrc.toml",
        "pytest.ini",
        "pytest.toml",
        "pyrightconfig.json",
        "radon.cfg",
        "resources/semgrep-rules/ai-bloat.yaml",
        "ruff.toml",
    }
)
_PYPROJECT_POLICY_SECTIONS = (
    ("tool", "basedpyright"),
    ("tool", "coverage"),
    ("tool", "pylint"),
    ("tool", "pyright"),
    ("tool", "pytest"),
    ("tool", "radon"),
    ("tool", "ruff"),
)
_INI_POLICY_SECTIONS = frozenset(
    {
        "coverage:html",
        "coverage:paths",
        "coverage:report",
        "coverage:run",
        "mypy",
        "pylint",
        "pytest",
        "radon",
        "tool:pytest",
    }
)


def _recognized_ini_policy_section(section: str) -> bool:
    normalized = section.lower()
    return normalized in _INI_POLICY_SECTIONS or normalized.startswith("pylint.")


class GitResolutionError(RuntimeError):
    """Git could not provide an unambiguous immutable scope identity."""


class ContextResolutionError(ValueError):
    """Claimed PR context is unsafe, malformed, or identity-mismatched."""


class PolicyResolutionError(ValueError):
    """Target-tip policy inputs cannot be safely parsed or materialized."""


class InvalidScopeOption(ValueError):  # noqa: N818 - public contract name is frozen by C14
    """A scope option would weaken or mutate immutable review evidence."""


class RunCommandError(ValueError):
    """Structured validation error for review-run command options."""

    error_code = "run_command_error"


class ConflictingScopeError(RunCommandError):
    """Positional files and automatic scope controls were combined."""

    error_code = "conflicting_scope"


class NoReviewableFilesError(RunCommandError):
    """No existing governed Python input survived scope selection."""

    error_code = "no_reviewable_files"


@dataclass(frozen=True)
class TreeEntry:
    """One immutable Git tree entry."""

    git_mode: str
    object_type: str
    object_id: str
    path: str


@dataclass(frozen=True)
class InputIdentity:
    """Verified identity of one governed Git input."""

    object_type: str
    git_mode: str
    blob_sha: str
    content_digest: str
    open_policy: str = "descriptor-relative-nofollow"


@dataclass(frozen=True)
class IndexMetadata:
    """Canonical stage/flag facts read from the captured index."""

    git_mode: str
    blob_sha: str
    stage: int
    intent_to_add: bool
    flag_tag: str


@dataclass(frozen=True)
class ExactRename:
    """Canonical exact-blob rename/copy disposition."""

    old_path: str
    new_path: str
    blob_sha: str
    git_mode: str
    disposition: Literal["exact_rename", "copy", "ambiguous"]


@dataclass(frozen=True)
class PolicyBundle:
    """Read-only target-tip policy inputs, separated from analyzed snapshots."""

    root: Path
    source_commit: str
    source_tree: str
    paths: tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class PolicyPayloadIdentity:
    """One selected target-tip or signed-module policy payload."""

    identity_kind: Literal["git_blob", "signed_module_payload", "unavailable"]
    source_path: str
    content_digest: str
    materialized_path: Path


@dataclass(frozen=True)
class SemgrepBundle:
    """One sealed explicit policy bundle shared by both snapshots."""

    status: ScopeStatus
    root: Path
    clean: PolicyPayloadIdentity
    ai_bloat: PolicyPayloadIdentity
    bundle_digest: str
    reason: str = ""


@dataclass(frozen=True)
class LocatedPolicy:
    """Pinned-loader logical configuration selection and ignored-source evidence."""

    status: ScopeStatus
    selected_path: str
    selected_section: str
    loader_version: str
    ignored_paths: tuple[str, ...]
    selection_reason: str
    source_order: tuple[str, ...]
    manifest_digest: str
    reason: str = ""


@dataclass(frozen=True)
class RuffPolicy:
    """Pinned Ruff source selection and sealed extend closure."""

    status: ScopeStatus
    selected_path: str | None
    isolated: bool
    loader_version: str
    closure_paths: tuple[str, ...]
    closure_digest: str
    bundle_root: Path | None
    values: dict[str, object]
    reason: str = ""

    @classmethod
    def default(
        cls,
        *,
        version: str,
        task_tags: tuple[str, ...] = (),
        fix: bool = False,
        fix_only: bool = False,
    ) -> RuffPolicy:
        status: ScopeStatus = "PASS" if version == "0.15.12" else "UNKNOWN"
        return cls(
            status,
            None,
            True,
            version,
            (),
            "ruff-default-v1",
            None,
            {"lint": {"task-tags": list(task_tags)}, "fix": fix, "fix-only": fix_only},
            "" if status == "PASS" else "ruff_version_drift",
        )


@dataclass(frozen=True)
class BasedPyrightPolicy:
    """Pinned basedpyright primary/reference graph and logical values."""

    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    strict: tuple[str, ...] = ()
    executionEnvironments: tuple[object, ...] = ()  # noqa: N815 - pinned tool key
    baseline_file: str | None = None
    status: ScopeStatus = "PASS"
    reason: str = ""
    selected_path: str | None = None
    reference_paths: tuple[str, ...] = ()
    loader_version: str = "1.39.10"
    graph_digest: str = ""
    bundle_root: Path | None = None
    values: dict[str, object] = field(default_factory=dict)
    identity: str = "basedpyright-default-v1"
    identity_kind: str = "builtin_mode"


@dataclass(frozen=True)
class PylintPolicy:
    """Pinned Pylint source selection and safe initial projection."""

    status: ScopeStatus
    selected_path: str | None
    loader_version: str
    projection: dict[str, object]
    stdin_policy: str
    manifest_digest: str
    reason: str = ""


@dataclass(frozen=True)
class PolicyProjection:
    """Canonical generated per-snapshot policy and launch controls."""

    status: ScopeStatus
    values: dict[str, object]
    argv: tuple[str, ...]
    config_path: Path | None
    projection_digest: str
    eligible_inputs: tuple[str, ...]
    provenance_kind: str = "generated_projection"
    reason: str = ""
    cache_writes: tuple[str, ...] = ()
    evidence: dict[str, object] = field(default_factory=dict)
    logical_policy_digest: str = ""

    @ensure(lambda result: isinstance(result, bool))
    def argv_contains(self, value: str) -> bool:
        return value in self.argv


@dataclass(frozen=True)
class RadonProjection:
    status: ScopeStatus
    contract: str
    values: dict[str, object]
    control_cwd_empty: bool
    private_home: bool
    environment: dict[str, str]
    reason: str = ""


def project_radon_policy(snapshot_root: Path, *, expected_version: str) -> RadonProjection:
    """Return the controller-owned full-result Radon policy."""

    del snapshot_root
    if expected_version != "6.0.1":
        return RadonProjection("UNKNOWN", "radon-full-result-v1", {}, True, True, {}, "radon_version_drift")
    return RadonProjection(
        "PASS",
        "radon-full-result-v1",
        {
            "exclude": "",
            "ignore": "",
            "cc_ranks": ["A", "B", "C", "D", "E", "F"],
            "mi_ranks": ["A", "B", "C"],
            "output_file": None,
        },
        True,
        True,
        {},
    )


@dataclass(frozen=True)
class ScopeRequest:
    """Caller inputs for one scope resolution."""

    repository: Path
    scope: ScopeKind | Literal["changed"]
    files: tuple[Path, ...] = ()
    base_ref: str | None = None
    head_ref: str | None = None
    enforcement: EnforcementKind | None = None
    include_tests: bool = True
    exclude_tests: bool = False
    focus: tuple[str, ...] = ()
    path_filters: tuple[Path, ...] = ()
    no_tests: bool = False
    level: str | None = None
    fix: bool = False
    preview_fixes: bool = False
    with_mutation: bool = False
    pr_context_file: Path | None = None
    repository_slug: str | None = None
    project_runtime_source_lock_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class Snapshot:
    """Detached commit snapshot with content-addressed file bytes."""

    root: Path
    commit: str
    tree: str
    contents: dict[str, bytes]
    entries: dict[str, TreeEntry]

    @require(lambda relative_path: bool(str(relative_path)), "relative path must not be empty")
    @ensure(lambda result: isinstance(result, bytes))
    def read_bytes(self, relative_path: str | Path) -> bytes:
        return self.contents[PurePosixPath(relative_path).as_posix()]

    @require(lambda relative_path: bool(str(relative_path)), "relative path must not be empty")
    @ensure(lambda result: result.startswith("sha256:") and len(result) == 71)
    def content_digest(self, relative_path: str | Path) -> str:
        return sha256_bytes(self.read_bytes(relative_path))

    @ensure(lambda result: result is None or isinstance(result, bytes))
    def bytes_or_none(self, relative_path: str) -> bytes | None:
        return self.contents.get(relative_path)

    @ensure(lambda result: result is None or isinstance(result, TreeEntry))
    def entry_or_none(self, relative_path: str) -> TreeEntry | None:
        return self.entries.get(relative_path)


@dataclass(frozen=True)
class ScopeResolution:
    """Resolved review scope and its assurance projection."""

    status: ScopeStatus
    reason: str
    selected_paths: tuple[str, ...]
    assurance_kind: AssuranceKind
    effective_assurance_kind: AssuranceKind
    ci_exit_code: int
    diagnostics: str = ""
    base_snapshot: Snapshot | None = None
    head_snapshot: Snapshot | None = None
    materialized: bool = False
    merge_base_candidates: tuple[str, ...] = ()
    merge_base_candidate_identities: tuple[tuple[str, str], ...] = ()
    merge_base_candidate_digest: str = ""
    context_digest: str = ""
    claimed_context: dict[str, object] | None = None
    resolved_target_commit: str = ""
    resolved_target_tree: str = ""
    resolved_head_commit: str = ""
    resolved_head_tree: str = ""
    input_manifest: dict[str, InputIdentity] = field(default_factory=dict)
    base_input_manifest: dict[str, InputIdentity] = field(default_factory=dict)
    index_metadata: dict[str, IndexMetadata] = field(default_factory=dict)
    index_tree: str = ""
    selection_tree: str = ""
    path_statuses: dict[str, str] = field(default_factory=dict)
    exact_renames: tuple[ExactRename, ...] = ()
    exact_rename_digest: str = ""
    base_source_manifest_digest: str = ""
    head_source_manifest_digest: str = ""
    policy_bundle: PolicyBundle | None = None
    policy_paths: tuple[str, ...] = ()
    policy_manifest_digest: str = ""
    candidate_policy_change_digest: str = ""


@dataclass(frozen=True)
class AssuranceVerification:
    """Result of protected-PR assurance verification."""

    status: ScopeStatus
    reason: str


@dataclass(frozen=True)
class _ResolvedRange:
    candidates: tuple[str, ...]
    target_commit: str
    target_tree: str
    base_snapshot: Snapshot
    head_snapshot: Snapshot
    selected_paths: tuple[str, ...]
    source_lock_paths: frozenset[str]
    path_statuses: dict[str, str]
    exact_renames: tuple[ExactRename, ...]
    exact_rename_digest: str
    base_source_manifest_digest: str
    head_source_manifest_digest: str
    policy_bundle: PolicyBundle
    candidate_policy_paths: tuple[str, ...]
    policy_manifest_digest: str
    candidate_policy_change_digest: str
    claimed_context: _ClaimedContext | None


@dataclass(frozen=True)
class _ClaimedContext:
    document: dict[str, object]
    digest: str


@dataclass(frozen=True)
class _IndexCapture:
    path: Path
    digest: str


@dataclass(frozen=True)
class _RangeResultContext:
    resolved: _ResolvedRange
    base_manifest: dict[str, InputIdentity]
    head_manifest: dict[str, InputIdentity]
    claimed_context: _ClaimedContext | None
    assurance: AssuranceKind
    candidate_identities: tuple[tuple[str, str], ...]
    candidate_digest: str


@dataclass(frozen=True)
class _IndexResolutionContext:
    base_snapshot: Snapshot
    index_snapshot: Snapshot
    selected_paths: tuple[str, ...]
    metadata: dict[str, IndexMetadata]
    index_tree: str
    manifest: dict[str, InputIdentity]


@dataclass(frozen=True)
class LegacyFileSelectionRequest:
    include_tests: bool
    scope: Literal["changed", "full"] | None
    path_filters: list[Path]
    changed_discovery: Callable[..., list[Path]]
    full_discovery: Callable[[], list[Path]]


@dataclass(frozen=True)
class _RuffGraph:
    paths: tuple[str, ...]
    digest: str
    bundle_root: Path
    values: dict[str, object]


@ensure(lambda result: result.startswith("sha256:") and len(result) == 71)
def sha256_bytes(payload: bytes) -> str:
    """Return the repository's canonical labelled SHA-256 value."""

    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _canonical_json_digest(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return sha256_bytes(payload)


def _git_environment(env_overrides: dict[str, str] | None = None) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if key not in _GIT_LOCAL_ENV_VARS}
    return {**environment, "GIT_CONFIG_NOSYSTEM": "1", **(env_overrides or {})}


def _git(
    repository: Path,
    args: Sequence[str],
    *,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=False,
        timeout=30,
        env=_git_environment(env_overrides),
    )
    if result.returncode != 0:
        stderr = str(result.stderr).strip()
        raise GitResolutionError(stderr or f"git {' '.join(args)} failed with exit {result.returncode}")
    return result


def _git_lines(repository: Path, args: Sequence[str]) -> list[str]:
    return [line.strip() for line in _git(repository, args).stdout.splitlines() if line.strip()]


def _git_paths(repository: Path, args: Sequence[str]) -> list[str]:
    """Decode repository-relative paths from a NUL-delimited Git command."""
    return [path for path in _git(repository, [*args, "-z"]).stdout.split("\0") if path]


def _git_bytes(repository: Path, args: Sequence[str], *, env_overrides: dict[str, str] | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        capture_output=True,
        text=False,
        check=False,
        timeout=30,
        env=_git_environment(env_overrides),
    )
    if result.returncode != 0:
        diagnostics = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitResolutionError(diagnostics or f"git {' '.join(args)} failed with exit {result.returncode}")
    return result.stdout


def _resolve_revision(repository: Path, ref: str, object_type: Literal["commit", "tree"]) -> str:
    resolved = _git(repository, ["rev-parse", "--verify", f"{ref}^{{{object_type}}}"]).stdout.strip()
    if len(resolved) != 40:
        raise GitResolutionError(f"Git returned a non-full {object_type} identity for {ref!r}: {resolved!r}")
    return resolved


def _resolve_commit(repository: Path, ref: str) -> str:
    return _resolve_revision(repository, ref, "commit")


def _resolve_tree(repository: Path, commit: str) -> str:
    return _resolve_revision(repository, commit, "tree")


def _best_merge_bases(repository: Path, base: str, head: str) -> tuple[str, ...]:
    return tuple(sorted(_git_lines(repository, ["merge-base", "--all", base, head])))


def _tree_entries(repository: Path, revision: str) -> list[TreeEntry]:
    output = _git(repository, ["ls-tree", "-r", "-z", "--full-tree", revision]).stdout
    entries: list[TreeEntry] = []
    for record in output.split("\0"):
        if not record:
            continue
        metadata, separator, path = record.partition("\t")
        if not separator:
            raise GitResolutionError("Git tree entry omitted its path separator")
        mode, object_type, object_id = metadata.split(" ", 2)
        entries.append(TreeEntry(mode, object_type, object_id, path))
    return entries


def _safe_snapshot_path(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts:
        raise GitResolutionError(f"Unsafe path in Git tree: {relative!r}")
    return root.joinpath(*path.parts)


def _materialize_tree(repository: Path, revision: str, *, snapshot_identity: str) -> Snapshot:
    tree = _resolve_tree(repository, revision)
    root = Path(tempfile.mkdtemp(prefix=f"specfact-review-{snapshot_identity[:12]}-"))
    contents: dict[str, bytes] = {}
    entries = {entry.path: entry for entry in _tree_entries(repository, revision)}
    for entry in entries.values():
        if entry.object_type != "blob":
            continue
        payload = _git_bytes(repository, ["cat-file", "blob", entry.object_id])
        contents[entry.path] = payload
        if entry.git_mode not in _REGULAR_GIT_MODES:
            continue
        destination = _safe_snapshot_path(root, entry.path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        destination.chmod(0o755 if entry.git_mode == "100755" else 0o644)
    return Snapshot(root=root, commit=snapshot_identity, tree=tree, contents=contents, entries=entries)


def _materialize_commit(repository: Path, commit: str) -> Snapshot:
    return _materialize_tree(repository, commit, snapshot_identity=commit)


def _is_test_path(path: Path) -> bool:
    return "tests" in path.parts


def _is_ignored_path(path: Path) -> bool:
    if path.is_absolute():
        return False
    return any(part.startswith(".") and len(part) > 1 for part in path.parts[:-1])


def _toml_policy_projection(payload: bytes | None) -> object:
    if payload is None:
        return {}
    try:
        document = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return "invalid-policy-document"
    projection: dict[str, object] = {}
    for section in _PYPROJECT_POLICY_SECTIONS:
        value: object = document
        for component in section:
            if not isinstance(value, dict) or component not in value:
                value = None
                break
            value = value[component]
        if value is not None:
            projection[".".join(section)] = value
    return projection


def _ini_policy_projection(payload: bytes | None) -> object:
    if payload is None:
        return {}
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(payload.decode("utf-8"))
    except (UnicodeDecodeError, configparser.Error):
        return "invalid-policy-document"
    return {
        section.lower(): dict(parser.items(section))
        for section in parser.sections()
        if _recognized_ini_policy_section(section)
    }


def _section_policy_changed(relative: str, base: Snapshot, head: Snapshot) -> bool:
    base_payload = base.bytes_or_none(relative)
    head_payload = head.bytes_or_none(relative)
    if relative == "pyproject.toml":
        return _toml_policy_projection(base_payload) != _toml_policy_projection(head_payload)
    if relative in {"setup.cfg", "tox.ini"}:
        return _ini_policy_projection(base_payload) != _ini_policy_projection(head_payload)
    return False


def _policy_projection(relative: str, payload: bytes | None) -> object:
    if relative == "pyproject.toml":
        return _toml_policy_projection(payload)
    if relative in {"setup.cfg", "tox.ini"}:
        return _ini_policy_projection(payload)
    return None


def _is_policy_path(
    relative: str,
    source_lock_paths: frozenset[str],
    *,
    base: Snapshot,
    head: Snapshot,
    additional_policy_paths: frozenset[str] = frozenset(),
) -> bool:
    return (
        relative in GOVERNED_POLICY_PATHS_V1
        or relative in additional_policy_paths
        or relative in source_lock_paths
        or _section_policy_changed(relative, base, head)
    )


def _governed_path(
    relative: str,
    source_lock_paths: frozenset[str],
    *,
    base: Snapshot,
    head: Snapshot,
    additional_policy_paths: frozenset[str] = frozenset(),
) -> bool:
    path = PurePosixPath(relative)
    return path.suffix in _PYTHON_SUFFIXES or _is_policy_path(
        relative,
        source_lock_paths,
        base=base,
        head=head,
        additional_policy_paths=additional_policy_paths,
    )


def _range_paths(repository: Path, merge_base: str, head: str) -> tuple[str, ...]:
    paths = _git(repository, ["diff", "--name-only", "--no-renames", "-z", merge_base, head]).stdout.split("\0")
    return tuple(sorted({path for path in paths if path}))


def _range_statuses(repository: Path, base: str, head: str) -> dict[str, str]:
    tokens = _git(repository, ["diff", "--name-status", "--no-renames", "-z", base, head]).stdout.split("\0")
    statuses: dict[str, str] = {}
    for index in range(0, len(tokens) - 1, 2):
        status, path = tokens[index : index + 2]
        if status and path:
            statuses[path] = status
    return dict(sorted(statuses.items()))


def _entry_identity(entry: TreeEntry) -> tuple[str, str, str]:
    return entry.object_type, entry.git_mode, entry.object_id


def _canonical_exact_renames(
    base: Snapshot,
    head: Snapshot,
    statuses: dict[str, str],
) -> tuple[ExactRename, ...]:
    deleted = _entries_with_status(base, statuses, "D")
    added = _entries_with_status(head, statuses, "A")
    facts: list[ExactRename] = []
    for new_path, new_entry in added.items():
        if new_entry is None:
            continue
        disposition = _rename_disposition(base, deleted, added, new_entry)
        if disposition is None:
            continue
        old_path, kind = disposition
        facts.append(ExactRename(old_path, new_path, new_entry.object_id, new_entry.git_mode, kind))
    return tuple(sorted(facts, key=lambda item: (item.old_path, item.new_path, item.disposition)))


def _entries_with_status(
    snapshot: Snapshot,
    statuses: dict[str, str],
    expected_status: str,
) -> dict[str, TreeEntry | None]:
    return {path: snapshot.entry_or_none(path) for path, status in statuses.items() if status == expected_status}


def _matching_entries(
    entries: dict[str, TreeEntry | None],
    candidate: TreeEntry,
) -> list[tuple[str, TreeEntry]]:
    identity = _entry_identity(candidate)
    return [
        (path, entry) for path, entry in entries.items() if entry is not None and _entry_identity(entry) == identity
    ]


def _rename_disposition(
    base: Snapshot,
    deleted: dict[str, TreeEntry | None],
    added: dict[str, TreeEntry | None],
    new_entry: TreeEntry,
) -> tuple[str, Literal["exact_rename", "copy", "ambiguous"]] | None:
    deleted_matches = _matching_entries(deleted, new_entry)
    all_base_matches = _matching_entries(dict(base.entries), new_entry)
    same_added_count = len(_matching_entries(added, new_entry))
    if len(deleted_matches) == 1 and same_added_count == 1:
        return deleted_matches[0][0], "exact_rename"
    if not deleted_matches and len(all_base_matches) == 1:
        return all_base_matches[0][0], "copy"
    matches = deleted_matches or all_base_matches
    if not matches:
        return None
    return min(path for path, _entry in matches), "ambiguous"


def _source_manifest_digest(snapshot: Snapshot) -> str:
    manifest = [
        {
            "blob_sha": entry.object_id,
            "git_mode": entry.git_mode,
            "object_type": entry.object_type,
            "path": entry.path,
            "content_digest": sha256_bytes(snapshot.bytes_or_none(entry.path) or b""),
        }
        for entry in sorted(snapshot.entries.values(), key=lambda item: item.path)
    ]
    return _canonical_json_digest(manifest)


def _unknown_range(
    reason: str,
    diagnostics: str,
    *,
    candidates: tuple[str, ...] = (),
    candidate_identities: tuple[tuple[str, str], ...] = (),
) -> ScopeResolution:
    return ScopeResolution(
        status="UNKNOWN",
        reason=reason,
        selected_paths=(),
        assurance_kind="range_preview",
        effective_assurance_kind="range_preview",
        ci_exit_code=1,
        diagnostics=diagnostics,
        materialized=False,
        merge_base_candidates=candidates,
        merge_base_candidate_identities=candidate_identities,
        merge_base_candidate_digest=_canonical_json_digest(candidate_identities),
    )


def _candidate_identities(repository: Path, candidates: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    identities: list[tuple[str, str]] = []
    for commit in candidates:
        try:
            tree = _resolve_tree(repository, commit)
        except GitResolutionError:
            tree = ""
        identities.append((commit, tree))
    return tuple(sorted(identities))


def _build_policy_bundle(
    repository: Path,
    target_commit: str,
    source_lock_paths: frozenset[str],
    additional_policy_paths: frozenset[str] = frozenset(),
) -> PolicyBundle:
    target_tree = _resolve_tree(repository, target_commit)
    entries = {entry.path: entry for entry in _tree_entries(repository, target_commit)}
    with ExitStack() as cleanup:
        policy_root = Path(tempfile.mkdtemp(prefix=f"specfact-policy-{target_commit[:12]}-"))
        cleanup.callback(shutil.rmtree, policy_root, ignore_errors=True)
        manifest: list[dict[str, object]] = []
        candidate_paths = sorted(
            {
                *GOVERNED_POLICY_PATHS_V1,
                *source_lock_paths,
                *additional_policy_paths,
                "pyproject.toml",
                "setup.cfg",
                "tox.ini",
            }
        )
        selected_paths: list[str] = []
        for relative in candidate_paths:
            entry = entries.get(relative)
            if entry is None:
                continue
            payload = (
                _git_bytes(repository, ["cat-file", "blob", entry.object_id]) if entry.object_type == "blob" else b""
            )
            projection = _policy_projection(relative, payload)
            if projection == "invalid-policy-document":
                raise PolicyResolutionError(f"Unable to parse target-tip policy input: {relative}")
            is_section_policy = relative in {"pyproject.toml", "setup.cfg", "tox.ini"}
            if is_section_policy and not projection:
                continue
            if entry.object_type != "blob" or entry.git_mode not in _REGULAR_GIT_MODES:
                raise PolicyResolutionError(f"Target-tip policy input is not a regular Git blob: {relative}")
            destination = _safe_snapshot_path(policy_root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            destination.chmod(0o444)
            selected_paths.append(relative)
            manifest.append(
                {
                    "blob_sha": entry.object_id,
                    "content_digest": sha256_bytes(payload),
                    "git_mode": entry.git_mode,
                    "object_type": entry.object_type,
                    "path": relative,
                    "sections": projection,
                }
            )
        result = PolicyBundle(
            root=policy_root,
            source_commit=target_commit,
            source_tree=target_tree,
            paths=tuple(selected_paths),
            digest=_canonical_json_digest(manifest),
        )
        cleanup.pop_all()
        return result


def _candidate_policy_evidence(
    selected_paths: tuple[str, ...],
    source_lock_paths: frozenset[str],
    base: Snapshot,
    head: Snapshot,
    statuses: dict[str, str],
    additional_policy_paths: frozenset[str] = frozenset(),
) -> tuple[tuple[str, ...], str, str]:
    policy_paths = tuple(
        path
        for path in selected_paths
        if _is_policy_path(
            path,
            source_lock_paths,
            base=base,
            head=head,
            additional_policy_paths=additional_policy_paths,
        )
    )
    manifest = [
        {
            "base": base.entry_or_none(path).__dict__ if base.entry_or_none(path) is not None else None,
            "base_sections": _policy_projection(path, base.bytes_or_none(path)),
            "head": head.entry_or_none(path).__dict__ if head.entry_or_none(path) is not None else None,
            "head_sections": _policy_projection(path, head.bytes_or_none(path)),
            "path": path,
            "status": statuses.get(path, ""),
        }
        for path in policy_paths
    ]
    manifest_digest = _canonical_json_digest(manifest)
    return policy_paths, manifest_digest, _canonical_json_digest({"policy_manifest_digest": manifest_digest})


def _selected_policy_payload(
    target_root: Path,
    signed_module_root: Path,
    relative: str,
    destination: Path,
) -> PolicyPayloadIdentity:
    target_path = target_root / relative
    fallback_path = signed_module_root / relative
    source = target_path if target_path.exists() else fallback_path
    identity_kind: Literal["git_blob", "signed_module_payload"] = (
        "git_blob" if source == target_path else "signed_module_payload"
    )
    if not source.exists():
        raise PolicyResolutionError(f"Semgrep policy is absent from target tip and signed module: {relative}")
    try:
        payload = _stable_regular_bytes(source, max_size=16 * 1024 * 1024)
    except GitResolutionError as exc:
        raise PolicyResolutionError(str(exc)) from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    destination.chmod(0o444)
    return PolicyPayloadIdentity(
        identity_kind=identity_kind,
        source_path=str(source),
        content_digest=sha256_bytes(payload),
        materialized_path=destination,
    )


@require(lambda target_root: target_root.is_dir(), "target root must be an existing directory")
@require(lambda signed_module_root: signed_module_root.is_dir(), "signed module root must be an existing directory")
@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def resolve_semgrep_bundle(target_root: Path, *, signed_module_root: Path) -> SemgrepBundle:
    """Seal the target-tip or signed-module Semgrep policies into one explicit bundle."""

    bundle_root = Path(tempfile.mkdtemp(prefix="specfact-semgrep-policy-"))
    try:
        clean = _selected_policy_payload(
            target_root,
            signed_module_root,
            ".semgrep/clean_code.yaml",
            bundle_root / ".semgrep/clean_code.yaml",
        )
        ai_bloat = _selected_policy_payload(
            target_root,
            signed_module_root,
            "resources/semgrep-rules/ai-bloat.yaml",
            bundle_root / "resources/semgrep-rules/ai-bloat.yaml",
        )
    except PolicyResolutionError as exc:
        unavailable = PolicyPayloadIdentity("unavailable", "", "", bundle_root)
        return SemgrepBundle("UNKNOWN", bundle_root, unavailable, unavailable, "", str(exc))
    projection = [
        {
            "content_digest": identity.content_digest,
            "identity_kind": identity.identity_kind,
            "logical_path": logical_path,
            "source_path": identity.source_path,
        }
        for logical_path, identity in (
            (".semgrep/clean_code.yaml", clean),
            ("resources/semgrep-rules/ai-bloat.yaml", ai_bloat),
        )
    ]
    return SemgrepBundle("PASS", bundle_root, clean, ai_bloat, _canonical_json_digest(projection))


def _policy_candidate_payloads(root: Path, source_order: tuple[str, ...]) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    for relative in source_order:
        candidate = root / relative
        if not os.path.lexists(candidate):
            continue
        try:
            payloads[relative] = _stable_regular_bytes(candidate, max_size=16 * 1024 * 1024)
        except GitResolutionError as exc:
            raise PolicyResolutionError(f"Unsafe policy source {relative}: {exc}") from exc
    return payloads


def _policy_manifest_digest(payloads: dict[str, bytes], source_order: tuple[str, ...]) -> str:
    return _canonical_json_digest(
        [
            {"path": path, "content_digest": sha256_bytes(payloads[path]), "precedence": source_order.index(path)}
            for path in source_order
            if path in payloads
        ]
    )


def _unknown_located_policy(
    loader_version: str,
    source_order: tuple[str, ...],
    reason: str,
    *,
    payloads: dict[str, bytes] | None = None,
) -> LocatedPolicy:
    return LocatedPolicy(
        status="UNKNOWN",
        selected_path="",
        selected_section="",
        loader_version=loader_version,
        ignored_paths=tuple(payloads or {}),
        selection_reason="unknown",
        source_order=source_order,
        manifest_digest=_policy_manifest_digest(payloads or {}, source_order),
        reason=reason,
    )


def _parsed_ini_sections(payload: bytes, relative: str) -> frozenset[str]:
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(payload.decode("utf-8"))
    except (UnicodeDecodeError, configparser.Error) as exc:
        raise PolicyResolutionError(f"Unable to parse {relative}: {exc}") from exc
    return frozenset(section.lower() for section in parser.sections())


def _pytest_pyproject_section(payload: bytes) -> tuple[str, bool]:
    try:
        document = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise PolicyResolutionError(f"Unable to parse pyproject.toml: {exc}") from exc
    tool = document.get("tool", {})
    pytest_table = tool.get("pytest") if isinstance(tool, dict) else None
    if pytest_table is None:
        return "", True
    if not isinstance(pytest_table, dict):
        raise PolicyResolutionError("pyproject.toml tool.pytest must be a table.")
    has_legacy = "ini_options" in pytest_table
    has_native = any(key != "ini_options" for key in pytest_table)
    if has_legacy and has_native:
        raise PolicyResolutionError("pyproject.toml contains both native tool.pytest and legacy ini_options values.")
    return ("tool.pytest.ini_options" if has_legacy else "tool.pytest"), False


def _pytest_policy_matches(payloads: dict[str, bytes]) -> tuple[dict[str, tuple[str, str]], bool]:
    matches: dict[str, tuple[str, str]] = {}
    for relative in ("pytest.toml", ".pytest.toml", "pytest.ini", ".pytest.ini"):
        if relative in payloads:
            matches[relative] = ("empty-or-native", "present_primary_source")
    bare_pyproject = _append_pytest_pyproject_match(payloads, matches)
    _append_pytest_ini_matches(payloads, matches)
    return matches, bare_pyproject


def _append_pytest_pyproject_match(
    payloads: dict[str, bytes],
    matches: dict[str, tuple[str, str]],
) -> bool:
    if "pyproject.toml" not in payloads:
        return False
    section, bare_pyproject = _pytest_pyproject_section(payloads["pyproject.toml"])
    if section:
        matches["pyproject.toml"] = (section, "table_match")
    return bare_pyproject


def _append_pytest_ini_matches(
    payloads: dict[str, bytes],
    matches: dict[str, tuple[str, str]],
) -> None:
    for relative, section in (("tox.ini", "pytest"), ("setup.cfg", "tool:pytest")):
        if relative in payloads and section in _parsed_ini_sections(payloads[relative], relative):
            matches[relative] = (section, "section_match")


def _selected_pytest_policy(
    source_order: tuple[str, ...],
    matches: dict[str, tuple[str, str]],
    bare_pyproject: bool,
) -> tuple[str, str, str]:
    selected = next((path for path in source_order if path in matches), "")
    if selected:
        return selected, matches[selected][0], matches[selected][1]
    if bare_pyproject:
        return "pyproject.toml", "", "bare_pyproject_fallback"
    return "", "", "pytest-default-v1"


@require(lambda root: root.is_dir(), "policy root must be an existing directory")
@ensure(lambda result: result.loader_version == "9.0.3")
def resolve_pytest_policy(root: Path, *, expected_version: str) -> LocatedPolicy:
    """Select one logical pytest policy using the frozen pytest 9.0.3 locator."""

    source_order = (
        "pytest.toml",
        ".pytest.toml",
        "pytest.ini",
        ".pytest.ini",
        "pyproject.toml",
        "tox.ini",
        "setup.cfg",
    )
    if expected_version != "9.0.3":
        return _unknown_located_policy("9.0.3", source_order, "pytest loader/profile version drift")
    payloads: dict[str, bytes] = {}
    try:
        payloads = _policy_candidate_payloads(root, source_order)
        matches, bare_pyproject = _pytest_policy_matches(payloads)
    except PolicyResolutionError as exc:
        return _unknown_located_policy("9.0.3", source_order, str(exc), payloads=payloads)
    selected, selected_section, selection_reason = _selected_pytest_policy(source_order, matches, bare_pyproject)
    return LocatedPolicy(
        status="PASS",
        selected_path=selected,
        selected_section=selected_section,
        loader_version="9.0.3",
        ignored_paths=tuple(path for path in source_order if path in payloads and path != selected),
        selection_reason=selection_reason,
        source_order=source_order,
        manifest_digest=_policy_manifest_digest(payloads, source_order),
    )


def _coverage_applicable(relative: str, payload: bytes) -> tuple[bool, str]:
    if relative == ".coveragerc.toml":
        try:
            document = tomllib.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise PolicyResolutionError(f"Unable to parse {relative}: {exc}") from exc
        return bool(document), "run"
    if relative == "pyproject.toml":
        try:
            document = tomllib.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise PolicyResolutionError(f"Unable to parse {relative}: {exc}") from exc
        tool = document.get("tool", {})
        return isinstance(tool, dict) and isinstance(tool.get("coverage"), dict), "tool.coverage"
    sections = _parsed_ini_sections(payload, relative)
    expected_prefix = "run" if relative == ".coveragerc" else "coverage:"
    return any(
        section == expected_prefix or section.startswith(expected_prefix) for section in sections
    ), expected_prefix


@require(lambda root: root.is_dir(), "policy root must be an existing directory")
@ensure(lambda result: result.loader_version == "7.15.4")
def resolve_coverage_policy(root: Path, *, expected_version: str) -> LocatedPolicy:
    """Select one logical Coverage policy using the frozen 7.15.4 locator."""

    source_order = (".coveragerc", ".coveragerc.toml", "setup.cfg", "tox.ini", "pyproject.toml")
    if expected_version != "7.15.4":
        return _unknown_located_policy("7.15.4", source_order, "Coverage loader/profile version drift")
    payloads: dict[str, bytes] = {}
    try:
        payloads = _policy_candidate_payloads(root, source_order)
        matches = {
            path: section
            for path in source_order
            if path in payloads and (applicability := _coverage_applicable(path, payloads[path]))[0]
            for section in (applicability[1],)
        }
    except PolicyResolutionError as exc:
        return _unknown_located_policy("7.15.4", source_order, str(exc), payloads=payloads)
    selected = next((path for path in source_order if path in matches), "")
    return LocatedPolicy(
        status="PASS",
        selected_path=selected,
        selected_section=matches.get(selected, ""),
        loader_version="7.15.4",
        ignored_paths=tuple(path for path in source_order if path in payloads and path != selected),
        selection_reason="section_match" if selected else "coverage-default-v1",
        source_order=source_order,
        manifest_digest=_policy_manifest_digest(payloads, source_order),
    )


def _ruff_values(payload: bytes, relative: str, *, pyproject_primary: bool) -> dict[str, object] | None:
    try:
        document = tomllib.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise PolicyResolutionError(f"Unable to parse Ruff source {relative}: {exc}") from exc
    if pyproject_primary:
        tool = document.get("tool", {})
        if not isinstance(tool, dict) or "ruff" not in tool:
            return None
        values = tool["ruff"]
    else:
        values = document
    if not isinstance(values, dict):
        raise PolicyResolutionError(f"Ruff source {relative} must resolve to a table.")
    extend = values.get("extend")
    if extend is not None and not isinstance(extend, str):
        raise PolicyResolutionError(f"Ruff source {relative} has a non-string extend value.")
    return cast(dict[str, object], values)


def _bounded_relative_path(base: PurePosixPath, value: str) -> PurePosixPath:
    candidate = base / PurePosixPath(value)
    if PurePosixPath(value).is_absolute() or ".." in candidate.parts:
        raise PolicyResolutionError(f"Policy reference escapes the target root: {value}")
    return candidate


def _reject_symlink_components(root: Path, relative: PurePosixPath) -> None:
    current = root
    for component in relative.parts:
        current /= component
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise PolicyResolutionError(f"Policy reference is missing: {relative.as_posix()}") from exc
        if stat.S_ISLNK(mode):
            raise PolicyResolutionError(f"Policy reference contains a symlink: {relative.as_posix()}")


def _merge_policy_values(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        if key == "extend":
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_policy_values(cast(dict[str, object], merged[key]), cast(dict[str, object], value))
        else:
            merged[key] = value
    return merged


def _resolve_ruff_graph(root: Path, selected: str) -> _RuffGraph:
    visiting: set[str] = set()
    visited: dict[str, tuple[bytes, dict[str, object], str | None]] = {}

    def visit(relative: PurePosixPath, *, pyproject_primary: bool = False) -> dict[str, object]:
        canonical = relative.as_posix()
        if canonical in visiting:
            raise PolicyResolutionError(f"Ruff extend graph contains a cycle at {canonical}")
        if canonical in visited:
            return visited[canonical][1]
        if len(visited) >= 32:
            raise PolicyResolutionError("Ruff extend graph exceeds the signed 32-node bound.")
        _reject_symlink_components(root, relative)
        try:
            payload = _stable_regular_bytes(root / relative, max_size=16 * 1024 * 1024)
        except GitResolutionError as exc:
            raise PolicyResolutionError(str(exc)) from exc
        values = _ruff_values(payload, canonical, pyproject_primary=pyproject_primary)
        if values is None:
            raise PolicyResolutionError(f"Selected Ruff pyproject source lacks tool.ruff: {canonical}")
        visiting.add(canonical)
        extend = cast(str | None, values.get("extend"))
        effective: dict[str, object] = {}
        if extend is not None:
            child = _bounded_relative_path(relative.parent, extend)
            effective = visit(child)
        visiting.remove(canonical)
        effective = _merge_policy_values(effective, values)
        visited[canonical] = (payload, effective, extend)
        return effective

    values = visit(PurePosixPath(selected), pyproject_primary=selected == "pyproject.toml")
    bundle_root = Path(tempfile.mkdtemp(prefix="specfact-ruff-policy-"))
    manifest: list[dict[str, object]] = []
    for relative, (payload, _effective, extend) in sorted(visited.items()):
        destination = _safe_snapshot_path(bundle_root, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        destination.chmod(0o444)
        manifest.append(
            {
                "content_digest": sha256_bytes(payload),
                "extend": extend,
                "path": relative,
                "materialized_digest": sha256_bytes(destination.read_bytes()),
            }
        )
    paths = tuple(sorted(visited))
    return _RuffGraph(paths, _canonical_json_digest(manifest), bundle_root, values)


def _unknown_ruff(reason: str, *, selected_path: str | None = None) -> RuffPolicy:
    return RuffPolicy("UNKNOWN", selected_path, False, "0.15.12", (), "", None, {}, reason)


@require(lambda root: root.is_dir(), "policy root must be an existing directory")
@ensure(lambda result: result.loader_version == "0.15.12")
def resolve_ruff_policy(root: Path, *, expected_version: str) -> RuffPolicy:
    """Select zero or one Ruff source and seal its bounded transitive extend graph."""

    if expected_version != "0.15.12":
        return _unknown_ruff("ruff_loader_profile_drift")
    sources: list[str] = []
    try:
        for relative in (".ruff.toml", "ruff.toml"):
            if os.path.lexists(root / relative):
                payload = _stable_regular_bytes(root / relative, max_size=16 * 1024 * 1024)
                _ruff_values(payload, relative, pyproject_primary=False)
                sources.append(relative)
        if os.path.lexists(root / "pyproject.toml"):
            payload = _stable_regular_bytes(root / "pyproject.toml", max_size=16 * 1024 * 1024)
            if _ruff_values(payload, "pyproject.toml", pyproject_primary=True) is not None:
                sources.append("pyproject.toml")
    except (GitResolutionError, PolicyResolutionError) as exc:
        return _unknown_ruff(str(exc))
    if len(sources) > 1:
        return _unknown_ruff("ruff_config_ambiguous")
    if not sources:
        return RuffPolicy("PASS", None, True, "0.15.12", (), _canonical_json_digest([]), None, {})
    selected = sources[0]
    try:
        graph = _resolve_ruff_graph(root, selected)
    except PolicyResolutionError as exc:
        return _unknown_ruff(str(exc), selected_path=selected)
    return RuffPolicy(
        "PASS",
        selected,
        False,
        "0.15.12",
        graph.paths,
        graph.digest,
        graph.bundle_root,
        graph.values,
    )


def _basedpyright_values(payload: bytes, relative: str, *, pyproject_primary: bool) -> dict[str, object] | None:
    try:
        if pyproject_primary:
            document = tomllib.loads(payload.decode("utf-8"))
            tool = document.get("tool", {})
            if not isinstance(tool, dict):
                return None
            pyright = tool.get("pyright")
            basedpyright = tool.get("basedpyright")
            if pyright is not None and basedpyright is not None:
                raise PolicyResolutionError("pyproject.toml contains both tool.pyright and tool.basedpyright.")
            values = basedpyright if basedpyright is not None else pyright
            if values is None:
                return None
        else:
            values = json.loads(payload)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
        raise PolicyResolutionError(f"Unable to parse basedpyright source {relative}: {exc}") from exc
    if not isinstance(values, dict):
        raise PolicyResolutionError(f"basedpyright source {relative} must resolve to an object.")
    for key in ("extends", "baselineFile"):
        value = values.get(key)
        if value is not None and not isinstance(value, str):
            raise PolicyResolutionError(f"basedpyright {key} in {relative} must be a string.")
    return cast(dict[str, object], values)


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PolicyResolutionError(f"basedpyright {key} must be an array of strings.")
    return tuple(cast(list[str], value))


def _object_tuple(values: dict[str, object], key: str) -> tuple[object, ...]:
    value = values.get(key, [])
    if not isinstance(value, list):
        raise PolicyResolutionError(f"basedpyright {key} must be an array.")
    return tuple(cast(list[object], value))


def _resolve_basedpyright_graph(root: Path, selected: str) -> tuple[dict[str, object], tuple[str, ...], str, Path]:
    visiting: set[str] = set()
    payloads: dict[str, bytes] = {}
    effective_by_path: dict[str, dict[str, object]] = {}
    edges: list[tuple[str, str, str]] = []

    def visit(relative: PurePosixPath, *, pyproject_primary: bool = False) -> dict[str, object]:
        canonical = relative.as_posix()
        if canonical in visiting:
            raise PolicyResolutionError(f"basedpyright extends graph contains a cycle at {canonical}")
        if canonical in effective_by_path:
            return effective_by_path[canonical]
        if len(payloads) >= 32:
            raise PolicyResolutionError("basedpyright reference graph exceeds the signed 32-node bound.")
        _reject_symlink_components(root, relative)
        try:
            payload = _stable_regular_bytes(root / relative, max_size=16 * 1024 * 1024)
        except GitResolutionError as exc:
            raise PolicyResolutionError(str(exc)) from exc
        values = _basedpyright_values(payload, canonical, pyproject_primary=pyproject_primary)
        if values is None:
            raise PolicyResolutionError(f"Selected basedpyright pyproject lacks a supported primary table: {canonical}")
        payloads[canonical] = payload
        visiting.add(canonical)
        effective: dict[str, object] = {}
        extends = cast(str | None, values.get("extends"))
        if extends is not None:
            child = _bounded_relative_path(relative.parent, extends)
            edges.append((canonical, "extends", child.as_posix()))
            effective = visit(child)
        baseline = cast(str | None, values.get("baselineFile"))
        if baseline is not None:
            baseline_path = _bounded_relative_path(relative.parent, baseline)
            _reject_symlink_components(root, baseline_path)
            try:
                baseline_payload = _stable_regular_bytes(root / baseline_path, max_size=64 * 1024 * 1024)
                parsed_baseline = json.loads(baseline_payload)
            except (GitResolutionError, json.JSONDecodeError) as exc:
                raise PolicyResolutionError(f"Unable to load basedpyright baseline {baseline_path}: {exc}") from exc
            if not isinstance(parsed_baseline, dict):
                raise PolicyResolutionError(f"basedpyright baseline must be an object: {baseline_path}")
            payloads[baseline_path.as_posix()] = baseline_payload
            edges.append((canonical, "baselineFile", baseline_path.as_posix()))
        visiting.remove(canonical)
        effective = _merge_policy_values(effective, values)
        effective_by_path[canonical] = effective
        return effective

    values = visit(PurePosixPath(selected), pyproject_primary=selected == "pyproject.toml")
    bundle_root = Path(tempfile.mkdtemp(prefix="specfact-basedpyright-policy-"))
    manifest: list[dict[str, object]] = []
    for relative, payload in sorted(payloads.items()):
        destination = _safe_snapshot_path(bundle_root, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        destination.chmod(0o444)
        manifest.append({"path": relative, "content_digest": sha256_bytes(payload)})
    digest = _canonical_json_digest({"edges": sorted(edges), "nodes": manifest})
    return values, tuple(sorted(payloads)), digest, bundle_root


def _unknown_basedpyright(reason: str) -> BasedPyrightPolicy:
    return BasedPyrightPolicy(status="UNKNOWN", reason=reason)


@require(lambda root: root.is_dir(), "policy root must be an existing directory")
@ensure(lambda result: result.loader_version == "1.39.10")
def resolve_basedpyright_policy(root: Path, *, expected_version: str) -> BasedPyrightPolicy:
    """Resolve one basedpyright primary plus bounded extends/baseline references."""

    if expected_version != "1.39.10":
        return _unknown_basedpyright("basedpyright_loader_profile_drift")
    primaries: list[str] = []
    try:
        if os.path.lexists(root / "pyrightconfig.json"):
            _basedpyright_values(
                _stable_regular_bytes(root / "pyrightconfig.json", max_size=16 * 1024 * 1024),
                "pyrightconfig.json",
                pyproject_primary=False,
            )
            primaries.append("pyrightconfig.json")
        if os.path.lexists(root / "pyproject.toml"):
            payload = _stable_regular_bytes(root / "pyproject.toml", max_size=16 * 1024 * 1024)
            if _basedpyright_values(payload, "pyproject.toml", pyproject_primary=True) is not None:
                primaries.append("pyproject.toml")
    except (GitResolutionError, PolicyResolutionError) as exc:
        return _unknown_basedpyright(str(exc))
    if len(primaries) > 1:
        return _unknown_basedpyright("basedpyright_config_ambiguous")
    if not primaries:
        return BasedPyrightPolicy(graph_digest=_canonical_json_digest([]))
    selected = primaries[0]
    try:
        values, paths, digest, bundle_root = _resolve_basedpyright_graph(root, selected)
        return BasedPyrightPolicy(
            include=_string_tuple(values, "include"),
            exclude=_string_tuple(values, "exclude"),
            ignore=_string_tuple(values, "ignore"),
            strict=_string_tuple(values, "strict"),
            executionEnvironments=_object_tuple(values, "executionEnvironments"),
            baseline_file=cast(str | None, values.get("baselineFile")),
            selected_path=selected,
            reference_paths=paths,
            graph_digest=digest,
            bundle_root=bundle_root,
            values=values,
            identity=digest,
            identity_kind="config_graph",
        )
    except PolicyResolutionError as exc:
        return _unknown_basedpyright(str(exc))


_PYLINT_CLEARED_OPTIONS = (
    "ignore",
    "ignore-patterns",
    "ignore-paths",
    "ignored-modules",
    "ignored-classes",
    "generated-members",
    "signature-mutators",
    "contextmanager-decorators",
    "ignored-checks-for-mixins",
    "mixin-class-rgx",
)
_PYLINT_FALSE_OPTIONS = ("ignore-none", "ignore-on-opaque-inference", "ignore-mixin-members")


def _flatten_policy_mapping(value: dict[str, object]) -> dict[str, object]:
    flattened: dict[str, object] = {}
    for key, item in value.items():
        normalized = key.lower().replace("_", "-")
        if isinstance(item, dict):
            flattened.update(_flatten_policy_mapping(cast(dict[str, object], item)))
        else:
            flattened[normalized] = item
    return flattened


def _pylint_ini_values(payload: bytes, relative: str) -> dict[str, object]:
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(payload.decode("utf-8"))
    except (UnicodeDecodeError, configparser.Error) as exc:
        raise PolicyResolutionError(f"Unable to parse Pylint source {relative}: {exc}") from exc
    return {
        key.lower().replace("_", "-"): value for section in parser.sections() for key, value in parser.items(section)
    }


def _pylint_values(payload: bytes, relative: str) -> dict[str, object]:
    if relative.endswith(".toml"):
        try:
            document = tomllib.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError):
            return _pylint_ini_values(payload, relative)
        tool = document.get("tool", {})
        if isinstance(tool, dict) and isinstance(tool.get("pylint"), dict):
            return _flatten_policy_mapping(cast(dict[str, object], tool["pylint"]))
        if relative == "pyproject.toml" and isinstance(document.get("MAIN"), dict):
            return _flatten_policy_mapping(cast(dict[str, object], document))
        if relative != "pyproject.toml":
            return _flatten_policy_mapping(cast(dict[str, object], document))
        raise PolicyResolutionError("pyproject.toml lacks the pinned tool.pylint table.")
    return _pylint_ini_values(payload, relative)


def _pylint_source_is_applicable(root: Path, relative: str) -> bool:
    if relative not in {"pyproject.toml", "setup.cfg", "tox.ini"}:
        return True
    payload = _stable_regular_bytes(root / relative, max_size=16 * 1024 * 1024)
    if relative == "pyproject.toml":
        try:
            document = tomllib.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise PolicyResolutionError(f"Unable to parse Pylint source {relative}: {exc}") from exc
        tool = document.get("tool", {})
        return (isinstance(tool, dict) and isinstance(tool.get("pylint"), dict)) or isinstance(
            document.get("MAIN"), dict
        )
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(payload.decode("utf-8"))
    except (UnicodeDecodeError, configparser.Error) as exc:
        raise PolicyResolutionError(f"Unable to parse Pylint source {relative}: {exc}") from exc
    return any(section.lower() == "pylint" or section.lower().startswith("pylint.") for section in parser.sections())


def _pylint_projection(values: dict[str, object]) -> dict[str, object]:
    projection = dict(values)
    for option in _PYLINT_CLEARED_OPTIONS:
        projection[option] = ""
    for option in _PYLINT_FALSE_OPTIONS:
        projection[option] = False
    projection.update(
        {
            "confidence": "HIGH,CONTROL_FLOW,INFERENCE,INFERENCE_FAILURE,UNDEFINED",
            "errors-only": False,
            "from-stdin": False,
            "recursive": False,
        }
    )
    return projection


def _unknown_pylint(reason: str, selected_path: str | None = None) -> PylintPolicy:
    return PylintPolicy("UNKNOWN", selected_path, "4.0.7", _pylint_projection({}), "closed", "", reason)


@require(lambda root: root.is_dir(), "policy root must be an existing directory")
@ensure(lambda result: result.loader_version == "4.0.7")
def resolve_pylint_policy(root: Path, *, expected_version: str) -> PylintPolicy:
    """Select zero or one Pylint source and create the initial sealed projection."""

    source_order = (
        "pylintrc",
        ".pylintrc",
        "pylintrc.toml",
        ".pylintrc.toml",
        "pyproject.toml",
        "setup.cfg",
        "tox.ini",
    )
    if expected_version != "4.0.7":
        return _unknown_pylint("pylint_loader_profile_drift")
    present = [
        relative
        for relative in source_order
        if os.path.lexists(root / relative) and _pylint_source_is_applicable(root, relative)
    ]
    if len(present) > 1:
        return _unknown_pylint("pylint_config_ambiguous")
    if not present:
        return PylintPolicy(
            "PASS",
            None,
            "4.0.7",
            _pylint_projection({}),
            "closed",
            _canonical_json_digest([]),
        )
    selected = present[0]
    try:
        payload = _stable_regular_bytes(root / selected, max_size=16 * 1024 * 1024)
        values = _pylint_values(payload, selected)
    except (GitResolutionError, PolicyResolutionError) as exc:
        return _unknown_pylint(str(exc), selected)
    extension_options = (
        "init-hook",
        "load-plugins",
        "extension-pkg-allow-list",
        "extension-pkg-whitelist",
    )
    if any(str(values.get(option, "")).strip() for option in extension_options):
        return PylintPolicy(
            "UNKNOWN",
            selected,
            "4.0.7",
            _pylint_projection(values),
            "closed",
            sha256_bytes(payload),
            "pylint_extension_unsupported",
        )
    return PylintPolicy(
        "PASS",
        selected,
        "4.0.7",
        _pylint_projection(values),
        "closed",
        sha256_bytes(payload),
    )


def _toml_key(value: str) -> str:
    return (
        value if value and all(character.isalnum() or character in "_-" for character in value) else json.dumps(value)
    )


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list | tuple):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise PolicyResolutionError(f"Unsupported generated TOML value: {type(value).__name__}")


def _toml_lines(values: dict[str, object], prefix: tuple[str, ...] = ()) -> list[str]:
    lines = [
        f"{_toml_key(key)} = {_toml_value(value)}"
        for key, value in sorted(values.items())
        if not isinstance(value, dict) and value is not None
    ]
    for key, nested in sorted(values.items()):
        if not isinstance(nested, dict):
            continue
        section = (*prefix, key)
        if lines:
            lines.append("")
        lines.append("[" + ".".join(_toml_key(component) for component in section) + "]")
        lines.extend(_toml_lines(cast(dict[str, object], nested), section))
    return lines


def _materialized_projection(
    values: dict[str, object],
    *,
    prefix: str,
    format_kind: Literal["json", "toml"],
) -> tuple[Path, str]:
    root = Path(tempfile.mkdtemp(prefix=f"specfact-{prefix}-projection-"))
    canonical = json.dumps(values, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    if format_kind == "json":
        payload = json.dumps(values, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
        path = root / f"{prefix}.json"
    else:
        payload = ("\n".join(_toml_lines(values)) + "\n").encode()
        path = root / f"{prefix}.toml"
    path.write_bytes(payload)
    path.chmod(0o444)
    return path, sha256_bytes(canonical)


def _unknown_projection(reason: str, eligible_inputs: tuple[str, ...] = ()) -> PolicyProjection:
    return PolicyProjection("UNKNOWN", {}, (), None, "", eligible_inputs, reason=reason)


@require(lambda snapshot_root: snapshot_root.is_absolute(), "snapshot root must be absolute")
@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def project_ruff_policy(policy: RuffPolicy, *, snapshot_root: Path) -> PolicyProjection:
    """Remove path-sensitive Ruff controls and bind one snapshot-root projection."""

    if policy.status != "PASS":
        return _unknown_projection(policy.reason)
    values = dict(policy.values)
    lint = dict(cast(dict[str, object], values.get("lint", {})))
    for option in ("per-file-ignores", "extend-per-file-ignores"):
        lint[option] = {}
        values[option] = {}
    pycodestyle = dict(cast(dict[str, object], lint.get("pycodestyle", {})))
    pycodestyle["ignore-overlong-task-comments"] = False
    lint["pycodestyle"] = pycodestyle
    original_task_tags = list(cast(list[str], lint.get("task-tags", [])))
    values.update(
        {
            "lint": lint,
            "per-file-target-version": {},
            "namespace-packages": [],
            "src": [str(snapshot_root)],
            "fix": False,
            "fix-only": False,
        }
    )
    try:
        config_path, digest = _materialized_projection(values, prefix="ruff", format_kind="toml")
    except PolicyResolutionError as exc:
        return _unknown_projection(str(exc))
    argv = (
        ("--isolated", "--no-cache", "--no-force-exclude")
        if policy.isolated
        else (
            "--config",
            str(config_path),
            "--no-cache",
            "--no-force-exclude",
        )
    )
    return PolicyProjection(
        "PASS",
        values,
        argv,
        config_path,
        digest,
        (),
        evidence={"original_task_tags": original_task_tags},
    )


@require(lambda snapshot_root: snapshot_root.is_absolute(), "snapshot root must be absolute")
@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def project_basedpyright_policy(
    policy: BasedPyrightPolicy,
    *,
    snapshot_root: Path,
    eligible_inputs: tuple[str, ...],
    project_runtime_site_packages: str = "/opt/specfact/project-runtime/site-packages",
) -> PolicyProjection:
    """Flatten basedpyright policy without path-scoped suppression controls."""

    eligible = tuple(sorted(set(eligible_inputs)))
    if policy.status != "PASS":
        return _unknown_projection(policy.reason, eligible)
    execution_environments = policy.executionEnvironments or tuple(
        cast(list[object], policy.values.get("executionEnvironments", []))
    )
    strict = policy.strict or tuple(cast(list[str], policy.values.get("strict", [])))
    if strict or execution_environments:
        return _unknown_projection("basedpyright_path_scoped_policy_unsupported", eligible)
    governed_paths = policy.include + policy.exclude + policy.ignore
    if any(Path(path).is_absolute() or ".." in PurePosixPath(path).parts for path in governed_paths):
        return _unknown_projection("basedpyright_unbound_policy_path", eligible)
    logical_policy_digest = _canonical_json_digest(
        {
            "exclude": list(policy.exclude),
            "graph_digest": policy.graph_digest,
            "identity": policy.identity,
            "identity_kind": policy.identity_kind,
            "ignore": list(policy.ignore),
            "include": list(policy.include),
            "values": policy.values,
        }
    )
    values = dict(policy.values)
    for key in ("extends", "baselineFile", "executionEnvironments"):
        values.pop(key, None)
    include_values = [str(snapshot_root / PurePosixPath(path)) for path in eligible]
    values.update(
        {
            "include": include_values,
            "exclude": [],
            "extraPaths": [project_runtime_site_packages],
            "ignore": [],
            "strict": [],
            "venvPath": str(PurePosixPath(project_runtime_site_packages).parent),
            "venv": PurePosixPath(project_runtime_site_packages).name,
        }
    )
    config_path, digest = _materialized_projection(values, prefix="basedpyright", format_kind="json")
    return PolicyProjection(
        "PASS",
        values,
        ("--project", str(config_path)),
        config_path,
        digest,
        eligible,
        logical_policy_digest=logical_policy_digest,
    )


def _read_regular_context(path: Path, repository: Path) -> bytes:
    if not path.is_absolute():
        raise ContextResolutionError("PR context path must be absolute.")
    try:
        path_stat = path.lstat()
        resolved_path = path.resolve(strict=True)
    except OSError as exc:
        raise ContextResolutionError(f"Unable to inspect PR context: {exc}") from exc
    if not stat.S_ISREG(path_stat.st_mode) or resolved_path.is_relative_to(repository.resolve()):
        raise ContextResolutionError("PR context must be a regular file outside the checkout.")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ContextResolutionError(f"Unable to open PR context without following links: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > 1_048_576:
            raise ContextResolutionError("PR context is not a bounded regular file.")
        payload = b""
        while chunk := os.read(descriptor, 65_536):
            payload += chunk
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after or len(payload) != before.st_size:
        raise ContextResolutionError("PR context changed while it was being frozen.")
    return payload


def _stable_regular_bytes(path: Path, *, max_size: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise GitResolutionError(f"Unable to open index dependency without following links: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_size:
            raise GitResolutionError("Index dependency is not a bounded regular file.")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1_048_576):
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    payload = b"".join(chunks)
    if before_identity != after_identity or len(payload) != before.st_size:
        raise GitResolutionError("Index dependency changed during capture.")
    return payload


def _is_full_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(character in "0123456789abcdef" for character in value)


def _is_sha256_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 71 and value.startswith("sha256:")


def _decode_context(payload: bytes) -> dict[str, object]:
    try:
        parsed = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContextResolutionError(f"PR context is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(parsed, dict) or not all(isinstance(key, str) for key in parsed):
        raise ContextResolutionError("PR context must be a JSON object with string keys.")
    return cast(dict[str, object], parsed)


def _validate_context_header(document: dict[str, object], request: ScopeRequest) -> None:
    required_strings = ("schema", "provider", "repository", "event", "target_ref", "head_ref")
    if not all(isinstance(document.get(field), str) and document[field] for field in required_strings):
        raise ContextResolutionError("PR context omits a required non-empty string field.")
    if document["schema"] != "github-actions-pr-v1" or document["provider"] != "github-actions":
        raise ContextResolutionError("PR context schema/provider is unsupported.")
    if request.repository_slug is not None and document["repository"] != request.repository_slug:
        raise ContextResolutionError("PR context repository identity does not match the request.")


def _validate_context_event(document: dict[str, object]) -> None:
    event = document["event"]
    if event not in {"pull_request", "merge_group"}:
        raise ContextResolutionError("PR context event is unsupported.")
    pull_request = document.get("pull_request")
    if event == "pull_request" and not (isinstance(pull_request, int) and pull_request > 0):
        raise ContextResolutionError("Pull-request context requires a positive pull_request identity.")


def _validate_context_git_identities(document: dict[str, object]) -> None:
    for context_field in ("target_commit", "head_commit"):
        if not _is_full_sha(document.get(context_field)):
            raise ContextResolutionError(f"PR context {context_field} must be a full lowercase commit SHA.")
    for context_field in ("target_tree", "head_tree"):
        if not _is_full_sha(document.get(context_field)):
            raise ContextResolutionError(f"PR context {context_field} must be a full lowercase tree SHA.")


def _validate_optional_digest(document: dict[str, object], field: str, *, prefix: str = "") -> None:
    value = document.get(field)
    if value is not None and not _is_sha256_digest(value):
        raise ContextResolutionError(f"PR context {prefix}{field} is not a canonical SHA-256 digest.")


def _validated_source_lock_records(runtime_document: dict[str, object]) -> list[dict[str, object]]:
    source_lock_paths = runtime_document.get("source_lock_paths", [])
    if not isinstance(source_lock_paths, list) or not all(isinstance(item, dict) for item in source_lock_paths):
        raise ContextResolutionError("PR context project_runtime.source_lock_paths must be lock records.")
    records = cast(list[dict[str, object]], source_lock_paths)
    paths = [item.get("path") for item in records]
    if not all(
        isinstance(path, str)
        and path
        and not PurePosixPath(path).is_absolute()
        and ".." not in PurePosixPath(path).parts
        for path in paths
    ):
        raise ContextResolutionError("PR context project_runtime.source_lock_paths must use safe relative paths.")
    if not all(
        _is_full_sha(item.get("blob_sha")) and _is_sha256_digest(item.get("content_sha256")) for item in records
    ):
        raise ContextResolutionError("PR context project_runtime.source_lock_paths identities are invalid.")
    if len(paths) != len(set(cast(list[str], paths))):
        raise ContextResolutionError("PR context project_runtime.source_lock_paths must not contain duplicates.")
    return records


def _validate_context_runtime(document: dict[str, object]) -> None:
    for context_field in ("project_runtime_descriptor_digest", "project_runtime_build_attestation_digest"):
        _validate_optional_digest(document, context_field)
    project_runtime = document.get("project_runtime")
    if project_runtime is None:
        return
    if not isinstance(project_runtime, dict):
        raise ContextResolutionError("PR context project_runtime must be an object when present.")
    runtime_document = cast(dict[str, object], project_runtime)
    for context_field in ("descriptor_digest", "build_attestation_digest"):
        _validate_optional_digest(runtime_document, context_field, prefix="project_runtime.")
    _validated_source_lock_records(runtime_document)


def _load_claimed_context(request: ScopeRequest) -> _ClaimedContext | None:
    if request.pr_context_file is None:
        return None
    payload = _read_regular_context(request.pr_context_file, request.repository)
    document = _decode_context(payload)
    _validate_context_header(document, request)
    _validate_context_event(document)
    _validate_context_git_identities(document)
    _validate_context_runtime(document)
    return _ClaimedContext(document=document, digest=sha256_bytes(payload))


def _context_source_lock_paths(context: _ClaimedContext | None) -> frozenset[str]:
    if context is None:
        return frozenset()
    project_runtime = context.document.get("project_runtime")
    if not isinstance(project_runtime, dict):
        return frozenset()
    records = cast(list[dict[str, object]], project_runtime.get("source_lock_paths", []))
    return frozenset(str(record["path"]) for record in records)


def _context_matches_range(context: _ClaimedContext, resolved: _ResolvedRange) -> bool:
    document = context.document
    return (
        document["target_commit"] == resolved.target_commit
        and document["head_commit"] == resolved.head_snapshot.commit
        and document["target_tree"] == resolved.target_tree
        and document["head_tree"] == resolved.head_snapshot.tree
    )


def _context_failure(reason: str, diagnostics: str, resolved: _ResolvedRange) -> ScopeResolution:
    candidate_identities = ((resolved.candidates[0], resolved.base_snapshot.tree),)
    return ScopeResolution(
        status="UNKNOWN",
        reason=reason,
        selected_paths=resolved.selected_paths,
        assurance_kind="range_preview",
        effective_assurance_kind="range_preview",
        ci_exit_code=1,
        diagnostics=diagnostics,
        base_snapshot=resolved.base_snapshot,
        head_snapshot=resolved.head_snapshot,
        materialized=True,
        merge_base_candidates=resolved.candidates,
        merge_base_candidate_identities=candidate_identities,
        merge_base_candidate_digest=_canonical_json_digest(candidate_identities),
        resolved_target_commit=resolved.target_commit,
        resolved_target_tree=resolved.target_tree,
        resolved_head_commit=resolved.head_snapshot.commit,
        resolved_head_tree=resolved.head_snapshot.tree,
    )


def _materialized_range(request: ScopeRequest) -> _ResolvedRange | ScopeResolution:
    claimed_context = _load_claimed_context(request)
    base = _resolve_commit(request.repository, cast(str, request.base_ref))
    head = _resolve_commit(request.repository, cast(str, request.head_ref))
    candidates = _best_merge_bases(request.repository, base, head)
    if len(candidates) != 1:
        identities = _candidate_identities(request.repository, candidates)
        return _unknown_range(
            "ambiguous_merge_base",
            f"Expected exactly one best merge base; observed {len(candidates)}.",
            candidates=candidates,
            candidate_identities=identities,
        )
    merge_base = candidates[0]
    with ExitStack() as cleanup:
        base_snapshot = _materialize_commit(request.repository, merge_base)
        cleanup.callback(shutil.rmtree, base_snapshot.root, ignore_errors=True)
        head_snapshot = _materialize_commit(request.repository, head)
        cleanup.callback(shutil.rmtree, head_snapshot.root, ignore_errors=True)
        source_locks = frozenset(PurePosixPath(path).as_posix() for path in request.project_runtime_source_lock_paths)
        source_locks |= _context_source_lock_paths(claimed_context)
        target_snapshot = base_snapshot if base == merge_base else _materialize_commit(request.repository, base)
        if target_snapshot is not base_snapshot:
            cleanup.callback(shutil.rmtree, target_snapshot.root, ignore_errors=True)
        ruff_policy = resolve_ruff_policy(target_snapshot.root, expected_version="0.15.12")
        if ruff_policy.bundle_root is not None:
            cleanup.callback(shutil.rmtree, ruff_policy.bundle_root, ignore_errors=True)
        if ruff_policy.status != "PASS":
            raise PolicyResolutionError(ruff_policy.reason)
        basedpyright_policy = resolve_basedpyright_policy(target_snapshot.root, expected_version="1.39.10")
        if basedpyright_policy.bundle_root is not None:
            cleanup.callback(shutil.rmtree, basedpyright_policy.bundle_root, ignore_errors=True)
        if basedpyright_policy.status != "PASS":
            raise PolicyResolutionError(basedpyright_policy.reason)
        additional_policy_paths = frozenset((*ruff_policy.closure_paths, *basedpyright_policy.reference_paths))
        selected = tuple(
            path
            for path in _range_paths(request.repository, merge_base, head)
            if _governed_path(
                path,
                source_locks,
                base=base_snapshot,
                head=head_snapshot,
                additional_policy_paths=additional_policy_paths,
            )
        )
        statuses = _range_statuses(request.repository, merge_base, head)
        renames = _canonical_exact_renames(base_snapshot, head_snapshot, statuses)
        policy_bundle = _build_policy_bundle(request.repository, base, source_locks, additional_policy_paths)
        cleanup.callback(shutil.rmtree, policy_bundle.root, ignore_errors=True)
        policy_paths, policy_manifest_digest, candidate_policy_change_digest = _candidate_policy_evidence(
            selected,
            source_locks,
            base_snapshot,
            head_snapshot,
            statuses,
            additional_policy_paths,
        )
        rename_projection = [
            {
                "blob_sha": item.blob_sha,
                "disposition": item.disposition,
                "git_mode": item.git_mode,
                "new_path": item.new_path,
                "old_path": item.old_path,
            }
            for item in renames
        ]
        result = _ResolvedRange(
            candidates,
            base,
            _resolve_tree(request.repository, base),
            base_snapshot,
            head_snapshot,
            selected,
            source_locks,
            statuses,
            renames,
            _canonical_json_digest(rename_projection),
            _source_manifest_digest(base_snapshot),
            _source_manifest_digest(head_snapshot),
            policy_bundle,
            policy_paths,
            policy_manifest_digest,
            candidate_policy_change_digest,
            claimed_context,
        )
        if target_snapshot is not base_snapshot:
            shutil.rmtree(target_snapshot.root, ignore_errors=True)
        if ruff_policy.bundle_root is not None:
            shutil.rmtree(ruff_policy.bundle_root, ignore_errors=True)
        if basedpyright_policy.bundle_root is not None:
            shutil.rmtree(basedpyright_policy.bundle_root, ignore_errors=True)
        cleanup.pop_all()
        return result


def _governed_range_manifests(
    resolved: _ResolvedRange,
) -> tuple[dict[str, InputIdentity], dict[str, InputIdentity]]:
    base_manifest: dict[str, InputIdentity] = {}
    head_manifest: dict[str, InputIdentity] = {}
    for path in resolved.selected_paths:
        base_identity = _input_identity(resolved.base_snapshot, path)
        head_identity = _input_identity(resolved.head_snapshot, path)
        if base_identity is not None:
            base_manifest[path] = base_identity
        if head_identity is not None:
            head_manifest[path] = head_identity
    return base_manifest, head_manifest


def _unsafe_manifest_path(
    base_manifest: dict[str, InputIdentity],
    head_manifest: dict[str, InputIdentity],
) -> str | None:
    for manifest in (base_manifest, head_manifest):
        for path, identity in sorted(manifest.items()):
            if identity.object_type != "blob" or identity.git_mode not in _REGULAR_GIT_MODES:
                return path
    return None


def _range_result(request: ScopeRequest, resolved: _ResolvedRange) -> ScopeResolution:
    manifests = _range_manifests_or_failure(resolved)
    if isinstance(manifests, ScopeResolution):
        return manifests
    base_manifest, head_manifest = manifests
    context = _range_result_context(
        resolved,
        base_manifest,
        head_manifest,
        claimed_context=None,
    )
    unsafe_path = _unsafe_manifest_path(base_manifest, head_manifest)
    if unsafe_path is not None:
        return _range_resolution(
            context,
            status="UNKNOWN",
            reason="unsafe_governed_input",
            ci_exit_code=1,
            diagnostics=f"Governed input is not a regular blob with an allowed Git mode: {unsafe_path}",
        )
    claimed_context = resolved.claimed_context
    if claimed_context is not None and not _context_matches_range(claimed_context, resolved):
        return _context_failure("pr_context_identity_mismatch", "Claimed target/head identity mismatch.", resolved)
    context = _range_result_context(
        resolved,
        base_manifest,
        head_manifest,
        claimed_context=claimed_context,
    )
    if any(path in resolved.source_lock_paths for path in resolved.selected_paths):
        return _range_resolution(
            context,
            status="UNKNOWN",
            reason="candidate_project_runtime_source_lock_change",
            ci_exit_code=1,
            diagnostics="Candidate source-lock bytes are governed evidence and cannot build the project-runtime layer.",
        )
    if resolved.candidate_policy_paths:
        return _range_resolution(
            context,
            status="UNKNOWN",
            reason="candidate_policy_change",
            ci_exit_code=1,
            diagnostics="Candidate policy/configuration changes are shadow-only and cannot authorize analysis.",
        )
    status: ScopeStatus = "PASS" if resolved.selected_paths else "NOT_APPLICABLE"
    return _range_resolution(
        context,
        status=status,
        reason="resolved" if resolved.selected_paths else "no_governed_impact",
        ci_exit_code=0,
    )


def _range_manifests_or_failure(
    resolved: _ResolvedRange,
) -> tuple[dict[str, InputIdentity], dict[str, InputIdentity]] | ScopeResolution:
    try:
        return _governed_range_manifests(resolved)
    except GitResolutionError as exc:
        return _context_failure("unsafe_governed_input", str(exc), resolved)


def _range_result_context(
    resolved: _ResolvedRange,
    base_manifest: dict[str, InputIdentity],
    head_manifest: dict[str, InputIdentity],
    *,
    claimed_context: _ClaimedContext | None,
) -> _RangeResultContext:
    candidate_identities = ((resolved.candidates[0], resolved.base_snapshot.tree),)
    assurance: AssuranceKind = "range_candidate" if claimed_context is not None else "range_preview"
    return _RangeResultContext(
        resolved=resolved,
        base_manifest=base_manifest,
        head_manifest=head_manifest,
        claimed_context=claimed_context,
        assurance=assurance,
        candidate_identities=candidate_identities,
        candidate_digest=_canonical_json_digest(candidate_identities),
    )


def _range_resolution(
    context: _RangeResultContext,
    *,
    status: ScopeStatus,
    reason: str,
    ci_exit_code: int,
    diagnostics: str = "",
) -> ScopeResolution:
    resolved = context.resolved
    claimed = context.claimed_context
    return ScopeResolution(
        status=status,
        reason=reason,
        selected_paths=resolved.selected_paths,
        assurance_kind=context.assurance,
        effective_assurance_kind=context.assurance,
        ci_exit_code=ci_exit_code,
        diagnostics=diagnostics,
        base_snapshot=resolved.base_snapshot,
        head_snapshot=resolved.head_snapshot,
        materialized=True,
        merge_base_candidates=resolved.candidates,
        merge_base_candidate_identities=context.candidate_identities,
        merge_base_candidate_digest=context.candidate_digest,
        context_digest=claimed.digest if claimed is not None else "",
        claimed_context=claimed.document if claimed is not None else None,
        resolved_target_commit=resolved.target_commit,
        resolved_target_tree=resolved.target_tree,
        resolved_head_commit=resolved.head_snapshot.commit,
        resolved_head_tree=resolved.head_snapshot.tree,
        input_manifest=context.head_manifest,
        base_input_manifest=context.base_manifest,
        path_statuses=resolved.path_statuses,
        exact_renames=resolved.exact_renames,
        exact_rename_digest=resolved.exact_rename_digest,
        base_source_manifest_digest=resolved.base_source_manifest_digest,
        head_source_manifest_digest=resolved.head_source_manifest_digest,
        policy_bundle=resolved.policy_bundle,
        policy_paths=resolved.candidate_policy_paths,
        policy_manifest_digest=resolved.policy_manifest_digest,
        candidate_policy_change_digest=resolved.candidate_policy_change_digest,
    )


def _resolve_range(request: ScopeRequest) -> ScopeResolution:
    if request.base_ref is None or request.head_ref is None:
        return _unknown_range("missing_range_ref", "Range scope requires full base and head refs.")
    try:
        resolved = _materialized_range(request)
    except ContextResolutionError as exc:
        return _unknown_range("unsafe_pr_context", str(exc))
    except PolicyResolutionError as exc:
        return _unknown_range("policy_parse_failure", str(exc))
    except GitResolutionError as exc:
        return _unknown_range("git_resolution_failed", str(exc))
    return resolved if isinstance(resolved, ScopeResolution) else _range_result(request, resolved)


def _resolved_git_path(repository: Path, *args: str) -> Path:
    raw = _git(repository, ["rev-parse", *args]).stdout.strip()
    path = Path(raw)
    return path if path.is_absolute() else repository / path


def _capture_index(repository: Path) -> _IndexCapture:
    live_index = _resolved_git_path(repository, "--git-path", "index")
    common_git = _resolved_git_path(repository, "--git-common-dir")
    capture_root = Path(tempfile.mkdtemp(prefix="specfact-index-"))
    captured_index = capture_root / "index"
    last_error = "index capture did not run"
    try:
        for _attempt in range(3):
            try:
                payload = _stable_regular_bytes(live_index, max_size=512 * 1024 * 1024)
            except GitResolutionError as exc:
                last_error = str(exc)
                continue
            captured_index.write_bytes(payload)
            for shared_index in sorted(common_git.glob("sharedindex.*")):
                shared_payload = _stable_regular_bytes(shared_index, max_size=512 * 1024 * 1024)
                (capture_root / shared_index.name).write_bytes(shared_payload)
            return _IndexCapture(path=captured_index, digest=sha256_bytes(payload))
        raise GitResolutionError(f"Unable to capture a stable Git index after three attempts: {last_error}")
    except Exception:
        shutil.rmtree(capture_root, ignore_errors=True)
        raise


def _after_index_capture() -> None:
    """Deterministic test seam immediately after the immutable index capture."""


def _captured_index_env(capture: _IndexCapture) -> dict[str, str]:
    return {"GIT_INDEX_FILE": str(capture.path)}


def _index_stage_entries(repository: Path, capture: _IndexCapture) -> list[tuple[str, str, int, str]]:
    output = _git(repository, ["ls-files", "--stage", "-z"], env_overrides=_captured_index_env(capture)).stdout
    entries: list[tuple[str, str, int, str]] = []
    for record in output.split("\0"):
        if not record:
            continue
        metadata, separator, path = record.partition("\t")
        if not separator:
            raise GitResolutionError("Captured index entry omitted its path separator.")
        mode, object_id, stage_text = metadata.split(" ", 2)
        entries.append((mode, object_id, int(stage_text), path))
    return entries


def _index_flag_tags(repository: Path, capture: _IndexCapture) -> dict[str, str]:
    output = _git(repository, ["ls-files", "-v", "-z"], env_overrides=_captured_index_env(capture)).stdout
    tags: dict[str, str] = {}
    for record in output.split("\0"):
        if not record:
            continue
        tag, separator, path = record.partition(" ")
        if not separator or len(tag) != 1:
            raise GitResolutionError("Captured index flag record is malformed.")
        tags[path] = tag
    return tags


def _write_index_tree(repository: Path, capture: _IndexCapture) -> str:
    tree = _git(repository, ["write-tree"], env_overrides=_captured_index_env(capture)).stdout.strip()
    if len(tree) != 40:
        raise GitResolutionError(f"Captured index produced a non-full tree identity: {tree!r}")
    return tree


def _descriptor_relative_bytes(root: Path, relative: str) -> bytes:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise GitResolutionError(f"Unsafe materialized path: {relative!r}")
    directory_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_DIRECTORY", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = [os.open(root, directory_flags | nofollow)]
    try:
        for component in path.parts[:-1]:
            descriptors.append(os.open(component, directory_flags | nofollow, dir_fd=descriptors[-1]))
        file_descriptor = os.open(
            path.parts[-1], os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | nofollow, dir_fd=descriptors[-1]
        )
        try:
            before = os.fstat(file_descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise GitResolutionError(f"Materialized governed input is not regular: {relative}")
            chunks: list[bytes] = []
            while chunk := os.read(file_descriptor, 1_048_576):
                chunks.append(chunk)
            after = os.fstat(file_descriptor)
        finally:
            os.close(file_descriptor)
    except OSError as exc:
        raise GitResolutionError(f"Descriptor-relative no-follow read failed for {relative}: {exc}") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise GitResolutionError(f"Materialized governed input changed while reading: {relative}")
    return b"".join(chunks)


def _input_identity(snapshot: Snapshot, relative: str) -> InputIdentity | None:
    entry = snapshot.entry_or_none(relative)
    if entry is None:
        return None
    payload = snapshot.bytes_or_none(relative) or b""
    if entry.object_type == "blob" and entry.git_mode in _REGULAR_GIT_MODES:
        opened_payload = _descriptor_relative_bytes(snapshot.root, relative)
        if opened_payload != payload:
            raise GitResolutionError(f"Materialized content does not match Git blob bytes: {relative}")
    return InputIdentity(
        object_type=entry.object_type,
        git_mode=entry.git_mode,
        blob_sha=entry.object_id,
        content_digest=sha256_bytes(payload),
    )


def _index_metadata(
    stage_entries: list[tuple[str, str, int, str]],
    flag_tags: dict[str, str],
    tree_entries: dict[str, TreeEntry],
) -> dict[str, IndexMetadata]:
    metadata: dict[str, IndexMetadata] = {}
    for mode, object_id, stage, path in stage_entries:
        intent_to_add = stage == 0 and path not in tree_entries
        metadata[path] = IndexMetadata(mode, object_id, stage, intent_to_add, flag_tags.get(path, ""))
    return metadata


def _index_unknown(
    reason: str,
    diagnostics: str,
    *,
    context: _IndexResolutionContext | None = None,
) -> ScopeResolution:
    base_snapshot = context.base_snapshot if context is not None else None
    head_snapshot = context.index_snapshot if context is not None else None
    selected_paths = context.selected_paths if context is not None else ()
    metadata = context.metadata if context is not None else {}
    index_tree = context.index_tree if context is not None else ""
    manifest = context.manifest if context is not None else {}
    return ScopeResolution(
        status="UNKNOWN",
        reason=reason,
        selected_paths=selected_paths,
        assurance_kind="index",
        effective_assurance_kind="index",
        ci_exit_code=1,
        diagnostics=diagnostics,
        base_snapshot=base_snapshot,
        head_snapshot=head_snapshot,
        materialized=head_snapshot is not None,
        input_manifest=manifest,
        index_metadata=metadata,
        index_tree=index_tree,
        selection_tree=index_tree,
    )


def _resolve_index(request: ScopeRequest) -> ScopeResolution:
    try:
        context = _materialized_index_context(request.repository)
    except GitResolutionError as exc:
        return _index_unknown("git_resolution_failed", str(exc))
    if isinstance(context, ScopeResolution):
        return context
    unsafe_path = _unsafe_index_path(context)
    if unsafe_path is not None:
        return _index_unknown(
            "unsafe_governed_input",
            f"Captured index contains unsafe governed input: {unsafe_path}",
            context=context,
        )
    return _resolved_index(context)


def _materialized_index_context(repository: Path) -> _IndexResolutionContext | ScopeResolution:
    capture = _capture_index(repository)
    try:
        return _materialized_index_context_from_capture(repository, capture)
    finally:
        shutil.rmtree(capture.path.parent, ignore_errors=True)


def _materialized_index_context_from_capture(
    repository: Path, capture: _IndexCapture
) -> _IndexResolutionContext | ScopeResolution:
    _after_index_capture()
    stage_entries = _index_stage_entries(repository, capture)
    if any(stage != 0 for _mode, _object_id, stage, _path in stage_entries):
        return _index_unknown("unsafe_governed_input", "Captured index contains unmerged stages.")
    tree = _write_index_tree(repository, capture)
    tree_entries = {entry.path: entry for entry in _tree_entries(repository, tree)}
    metadata = _index_metadata(stage_entries, _index_flag_tags(repository, capture), tree_entries)
    head_commit = _resolve_commit(repository, "HEAD")
    base_snapshot = _materialize_commit(repository, head_commit)
    index_snapshot = _materialize_tree(repository, tree, snapshot_identity=f"index-{capture.digest[7:]}")
    changed_paths = set(_range_paths(repository, head_commit, tree))
    changed_paths.update(path for path, item in metadata.items() if item.intent_to_add)
    selected_paths = tuple(
        path
        for path in sorted(changed_paths)
        if _governed_path(path, frozenset(), base=base_snapshot, head=index_snapshot)
    )
    manifest = {
        path: identity for path in selected_paths if (identity := _input_identity(index_snapshot, path)) is not None
    }
    return _IndexResolutionContext(base_snapshot, index_snapshot, selected_paths, metadata, tree, manifest)


def _unsafe_index_path(context: _IndexResolutionContext) -> str | None:
    for path in context.selected_paths:
        metadata = context.metadata.get(path)
        identity = context.manifest.get(path)
        if metadata is not None and (metadata.intent_to_add or metadata.stage != 0):
            return path
        if identity is not None and (identity.object_type != "blob" or identity.git_mode not in _REGULAR_GIT_MODES):
            return path
    return None


def _resolved_index(context: _IndexResolutionContext) -> ScopeResolution:
    status: ScopeStatus = "PASS" if context.selected_paths else "NOT_APPLICABLE"
    return ScopeResolution(
        status=status,
        reason="resolved" if context.selected_paths else "no_governed_impact",
        selected_paths=context.selected_paths,
        assurance_kind="index",
        effective_assurance_kind="index",
        ci_exit_code=0,
        base_snapshot=context.base_snapshot,
        head_snapshot=context.index_snapshot,
        materialized=True,
        input_manifest=context.manifest,
        index_metadata=context.metadata,
        index_tree=context.index_tree,
        selection_tree=context.index_tree,
    )


@ensure(lambda result: result.scope != "changed")
def normalize_scope_request(request: ScopeRequest) -> ScopeRequest:
    """Normalize compatibility spellings and immutable-range defaults."""

    scope = "worktree" if request.scope == "changed" else cast(ScopeKind, request.scope)
    enforcement = request.enforcement
    if scope == "range" and enforcement is None:
        enforcement = "full"
    return replace(request, scope=scope, enforcement=enforcement)


def _validate_immutable_scope_options(request: ScopeRequest) -> None:
    if request.scope not in {"index", "range"}:
        return
    mutations = {
        "fix": request.fix,
        "preview_fixes": request.preview_fixes,
        "with_mutation": request.with_mutation,
    }
    if rejected := next((name for name, enabled in mutations.items() if enabled), None):
        raise InvalidScopeOption(f"{rejected} is forbidden for immutable {request.scope} scope")
    if request.scope != "range":
        return
    narrowing = {
        "files": bool(request.files),
        "include_tests": not request.include_tests,
        "exclude_tests": request.exclude_tests,
        "focus": bool(request.focus),
        "path_filters": bool(request.path_filters),
        "no_tests": request.no_tests,
        "level": request.level is not None,
        "enforcement": request.enforcement not in {"full", "shadow"},
    }
    if rejected := next((name for name, enabled in narrowing.items() if enabled), None):
        raise InvalidScopeOption(f"{rejected} would narrow immutable range evidence")


@require(lambda request: request.repository.is_dir(), "repository must be an existing directory")
@ensure(lambda result: result.status in {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"})
def resolve_scope(request: ScopeRequest) -> ScopeResolution:
    """Resolve one request into a typed scope result."""

    normalized = normalize_scope_request(request)
    _validate_immutable_scope_options(normalized)
    if normalized.scope == "range":
        return _resolve_range(normalized)
    if normalized.scope == "index":
        return _resolve_index(normalized)
    if normalized.scope == "explicit_files":
        selected = tuple(sorted(PurePosixPath(path).as_posix() for path in normalized.files))
        return ScopeResolution(
            status="PASS" if selected else "NOT_APPLICABLE",
            reason="resolved" if selected else "no_governed_impact",
            selected_paths=selected,
            assurance_kind="explicit_files",
            effective_assurance_kind="explicit_files",
            ci_exit_code=0,
        )
    assurance = cast(AssuranceKind, normalized.scope)
    return ScopeResolution(
        status="UNKNOWN",
        reason="scope_not_materialized",
        selected_paths=(),
        assurance_kind=assurance,
        effective_assurance_kind=assurance,
        ci_exit_code=1,
        diagnostics=f"{normalized.scope} scope materialization is not available yet.",
    )


def cleanup_scope_resolution(resolution: ScopeResolution) -> None:
    """Remove every temporary root owned by a completed scope resolution."""

    roots = {snapshot.root for snapshot in (resolution.base_snapshot, resolution.head_snapshot) if snapshot is not None}
    if resolution.policy_bundle is not None:
        roots.add(resolution.policy_bundle.root)
    for root in sorted(roots, key=lambda path: len(path.parts), reverse=True):
        shutil.rmtree(root, ignore_errors=True)


@ensure(lambda result: result.status in {"PASS", "UNKNOWN"})
def verify_pr_assurance(resolution: ScopeResolution, envelope: object | None) -> AssuranceVerification:
    """Require a separately verified consumer envelope for protected PR assurance."""

    if resolution.effective_assurance_kind == "pr_range" and envelope is not None:
        return AssuranceVerification(status="PASS", reason="trusted_consumer_envelope")
    return AssuranceVerification(status="UNKNOWN", reason="protected_pr_assurance_unverified")


@ensure(lambda result: isinstance(result, bool))
def local_enforcement_allowed(resolution: ScopeResolution) -> bool:
    """Return whether this result can enforce a local, non-PR invocation."""

    return resolution.status == "PASS" and resolution.assurance_kind in {
        "explicit_files",
        "full",
        "index",
        "worktree",
    }


def _matches_focus(file_path: Path, facet: str) -> bool:
    if file_path.suffix not in _PYTHON_SUFFIXES:
        return False
    if facet == "tests":
        return _is_test_path(file_path)
    if facet == "docs":
        return "docs" in file_path.parts
    return facet == "source" and not _is_test_path(file_path) and "docs" not in file_path.parts


@ensure(lambda result: isinstance(result, list))
def filter_files_by_focus(files: list[Path], facets: tuple[str, ...]) -> list[Path]:
    """Restrict files to the union of requested Python source facets."""

    file_facets = tuple(facet for facet in facets if facet in {"source", "tests", "docs"})
    if not file_facets:
        return files
    return [file_path for file_path in files if any(_matches_focus(file_path, facet) for facet in file_facets)]


def _path_filter_matches(file_path: Path, path_filter: Path) -> bool:
    return file_path == path_filter or path_filter in file_path.parents


def _filtered_files(files: Iterable[Path], path_filters: list[Path]) -> list[Path]:
    normalized = [path_filter for path_filter in path_filters if str(path_filter).strip()]
    absolute = next((path_filter for path_filter in normalized if path_filter.is_absolute()), None)
    if absolute is not None:
        raise RunCommandError(f"Path filters must be repo-relative: {absolute}")
    if not normalized:
        return list(files)
    return [
        file_path
        for file_path in files
        if any(_path_filter_matches(file_path, path_filter) for path_filter in normalized)
    ]


def _auto_scope_message(scope: Literal["changed", "full"], path_filters: list[Path]) -> str:
    return " ".join([f"--scope {scope}", *(f"--path {path_filter}" for path_filter in path_filters)])


def _auto_discovered_files(
    scope: Literal["changed", "full"],
    *,
    include_tests: bool,
    path_filters: list[Path],
    changed_discovery: Callable[..., list[Path]],
    full_discovery: Callable[[], list[Path]],
) -> list[Path]:
    if scope == "full":
        resolved = full_discovery()
        return resolved if include_tests or path_filters else [path for path in resolved if not _is_test_path(path)]
    return changed_discovery(include_tests=include_tests or bool(path_filters))


@ensure(lambda result: bool(result), "scope selection must return at least one existing file")
def resolve_legacy_files(
    files: list[Path],
    request: LegacyFileSelectionRequest,
) -> list[Path]:
    """Resolve the legacy local command surface through scope-owned selection."""

    if files and (request.scope is not None or request.path_filters):
        raise ConflictingScopeError("Choose positional files or auto-scope controls, not both.")
    resolved = _resolved_explicit_files(files) if files else _resolved_automatic_files(request)
    if not resolved:
        message = _auto_scope_message(request.scope or "changed", request.path_filters)
        raise NoReviewableFilesError(
            f"No reviewable files matched the selected auto-scope controls ({message}). "
            "Adjust --scope/--path or pass positional files."
        )
    missing = next((file_path for file_path in resolved if not file_path.is_file()), None)
    if missing is not None:
        raise NoReviewableFilesError(f"File not found: {missing}")
    return resolved


def _resolved_explicit_files(files: list[Path]) -> list[Path]:
    resolved = [file_path for file_path in files if not _is_ignored_path(file_path)]
    if not resolved:
        raise NoReviewableFilesError(
            "No Python files to review were provided or detected from tracked or untracked changes."
        )
    return resolved


def _resolved_automatic_files(request: LegacyFileSelectionRequest) -> list[Path]:
    discovered = _auto_discovered_files(
        request.scope or "changed",
        include_tests=request.include_tests,
        path_filters=request.path_filters,
        changed_discovery=request.changed_discovery,
        full_discovery=request.full_discovery,
    )
    filtered = _filtered_files(discovered, request.path_filters)
    return [file_path for file_path in filtered if not _is_ignored_path(file_path)]


def _discovered_python_files(paths: Sequence[Path], *, include_tests: bool) -> list[Path]:
    selected = [
        path for path in paths if path.suffix in _PYTHON_SUFFIXES and path.is_file() and not _is_ignored_path(path)
    ]
    deduplicated = list(dict.fromkeys(selected))
    return deduplicated if include_tests else [path for path in deduplicated if not _is_test_path(path)]


@require(lambda repository: repository.is_dir(), "repository must be an existing directory")
@ensure(lambda result: all(path.suffix in _PYTHON_SUFFIXES for path in result))
def discover_worktree_python_files(
    repository: Path,
    *,
    include_tests: bool,
) -> list[Path]:
    """Discover tracked modifications and untracked Python files for local review."""

    tracked = [Path(path) for path in _git_paths(repository, ["diff", "HEAD", "--name-only"])]
    untracked = [Path(path) for path in _git_paths(repository, ["ls-files", "--others", "--exclude-standard"])]
    return _discovered_python_files([*tracked, *untracked], include_tests=include_tests)


@require(lambda repository: repository.is_dir(), "repository must be an existing directory")
@ensure(lambda result: all(path.suffix in _PYTHON_SUFFIXES for path in result))
def discover_full_python_files(
    repository: Path,
    *,
    include_tests: bool,
) -> list[Path]:
    """Discover tracked and untracked Python files for a local full review."""

    tracked = [Path(path) for path in _git_paths(repository, ["ls-files", "--cached"])]
    untracked = [Path(path) for path in _git_paths(repository, ["ls-files", "--others", "--exclude-standard"])]
    return _discovered_python_files([*tracked, *untracked], include_tests=include_tests)
