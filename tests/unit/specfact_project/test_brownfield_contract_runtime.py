"""Verify the contract cache and the Specmatic boundary used by code import."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from specfact_cli.integrations import specmatic
from specfact_cli.models.plan import Feature, PlanBundle, Product
from specfact_cli.models.source_tracking import SourceTracking

from specfact_project.generators.openapi_extractor import OpenAPIExtractor
from specfact_project.import_cmd.commands import _extract_contracts, _validate_api_specs, _validate_bundle_contracts


@pytest.fixture(name="contract_bundle")
def make_contract_bundle(tmp_path: Path) -> PlanBundle:
    contracts = tmp_path / "contracts"
    contracts.mkdir()
    (contracts / "available.yaml").write_text("openapi: '3.0.3'\npaths: {}\n", encoding="utf-8")
    (contracts / "broken.yaml").write_text("paths: [\n", encoding="utf-8")
    return PlanBundle(
        idea=None,
        business=None,
        product=Product(themes=["Import"]),
        features=[
            Feature(key="FEATURE-AVAILABLE", title="Available contract", contract="contracts/available.yaml"),
            Feature(key="FEATURE-BROKEN", title="Malformed contract", contract="contracts/broken.yaml"),
            Feature(key="FEATURE-MISSING", title="Missing contract", contract="contracts/missing.yaml"),
            Feature(key="FEATURE-UNLINKED", title="Feature without a contract"),
        ],
        clarifications=None,
        metadata=None,
    )


@pytest.mark.parametrize("test_mode", ["true", "false"], ids=["sequential", "workers"])
def test_cached_contracts_omit_invalid_and_missing_files(
    tmp_path: Path, contract_bundle: PlanBundle, monkeypatch: pytest.MonkeyPatch, test_mode: str
) -> None:
    monkeypatch.setenv("TEST_MODE", test_mode)

    contracts = _extract_contracts(tmp_path, tmp_path, contract_bundle, False, lambda _: None)

    assert contracts == {"FEATURE-AVAILABLE": {"openapi": "3.0.3", "paths": {}}}


@pytest.fixture(name="observed_specmatic")
def observe_specmatic(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stand in for the installed Specmatic process and retain the files it sees."""
    calls: list[str] = []

    async def validate(path: Path) -> specmatic.SpecValidationResult:
        calls.append(path.name)
        if path.name.endswith("-error.yaml") or path.suffix == ".json":
            raise OSError("Specmatic process stopped")
        valid = not (path.name.endswith("-invalid.yaml") or path.suffix == ".yml")
        return specmatic.SpecValidationResult(
            is_valid=valid, schema_valid=valid, examples_valid=valid, errors=[] if valid else ["Invalid example"]
        )

    monkeypatch.setenv("TEST_MODE", "false")
    monkeypatch.setattr(specmatic, "check_specmatic_available", lambda: (True, None))
    monkeypatch.setattr(specmatic, "validate_spec_with_specmatic", validate)
    return calls


def test_bundle_validation_counts_rejections_and_limits_the_work(
    tmp_path: Path, contract_bundle: PlanBundle, observed_specmatic: list[str]
) -> None:
    suffixes = ("valid", "invalid", "error", "valid", "valid", "outside-budget")
    for index, suffix in enumerate(suffixes):
        filename = f"check-{index}-{suffix}.yaml"
        (tmp_path / filename).write_text("openapi: '3.0.3'\npaths: {}\n", encoding="utf-8")
        contract_bundle.features.append(Feature(key=f"FEATURE-CHECK{index}", title=filename, contract=filename))

    assert _validate_bundle_contracts(tmp_path, contract_bundle) == (3, 2)
    assert observed_specmatic == [
        "available.yaml",
        "broken.yaml",
        "check-0-valid.yaml",
        "check-1-invalid.yaml",
        "check-2-error.yaml",
    ]


def test_repo_validation_explains_how_to_install_specmatic(
    tmp_path: Path, contract_bundle: PlanBundle, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "openapi.yaml").write_text("openapi: '3.0.3'\npaths: {}\n", encoding="utf-8")
    monkeypatch.setenv("TEST_MODE", "false")
    monkeypatch.setattr(specmatic, "check_specmatic_available", lambda: (False, "Dependency unavailable"))

    _validate_api_specs(tmp_path, tmp_path, contract_bundle)

    assert "Install Specmatic" in capsys.readouterr().out


def test_repo_validation_reports_each_outcome_and_respects_its_budget(
    tmp_path: Path, observed_specmatic: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("openapi.yaml", "openapi.yml", "openapi.json", "asyncapi.yaml"):
        (tmp_path / name).write_text("{}", encoding="utf-8")

    _validate_api_specs(tmp_path)

    assert observed_specmatic == ["openapi.yaml", "openapi.yml", "openapi.json"]
    output = capsys.readouterr().out
    assert "openapi.yaml is valid" in output
    assert "openapi.yml has validation issues" in output
    assert "Specmatic process stopped" in output
    assert "and 1 more spec file" in output


def test_interrupted_cache_load_preserves_the_cached_contract(
    tmp_path: Path, contract_bundle: PlanBundle, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_MODE", "false")
    cached = tmp_path / "contracts" / "available.yaml"
    initial = cached.read_text(encoding="utf-8")
    safe_load = yaml.safe_load

    def interrupt_parse(text: str) -> object:
        if text == initial:
            raise KeyboardInterrupt
        return safe_load(text)

    monkeypatch.setattr(yaml, "safe_load", interrupt_parse)

    with pytest.raises(KeyboardInterrupt):
        _extract_contracts(tmp_path, tmp_path, contract_bundle, False, lambda _: None)
    assert cached.read_text(encoding="utf-8") == initial


def test_interrupted_extraction_leaves_the_bundle_contract_unlinked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupt_extraction(*_args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setenv("TEST_MODE", "false")
    monkeypatch.setenv("SPECFACT_CONTRACT_POOL", "thread")
    monkeypatch.setattr(OpenAPIExtractor, "extract_openapi_from_code", interrupt_extraction)
    (tmp_path / "api.py").write_text("def list_items():\n    return []\n", encoding="utf-8")
    feature = Feature(
        key="FEATURE-ITEMS", title="Items", source_tracking=SourceTracking(implementation_files=["api.py"])
    )
    bundle = PlanBundle(
        idea=None, business=None, product=Product(themes=[]), features=[feature], clarifications=None, metadata=None
    )
    destination = tmp_path / "bundle"

    with pytest.raises(KeyboardInterrupt):
        _extract_contracts(tmp_path, destination, bundle, True, lambda _: None, force=True)
    assert not list((destination / "contracts").glob("*.yaml"))
    assert feature.contract is None
