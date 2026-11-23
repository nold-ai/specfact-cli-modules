"""Code analyzer for extracting features from brownfield codebases."""

from __future__ import annotations

import ast
import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import networkx as nx
from beartype import beartype
from icontract import ensure, require
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from specfact_cli.models.plan import Feature, Idea, Metadata, PlanBundle, Product, Story
from specfact_cli.utils import optional_deps

from specfact_project.analyzers.contract_extractor import ContractExtractor
from specfact_project.analyzers.control_flow_analyzer import ControlFlowAnalyzer
from specfact_project.analyzers.python_patterns import feature_patterns
from specfact_project.analyzers.requirement_extractor import RequirementExtractor
from specfact_project.analyzers.test_pattern_extractor import TestPatternExtractor
from specfact_project.migrations.plan_migrator import get_current_schema_version
from specfact_project.utils.feature_keys import to_classname_key, to_sequential_key


console = Console()


@dataclass
class _PatternFeatureBuckets:
    api_endpoints: list[str] = field(default_factory=list)
    data_models: list[str] = field(default_factory=list)
    auth_patterns: list[str] = field(default_factory=list)
    crud_operations: list[dict[str, str]] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    code_smells: list[str] = field(default_factory=list)
    themes: set[str] = field(default_factory=set)


@dataclass
class _PatternEnhancementContext:
    pattern_findings: list[dict[str, Any]]
    file_path: Path
    class_start_line: int | None = None
    class_end_line: int | None = None
    file_theme_accumulator: set[str] | None = None


