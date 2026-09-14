"""Builder inventories retain dependency facts without credentials."""


def test_inventory_never_serializes_index_credentials() -> None:
    from specfact_code_review.run.runtime_build_driver import clean_inventory

    inventory = clean_inventory(
        {
            "installed": [
                {
                    "metadata": {
                        "name": "consumer",
                        "version": "1",
                        "description": "do not retain arbitrary metadata",
                        "requires_dist": ["dependency @ https://user:secret@example.test/pkg.whl?token=secret"],
                    },
                    "direct_url": {"url": "https://user:secret@example.test/pkg.whl?token=secret"},
                }
            ]
        }
    )
    import json

    encoded = json.dumps(inventory)
    assert "secret" not in encoded
    assert "description" not in encoded
    assert "example.test/pkg.whl" in encoded


def test_hatch_export_selects_one_native_matrix_environment() -> None:
    from specfact_code_review.run.runtime_build_driver import select_hatch_environment

    export = {"hatch-test.py3.11": {"python": "3.11"}, "hatch-test.py3.12": {"python": "3.12"}}
    assert select_hatch_environment(export, "hatch-test", "3.12") == "hatch-test.py3.12"


def test_hatch_export_rejects_ambiguous_matrix() -> None:
    import pytest

    from specfact_code_review.run.runtime_build_driver import select_hatch_environment

    export = {"test.py3.12-a": {"python": "3.12"}, "test.py3.12-b": {"python": "3.12"}}
    with pytest.raises(RuntimeError, match="project_environment_ambiguous"):
        select_hatch_environment(export, "test", "3.12")


def test_distribution_executables_are_rebased_and_unowned_files_excluded(tmp_path) -> None:
    from specfact_code_review.run.runtime_build_driver import copy_executables

    environment, artifact = tmp_path / "env", tmp_path / "artifact"
    (environment / "bin").mkdir(parents=True)
    artifact.mkdir()
    (environment / "bin/customer").write_text('#!/private/build/env/bin/python\nprint("customer")\n')
    (environment / "bin/uv").write_bytes(b"\x7fELFowned-native-executable")
    (environment / "bin/unowned").write_text("do not import host tools")
    records = [
        {"path": str(environment / "bin/customer"), "distribution": "customer"},
        {"path": str(environment / "bin/uv"), "distribution": "uv"},
    ]
    copied = copy_executables(environment, artifact, records)
    assert len(copied) == 2
    assert "/private/build" not in (artifact / "bin/customer").read_text()
    assert (artifact / "bin/customer").read_text().startswith("#!/opt/specfact/project-runtime/bin/python\n")
    assert (artifact / "executables/uv").read_bytes().startswith(b"\x7fELF")
    assert not (artifact / "bin/unowned").exists()


def test_hatch_export_has_its_owned_uv_executable(monkeypatch) -> None:
    from specfact_code_review.run import runtime_build_driver as driver

    observed = []

    def run(command, *, env=None):
        assert env is not None
        observed.append(env.copy())
        return '{"review": {}}'

    monkeypatch.setattr(driver, "_run", run)
    driver._prepare_hatch({"environment": "review"}, "/private/tools/bin/python", {})
    assert observed[0]["HATCH_UV"] == "/private/tools/bin/uv"


def test_hatch_dependencies_are_not_redirected_into_the_pip_environment() -> None:
    from specfact_code_review.run.runtime_build_driver import installer_environment

    hatch = installer_environment("hatch", {"PATH": "/usr/bin", "PIP_PYTHON": "/wrong/python", "VIRTUAL_ENV": "/wrong"})
    assert "PIP_PYTHON" not in hatch
    assert "VIRTUAL_ENV" not in hatch
    assert installer_environment("pip", {})["PIP_PYTHON"] == "/opt/specfact/output/env/bin/python"
    assert installer_environment("poetry", {})["VIRTUAL_ENV"] == "/opt/specfact/output/env"
