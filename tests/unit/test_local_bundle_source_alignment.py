from __future__ import annotations

import sys
import types
from pathlib import Path

from tests import conftest as test_bootstrap


# pylint: disable=protected-access
def test_enforce_local_bundle_sources_removes_shadowed_user_bundle_modules(monkeypatch) -> None:
    user_bundle_src = str((Path.home() / ".specfact" / "modules" / "specfact-backlog" / "src").resolve())
    local_bundle_src = str((test_bootstrap.MODULES_REPO_ROOT / "packages" / "specfact-backlog" / "src").resolve())
    fake_module_path = f"{user_bundle_src}/specfact_backlog/backlog/commands.py"

    monkeypatch.setattr(sys, "path", [user_bundle_src, local_bundle_src, *sys.path], raising=False)

    for module_name in (
        "specfact_backlog",
        "specfact_backlog.backlog",
        "specfact_backlog.backlog.commands",
    ):
        shadowed_module = types.ModuleType(module_name)
        shadowed_module.__file__ = fake_module_path
        monkeypatch.setitem(sys.modules, module_name, shadowed_module)

    test_bootstrap._enforce_local_bundle_sources()

    assert user_bundle_src not in sys.path
    assert local_bundle_src in sys.path[:5]
    assert "specfact_backlog" not in sys.modules
    assert "specfact_backlog.backlog" not in sys.modules
    assert "specfact_backlog.backlog.commands" not in sys.modules
