"""Code analyzer for extracting features from brownfield codebases."""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import certifi
import networkx as nx
from beartype import beartype
from icontract import ensure, require
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
from specfact_cli.models.plan import Feature, Idea, Metadata, PlanBundle, Product, Story

from specfact_project.analyzers.contract_extractor import ContractExtractor
from specfact_project.analyzers.control_flow_analyzer import ControlFlowAnalyzer
from specfact_project.analyzers.requirement_extractor import RequirementExtractor
from specfact_project.analyzers.test_pattern_extractor import TestPatternExtractor
from specfact_project.migrations.plan_migrator import get_current_schema_version
from specfact_project.utils.feature_keys import to_classname_key, to_sequential_key


console = Console()
_LOGGER = logging.getLogger(__name__)

_DEPENDENCY_IMPORT_EXCLUSIONS = frozenset(
    {
        "sys",
        "os",
        "json",
        "yaml",
        "pathlib",
        "typing",
        "collections",
        "dataclasses",
        "enum",
        "abc",
        "asyncio",
        "functools",
        "itertools",
        "re",
        "datetime",
        "time",
        "logging",
        "hashlib",
        "base64",
        "urllib",
        "http",
        "socket",
        "threading",
        "multiprocessing",
    }
)


_SEMGREP_EVIDENCE_RULES = (
    ("has_api_endpoints", ("route-detection", "api-endpoint")),
    ("has_database_models", ("model-detection", "database-model")),
    ("has_crud_operations", ("crud",)),
    ("has_auth_patterns", ("auth", "authentication", "permission")),
    ("has_framework_patterns", ("framework", "async", "context-manager")),
    ("has_test_patterns", ("test", "pytest", "unittest")),
    (
        "has_anti_patterns",
        (
            "antipattern",
            "code-smell",
            "god-class",
            "mutable-default",
            "lambda-assignment",
            "string-concatenation",
            "deprecated",
        ),
    ),
    (
        "has_security_issues",
        ("security", "unsafe", "insecure", "weak-cryptographic", "hardcoded-secret", "command-injection"),
    ),
)


@dataclass(frozen=True)
class _SemgrepClassScope:
    file_path: Path
    class_name: str
    start_line: int | None = None
    end_line: int | None = None


@dataclass
class _SemgrepFeatureBuckets:
    api_endpoints: list[str] = field(default_factory=list)
    data_models: list[str] = field(default_factory=list)
    auth_patterns: list[str] = field(default_factory=list)
    crud_operations: list[dict[str, Any]] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    code_smells: list[str] = field(default_factory=list)


@dataclass
class _FileAnalysisState:
    progress: Progress
    task_id: TaskID
    completed_count: int = 0
    interrupted: bool = False


