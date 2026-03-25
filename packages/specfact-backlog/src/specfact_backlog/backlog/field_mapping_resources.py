"""Locate packaged ADO field-mapping template YAML for the backlog bundle."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require
from specfact_cli.utils.ide_setup import find_package_resources_path

from specfact_backlog.backlog.mappers.template_config import FieldMappingConfig


@beartype
@require(lambda framework: isinstance(framework, str), "framework must be str")
@ensure(lambda result: isinstance(result, dict), "Must return dict")
def load_ado_framework_template_config(framework: str) -> dict[str, Any]:
    """
    Load built-in ADO field mapping template config for a framework.

    Returns a dict with keys: framework, field_mappings, work_item_type_mappings.
    Falls back to ado_default.yaml when framework-specific file is unavailable.
    """
    normalized = (framework or "default").strip().lower() or "default"
    candidates = [f"ado_{normalized}.yaml", "ado_default.yaml"]

    candidate_roots: list[Path] = []
    with contextlib.suppress(Exception):
        backlog_packaged = find_package_resources_path(
            "specfact_backlog",
            "resources/templates/backlog/field_mappings",
        )
        if backlog_packaged and backlog_packaged.exists():
            candidate_roots.append(backlog_packaged)

        core_packaged = find_package_resources_path(
            "specfact_cli",
            "resources/templates/backlog/field_mappings",
        )
        if core_packaged and core_packaged.exists():
            candidate_roots.append(core_packaged)

    module_root = Path(__file__).resolve().parents[3]
    candidate_roots.append(module_root / "resources" / "templates" / "backlog" / "field_mappings")

    for root in candidate_roots:
        if not root.exists():
            continue
        for filename in candidates:
            file_path = root / filename
            if file_path.exists():
                with contextlib.suppress(Exception):
                    cfg = FieldMappingConfig.from_file(file_path)
                    return cfg.model_dump()

    return {
        "framework": "default",
        "field_mappings": {},
        "work_item_type_mappings": {},
    }