class CodeAnalyzer:
    """
    Analyzes Python code to auto-derive plan bundles.

    Extracts features from classes and user stories from method patterns
    following Scrum/Agile practices.
    """

    # Fibonacci sequence for story points
    FIBONACCI = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    FEATURE_EVIDENCE_FLAGS = {
        "api": "has_api_endpoints",
        "model": "has_database_models",
        "crud": "has_crud_operations",
        "auth": "has_auth_patterns",
        "framework": "has_framework_patterns",
        "test": "has_test_patterns",
        "anti": "has_anti_patterns",
        "security": "has_security_issues",
    }

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

            # Phase 2: Build dependency graph
            task2 = progress.add_task("[cyan]Phase 2: Building dependency graph...", total=None)
            self._build_dependency_graph(python_files)
            progress.update(task2, description="[green]✓ Dependency graph built")
            progress.remove_task(task2)

            # Phase 3: Analyze files and extract features (parallelized)
            task3 = progress.add_task(
                "[cyan]Phase 3: Analyzing files and extracting features...", total=len(python_files)
            )

            # Filter out files to skip
            files_to_analyze = [f for f in python_files if not self._should_skip_file(f)]

            # Process files in parallel
            # In test mode, use fewer workers to avoid resource contention
            if os.environ.get("TEST_MODE") == "true":
                max_workers = max(1, min(2, len(files_to_analyze)))  # Max 2 workers in test mode
            else:
                max_workers = max(
                    1, min(os.cpu_count() or 4, 8, len(files_to_analyze))
                )  # Cap at 8 workers, ensure at least 1
            completed_count = 0

            def analyze_file_safe(file_path: Path) -> dict[str, Any]:
                """Analyze a file and return results (thread-safe)."""
                return self._analyze_file_parallel(file_path)

            if files_to_analyze:
                # In test mode, use sequential processing to avoid ThreadPoolExecutor deadlocks
                is_test_mode = os.environ.get("TEST_MODE") == "true"
                if is_test_mode:
                    # Sequential processing in test mode - avoids ThreadPoolExecutor deadlocks entirely
                    for file_path in files_to_analyze:
                        try:
                            results = analyze_file_safe(file_path)
                            prev_features_count = len(self.features)
                            self._merge_analysis_results(results)
                            completed_count += 1
                            # Update progress with feature count in description
                            features_count = len(self.features)
                            progress.update(
                                task3,
                                completed=completed_count,
                                description=f"[cyan]Phase 3: Analyzing files and extracting features... ({features_count} features discovered)",
                            )

                            # Phase 4.9: Report incremental results for quick first value
                            if self.incremental_callback and len(self.features) > prev_features_count:
                                # Only call callback when new features are discovered
                                self.incremental_callback(len(self.features), sorted(self.themes))
                        except Exception as e:
                            console.print(f"[dim]⚠ Warning: Failed to analyze {file_path}: {e}[/dim]")
                            completed_count += 1
                            features_count = len(self.features)
                            progress.update(
                                task3,
                                completed=completed_count,
                                description=f"[cyan]Phase 3: Analyzing files and extracting features... ({features_count} features discovered)",
                            )
                else:
                    executor = ThreadPoolExecutor(max_workers=max_workers)
                    interrupted = False
                    # In test mode, use wait=False to avoid hanging on shutdown
                    wait_on_shutdown = not is_test_mode
                    try:
                        # Submit all tasks
                        future_to_file = {executor.submit(analyze_file_safe, f): f for f in files_to_analyze}

                        # Collect results as they complete
                        try:
                            for future in as_completed(future_to_file):
                                try:
                                    results = future.result()
                                    # Merge results into instance variables (sequential merge is fast)
                                    prev_features_count = len(self.features)
                                    self._merge_analysis_results(results)
                                    completed_count += 1
                                    # Update progress with feature count in description
                                    features_count = len(self.features)
                                    progress.update(
                                        task3,
                                        completed=completed_count,
                                        description=f"[cyan]Phase 3: Analyzing files and extracting features... ({features_count} features discovered)",
                                    )

                                    # Phase 4.9: Report incremental results for quick first value
                                    if self.incremental_callback and len(self.features) > prev_features_count:
                                        # Only call callback when new features are discovered
                                        self.incremental_callback(len(self.features), sorted(self.themes))
                                except KeyboardInterrupt:
                                    # Cancel remaining tasks and break out of loop immediately
                                    interrupted = True
                                    for f in future_to_file:
                                        if not f.done():
                                            f.cancel()
                                    break
                                except Exception as e:
                                    # Log error but continue processing
                                    file_path = future_to_file[future]
                                    console.print(f"[dim]⚠ Warning: Failed to analyze {file_path}: {e}[/dim]")
                                    completed_count += 1
                                    features_count = len(self.features)
                                    progress.update(
                                        task3,
                                        completed=completed_count,
                                        description=f"[cyan]Phase 3: Analyzing files and extracting features... ({features_count} features discovered)",
                                    )
                        except KeyboardInterrupt:
                            # Also catch KeyboardInterrupt from as_completed() itself
                            interrupted = True
                            for f in future_to_file:
                                if not f.done():
                                    f.cancel()

                        # If interrupted, re-raise KeyboardInterrupt after breaking out of loop
                        if interrupted:
                            raise KeyboardInterrupt
                    except KeyboardInterrupt:
                        # Gracefully shutdown executor on interrupt (cancel pending tasks, don't wait)
                        interrupted = True
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise
                    finally:
                        # Ensure executor is properly shutdown
                        # If interrupted, don't wait for tasks (they're already cancelled)
                        # shutdown() is safe to call multiple times
                        # In test mode, use wait=False to avoid hanging
                        if not interrupted:
                            executor.shutdown(wait=wait_on_shutdown)
                        else:
                            # Already shutdown with wait=False, just ensure cleanup
                            executor.shutdown(wait=False)

            # Update progress for skipped files
            skipped_count = len(python_files) - len(files_to_analyze)
            if skipped_count > 0:
                features_count = len(self.features)
                progress.update(
                    task3,
                    completed=len(python_files),
                    description=f"[cyan]Phase 3: Analyzing files and extracting features... ({features_count} features discovered)",
                )

            progress.update(
                task3,
                description=f"[green]✓ Analyzed {len(python_files)} files, extracted {len(self.features)} features",
            )
            progress.remove_task(task3)

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

        # If sequential format, update all keys now that we know the total count
        if self.key_format == "sequential":
            for idx, feature in enumerate(self.features, start=1):
                feature.key = to_sequential_key(feature.key, idx)

        # Generate plan bundle
        # Use plan_name if provided, otherwise use entry point name or repo name
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

    @beartype
    @ensure(
        lambda result: any(status["name"] == "AST Analysis" and status["used"] for status in result),
        "Built-in Python checks must be reported as used",
    )
    def get_plugin_status(self) -> list[dict[str, Any]]:
        """
        Get status of all analysis plugins.

        Returns:
            List of plugin status dictionaries with keys: name, enabled, used, reason
        """
        plugins: list[dict[str, Any]] = []

        reason = "Built-in Python feature and quality checks"
        legacy_directory = self.repo_path / "tools" / "semgrep"
        legacy_filenames = ("feature-detection.yml", "code-quality.yml")
        if any((legacy_directory / filename).is_file() for filename in legacy_filenames):
            reason += ". Legacy Semgrep feature or quality rules require migration; custom rules were not run."
        plugins.append({"name": "AST Analysis", "enabled": True, "used": True, "reason": reason})

        # Dependency Graph Analysis (requires pyan3 and networkx)
        pyan3_available, _ = optional_deps.check_cli_tool_available("pyan3")
        networkx_available = optional_deps.check_python_package_available("networkx")
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
            type_hints = self._extract_type_hints_parallel(tree, file_path)
            if type_hints:
                results["type_hints"][module_name] = type_hints

            # Detect async patterns (return instead of modifying self)
            async_methods = self._detect_async_patterns_parallel(tree, file_path)
            if async_methods:
                results["async_patterns"][module_name] = async_methods

            pattern_findings = feature_patterns(tree, file_path)

            # Extract classes as features
            classes = (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
            for class_node in classes:
                feature = self._extract_feature_for_results(class_node, file_path, pattern_findings, results["themes"])
                if feature is not None:
                    results["features"].append(feature)

        except (SyntaxError, UnicodeDecodeError):
            # Skip files that can't be parsed
            pass

        return results

    def _extract_feature_for_results(
        self,
        node: ast.ClassDef,
        file_path: Path,
        pattern_findings: list[dict[str, Any]],
        file_theme_accumulator: set[str],
    ) -> Feature | None:
        """Extract and enrich one feature using its source findings."""
        current_count = 0 if self.key_format == "sequential" else len(self.features)
        class_start_line = min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])
        class_end_line = node.end_lineno if hasattr(node, "end_lineno") else None
        pattern_evidence = self._extract_pattern_evidence(pattern_findings, class_start_line, class_end_line)

        feature = self._extract_feature_from_class_parallel(node, file_path, current_count, pattern_evidence)
        if feature is None:
            return None

        self._enhance_feature_with_patterns(
            feature,
            _PatternEnhancementContext(
                pattern_findings=pattern_findings,
                file_path=file_path,
                class_start_line=class_start_line,
                class_end_line=class_end_line,
                file_theme_accumulator=file_theme_accumulator,
            ),
        )

        return feature

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
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for keyword, theme in theme_keywords.items():
                            if keyword in alias.name.lower():
                                themes.add(theme)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    for keyword, theme in theme_keywords.items():
                        if keyword in node.module.lower():
                            themes.add(theme)

        return themes

    def _extract_pattern_evidence(
        self,
        pattern_findings: list[dict[str, Any]],
        class_start_line: int | None,
        class_end_line: int | None,
    ) -> dict[str, Any]:
        """
        Extract Pattern evidence for confidence scoring.

        Args:
            pattern_findings: List of Pattern findings
            class_start_line: Starting line number of the class
            class_end_line: Ending line number of the class

        Returns:
            Evidence dict with boolean flags for different pattern types
        """
        evidence: dict[str, Any] = dict.fromkeys(self.FEATURE_EVIDENCE_FLAGS.values(), False)

        for finding in pattern_findings:
            rule_id = str(finding.get("check_id", "")).lower()
            if not self._finding_matches_class(finding, class_start_line, class_end_line):
                continue
            self._apply_pattern_evidence_flag(evidence, rule_id)

        return evidence

    def _finding_matches_class(
        self,
        finding: dict[str, Any],
        class_start_line: int | None,
        class_end_line: int | None,
    ) -> bool:
        """Check whether a pattern finding belongs to the target class."""
        finding_line = self._pattern_finding_line(finding)
        return bool(
            class_start_line and class_end_line and finding_line and class_start_line <= finding_line <= class_end_line
        )

    def _pattern_finding_line(self, finding: dict[str, Any]) -> int:
        """Extract the start line from a Pattern finding."""
        raw_start = finding.get("start", {})
        if not isinstance(raw_start, dict):
            return 0
        start: dict[str, Any] = raw_start
        return int(start.get("line", 0))

    def _apply_pattern_evidence_flag(self, evidence: dict[str, Any], rule_id: str) -> None:
        """Apply the first matching evidence flag for a rule id."""
        matchers = (
            ("api", ("route-detection", "api-endpoint")),
            ("model", ("model-detection", "database-model")),
            ("crud", ("crud",)),
            ("auth", ("auth", "authentication", "permission")),
            ("framework", ("framework", "async", "context-manager")),
            ("test", ("test", "pytest", "unittest")),
            (
                "anti",
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
                "security",
                ("security", "unsafe", "insecure", "weak-cryptographic", "hardcoded-secret", "command-injection"),
            ),
        )
        for category, keywords in matchers:
            if any(keyword in rule_id for keyword in keywords):
                evidence[self.FEATURE_EVIDENCE_FLAGS[category]] = True
                return

    def _extract_feature_from_class(self, node: ast.ClassDef, file_path: Path) -> Feature | None:
        """Extract feature from class definition (legacy version)."""
        return self._extract_feature_from_class_parallel(node, file_path, len(self.features), None)

    def _extract_feature_from_class_parallel(
        self,
        node: ast.ClassDef,
        file_path: Path,
        current_feature_count: int,
        pattern_evidence: dict[str, Any] | None = None,
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
            outcomes.append(f"Provides {self._humanize_name(node.name)} functionality")  # type: ignore[reportUnknownMemberType]

        # Collect all methods
        methods = [item for item in node.body if isinstance(item, ast.FunctionDef)]

        # Group methods into user stories
        stories = self._extract_stories_from_methods(methods, node.name)

        # Calculate confidence based on documentation, story quality, and pattern evidence
        confidence = self._calculate_feature_confidence(node, stories, pattern_evidence)

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

    def _filter_relevant_pattern_findings(self, ctx: _PatternEnhancementContext) -> list[dict[str, Any]]:
        """Select findings located inside the owning class in this source file."""
        path = str(ctx.file_path)
        return [
            finding
            for finding in ctx.pattern_findings
            if finding.get("path") == path
            and self._finding_matches_class(finding, ctx.class_start_line, ctx.class_end_line)
        ]

    def _categorise_pattern_finding(
        self,
        finding: dict[str, Any],
    ) -> tuple[str, str]:
        """
        Categorise a single Pattern finding into a type string and its payload value.

        Args:
            finding: Single Pattern finding dict

        Returns:
            Tuple of (category, value) where category is one of
            "api", "model", "auth", "crud", "antipattern", "codesmell", or "".
        """
        rule_id = str(finding.get("check_id", "")).lower()
        extra_raw = finding.get("extra", {})
        extra: dict[str, Any] = extra_raw if isinstance(extra_raw, dict) else {}
        metadata_raw = extra.get("metadata", {})
        metadata: dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
        category_builders = (
            self._categorise_api_finding,
            self._categorise_model_finding,
            self._categorise_auth_finding,
            self._categorise_crud_finding,
            self._categorise_antipattern_finding,
            self._categorise_codesmell_finding,
        )
        for builder in category_builders:
            category, value = builder(finding, rule_id, metadata, extra)
            if category:
                return category, value
        return "", ""

    def _categorise_api_finding(
        self,
        _finding: dict[str, Any],
        rule_id: str,
        metadata: dict[str, Any],
        _extra: Any,
    ) -> tuple[str, str]:
        """Categorise API findings."""
        if "route-detection" not in rule_id:
            return "", ""
        method = str(metadata.get("method", "")).upper()
        path = str(metadata.get("path", ""))
        return ("api", f"{method} {path}") if method and path else ("", "")

    def _categorise_model_finding(
        self,
        _finding: dict[str, Any],
        rule_id: str,
        metadata: dict[str, Any],
        _extra: Any,
    ) -> tuple[str, str]:
        """Categorise model findings."""
        if "model-detection" not in rule_id:
            return "", ""
        model_name = str(metadata.get("model", ""))
        return ("model", model_name) if model_name else ("", "")

    def _categorise_auth_finding(
        self,
        _finding: dict[str, Any],
        rule_id: str,
        metadata: dict[str, Any],
        _extra: Any,
    ) -> tuple[str, str]:
        """Categorise auth findings."""
        if "auth" not in rule_id:
            return "", ""
        permission = str(metadata.get("permission", ""))
        return "auth", permission or "authentication required"

    def _categorise_crud_finding(
        self,
        finding: dict[str, Any],
        rule_id: str,
        metadata: dict[str, Any],
        extra: Any,
    ) -> tuple[str, str]:
        """Categorise CRUD findings."""
        if "crud" not in rule_id:
            return "", ""
        operation = str(metadata.get("operation", "")).upper()
        entity = self._extract_crud_entity(finding, extra)
        return ("crud", f"{operation or 'UNKNOWN'}:{entity or 'unknown'}") if (operation or entity) else ("", "")

    def _extract_crud_entity(self, finding: dict[str, Any], extra: Any) -> str:
        """Extract the target entity from a CRUD finding."""
        if isinstance(extra, dict):
            extra_d: dict[str, Any] = cast(dict[str, Any], extra)
            func_name = str(extra_d.get("message", ""))
        else:
            func_name = ""
        if func_name:
            parts = func_name.split("_")
            return "_".join(parts[1:]) if len(parts) > 1 else ""
        message = str(finding.get("message", "")).lower()
        for operation in ["create", "get", "update", "delete", "add", "find", "remove"]:
            if operation in message:
                parts = message.split(operation + "_")
                if len(parts) > 1 and parts[1]:
                    return parts[1].split()[0]
        return ""

    def _categorise_antipattern_finding(
        self,
        finding: dict[str, Any],
        rule_id: str,
        _metadata: dict[str, Any],
        _extra: Any,
    ) -> tuple[str, str]:
        """Categorise anti-pattern findings."""
        terms = (
            "antipattern",
            "code-smell",
            "god-class",
            "mutable-default",
            "lambda-assignment",
            "string-concatenation",
        )
        return ("antipattern", str(finding.get("message", ""))) if any(term in rule_id for term in terms) else ("", "")

    def _categorise_codesmell_finding(
        self,
        finding: dict[str, Any],
        rule_id: str,
        _metadata: dict[str, Any],
        _extra: Any,
    ) -> tuple[str, str]:
        """Categorise code-smell and security findings."""
        terms = (
            "security",
            "unsafe",
            "insecure",
            "weak-cryptographic",
            "hardcoded-secret",
            "command-injection",
            "deprecated",
        )
        return ("codesmell", str(finding.get("message", ""))) if any(term in rule_id for term in terms) else ("", "")

    def _apply_pattern_findings_to_feature(self, feature: Feature, buckets: _PatternFeatureBuckets) -> None:
        """
        Apply categorised Pattern findings to a feature by updating outcomes and constraints.

        Args:
            feature: Feature to update in-place
            buckets: Categorized source finding lists (API, models, auth, CRUD, anti-patterns, smells).
        """
        if buckets.api_endpoints:
            feature.outcomes.append(f"Exposes API endpoints: {', '.join(buckets.api_endpoints)}")
        if buckets.data_models:
            feature.outcomes.append(f"Defines data models: {', '.join(buckets.data_models)}")
        if buckets.auth_patterns:
            feature.outcomes.append(f"Requires authentication: {', '.join(buckets.auth_patterns)}")
        if buckets.crud_operations:
            crud_str = ", ".join(
                f"{op.get('operation', 'UNKNOWN')} {op.get('entity', 'unknown')}" for op in buckets.crud_operations
            )
            feature.outcomes.append(f"Provides CRUD operations: {crud_str}")
        if buckets.anti_patterns:
            anti_str = "; ".join(buckets.anti_patterns[:3])
            if anti_str:
                if feature.constraints:
                    feature.constraints.append(f"Code quality: {anti_str}")
                else:
                    feature.constraints = [f"Code quality: {anti_str}"]
        if buckets.code_smells:
            smell_str = "; ".join(buckets.code_smells[:3])
            if smell_str:
                if feature.constraints:
                    feature.constraints.append(f"Issues detected: {smell_str}")
                else:
                    feature.constraints = [f"Issues detected: {smell_str}"]

    def _accumulate_pattern_finding_bucket(self, buckets: _PatternFeatureBuckets, category: str, value: str) -> None:
        if category == "api":
            buckets.api_endpoints.append(value)
            buckets.themes.add("API")
            return
        if category == "model":
            buckets.data_models.append(value)
            buckets.themes.add("Database")
            return
        if category == "auth":
            buckets.auth_patterns.append(value)
            buckets.themes.add("Security")
            return
        if category == "crud":
            op, _, entity = value.partition(":")
            buckets.crud_operations.append({"operation": op, "entity": entity})
            return
        if category == "antipattern":
            buckets.anti_patterns.append(value)
            return
        if category == "codesmell":
            buckets.code_smells.append(value)

    def _enhance_feature_with_patterns(self, feature: Feature, ctx: _PatternEnhancementContext) -> None:
        """
        Enrich a feature with findings from parsed source.

        Args:
            feature: Feature to enhance
            ctx: File and class scope for the source findings
        """
        if not ctx.pattern_findings:
            return

        relevant_findings = self._filter_relevant_pattern_findings(ctx)
        if not relevant_findings:
            return

        buckets = _PatternFeatureBuckets()

        for finding in relevant_findings:
            category, value = self._categorise_pattern_finding(finding)
            self._accumulate_pattern_finding_bucket(buckets, category, value)

        self._apply_pattern_findings_to_feature(feature, buckets)
        if ctx.file_theme_accumulator is not None:
            ctx.file_theme_accumulator.update(buckets.themes)

        # Confidence is already calculated with Pattern evidence in _calculate_feature_confidence
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

        # Filter out private methods (except __init__)
        public_methods = [m for m in methods if not m.name.startswith("_") or m.name == "__init__"]

        for method in public_methods:
            # CRUD operations
            if any(crud in method.name.lower() for crud in ["create", "add", "insert", "new"]):
                groups["Create Operations"].append(method)  # type: ignore[reportUnknownMemberType]
            elif any(read in method.name.lower() for read in ["get", "read", "fetch", "find", "list", "retrieve"]):
                groups["Read Operations"].append(method)  # type: ignore[reportUnknownMemberType]
            elif any(update in method.name.lower() for update in ["update", "modify", "edit", "change", "set"]):
                groups["Update Operations"].append(method)  # type: ignore[reportUnknownMemberType]
            elif any(delete in method.name.lower() for delete in ["delete", "remove", "destroy"]):
                groups["Delete Operations"].append(method)  # type: ignore[reportUnknownMemberType]

            # Validation
            elif any(val in method.name.lower() for val in ["validate", "check", "verify", "is_valid"]):
                groups["Validation"].append(method)  # type: ignore[reportUnknownMemberType]

            # Processing/Computation
            elif any(
                proc in method.name.lower() for proc in ["process", "compute", "calculate", "transform", "convert"]
            ):
                groups["Processing"].append(method)  # type: ignore[reportUnknownMemberType]

            # Analysis
            elif any(an in method.name.lower() for an in ["analyze", "parse", "extract", "detect"]):
                groups["Analysis"].append(method)  # type: ignore[reportUnknownMemberType]

            # Generation
            elif any(gen in method.name.lower() for gen in ["generate", "build", "create", "make"]):
                groups["Generation"].append(method)  # type: ignore[reportUnknownMemberType]

            # Comparison
            elif any(cmp in method.name.lower() for cmp in ["compare", "diff", "match"]):
                groups["Comparison"].append(method)  # type: ignore[reportUnknownMemberType]

            # Setup/Configuration
            elif method.name == "__init__" or any(
                setup in method.name.lower() for setup in ["setup", "configure", "initialize"]
            ):
                groups["Configuration"].append(method)  # type: ignore[reportUnknownMemberType]

            # Catch-all for other public methods
            else:
                groups["Core Functionality"].append(method)  # type: ignore[reportUnknownMemberType]

        return dict(groups)

    def _create_story_from_method_group(
        self, group_name: str, methods: list[ast.FunctionDef], class_name: str, story_number: int
    ) -> Story | None:
        """Create a user story from a group of related methods."""
        if not methods:
            return None

        # Generate story key
        story_key = f"STORY-{class_name.upper()}-{story_number:03d}"

        # Create user-centric title based on group
        title = self._generate_story_title(group_name, class_name)

        # Extract testable acceptance criteria using test patterns
        acceptance: list[str] = []
        tasks: list[str] = []

        # Try to extract test patterns from existing tests
        # Use minimal acceptance criteria (examples stored in contracts, not YAML)
        test_patterns = self.test_extractor.extract_test_patterns_for_class(class_name, as_openapi_examples=True)

        # If test patterns found, limit to 1-3 high-level acceptance criteria
        # Detailed test patterns are extracted to OpenAPI contracts (Phase 5)
        if test_patterns:
            # Limit acceptance criteria to 1-3 high-level items per story
            # All detailed test patterns are in OpenAPI contract files
            if len(test_patterns) <= 3:
                acceptance.extend(test_patterns)
            else:
                # Use first 3 as representative high-level acceptance criteria
                # All test patterns are available in OpenAPI contract examples
                acceptance.extend(test_patterns[:3])
                # Note: Remaining test patterns are extracted to OpenAPI examples in contract files

        # Also extract from code patterns (for methods without tests)
        for method in methods:
            # Add method as task
            tasks.append(f"{method.name}()")

            # Extract test patterns from code if no test file patterns found
            if not test_patterns:
                code_patterns = self.test_extractor.infer_from_code_patterns(method, class_name)
                acceptance.extend(code_patterns)

            # Also check docstrings for additional context
            docstring = ast.get_docstring(method)
            if docstring:
                # Check if docstring contains Given/When/Then format (preserve if already present)
                if "Given" in docstring and "When" in docstring and "Then" in docstring:
                    # Extract Given/When/Then from docstring (legacy support)
                    gwt_match = re.search(
                        r"Given\s+(.+?),\s*When\s+(.+?),\s*Then\s+(.+?)(?:\.|$)", docstring, re.IGNORECASE
                    )
                    if gwt_match:
                        # Convert to simple text format (not verbose GWT)
                        then_part = gwt_match.group(3).strip()
                        acceptance.append(then_part)
                else:
                    # Use first line as simple text description (not GWT format)
                    first_line = docstring.split("\n")[0].strip()
                    if first_line and first_line not in acceptance:
                        # Use simple text description (examples will be in OpenAPI contracts)
                        acceptance.append(first_line)

        # Add default simple acceptance if none found
        if not acceptance:
            # Use simple text description (not GWT format)
            # Detailed examples will be extracted to OpenAPI contracts for Specmatic
            acceptance.append(f"{group_name} functionality works correctly")

        # Extract scenarios from control flow (Step 1.2)
        scenarios: dict[str, list[str]] | None = None
        if methods:
            # Extract scenarios from the first method (representative of the group)
            # In the future, we could merge scenarios from all methods in the group
            primary_method = methods[0]
            scenarios = self.control_flow_analyzer.extract_scenarios_from_method(
                primary_method, class_name, primary_method.name
            )

        # Extract contracts from function signatures (Step 2.1)
        contracts: dict[str, Any] | None = None
        if methods:
            # Extract contracts from the first method (representative of the group)
            # In the future, we could merge contracts from all methods in the group
            primary_method = methods[0]
            contracts = self.contract_extractor.extract_function_contracts(primary_method)

        # Calculate story points (complexity) based on number of methods and their size
        story_points = self._calculate_story_points(methods)

        # Calculate value points based on public API exposure
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
        pattern_evidence: dict[str, Any] | None = None,
    ) -> float:
        """
        Calculate confidence score for a feature combining AST + Pattern evidence.

        Args:
            node: AST class node
            stories: List of stories extracted from methods
            pattern_evidence: Optional Pattern findings evidence dict with keys:
                - has_api_endpoints: bool
                - has_database_models: bool
                - has_crud_operations: bool
                - has_auth_patterns: bool
                - has_framework_patterns: bool
                - has_test_patterns: bool
                - has_anti_patterns: bool
                - has_security_issues: bool

        Returns:
            Confidence score (0.0-1.0) combining AST and Pattern evidence
        """
        score = 0.3
        score += self._ast_confidence_bonus(node, stories)
        score += self._pattern_confidence_bonus(pattern_evidence)
        return min(max(score, 0.0), 1.0)

    def _ast_confidence_bonus(self, node: ast.ClassDef, stories: list[Story]) -> float:
        """Calculate AST-derived confidence bonuses."""
        score = 0.0
        if ast.get_docstring(node):
            score += 0.2
        if stories:
            score += 0.2
        if len(stories) > 2:
            score += 0.2
        documented_stories = sum(1 for story in stories if story.acceptance and len(story.acceptance) > 1)
        if stories and documented_stories > len(stories) / 2:
            score += 0.1
        return score

    def _pattern_confidence_bonus(self, pattern_evidence: dict[str, Any] | None) -> float:
        """Calculate confidence adjustments from Pattern evidence."""
        if not pattern_evidence:
            return 0.0
        positive_adjustments = {
            "has_api_endpoints": 0.1,
            "has_database_models": 0.15,
            "has_crud_operations": 0.1,
            "has_auth_patterns": 0.1,
            "has_framework_patterns": 0.05,
            "has_test_patterns": 0.1,
        }
        negative_adjustments = {
            "has_anti_patterns": -0.05,
            "has_security_issues": -0.1,
        }
        score = 0.0
        for key, value in positive_adjustments.items():
            if pattern_evidence.get(key, False):
                score += value
        for key, value in negative_adjustments.items():
            if pattern_evidence.get(key, False):
                score += value
        return score

    def _humanize_name(self, name: str) -> str:
        """Convert snake_case or PascalCase to human-readable title."""
        # Handle PascalCase
        name = re.sub(r"([A-Z])", r" \1", name).strip()
        # Handle snake_case
        name = name.replace("_", " ").replace("-", " ")
        return name.title()

    def _build_dependency_graph(self, python_files: list[Path]) -> None:
        """
        Build module dependency graph using AST imports.

        Creates a directed graph where nodes are modules and edges represent imports.
        """
        # First pass: collect all modules as nodes
        modules: dict[str, Path] = {}
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue

            # Convert file path to module name
            module_name = self._path_to_module_name(file_path)
            modules[module_name] = file_path
            self.dependency_graph.add_node(module_name, path=file_path)

        # Second pass: add edges based on imports
        for module_name, file_path in modules.items():
            try:
                content = file_path.read_text(encoding="utf-8")
                tree = ast.parse(content)

                # Extract imports
                imports = self._extract_imports_from_ast(tree, file_path)
                for imported_module in imports:
                    # Only add edges for modules we know about (within repo)
                    # Try exact match first, then partial match
                    if imported_module in modules:
                        self.dependency_graph.add_edge(module_name, imported_module)
                    else:
                        # Try to find matching module (e.g., "module_a" matches "src.module_a")
                        matching_module = None
                        for known_module in modules:
                            # Check if imported name matches the module name (last part)
                            if imported_module == known_module.split(".")[-1]:
                                matching_module = known_module
                                break
                        if matching_module:
                            self.dependency_graph.add_edge(module_name, matching_module)
                        elif self.entry_point and not any(
                            imported_module.startswith(prefix) for prefix in ["src.", "lib.", "app.", "main.", "core."]
                        ):
                            # Track external dependencies when using entry point
                            # Check if it's a standard library or third-party import
                            # (heuristic: if it doesn't start with known repo patterns)
                            # Likely external dependency
                            self.external_dependencies.add(imported_module)
            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue

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
        imports: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Import aliases (e.g., import foo as bar)
                    if "." in alias.name:
                        # Extract root module (e.g., foo.bar.baz -> foo)
                        root_module = alias.name.split(".")[0]
                        imports.add(root_module)
                    else:
                        imports.add(alias.name)

            elif isinstance(node, ast.ImportFrom) and node.module:
                # From imports (e.g., from foo.bar import baz)
                if "." in node.module:
                    # Extract root module
                    root_module = node.module.split(".")[0]
                    imports.add(root_module)
                else:
                    imports.add(node.module)

        # Try to resolve local imports (relative to current file)
        resolved_imports: list[str] = []
        current_module = self._path_to_module_name(file_path)

        for imported in imports:
            # Skip stdlib imports (common patterns)
            stdlib_modules = {
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

            if imported in stdlib_modules:
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

    def _extract_type_hints(self, tree: ast.AST, file_path: Path) -> dict[str, str]:
        """
        Extract type hints from function/method signatures (legacy version).
        """
        return self._extract_type_hints_parallel(tree, file_path)

    def _extract_type_hints_parallel(self, tree: ast.AST, file_path: Path) -> dict[str, str]:
        """
        Extract type hints from function/method signatures (thread-safe version).

        Returns:
            Dictionary mapping function names to their return type hints
        """
        type_hints: dict[str, str] = {}

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name
                return_type = "None"

                # Extract return type annotation
                if node.returns:
                    # Convert AST node to string representation
                    if isinstance(node.returns, ast.Name):
                        return_type = node.returns.id
                    elif isinstance(node.returns, ast.Subscript):
                        # Handle generics like List[str], Dict[str, int]
                        container = node.returns.value.id if isinstance(node.returns.value, ast.Name) else "Any"
                        return_type = str(container)  # Simplified representation

                type_hints[func_name] = return_type

        return type_hints

    def _detect_async_patterns(self, tree: ast.AST, file_path: Path) -> list[str]:
        """
        Detect async/await patterns in code (legacy version).
        """
        async_methods = self._detect_async_patterns_parallel(tree, file_path)
        module_name = self._path_to_module_name(file_path)
        if module_name not in self.async_patterns:
            self.async_patterns[module_name] = []
        self.async_patterns[module_name].extend(async_methods)
        return async_methods

    def _detect_async_patterns_parallel(self, tree: ast.AST, file_path: Path) -> list[str]:
        """
        Detect async/await patterns in code (thread-safe version).

        Returns:
            List of async method/function names
        """
        async_methods: list[str] = []

        for node in ast.walk(tree):
            # Check for async functions
            if isinstance(node, ast.AsyncFunctionDef):
                async_methods.append(node.name)

            # Check for await statements (even in sync functions)
            if isinstance(node, ast.Await):
                # Find containing function
                for parent in ast.walk(tree):
                    if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for child in ast.walk(parent):
                            if child == node:
                                if parent.name not in async_methods:
                                    async_methods.append(parent.name)
                                break

        return async_methods

    def _analyze_commit_history(self) -> None:
        """
        Mine commit history to identify feature boundaries.

        Uses GitPython to analyze commit messages and associate them with features.
        Limits analysis to recent commits to avoid performance issues.
        """
        try:
            from git import Repo

            if not (self.repo_path / ".git").exists():
                return

            repo = Repo(self.repo_path)
            # Limit to last 100 commits to avoid performance issues with large repositories
            max_commits = 100
            commits = list(repo.iter_commits(max_count=max_commits))

            # Map commits to files to features
            # Note: This mapping would be implemented in a full version
            # For now, we track commit bounds per feature
            for _feature in self.features:
                # Extract potential file paths from feature key
                # This is simplified - in reality we'd track which files contributed to which features
                pass

            # Analyze commit messages for feature references
            for commit in commits:
                try:
                    # Skip commits that can't be accessed (corrupted or too old)
                    # Use commit.message which is lazy-loaded but faster than full commit object
                    commit_message = commit.message
                    if isinstance(commit_message, bytes):
                        commit_message = commit_message.decode("utf-8", errors="ignore")
                    message = commit_message.lower()
                    # Look for feature patterns (e.g., FEATURE-001, feat:, feature:)
                    if "feat" in message or "feature" in message:
                        # Try to extract feature keys from commit message
                        feature_match = re.search(r"feature[-\s]?(\d+)", message, re.IGNORECASE)
                        if feature_match:
                            feature_num = feature_match.group(1)
                            commit_hash = commit.hexsha[:8]  # Short hash

                            # Find feature by key format (FEATURE-001, FEATURE-1, etc.)
                            for feature in self.features:
                                # Match feature key patterns: FEATURE-001, FEATURE-1, Feature-001, etc.
                                if re.search(rf"feature[-\s]?{feature_num}", feature.key, re.IGNORECASE):
                                    # Update commit bounds for this feature
                                    if feature.key not in self.commit_bounds:
                                        # First commit found for this feature
                                        self.commit_bounds[feature.key] = (commit_hash, commit_hash)
                                    else:
                                        # Update last commit (commits are in reverse chronological order)
                                        first_commit, _last_commit = self.commit_bounds[feature.key]
                                        self.commit_bounds[feature.key] = (first_commit, commit_hash)
                                    break
                except Exception:
                    # Skip individual commits that fail (corrupted, etc.)
                    continue

        except ImportError:
            # GitPython not available, skip
            pass
        except Exception:
            # Git operations failed, skip gracefully
            pass

    def _enhance_features_with_dependencies(self) -> None:
        """Enhance features with dependency graph information."""
        for _feature in self.features:
            # Find dependencies for this feature's module
            # This is simplified - would need to track which module each feature comes from
            pass

    @beartype
    @ensure(lambda result: isinstance(result, list), "Must return list")
    def _extract_technology_stack_from_dependencies(self) -> list[str]:
        """
        Extract technology stack from dependency files (requirements.txt, pyproject.toml).

        Returns:
            List of technology constraints extracted from dependency files
        """
        constraints: list[str] = []

        # Try to read requirements.txt
        requirements_file = self.repo_path / "requirements.txt"
        if requirements_file.exists():
            try:
                content = requirements_file.read_text(encoding="utf-8")
                # Parse requirements.txt format: package==version or package>=version
                for line in content.splitlines():
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue

                    # Remove version specifiers for framework detection
                    package = (
                        line.split("==")[0]
                        .split(">=")[0]
                        .split(">")[0]
                        .split("<=")[0]
                        .split("<")[0]
                        .split("~=")[0]
                        .strip()
                    )
                    package_lower = package.lower()

                    # Detect Python version requirement
                    if package_lower == "python":
                        # Extract version from line
                        if ">=" in line:
                            version = line.split(">=")[1].split(",")[0].strip()
                            constraints.append(f"Python {version}+")
                        elif "==" in line:
                            version = line.split("==")[1].split(",")[0].strip()
                            constraints.append(f"Python {version}")

                    # Detect frameworks
                    framework_map = {
                        "fastapi": "FastAPI framework",
                        "django": "Django framework",
                        "flask": "Flask framework",
                        "typer": "Typer for CLI",
                        "tornado": "Tornado framework",
                        "bottle": "Bottle framework",
                    }

                    if package_lower in framework_map:
                        constraints.append(framework_map[package_lower])

                    # Detect databases
                    db_map = {
                        "psycopg2": "PostgreSQL database",
                        "psycopg2-binary": "PostgreSQL database",
                        "mysql-connector-python": "MySQL database",
                        "pymongo": "MongoDB database",
                        "redis": "Redis database",
                        "sqlalchemy": "SQLAlchemy ORM",
                    }

                    if package_lower in db_map:
                        constraints.append(db_map[package_lower])

                    # Detect testing tools
                    test_map = {
                        "pytest": "pytest for testing",
                        "unittest": "unittest for testing",
                        "nose": "nose for testing",
                        "tox": "tox for testing",
                    }

                    if package_lower in test_map:
                        constraints.append(test_map[package_lower])

                    # Detect deployment tools
                    deploy_map = {
                        "docker": "Docker for containerization",
                        "kubernetes": "Kubernetes for orchestration",
                    }

                    if package_lower in deploy_map:
                        constraints.append(deploy_map[package_lower])

                    # Detect data validation
                    if package_lower == "pydantic":
                        constraints.append("Pydantic for data validation")
            except Exception:
                # If reading fails, continue silently
                pass

        # Try to read pyproject.toml
        pyproject_file = self.repo_path / "pyproject.toml"
        if pyproject_file.exists():
            try:
                import tomli  # type: ignore[import-untyped]

                content = pyproject_file.read_text(encoding="utf-8")
                data = tomli.loads(content)

                # Extract Python version requirement
                if "project" in data and "requires-python" in data["project"]:
                    python_req = data["project"]["requires-python"]
                    if python_req:
                        constraints.append(f"Python {python_req}")

                # Extract dependencies
                if "project" in data and "dependencies" in data["project"]:
                    deps = data["project"]["dependencies"]
                    for dep in deps:
                        # Similar parsing as requirements.txt
                        package = (
                            dep.split("==")[0]
                            .split(">=")[0]
                            .split(">")[0]
                            .split("<=")[0]
                            .split("<")[0]
                            .split("~=")[0]
                            .strip()
                        )
                        package_lower = package.lower()

                        # Apply same mapping as requirements.txt
                        framework_map = {
                            "fastapi": "FastAPI framework",
                            "django": "Django framework",
                            "flask": "Flask framework",
                            "typer": "Typer for CLI",
                            "tornado": "Tornado framework",
                            "bottle": "Bottle framework",
                        }

                        if package_lower in framework_map:
                            constraints.append(framework_map[package_lower])

                        db_map = {
                            "psycopg2": "PostgreSQL database",
                            "psycopg2-binary": "PostgreSQL database",
                            "mysql-connector-python": "MySQL database",
                            "pymongo": "MongoDB database",
                            "redis": "Redis database",
                            "sqlalchemy": "SQLAlchemy ORM",
                        }

                        if package_lower in db_map:
                            constraints.append(db_map[package_lower])

                        if package_lower == "pydantic":
                            constraints.append("Pydantic for data validation")
            except ImportError:
                # tomli not available, try tomllib (Python 3.11+)
                try:
                    import tomllib  # type: ignore[import-untyped]

                    # tomllib.load() takes a file object opened in binary mode
                    with pyproject_file.open("rb") as f:
                        data = tomllib.load(f)

                    # Extract Python version requirement
                    if "project" in data and "requires-python" in data["project"]:
                        python_req = data["project"]["requires-python"]
                        if python_req:
                            constraints.append(f"Python {python_req}")

                    # Extract dependencies
                    if "project" in data and "dependencies" in data["project"]:
                        deps = data["project"]["dependencies"]
                        for dep in deps:
                            package = (
                                dep.split("==")[0]
                                .split(">=")[0]
                                .split(">")[0]
                                .split("<=")[0]
                                .split("<")[0]
                                .split("~=")[0]
                                .strip()
                            )
                            package_lower = package.lower()

                            framework_map = {
                                "fastapi": "FastAPI framework",
                                "django": "Django framework",
                                "flask": "Flask framework",
                                "typer": "Typer for CLI",
                                "tornado": "Tornado framework",
                                "bottle": "Bottle framework",
                            }

                            if package_lower in framework_map:
                                constraints.append(framework_map[package_lower])

                            db_map = {
                                "psycopg2": "PostgreSQL database",
                                "psycopg2-binary": "PostgreSQL database",
                                "mysql-connector-python": "MySQL database",
                                "pymongo": "MongoDB database",
                                "redis": "Redis database",
                                "sqlalchemy": "SQLAlchemy ORM",
                            }

                            if package_lower in db_map:
                                constraints.append(db_map[package_lower])

                            if package_lower == "pydantic":
                                constraints.append("Pydantic for data validation")
                except ImportError:
                    # Neither tomli nor tomllib available, skip
                    pass
            except Exception:
                # If parsing fails, continue silently
                pass

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_constraints: list[str] = []
        for constraint in constraints:
            if constraint not in seen:
                seen.add(constraint)
                unique_constraints.append(constraint)

        # Default fallback if nothing extracted
        if not unique_constraints:
            unique_constraints = ["Python 3.11+", "Typer for CLI", "Pydantic for data validation"]

        return unique_constraints

    @beartype
    def _convert_to_gwt_format(self, text: str, method_name: str, class_name: str) -> str:
        """
        DEPRECATED: Convert a text description to Given/When/Then format.

        This method is deprecated. We now use simple text descriptions instead of verbose GWT format.
        Detailed examples are extracted to OpenAPI contracts for Specmatic.

        Args:
            text: Original text description
            method_name: Name of the method
            class_name: Name of the class

        Returns:
            Simple text description (legacy GWT format preserved for backward compatibility)
        """
        # Return simple text instead of GWT format
        # If text already contains GWT keywords, extract the "Then" part
        if "Given" in text and "When" in text and "Then" in text:
            # Extract the "Then" part from existing GWT format
            then_match = re.search(r"Then\s+(.+?)(?:\.|$)", text, re.IGNORECASE)
            if then_match:
                return then_match.group(1).strip()

        # Return simple text description
        return text if text else f"{method_name} works correctly"

    def _get_module_dependencies(self, module_name: str) -> list[str]:
        """Get list of modules that the given module depends on."""
        if module_name not in self.dependency_graph:
            return []

        return list(self.dependency_graph.successors(module_name))
