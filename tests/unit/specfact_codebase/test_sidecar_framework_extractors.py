"""Tests for sidecar framework extractors (path exclusions)."""

from __future__ import annotations

from pathlib import Path

from specfact_codebase.validators.sidecar.frameworks.fastapi import FastAPIExtractor


def _fake_fastapi_main() -> str:
    return """
from fastapi import FastAPI
app = FastAPI()

@app.get("/real")
def real():
    return {"ok": True}
"""


def test_fastapi_extractor_resolves_api_route_methods(tmp_path: Path) -> None:
    """api_route(methods=[...]) should yield a canonical HTTP verb, not the decorator name."""
    (tmp_path / "routes.py").write_text(
        """
from fastapi import APIRouter
router = APIRouter()

@router.api_route("/multi", methods=["GET", "POST"])
def multi():
    return {"ok": True}
""",
        encoding="utf-8",
    )
    extractor = FastAPIExtractor()
    routes = extractor.extract_routes(tmp_path)
    match = next((r for r in routes if r.path == "/multi"), None)
    assert match is not None
    assert match.method == "GET"


def test_fastapi_extractor_ignores_non_http_decorators(tmp_path: Path) -> None:
    """Middleware-style decorators must not overwrite method with bogus verb names."""
    (tmp_path / "app.py").write_text(
        """
from fastapi import FastAPI
app = FastAPI()

@app.middleware("http")
@app.get("/ok")
def ok():
    return {"ok": True}
""",
        encoding="utf-8",
    )
    extractor = FastAPIExtractor()
    routes = extractor.extract_routes(tmp_path)
    match = next((r for r in routes if r.path == "/ok"), None)
    assert match is not None
    assert match.method == "GET"


def test_fastapi_extractor_ignores_specfact_venv_routes(tmp_path: Path) -> None:
    """Routes under .specfact/venv must not be counted (sidecar installs deps there)."""
    (tmp_path / "main.py").write_text(_fake_fastapi_main(), encoding="utf-8")

    venv_app = tmp_path / ".specfact" / "venv" / "lib" / "site-packages" / "fastapi_app"
    venv_app.mkdir(parents=True)
    (venv_app / "noise.py").write_text(
        """
from fastapi import FastAPI
app = FastAPI()

@app.get("/ghost-from-venv")
def ghost():
    return {}
""",
        encoding="utf-8",
    )

    extractor = FastAPIExtractor()
    routes = extractor.extract_routes(tmp_path)
    paths = {route.path for route in routes}
    assert "/real" in paths
    assert "/ghost-from-venv" not in paths
