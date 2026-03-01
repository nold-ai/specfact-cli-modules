"""Patch pipeline: generator, applier, idempotency."""

from specfact_govern.patch_mode.patch_mode.pipeline.applier import apply_patch_local, apply_patch_write
from specfact_govern.patch_mode.patch_mode.pipeline.generator import generate_unified_diff
from specfact_govern.patch_mode.patch_mode.pipeline.idempotency import check_idempotent


__all__ = ["apply_patch_local", "apply_patch_write", "check_idempotent", "generate_unified_diff"]