class CodeAnalyzer:
    """
    Analyzes Python code to auto-derive plan bundles.

    Extracts features from classes and user stories from method patterns
    following Scrum/Agile practices.
    """

    # Fibonacci sequence for story points
    FIBONACCI = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]

    @beartype
    @require(lambda repo_path: repo_path is not None and isinstance(repo_path, Path), "Repo path must be Path")
    @require(lambda confidence_threshold: 0.0 <= confidence_threshold <= 1.0, "Confidence threshold must be 0.0-1.0")
    @require(lambda plan_name: plan_name is None or isinstance(plan_name, str), "Plan name must be None or str")
    @require(
        lambda entry_point: entry_point is None or isinstance(entry_point, Path),
        "Entry point must be None or Path",
    )
    def __init__(
        self,
        repo_path: Path,
        confidence_threshold: float = 0.5,
        key_format: str = "classname",
        plan_name: str | None = None,
        entry_point: Path | None = None,
        incremental_callback: Any | None = None,
    ) -> None:
        """
        Initialize code analyzer.

        Args:
            repo_path: Path to repository root
            confidence_threshold: Minimum confidence score (0.0-1.0)
            key_format: Feature key format ('classname' or 'sequential', default: 'classname')
            plan_name: Custom plan name (will be used for idea.title, optional)
            entry_point: Optional entry point path for partial analysis (relative to repo_path)
            incremental_callback: Optional callback function(features_count, themes) for incremental results (Phase 4.9)
        """
        self.repo_path = Path(repo_path).resolve()
        self.confidence_threshold = confidence_threshold
        self.key_format = key_format
        self.plan_name = plan_name
        self.incremental_callback = incremental_callback
        self.entry_point: Path | None = None
        if entry_point is not None:
            # Resolve entry point relative to repo_path
            if entry_point.is_absolute():
                self.entry_point = entry_point
            else:
                self.entry_point = (self.repo_path / entry_point).resolve()
            # Validate entry point exists and is within repo
            if not self.entry_point.exists():
                raise ValueError(f"Entry point does not exist: {self.entry_point}")
            if not str(self.entry_point).startswith(str(self.repo_path)):
                raise ValueError(f"Entry point must be within repository: {self.entry_point}")
        self.features: list[Feature] = []
        self.themes: set[str] = set()
        self.dependency_graph: nx.DiGraph[str] = nx.DiGraph()  # Module dependency graph
        self.type_hints: dict[str, dict[str, str]] = {}  # Module -> {function: type_hint}
        self.async_patterns: dict[str, list[str]] = {}  # Module -> [async_methods]
        self.commit_bounds: dict[str, tuple[str, str]] = {}  # Feature -> (first_commit, last_commit)
        self.external_dependencies: set[str] = set()  # External modules imported from outside entry point
        # Use entry_point for test extractor if provided, otherwise repo_path
        test_extractor_path = self.entry_point if self.entry_point else self.repo_path
        self.test_extractor = TestPatternExtractor(test_extractor_path)
        self.control_flow_analyzer = ControlFlowAnalyzer()
        self.requirement_extractor = RequirementExtractor()
        self.contract_extractor = ContractExtractor()

        self._configure_semgrep()

    def _configure_semgrep(self) -> None:
        # Semgrep integration
        self.semgrep_enabled = True
        # Try to find Semgrep config: check resources first (runtime), then tools (development)
        self.semgrep_config: Path | None = None
        self.semgrep_quality_config: Path | None = None
        resources_config = Path(__file__).parent.parent / "resources" / "semgrep" / "feature-detection.yml"
        tools_config = self.repo_path / "tools" / "semgrep" / "feature-detection.yml"
        resources_quality_config = Path(__file__).parent.parent / "resources" / "semgrep" / "code-quality.yml"
        tools_quality_config = self.repo_path / "tools" / "semgrep" / "code-quality.yml"
        if resources_config.exists():
            self.semgrep_config = resources_config
        elif tools_config.exists():
            self.semgrep_config = tools_config
        if resources_quality_config.exists():
            self.semgrep_quality_config = resources_quality_config
        elif tools_quality_config.exists():
            self.semgrep_quality_config = tools_quality_config
        # Disable if Semgrep not available or config missing
        # Check TEST_MODE first to avoid any subprocess calls in tests
        if os.environ.get("TEST_MODE") == "true" or self.semgrep_config is None or not self._check_semgrep_available():
            self.semgrep_enabled = False

    @beartype
    @ensure(lambda result: isinstance(result, PlanBundle), "Must return PlanBundle")
    @ensure(
        lambda result: (
            isinstance(result, PlanBundle)
            and hasattr(result, "version")
            and hasattr(result, "features")
            and result.version == get_current_schema_version()  # type: ignore[reportUnknownMemberType]
            and len(result.features) >= 0
        ),  # type: ignore[reportUnknownMemberType]
        "Plan bundle must be valid",
    )
    def analyze(self) -> PlanBundle:
        """
        Analyze repository and generate plan bundle.

        Returns:
            Generated PlanBundle from code analysis
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            python_files = self._discover_python_files(progress)
            # Phase 2: Build dependency graph
            task2 = progress.add_task("[cyan]Phase 2: Building dependency graph...", total=None)
            self._build_dependency_graph(python_files)
            progress.update(task2, description="[green]✓ Dependency graph built")
            progress.remove_task(task2)

            self._analyze_python_files(python_files, progress)

            # Phase 4: Analyze commit history
            task4 = progress.add_task("[cyan]Phase 4: Analyzing commit history...", total=None)
            self._analyze_commit_history()
            progress.update(task4, description="[green]✓ Commit history analyzed")
            progress.remove_task(task4)

            # Phase 5: Enhance features with dependencies
            task5 = progress.add_task("[cyan]Phase 5: Enhancing features with dependency information...", total=None)
            self._enhance_features_with_dependencies()
            progress.update(task5, description="[green]✓ Features enhanced")
            progress.remove_task(task5)

            # Phase 6: Extract technology stack
            task6 = progress.add_task("[cyan]Phase 6: Extracting technology stack...", total=None)
            technology_constraints = self._extract_technology_stack_from_dependencies()
            progress.update(task6, description="[green]✓ Technology stack extracted")
            progress.remove_task(task6)

        return self._build_plan_bundle(technology_constraints)

    def _discover_python_files(self, progress: Progress) -> list[Path]:
        # Phase 1: Discover Python files
        task1 = progress.add_task("[cyan]Phase 1: Discovering Python files...", total=None)
        if self.entry_point:
            # Scope analysis to entry point directory
            python_files = list(self.entry_point.rglob("*.py"))
            entry_point_rel = self.entry_point.relative_to(self.repo_path)
            progress.update(
                task1,
                description=f"[green]✓ Found {len(python_files)} Python files in {entry_point_rel}",
            )
        else:
            # Full repository analysis
            python_files = list(self.repo_path.rglob("*.py"))
            progress.update(task1, description=f"[green]✓ Found {len(python_files)} Python files")
        progress.remove_task(task1)

        return python_files

    def _build_plan_bundle(self, technology_constraints: list[str]) -> PlanBundle:
        # If sequential format, update all keys now that we know the total count
        if self.key_format == "sequential":
            for idx, feature in enumerate(self.features, start=1):
                feature.key = to_sequential_key(feature.key, idx)

        title = self._plan_title()
        narrative = f"Auto-derived plan from brownfield analysis of {title}"
        if self.entry_point:
            entry_point_rel = self.entry_point.relative_to(self.repo_path)
            narrative += f" (scoped to {entry_point_rel})"

        idea = Idea(
            title=title,
            narrative=narrative,
            constraints=technology_constraints,
            metrics=None,
        )

        product = Product(
            themes=sorted(self.themes) if self.themes else ["Core"],
            releases=[],
        )

        # Build metadata with scope information
        metadata = Metadata(
            stage="draft",
            promoted_at=None,
            promoted_by=None,
            analysis_scope="partial" if self.entry_point else "full",
            entry_point=str(self.entry_point.relative_to(self.repo_path)) if self.entry_point else None,
            external_dependencies=sorted(self.external_dependencies),
            summary=None,
        )

        return PlanBundle(
            version=get_current_schema_version(),
            idea=idea,
            business=None,
            product=product,
            features=self.features,
            metadata=metadata,
            clarifications=None,
        )

    def _plan_title(self) -> str:
        if self.plan_name:
            # Use the plan name (already sanitized, but humanize for title)
            title = self.plan_name.replace("_", " ").replace("-", " ").title()
        elif self.entry_point:
            # Use entry point name for partial analysis
            entry_point_name = self.entry_point.name or self.entry_point.relative_to(self.repo_path).as_posix()
            title = f"{self._humanize_name(entry_point_name)} Module"
        else:
            repo_name = self.repo_path.name or "Unknown Project"
            title = self._humanize_name(repo_name)

        return title

    def _analyze_python_files(self, python_files: list[Path], progress: Progress) -> None:
        task_id = progress.add_task(
            "[cyan]Phase 3: Analyzing files and extracting features...", total=len(python_files)
        )
        files = [path for path in python_files if not self._should_skip_file(path)]
        if os.environ.get("TEST_MODE") == "true":
            max_workers = max(1, min(2, len(files)))
        else:
            max_workers = max(1, min(os.cpu_count() or 4, 8, len(files)))
        state = _FileAnalysisState(progress, task_id)
        if files:
            is_test_mode = os.environ.get("TEST_MODE") == "true"
            if is_test_mode:
                self._analyze_files_sequential(files, state)
            else:
                self._analyze_files_parallel(files, state, max_workers)
        skipped_count = len(python_files) - len(files)
        if skipped_count > 0:
            features_count = len(self.features)
            progress.update(
                task_id,
                completed=len(python_files),
                description=(
                    f"[cyan]Phase 3: Analyzing files and extracting features... ({features_count} features discovered)"
                ),
            )
        progress.update(
            task_id,
            description=f"[green]✓ Analyzed {len(python_files)} files, extracted {len(self.features)} features",
        )
        progress.remove_task(task_id)

    def _analyze_files_sequential(self, files: list[Path], state: _FileAnalysisState) -> None:
        for file_path in files:
            try:
                self._merge_file_analysis(self._analyze_file_parallel(file_path), state)
            except Exception as error:
                self._record_file_analysis_failure(file_path, error, state)

    def _merge_file_analysis(self, results: dict[str, Any], state: _FileAnalysisState) -> None:
        previous_count = len(self.features)
        self._merge_analysis_results(results)
        state.completed_count += 1
        self._update_file_analysis_progress(state)
        if self.incremental_callback and len(self.features) > previous_count:
            self.incremental_callback(len(self.features), sorted(self.themes))

    def _update_file_analysis_progress(self, state: _FileAnalysisState) -> None:
        features_count = len(self.features)
        state.progress.update(
            state.task_id,
            completed=state.completed_count,
            description=(
                f"[cyan]Phase 3: Analyzing files and extracting features... ({features_count} features discovered)"
            ),
        )

    def _record_file_analysis_failure(self, file_path: Path, error: Exception, state: _FileAnalysisState) -> None:
        console.print(f"[dim]⚠ Warning: Failed to analyze {file_path}: {error}[/dim]")
        state.completed_count += 1
        self._update_file_analysis_progress(state)

    def _analyze_files_parallel(self, files: list[Path], state: _FileAnalysisState, max_workers: int) -> None:
        executor = ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_to_file = {executor.submit(self._analyze_file_parallel, path): path for path in files}
            self._collect_completed_file_results(future_to_file, state)
        except KeyboardInterrupt:
            state.interrupted = True
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        finally:
            if not state.interrupted:
                executor.shutdown(wait=True)
            else:
                executor.shutdown(wait=False)

    def _collect_completed_file_results(
        self, future_to_file: dict[Future[dict[str, Any]], Path], state: _FileAnalysisState
    ) -> None:
        try:
            for future in as_completed(future_to_file):
                try:
                    self._merge_file_analysis(future.result(), state)
                except KeyboardInterrupt:
                    state.interrupted = True
                    self._cancel_pending_file_tasks(future_to_file)
                    break
                except Exception as error:
                    self._record_file_analysis_failure(future_to_file[future], error, state)
        except KeyboardInterrupt:
            state.interrupted = True
            self._cancel_pending_file_tasks(future_to_file)
        if state.interrupted:
            raise KeyboardInterrupt

    @staticmethod
    def _cancel_pending_file_tasks(future_to_file: dict[Future[dict[str, Any]], Path]) -> None:
        for future in future_to_file:
            if not future.done():
                future.cancel()

    def _probe_semgrep(self) -> tuple[bool, str | None]:
        """Check if Semgrep is available in the active repository environment."""
        # Skip Semgrep check in test mode to avoid timeouts
        if os.environ.get("TEST_MODE") == "true":
            return False, "Semgrep skipped in TEST_MODE"

        from specfact_cli.utils.env_manager import check_tool_in_env, detect_env_manager

        env_info = detect_env_manager(self.repo_path)
        available, message = check_tool_in_env(self.repo_path, "osemgrep", env_info)
        return available, message

    def _check_semgrep_available(self) -> bool:
        """Check if Semgrep is available in the active repository environment."""
        available, _message = self._probe_semgrep()
        return available

    @ensure(
        lambda result: (
            isinstance(result, list)
            and all(
                isinstance(plugin, dict)
                and isinstance(plugin.get("name"), str)
                and isinstance(plugin.get("reason"), str)
                and isinstance(plugin.get("enabled"), bool)
                and isinstance(plugin.get("used"), bool)
                and (not plugin["used"] or plugin["enabled"])
                for plugin in result
            )
        ),
        "Plugin status records must contain display text and consistent Boolean states",
    )
    def get_plugin_status(self) -> list[dict[str, Any]]:
        """
        Get status of all analysis plugins.

        Returns:
            List of plugin status dictionaries with keys: name, enabled, used, reason
        """
        from specfact_cli.utils.optional_deps import check_cli_tool_available, check_python_package_available

        plugins: list[dict[str, Any]] = []

        # AST Analysis (always enabled)
        plugins.append(
            {
                "name": "AST Analysis",
                "enabled": True,
                "used": True,
                "reason": "Core analysis engine",
            }
        )

        # Semgrep Pattern Detection
        semgrep_available, semgrep_message = self._probe_semgrep()
        semgrep_enabled = self.semgrep_enabled and semgrep_available
        semgrep_used = semgrep_enabled and self.semgrep_config is not None

        if not semgrep_available:
            reason = semgrep_message or "Native Semgrep executable osemgrep is not installed"
        elif self.semgrep_config is None:
            reason = "Semgrep config not found"
        else:
            reason = "Pattern detection enabled"
            if self.semgrep_quality_config:
                reason += " (with code quality rules)"

        plugins.append(
            {
                "name": "Semgrep Pattern Detection",
                "enabled": semgrep_enabled,
                "used": semgrep_used,
                "reason": reason,
            }
        )

        # Dependency Graph Analysis (requires pyan3 and networkx)
        pyan3_available, _ = check_cli_tool_available("pyan3")
        networkx_available = check_python_package_available("networkx")
        graph_enabled = pyan3_available and networkx_available
        graph_used = graph_enabled  # Used if both dependencies are available

        if not pyan3_available and not networkx_available:
            reason = "pyan3 and networkx not installed (install: pip install pyan3 networkx)"
        elif not pyan3_available:
            reason = "pyan3 not installed (install: pip install pyan3)"
        elif not networkx_available:
            reason = "networkx not installed (install: pip install networkx)"
        else:
            reason = "Dependency graph analysis enabled"

        plugins.append(
            {
                "name": "Dependency Graph Analysis",
                "enabled": graph_enabled,
                "used": graph_used,
                "reason": reason,
            }
        )

        return plugins

    def _run_semgrep_patterns(self, file_path: Path) -> list[dict[str, Any]]:
        """
        Run Semgrep for pattern detection on a single file.

        Returns:
            List of Semgrep findings (empty list if Semgrep not available or error)
        """
        # Skip Semgrep in test mode to avoid timeouts
        if os.environ.get("TEST_MODE") == "true":
            return []

        if not self.semgrep_enabled or self.semgrep_config is None:
            return []

        try:
            from specfact_cli.utils.env_manager import build_tool_command, check_tool_in_env, detect_env_manager

            env_info = detect_env_manager(self.repo_path)
            semgrep_available, _message = check_tool_in_env(self.repo_path, "osemgrep", env_info)
            if not semgrep_available:
                return []

            # Run feature detection
            configs = [str(self.semgrep_config)]
            # Also include code-quality config if available (for anti-patterns)
            if self.semgrep_quality_config is not None:
                configs.append(str(self.semgrep_quality_config))

            # Use shorter timeout in test environments (though we already skip in TEST_MODE)
            timeout = 10
            env = dict(os.environ)
            env.setdefault("SSL_CERT_FILE", certifi.where())
            if sys.platform == "linux":
                env.setdefault("LD_LIBRARY_PATH", "$ORIGIN/libs")

            result = subprocess.run(
                build_tool_command(
                    env_info,
                    [
                        "osemgrep",
                        "scan",
                        "--experimental",
                        "--metrics=off",
                        "--disable-version-check",
                        *(argument for config in configs for argument in ("--config", config)),
                        "--json",
                        str(file_path),
                    ],
                ),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                env=env,
                check=False,
            )

            return self._parse_semgrep_result(result)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, ValueError):
            # Semgrep not available or config missing - continue without it
            return []

    @staticmethod
    def _parse_semgrep_result(result: subprocess.CompletedProcess[str]) -> list[dict[str, Any]]:
        # Semgrep may return non-zero for valid findings
        # Only fail if stderr indicates actual error
        if result.returncode != 0 and ("error" in result.stderr.lower() or "not found" in result.stderr.lower()):
            return []

        # Parse JSON results
        findings = json.loads(result.stdout)
        return findings.get("results", [])

    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Check if file should be skipped.

        Test files are always skipped from feature extraction because:
        - Tests are validation artifacts, not specification artifacts
        - Tests validate code, they don't define what code should do
        - Test files should only be used for linking to production features and extracting examples
        """
        file_str = str(file_path)
        file_name = file_path.name

        # Skip common non-source directories
        skip_patterns = [
            "__pycache__",
            ".git",
            "venv",
            ".venv",
            "env",
            ".pytest_cache",
            "htmlcov",
            "dist",
            "build",
            ".eggs",
        ]

        if any(pattern in file_str for pattern in skip_patterns):
            return True

        # Skip test directories (both "test/" and "tests/")
        # Check if any path component is a test directory
        path_parts = file_path.parts
        if any(part in ("test", "tests") for part in path_parts):
            return True

        # Skip test files by naming pattern (test_*.py, *_test.py)
        return file_name.startswith("test_") or file_name.endswith("_test.py")

    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file (legacy sequential version)."""
        results = self._analyze_file_parallel(file_path)
        self._merge_analysis_results(results)

    def _analyze_file_parallel(self, file_path: Path) -> dict[str, Any]:
        """
        Analyze a single Python file and return results (thread-safe).

        Returns:
            Dictionary with extracted data:
            - 'themes': set of theme strings
            - 'type_hints': dict mapping module -> {function: type_hint}
            - 'async_patterns': dict mapping module -> [async_methods]
            - 'features': list of Feature objects
        """
        results: dict[str, Any] = {
            "themes": set(),
            "type_hints": {},
            "async_patterns": {},
            "features": [],
        }

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            # Extract module-level info (return themes instead of modifying self)
            themes = self._extract_themes_from_imports_parallel(tree)
            results["themes"].update(themes)

            # Extract type hints (return instead of modifying self)
            module_name = self._path_to_module_name(file_path)
            type_hints = self._extract_type_hints_parallel(tree)
            if type_hints:
                results["type_hints"][module_name] = type_hints

            # Detect async patterns (return instead of modifying self)
            async_methods = self._detect_async_patterns_parallel(tree)
            if async_methods:
                results["async_patterns"][module_name] = async_methods

            # NEW: Run Semgrep for pattern detection
            semgrep_findings = self._run_semgrep_patterns(file_path)

            # Extract classes as features
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                # Extract Semgrep evidence for confidence scoring
                class_start_line = node.lineno if hasattr(node, "lineno") else None
                class_end_line = node.end_lineno if hasattr(node, "end_lineno") else None
                semgrep_evidence = self._extract_semgrep_evidence(
                    semgrep_findings, node.name, class_start_line, class_end_line
                )

                # Create feature with Semgrep evidence included in confidence calculation
                feature = self._extract_feature_from_class_parallel(node, semgrep_evidence)
                if feature:
                    # Enhance feature with detailed Semgrep findings (outcomes, constraints, themes)
                    self._enhance_feature_with_semgrep(
                        feature,
                        semgrep_findings,
                        _SemgrepClassScope(file_path, node.name, class_start_line, class_end_line),
                    )
                    results["features"].append(feature)

        except (SyntaxError, UnicodeDecodeError):
            # Skip files that can't be parsed
            pass

        return results

    def _merge_analysis_results(self, results: dict[str, Any]) -> None:
        """Merge parallel analysis results into instance variables."""
        # Merge themes
        self.themes.update(results.get("themes", set()))

        # Merge type hints
        for module, hints in results.get("type_hints", {}).items():
            if module not in self.type_hints:
                self.type_hints[module] = {}
            self.type_hints[module].update(hints)

        # Merge async patterns
        for module, methods in results.get("async_patterns", {}).items():
            if module not in self.async_patterns:
                self.async_patterns[module] = []
            self.async_patterns[module].extend(methods)

        # Merge features (append to list)
        self.features.extend(results.get("features", []))

    def _extract_themes_from_imports(self, tree: ast.AST) -> None:
        """Extract themes from import statements (legacy version)."""
        themes = self._extract_themes_from_imports_parallel(tree)
        self.themes.update(themes)

    def _extract_themes_from_imports_parallel(self, tree: ast.AST) -> set[str]:
        """Extract themes from import statements (thread-safe, returns themes)."""
        themes: set[str] = set()
        theme_keywords = {
            "fastapi": "API",
            "flask": "API",
            "django": "Web",
            "redis": "Caching",
            "postgres": "Database",
            "mysql": "Database",
            "asyncio": "Async",
            "typer": "CLI",
            "click": "CLI",
            "pydantic": "Validation",
            "pytest": "Testing",
            "sqlalchemy": "ORM",
            "requests": "HTTP Client",
            "aiohttp": "Async HTTP",
        }
        for node in ast.walk(tree):
            for name in self._import_module_names(node):
                themes.update(theme for keyword, theme in theme_keywords.items() if keyword in name.lower())
        return themes

    @staticmethod
    def _import_module_names(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Import):
            return [alias.name for alias in node.names]
        if isinstance(node, ast.ImportFrom) and node.module:
            return [node.module]
        return []

    def _extract_semgrep_evidence(
        self,
        semgrep_findings: list[dict[str, Any]],
        class_name: str,
        class_start_line: int | None,
        class_end_line: int | None,
    ) -> dict[str, Any]:
        """Extract Semgrep evidence for confidence scoring."""
        evidence: dict[str, Any] = {flag: False for flag, _ in _SEMGREP_EVIDENCE_RULES}
        for finding in semgrep_findings:
            rule_id = str(finding.get("check_id", "")).lower()
            start = finding.get("start", {})
            finding_line = start.get("line", 0) if isinstance(start, dict) else 0
            message = str(finding.get("message", ""))
            matches_class = (
                class_name.lower() in message.lower()
                or class_name.lower() in rule_id
                or (
                    class_start_line
                    and class_end_line
                    and finding_line
                    and class_start_line <= finding_line <= class_end_line
                )
            )
            if matches_class:
                self._record_semgrep_evidence(evidence, rule_id)
        return evidence

    @staticmethod
    def _record_semgrep_evidence(evidence: dict[str, Any], rule_id: str) -> None:
        for flag, tokens in _SEMGREP_EVIDENCE_RULES:
            if any(token in rule_id for token in tokens):
                evidence[flag] = True
                break

    def _extract_feature_from_class_parallel(
        self,
        node: ast.ClassDef,
        semgrep_evidence: dict[str, Any] | None = None,
    ) -> Feature | None:
        """Extract feature from class definition (thread-safe version)."""
        # Skip private classes and test classes
        if node.name.startswith("_") or node.name.startswith("Test"):
            return None

        # Generate feature key based on configured format
        # For sequential keys, use placeholder (will be fixed after all features collected)
        # During parallel processing, we can't know the final position
        feature_key = (
            "FEATURE-PLACEHOLDER"  # Will be replaced in post-processing
            if self.key_format == "sequential"
            else to_classname_key(node.name)
        )

        # Extract docstring as outcome
        docstring = ast.get_docstring(node)
        outcomes: list[str] = []
        if docstring:
            # Take first paragraph as primary outcome
            first_para = docstring.split("\n\n")[0].strip()
            outcomes.append(first_para)  # type: ignore[reportUnknownMemberType]
        else:
            outcomes.append(f"Provides {self._humanize_name(node.name)} functionality")

        # Collect all methods
        methods = [item for item in node.body if isinstance(item, ast.FunctionDef)]

        # Group methods into user stories
        stories = self._extract_stories_from_methods(methods, node.name)

        # Calculate confidence based on documentation, story quality, and Semgrep evidence
        confidence = self._calculate_feature_confidence(node, stories, semgrep_evidence)

        if confidence < self.confidence_threshold:
            return None

        # Skip if no meaningful stories
        if not stories:
            return None

        # Extract complete requirements (Step 1.3)
        complete_requirement = self.requirement_extractor.extract_complete_requirement(node)
        acceptance_criteria = (
            [complete_requirement] if complete_requirement else [f"{node.name} class provides documented functionality"]
        )

        # Extract NFRs from code patterns (Step 1.3)
        nfrs = self.requirement_extractor.extract_nfrs(node)
        # Add NFRs as constraints
        constraints = nfrs if nfrs else []

        return Feature(
            key=feature_key,
            title=self._humanize_name(node.name),
            outcomes=outcomes,
            acceptance=acceptance_criteria,
            constraints=constraints,
            stories=stories,
            confidence=round(confidence, 2),
            source_tracking=None,
            contract=None,
            protocol=None,
        )

    def _enhance_feature_with_semgrep(
        self, feature: Feature, semgrep_findings: list[dict[str, Any]], scope: _SemgrepClassScope
    ) -> None:
        """Enhance feature with Semgrep pattern detection results."""
        if not semgrep_findings:
            return
        relevant = [finding for finding in semgrep_findings if self._finding_matches_semgrep_scope(finding, scope)]
        if not relevant:
            return
        buckets = _SemgrepFeatureBuckets()
        for finding in relevant:
            self._collect_semgrep_finding(finding, buckets)
        self._append_semgrep_outcomes(feature, buckets)
        self._append_semgrep_constraint(feature, "Code quality", buckets.anti_patterns)
        self._append_semgrep_constraint(feature, "Issues detected", buckets.code_smells)

    def _finding_matches_semgrep_scope(self, finding: dict[str, Any], scope: _SemgrepClassScope) -> bool:
        finding_path = finding.get("path", "")
        if str(scope.file_path) not in finding_path and finding_path not in str(scope.file_path):
            return False
        start = finding.get("start", {})
        finding_line = start.get("line", 0) if isinstance(start, dict) else 0
        message = str(finding.get("message", ""))
        check_id = str(finding.get("check_id", ""))
        is_anti_pattern = any(
            token in check_id.lower() for token in ("antipattern", "code-smell", "god-class", "deprecated", "security")
        )
        if scope.class_name.lower() in message.lower() or scope.class_name.lower() in check_id.lower():
            return True
        return self._line_matches_semgrep_scope(finding_line, is_anti_pattern, scope)

    @staticmethod
    def _line_matches_semgrep_scope(finding_line: Any, is_anti_pattern: bool, scope: _SemgrepClassScope) -> bool:
        if scope.start_line and scope.end_line and finding_line:
            return bool(scope.start_line <= finding_line <= scope.end_line)
        return bool(
            is_anti_pattern
            and scope.start_line
            and finding_line
            and finding_line >= scope.start_line
            and (not scope.end_line or finding_line <= scope.start_line + 100)
        )

    def _collect_semgrep_finding(self, finding: dict[str, Any], buckets: _SemgrepFeatureBuckets) -> None:
        rule_id = str(finding.get("check_id", ""))
        extra = finding.get("extra", {})
        metadata = extra.get("metadata", {}) if isinstance(extra, dict) else {}
        category = self._semgrep_enhancement_category(rule_id.lower())
        if category == "api":
            self._collect_semgrep_endpoint(metadata, buckets)
            return
        if category == "model":
            self._collect_semgrep_model(metadata, buckets)
            return
        if category == "auth":
            permission = str(metadata.get("permission", ""))
            buckets.auth_patterns.append(permission or "authentication required")
            self.themes.add("Security")
            return
        if category == "crud":
            self._collect_semgrep_crud(finding, extra, metadata, buckets)
            return
        if category == "anti":
            buckets.anti_patterns.append(str(finding.get("message", "")))
            return
        if category == "smell":
            buckets.code_smells.append(str(finding.get("message", "")))
            return

    @staticmethod
    def _semgrep_enhancement_category(rule_id: str) -> str | None:
        categories = (
            ("api", ("route-detection",)),
            ("model", ("model-detection",)),
            ("auth", ("auth",)),
            ("crud", ("crud",)),
            (
                "anti",
                (
                    "antipattern",
                    "code-smell",
                    "god-class",
                    "mutable-default",
                    "lambda-assignment",
                    "string-concatenation",
                ),
            ),
            (
                "smell",
                (
                    "security",
                    "unsafe",
                    "insecure",
                    "weak-cryptographic",
                    "hardcoded-secret",
                    "command-injection",
                    "deprecated",
                ),
            ),
        )
        return next((category for category, tokens in categories if any(token in rule_id for token in tokens)), None)

    def _collect_semgrep_endpoint(self, metadata: Any, buckets: _SemgrepFeatureBuckets) -> None:
        method = str(metadata.get("method", "")).upper()
        path = str(metadata.get("path", ""))
        if method and path:
            buckets.api_endpoints.append(f"{method} {path}")
            self.themes.add("API")

    def _collect_semgrep_model(self, metadata: Any, buckets: _SemgrepFeatureBuckets) -> None:
        model_name = str(metadata.get("model", ""))
        if model_name:
            buckets.data_models.append(model_name)
            self.themes.add("Database")

    def _collect_semgrep_crud(
        self, finding: dict[str, Any], extra: Any, metadata: Any, buckets: _SemgrepFeatureBuckets
    ) -> None:
        operation = str(metadata.get("operation", "")).upper()
        message = str(finding.get("message", ""))
        func_name = str(extra.get("message", "")) if isinstance(extra, dict) else ""
        entity = self._semgrep_crud_entity(message, func_name)
        if operation or entity:
            buckets.crud_operations.append({"operation": operation or "UNKNOWN", "entity": entity or "unknown"})

    @staticmethod
    def _semgrep_crud_entity(message: str, func_name: str) -> str:
        if func_name:
            parts = func_name.split("_")
            return "_".join(parts[1:]) if len(parts) > 1 else ""
        if not message:
            return ""
        for operation in ["create", "get", "update", "delete", "add", "find", "remove"]:
            if operation not in message.lower():
                continue
            parts = message.lower().split(operation + "_")
            if len(parts) > 1:
                return parts[1].split()[0] if parts[1] else ""
        return ""

    @staticmethod
    def _append_semgrep_outcomes(feature: Feature, buckets: _SemgrepFeatureBuckets) -> None:
        if buckets.api_endpoints:
            feature.outcomes.append(f"Exposes API endpoints: {', '.join(buckets.api_endpoints)}")
        if buckets.data_models:
            feature.outcomes.append(f"Defines data models: {', '.join(buckets.data_models)}")
        if buckets.auth_patterns:
            feature.outcomes.append(f"Requires authentication: {', '.join(buckets.auth_patterns)}")
        if buckets.crud_operations:
            crud = ", ".join(
                [
                    f"{operation.get('operation', 'UNKNOWN')} {operation.get('entity', 'unknown')}"
                    for operation in buckets.crud_operations
                ]
            )
            feature.outcomes.append(f"Provides CRUD operations: {crud}")

    @staticmethod
    def _append_semgrep_constraint(feature: Feature, label: str, values: list[str]) -> None:
        if values:
            text = "; ".join(values[:3])
            if text:
                if feature.constraints:
                    feature.constraints.append(f"{label}: {text}")
                else:
                    feature.constraints = [f"{label}: {text}"]

        # Confidence is already calculated with Semgrep evidence in _calculate_feature_confidence
        # No need to adjust here - this method only adds outcomes, constraints, and themes

    def _extract_stories_from_methods(self, methods: list[ast.FunctionDef], class_name: str) -> list[Story]:
        """
        Extract user stories from methods by grouping related functionality.

        Groups methods by:
        - CRUD operations (create, read, update, delete)
        - Common prefixes (get_, set_, validate_, process_)
        - Functionality patterns
        """
        # Group methods by pattern
        method_groups = self._group_methods_by_functionality(methods)

        stories: list[Story] = []
        story_counter = 1

        for group_name, group_methods in method_groups.items():
            if not group_methods:
                continue

            # Create a user story for this group
            story = self._create_story_from_method_group(group_name, group_methods, class_name, story_counter)

            if story:
                stories.append(story)  # type: ignore[reportUnknownMemberType]
                story_counter += 1

        return stories

    def _group_methods_by_functionality(self, methods: list[ast.FunctionDef]) -> dict[str, list[ast.FunctionDef]]:
        """Group methods by their functionality patterns."""
        groups: dict[str, list[ast.FunctionDef]] = defaultdict(list)
        public_methods = [method for method in methods if not method.name.startswith("_") or method.name == "__init__"]
        for method in public_methods:
            groups[self._classify_method_group(method.name)].append(method)
        return dict(groups)

    @staticmethod
    def _classify_method_group(method_name: str) -> str:
        matchers = (
            ("Create Operations", ("create", "add", "insert", "new")),
            ("Read Operations", ("get", "read", "fetch", "find", "list", "retrieve")),
            ("Update Operations", ("update", "modify", "edit", "change", "set")),
            ("Delete Operations", ("delete", "remove", "destroy")),
            ("Validation", ("validate", "check", "verify", "is_valid")),
            ("Processing", ("process", "compute", "calculate", "transform", "convert")),
            ("Analysis", ("analyze", "parse", "extract", "detect")),
            ("Generation", ("generate", "build", "create", "make")),
            ("Comparison", ("compare", "diff", "match")),
            ("Configuration", ("setup", "configure", "initialize")),
        )
        for group, keywords in matchers:
            if any(keyword in method_name.lower() for keyword in keywords):
                return group
        return "Configuration" if method_name == "__init__" else "Core Functionality"

    def _create_story_from_method_group(
        self, group_name: str, methods: list[ast.FunctionDef], class_name: str, story_number: int
    ) -> Story | None:
        """Create a user story from a group of related methods."""
        if not methods:
            return None
        story_key = f"STORY-{class_name.upper()}-{story_number:03d}"
        title = self._generate_story_title(group_name, class_name)
        acceptance, tasks = self._story_acceptance_and_tasks(methods, class_name)
        if not acceptance:
            acceptance.append(f"{group_name} functionality works correctly")
        primary_method = methods[0]
        scenarios = self.control_flow_analyzer.extract_scenarios_from_method(
            primary_method, class_name, primary_method.name
        )
        contracts = self.contract_extractor.extract_function_contracts(primary_method)
        story_points = self._calculate_story_points(methods)
        value_points = self._calculate_value_points(methods, group_name)
        return Story(
            key=story_key,
            title=title,
            acceptance=acceptance,
            story_points=story_points,
            value_points=value_points,
            tasks=tasks,
            confidence=0.8 if len(methods) > 1 else 0.6,
            scenarios=scenarios,
            contracts=contracts,
        )

    def _story_acceptance_and_tasks(
        self, methods: list[ast.FunctionDef], class_name: str
    ) -> tuple[list[str], list[str]]:
        acceptance: list[str] = []
        tasks: list[str] = []
        test_patterns = self.test_extractor.extract_test_patterns_for_class(class_name, as_openapi_examples=True)
        if test_patterns:
            acceptance.extend(test_patterns if len(test_patterns) <= 3 else test_patterns[:3])
        for method in methods:
            tasks.append(f"{method.name}()")
            if not test_patterns:
                acceptance.extend(self.test_extractor.infer_from_code_patterns(method, class_name))
            self._append_method_docstring_acceptance(acceptance, method)
        return acceptance, tasks

    @staticmethod
    def _append_method_docstring_acceptance(acceptance: list[str], method: ast.FunctionDef) -> None:
        docstring = ast.get_docstring(method)
        if not docstring:
            return
        if "Given" in docstring and "When" in docstring and "Then" in docstring:
            match = re.search(r"Given\s+(.+?),\s*When\s+(.+?),\s*Then\s+(.+?)(?:\.|$)", docstring, re.IGNORECASE)
            if match:
                acceptance.append(match.group(3).strip())
            return
        first_line = docstring.split("\n")[0].strip()
        if first_line and first_line not in acceptance:
            acceptance.append(first_line)

    def _generate_story_title(self, group_name: str, class_name: str) -> str:
        """Generate user-centric story title."""
        # Map group names to user-centric titles
        title_templates = {
            "Create Operations": f"As a user, I can create new {self._humanize_name(class_name)} records",
            "Read Operations": f"As a user, I can view {self._humanize_name(class_name)} data",
            "Update Operations": f"As a user, I can update {self._humanize_name(class_name)} records",
            "Delete Operations": f"As a user, I can delete {self._humanize_name(class_name)} records",
            "Validation": f"As a developer, I can validate {self._humanize_name(class_name)} data",
            "Processing": f"As a user, I can process data using {self._humanize_name(class_name)}",
            "Analysis": f"As a user, I can analyze data with {self._humanize_name(class_name)}",
            "Generation": f"As a user, I can generate outputs from {self._humanize_name(class_name)}",
            "Comparison": f"As a user, I can compare {self._humanize_name(class_name)} data",
            "Configuration": f"As a developer, I can configure {self._humanize_name(class_name)}",
            "Core Functionality": f"As a user, I can use {self._humanize_name(class_name)} features",
        }

        return title_templates.get(group_name, f"As a user, I can work with {self._humanize_name(class_name)}")

    def _calculate_story_points(self, methods: list[ast.FunctionDef]) -> int:
        """
        Calculate story points (complexity) using Fibonacci sequence.

        Based on:
        - Number of methods
        - Average method size
        - Complexity indicators (loops, conditionals)
        """
        # Base complexity on number of methods
        method_count = len(methods)

        # Count total lines across all methods
        total_lines = sum(len(ast.unparse(m).split("\n")) for m in methods)
        avg_lines = total_lines / method_count if method_count > 0 else 0

        # Simple heuristic: 1-2 methods = small, 3-5 = medium, 6+ = large
        if method_count <= 2 and avg_lines < 20:
            base_points = 2  # Small
        elif method_count <= 5 and avg_lines < 40:
            base_points = 5  # Medium
        elif method_count <= 8:
            base_points = 8  # Large
        else:
            base_points = 13  # Extra Large

        # Return nearest Fibonacci number
        return min(self.FIBONACCI, key=lambda x: abs(x - base_points))

    def _calculate_value_points(self, methods: list[ast.FunctionDef], group_name: str) -> int:
        """
        Calculate value points (business value) using Fibonacci sequence.

        Based on:
        - Public API exposure
        - CRUD operations have high value
        - Validation has medium value
        """
        # CRUD operations are high value
        crud_groups = ["Create Operations", "Read Operations", "Update Operations", "Delete Operations"]
        if group_name in crud_groups:
            base_value = 8  # High business value

        # User-facing operations
        elif group_name in ["Processing", "Analysis", "Generation", "Comparison"]:
            base_value = 5  # Medium-high value

        # Developer/internal operations
        elif group_name in ["Validation", "Configuration"]:
            base_value = 3  # Medium value

        # Core functionality
        else:
            base_value = 3  # Default medium value

        # Adjust based on number of public methods (more = higher value)
        public_count = sum(1 for m in methods if not m.name.startswith("_"))
        if public_count >= 3:
            base_value = min(base_value + 2, 13)

        # Return nearest Fibonacci number
        return min(self.FIBONACCI, key=lambda x: abs(x - base_value))

    def _calculate_feature_confidence(
        self,
        node: ast.ClassDef,
        stories: list[Story],
        semgrep_evidence: dict[str, Any] | None = None,
    ) -> float:
        """
        Calculate confidence score for a feature combining AST + Semgrep evidence.

        Args:
            node: AST class node
            stories: List of stories extracted from methods
            semgrep_evidence: Optional Semgrep findings evidence dict with keys:
                - has_api_endpoints: bool
                - has_database_models: bool
                - has_crud_operations: bool
                - has_auth_patterns: bool
                - has_framework_patterns: bool
                - has_test_patterns: bool
                - has_anti_patterns: bool
                - has_security_issues: bool

        Returns:
            Confidence score (0.0-1.0) combining AST and Semgrep evidence
        """
        score = 0.3  # Base score (30%)

        # === AST Evidence (Structure) ===

        # Has docstring (+20%)
        if ast.get_docstring(node):
            score += 0.2

        # Has stories (+20%)
        if stories:
            score += 0.2

        # Has multiple stories (better coverage) (+20%)
        if len(stories) > 2:
            score += 0.2

        # Stories are well-documented (+10%)
        documented_stories = sum(1 for s in stories if s.acceptance and len(s.acceptance) > 1)
        if stories and documented_stories > len(stories) / 2:
            score += 0.1

        if semgrep_evidence:
            score = self._apply_semgrep_confidence(score, semgrep_evidence)

        # Cap at 0.0-1.0 range
        return min(max(score, 0.0), 1.0)

    @staticmethod
    def _apply_semgrep_confidence(score: float, semgrep_evidence: dict[str, Any]) -> float:
        if semgrep_evidence.get("has_api_endpoints", False):
            score += 0.1
        if semgrep_evidence.get("has_database_models", False):
            score += 0.15
        if semgrep_evidence.get("has_crud_operations", False):
            score += 0.1
        if semgrep_evidence.get("has_auth_patterns", False):
            score += 0.1
        if semgrep_evidence.get("has_framework_patterns", False):
            score += 0.05
        if semgrep_evidence.get("has_test_patterns", False):
            score += 0.1
        if semgrep_evidence.get("has_anti_patterns", False):
            score -= 0.05
        if semgrep_evidence.get("has_security_issues", False):
            score -= 0.1
        return score

    def _humanize_name(self, name: str) -> str:
        """Convert snake_case or PascalCase to human-readable title."""
        # Handle PascalCase
        name = re.sub(r"([A-Z])", r" \1", name).strip()
        # Handle snake_case
        name = name.replace("_", " ").replace("-", " ")
        return name.title()

    def _build_dependency_graph(self, python_files: list[Path]) -> None:
        """Build module dependency graph using AST imports."""
        modules: dict[str, Path] = {}
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
            module_name = self._path_to_module_name(file_path)
            modules[module_name] = file_path
            self.dependency_graph.add_node(module_name, path=file_path)
        for module_name, file_path in modules.items():
            self._add_module_dependencies(module_name, file_path, modules)

    def _add_module_dependencies(self, module_name: str, file_path: Path, modules: dict[str, Path]) -> None:
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
            for imported_module in self._extract_imports_from_ast(tree, file_path):
                self._add_import_dependency(module_name, imported_module, modules)
        except (SyntaxError, UnicodeDecodeError):
            _LOGGER.debug("Dependency analysis incomplete; retaining collected edges.")

    def _add_import_dependency(self, module_name: str, imported_module: str, modules: dict[str, Path]) -> None:
        if imported_module in modules:
            self.dependency_graph.add_edge(module_name, imported_module)
            return
        matching_module = next((known for known in modules if imported_module == known.split(".")[-1]), None)
        if matching_module:
            self.dependency_graph.add_edge(module_name, matching_module)
        elif self.entry_point and not any(
            imported_module.startswith(prefix) for prefix in ["src.", "lib.", "app.", "main.", "core."]
        ):
            self.external_dependencies.add(imported_module)

    def _path_to_module_name(self, file_path: Path) -> str:
        """Convert file path to module name (e.g., src/foo/bar.py -> src.foo.bar)."""
        # Get relative path from repo root
        try:
            relative_path = file_path.relative_to(self.repo_path)
        except ValueError:
            # File is outside repo, use full path
            relative_path = file_path

        # Convert to module name
        parts = [*relative_path.parts[:-1], relative_path.stem]  # Remove .py extension
        return ".".join(parts)

    def _extract_imports_from_ast(self, tree: ast.AST, file_path: Path) -> list[str]:
        """
        Extract imported module names from AST.

        Returns:
            List of module names (relative to repo root if possible)
        """
        imports = {name.split(".")[0] for node in ast.walk(tree) for name in self._import_module_names(node)}

        # Try to resolve local imports (relative to current file)
        resolved_imports: list[str] = []
        current_module = self._path_to_module_name(file_path)

        for imported in imports:
            if imported in _DEPENDENCY_IMPORT_EXCLUSIONS:
                continue

            # Try to resolve relative imports
            # If imported module matches a pattern from our repo, resolve it
            potential_module = self._resolve_local_import(imported, current_module)
            if potential_module:
                resolved_imports.append(potential_module)
            else:
                # Keep as external dependency
                resolved_imports.append(imported)

        return resolved_imports

    def _resolve_local_import(self, imported: str, current_module: str) -> str | None:
        """
        Try to resolve a local import relative to current module.

        Returns:
            Resolved module name if found in repo, None otherwise
        """
        # Check if it's already in our dependency graph
        if imported in self.dependency_graph:
            return imported

        # Try relative import resolution (e.g., from .foo import bar)
        # This is simplified - full resolution would need to handle package structure
        current_parts = current_module.split(".")
        if len(current_parts) > 1:
            # Try parent package
            parent_module = ".".join(current_parts[:-1])
            potential = f"{parent_module}.{imported}"
            if potential in self.dependency_graph:
                return potential

        return None

    def _extract_type_hints_parallel(self, tree: ast.AST) -> dict[str, str]:
        """Extract type hints from function/method signatures (thread-safe version)."""
        return {
            node.name: self._return_annotation_name(node.returns)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    @staticmethod
    def _return_annotation_name(annotation: ast.expr | None) -> str:
        if isinstance(annotation, ast.Name):
            return annotation.id
        if isinstance(annotation, ast.Subscript):
            return str(annotation.value.id if isinstance(annotation.value, ast.Name) else "Any")
        return "None"

    def _detect_async_patterns(self, tree: ast.AST, file_path: Path) -> list[str]:
        """
        Detect async/await patterns in code (legacy version).
        """
        async_methods = self._detect_async_patterns_parallel(tree)
        module_name = self._path_to_module_name(file_path)
        if module_name not in self.async_patterns:
            self.async_patterns[module_name] = []
        self.async_patterns[module_name].extend(async_methods)
        return async_methods

    def _detect_async_patterns_parallel(self, tree: ast.AST) -> list[str]:
        """Detect async/await patterns in code (thread-safe version)."""
        async_methods: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                async_methods.append(node.name)
            if isinstance(node, ast.Await):
                async_methods.extend(
                    name for name in self._enclosing_function_names(tree, node) if name not in async_methods
                )
        return async_methods

    @staticmethod
    def _enclosing_function_names(tree: ast.AST, node: ast.Await) -> list[str]:
        return [
            parent.name
            for parent in ast.walk(tree)
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) and node in ast.walk(parent)
        ]

    def _analyze_commit_history(self) -> None:
        """Mine recent commit history to identify feature boundaries."""
        try:
            from git import Repo

            if not (self.repo_path / ".git").exists():
                return
            repo = Repo(self.repo_path)
            commits = list(repo.iter_commits(max_count=100))
            for commit in commits:
                try:
                    self._record_commit_feature_bounds(commit)
                except Exception:
                    continue
        except ImportError:
            pass
        except Exception:
            _LOGGER.debug("Commit history analysis incomplete; retaining collected feature bounds.")

    def _record_commit_feature_bounds(self, commit: Any) -> None:
        commit_message = commit.message
        if isinstance(commit_message, bytes):
            commit_message = commit_message.decode("utf-8", errors="ignore")
        message = commit_message.lower()
        if "feat" in message or "feature" in message:
            feature_match = re.search(r"feature[-\s]?(\d+)", message, re.IGNORECASE)
            if feature_match:
                self._update_feature_commit_bounds(feature_match.group(1), commit.hexsha[:8])

    def _update_feature_commit_bounds(self, feature_num: str, commit_hash: str) -> None:
        for feature in self.features:
            if re.search(rf"feature[-\s]?{feature_num}", feature.key, re.IGNORECASE):
                first_commit = self.commit_bounds[feature.key][0] if feature.key in self.commit_bounds else commit_hash
                self.commit_bounds[feature.key] = (first_commit, commit_hash)
                break

    def _enhance_features_with_dependencies(self) -> None:
        """Enhance features with dependency graph information."""
        for _feature in self.features:
            # Find dependencies for this feature's module
            # This is simplified - would need to track which module each feature comes from
            pass

    @beartype
    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _extract_technology_stack_from_dependencies(self) -> list[str]:
        """Extract technology stack from requirements.txt and pyproject.toml."""
        constraints: list[str] = []
        self._read_requirement_constraints(constraints)
        self._read_project_constraints(constraints)
        unique_constraints = list(dict.fromkeys(constraints))
        return unique_constraints or ["Python 3.11+", "Typer for CLI", "Pydantic for data validation"]

    def _read_requirement_constraints(self, constraints: list[str]) -> None:
        requirements_file = self.repo_path / "requirements.txt"
        if not requirements_file.exists():
            return
        try:
            content = requirements_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    self._append_requirement_constraints(line, constraints)
        except Exception:
            _LOGGER.debug("Requirements analysis incomplete; retaining collected constraints.")

    @staticmethod
    def _dependency_package_name(dependency: str) -> str:
        return (
            dependency.split("==")[0]
            .split(">=")[0]
            .split(">")[0]
            .split("<=")[0]
            .split("<")[0]
            .split("~=")[0]
            .strip()
            .lower()
        )

    def _append_requirement_constraints(self, line: str, constraints: list[str]) -> None:
        package = self._dependency_package_name(line)
        if package == "python":
            if ">=" in line:
                version = line.split(">=")[1].split(",")[0].strip()
                constraints.append(f"Python {version}+")
            elif "==" in line:
                version = line.split("==")[1].split(",")[0].strip()
                constraints.append(f"Python {version}")
        self._append_framework_database_constraints(package, constraints)
        tool_maps = (
            {
                "pytest": "pytest for testing",
                "unittest": "unittest for testing",
                "nose": "nose for testing",
                "tox": "tox for testing",
            },
            {"docker": "Docker for containerization", "kubernetes": "Kubernetes for orchestration"},
        )
        for mapping in tool_maps:
            if package in mapping:
                constraints.append(mapping[package])
        if package == "pydantic":
            constraints.append("Pydantic for data validation")

    @staticmethod
    def _append_framework_database_constraints(package: str, constraints: list[str]) -> None:
        mappings = (
            {
                "fastapi": "FastAPI framework",
                "django": "Django framework",
                "flask": "Flask framework",
                "typer": "Typer for CLI",
                "tornado": "Tornado framework",
                "bottle": "Bottle framework",
            },
            {
                "psycopg2": "PostgreSQL database",
                "psycopg2-binary": "PostgreSQL database",
                "mysql-connector-python": "MySQL database",
                "pymongo": "MongoDB database",
                "redis": "Redis database",
                "sqlalchemy": "SQLAlchemy ORM",
            },
        )
        for mapping in mappings:
            if package in mapping:
                constraints.append(mapping[package])

    def _append_project_constraints(self, data: dict[str, Any], constraints: list[str]) -> None:
        if "project" in data and "requires-python" in data["project"]:
            python_req = data["project"]["requires-python"]
            if python_req:
                constraints.append(f"Python {python_req}")
        if "project" in data and "dependencies" in data["project"]:
            for dependency in data["project"]["dependencies"]:
                package = self._dependency_package_name(dependency)
                self._append_framework_database_constraints(package, constraints)
                if package == "pydantic":
                    constraints.append("Pydantic for data validation")

    def _read_project_constraints(self, constraints: list[str]) -> None:
        pyproject_file = self.repo_path / "pyproject.toml"
        if pyproject_file.exists():
            try:
                import tomli

                data = tomli.loads(pyproject_file.read_text(encoding="utf-8"))
                self._append_project_constraints(data, constraints)
            except ImportError:
                self._read_project_constraints_fallback(pyproject_file, constraints)
            except Exception:
                _LOGGER.debug("Project analysis incomplete; retaining collected constraints.")

    def _read_project_constraints_fallback(self, pyproject_file: Path, constraints: list[str]) -> None:
        try:
            import tomllib

            with pyproject_file.open("rb") as stream:
                data = tomllib.load(stream)
            self._append_project_constraints(data, constraints)
        except ImportError:
            pass

    def _get_module_dependencies(self, module_name: str) -> list[str]:
        """Get list of modules that the given module depends on."""
        if module_name not in self.dependency_graph:
            return []

        return list(self.dependency_graph.successors(module_name))
