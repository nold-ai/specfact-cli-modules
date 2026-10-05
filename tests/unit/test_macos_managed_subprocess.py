"""Managed requests cannot become arbitrary host subprocesses."""

import importlib.util
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "scripts/macos_managed_boundary/managed_subprocess.py"


def module():
    spec = importlib.util.spec_from_file_location("managed_subprocess_test", SOURCE)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_bound_run_preserves_actual_status_and_never_launches_host():
    api = module()
    calls = []

    def transport(request):
        calls.append(request)
        return {"returncode": 7, "stdout": "finding", "stderr": "", "broker_verified": True}

    runner = api.ManagedRun({"/payload/ruff": "ruff"}, transport, cwd="/data")
    result = runner.run(["/payload/ruff", "check", "/data/x.py"], capture_output=True, text=True, check=False)
    assert result.returncode == 7 and result.stdout == "finding"
    assert calls[0]["tool"] == "ruff"


def test_unadapted_requests_reject_before_transport():
    api = module()
    calls = []
    runner = api.ManagedRun({"/payload/ruff": "ruff"}, lambda request: calls.append(request), cwd="/data")
    for argv, options in (
        (["/usr/bin/true"], {}),
        (["ruff"], {}),
        (["/payload/ruff"], {"shell": True}),
        (["/payload/ruff"], {"preexec_fn": lambda: None}),
        (["/payload/ruff"], {"pass_fds": (4,)}),
        (["/payload/ruff"], {"env": {"PATH": "/opt/homebrew/bin"}}),
    ):
        with pytest.raises(api.UnadaptedProcessError, match="managed subprocess"):
            runner.run(argv, **options)
    assert not calls


def test_unverified_or_oversized_result_rejects():
    api = module()
    for response in (
        {"broker_verified": False, "returncode": 0, "stdout": "", "stderr": ""},
        {"broker_verified": True, "returncode": 0, "stdout": "x" * (api.MAX_OUTPUT + 1), "stderr": ""},
    ):
        runner = api.ManagedRun({"/payload/ruff": "ruff"}, lambda request, response=response: response, cwd="/data")
        with pytest.raises(api.UnadaptedProcessError):
            runner.run(["/payload/ruff"])


def test_manifest_copy_requires_record_hash(tmp_path):
    spec = importlib.util.spec_from_file_location("candidate_analyzers_test", SOURCE.with_name("python_analyzers.py"))
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    path = tmp_path / "source.py"
    path.write_text("pass\n")
    with pytest.raises(ValueError):
        api.record_bytes(path, "sha256=wrong", "5")


def test_rpath_rewrite_requires_exact_bundled_dependency(tmp_path):
    spec = importlib.util.spec_from_file_location("candidate_analyzers_rpath", SOURCE.with_name("python_analyzers.py"))
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    core = tmp_path / "engine"
    core.write_bytes(b"fixture")
    image = {"rpaths": ["/opt/homebrew/opt/missing/lib"], "dependencies": [{"name": "@rpath/missing.dylib"}]}
    with pytest.raises(ValueError, match="bundled"):
        api.bind_rpaths(core, image, tmp_path, lambda argv: None)


def test_library_loading_experiment_is_explicit_and_profile_identified():
    spec = importlib.util.spec_from_file_location(
        "candidate_analyzers_signing", SOURCE.with_name("python_analyzers.py")
    )
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    assert api.LIBRARY_EXPERIMENT_ENTITLEMENTS == {"com.apple.security.cs.disable-library-validation": True}
    import inspect

    assert inspect.signature(api.prepare).parameters["library_loading_experiment"].default is False


def test_profile_uses_exact_compat_pagesize_not_broad_sysctl(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "candidate_analyzers_profile", SOURCE.with_name("python_analyzers.py")
    )
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    payload = tmp_path / "payload"
    payload.mkdir()
    domain = tmp_path / "domain"
    domain.mkdir()
    stage = tmp_path / "stage"
    stage.mkdir()
    profile = api.plan_profile(
        {"payload": payload, "inventory": {}, "signed_images": []}, domain, stage, payload / "python"
    )
    assert '(sysctl-name "hw.pagesize_compat")' in profile
    assert "(allow sysctl-read)" not in profile


def test_native_output_read_is_bounded_and_rejects_links(tmp_path):
    spec = importlib.util.spec_from_file_location("candidate_analyzers_output", SOURCE.with_name("python_analyzers.py"))
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    output = tmp_path / "output"
    output.write_bytes(b"x" * (4 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="bounded"):
        api.read_output(output)
    output.unlink()
    output.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="regular"):
        api.read_output(output)


def test_profile_does_not_expose_broker_authority(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "candidate_analyzers_authority", SOURCE.with_name("python_analyzers.py")
    )
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    payload, domain, stage = (tmp_path / name for name in ("payload", "domain", "stage"))
    for path in (payload, domain, stage):
        path.mkdir()
    profile = api.plan_profile({"payload": payload, "signed_images": []}, domain, stage, payload / "python")
    assert f'(subpath "{stage}")' not in profile
    assert f'(literal "{stage / "request.json"}")' in profile


def test_native_frontend_identity_preserves_fixed_executable(tmp_path):
    spec = importlib.util.spec_from_file_location("candidate_analyzers_cli", SOURCE.with_name("python_analyzers.py"))
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    candidate = {"payload": tmp_path, "version": "3.13"}
    target, argv, _ = api.admit_request(
        candidate,
        tmp_path,
        "semgrepclean",
        {
            "tool": "semgrep",
            "cwd": str(tmp_path),
            "argv": [str(tmp_path / "bin/semgrep"), "--disable-version-check", "--quiet", "--disable-nosem"],
        },
    )
    assert target == tmp_path / "site-packages/semgrep/bin/semgrep-core"
    assert argv[0] == "osemgrep"


def test_basedpyright_requires_inventoried_fail_closed_preloader(tmp_path):
    spec = importlib.util.spec_from_file_location("candidate_analyzers_node", SOURCE.with_name("python_analyzers.py"))
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    target, argv, _ = api.admit_request(
        {"payload": tmp_path, "version": "3.13"},
        tmp_path,
        "basedpyright",
        {"tool": "basedpyright", "cwd": str(tmp_path), "argv": [str(tmp_path / "bin/basedpyright"), "--outputjson"]},
    )
    assert target == tmp_path / "node/bin/node"
    assert argv[1:5] == [
        "--jitless",
        "--unhandled-rejections=warn",
        "--require",
        str(tmp_path / "trusted/node_guard.cjs"),
    ]


def test_candidate_payload_binds_all_four_offline_manager_plans(tmp_path):
    spec = importlib.util.spec_from_file_location("candidate_manager_plans", SOURCE.with_name("python_analyzers.py"))
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)

    plans = api.write_manager_plans(tmp_path)

    assert set(plans) == {"pip", "hatch", "uv", "poetry"}
    for manager, version in api.project_acquisition.MANAGER_VERSIONS.items():
        path = tmp_path / "managers" / manager / "adapter.json"
        document = __import__("json").loads(path.read_bytes())
        assert document["manager"] == {"name": manager, "version": version}
        assert document["module"] == "specfact_code_review.run.native_project_manager"
        assert document["executes_project_code"] is False


def test_native_unadapted_spawn_is_actionable_not_clean():
    spec = importlib.util.spec_from_file_location(
        "candidate_analyzers_incomplete", SOURCE.with_name("python_analyzers.py")
    )
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    reason = api.native_incomplete(
        "semgrepclean",
        {"stderr": "Fatal error: exception Failure: run ['uname' '-s']: No such file or directory", "returncode": 2},
    )
    assert reason and "uname" in reason and "no host fallback" in reason
    assert api.native_incomplete("ruff", {"stderr": "", "returncode": 1}) is None


def test_certificate_binding_uses_verified_private_bundle(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("candidate_semgrep_ca", SOURCE.with_name("python_analyzers.py"))
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    certificate = tmp_path / "site-packages/certifi/cacert.pem"
    certificate.parent.mkdir(parents=True)
    certificate.write_bytes(b"pinned PEM")
    import hashlib

    monkeypatch.setattr(api, "SEMGREP_CA_SHA256", hashlib.sha256(certificate.read_bytes()).hexdigest())
    candidate = {
        "payload": tmp_path,
        "inventory": {
            "site-packages/certifi/cacert.pem": {
                "kind": "file",
                "sha256": hashlib.sha256(certificate.read_bytes()).hexdigest(),
            }
        },
    }
    env = api.fixed_environment(candidate, tmp_path)
    assert env["SSL_CERT_FILE"] == str(certificate)
    assert env["PATH"] == "/nonexistent"
    assert not any(key in env for key in ("NIX_SSL_CERT_FILE", "OCAML_EXTRA_CA_CERTS", "HTTP_PROXY"))
    certificate.write_bytes(b"changed")
    with pytest.raises(ValueError, match="certificate"):
        api.fixed_environment(candidate, tmp_path)
    certificate.unlink()
    certificate.symlink_to("missing")
    with pytest.raises(ValueError, match="certificate"):
        api.fixed_environment(candidate, tmp_path)


def test_semgrep_adapter_rejects_unpinned_engine_before_launch(tmp_path):
    spec = importlib.util.spec_from_file_location("candidate_semgrep_identity", SOURCE.with_name("python_analyzers.py"))
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    with pytest.raises(ValueError, match="pinned Semgrep"):
        api.validate_semgrep({"site": {"distributions": {"semgrep": "1.175.0"}, "selected_input_hashes": {}}})


def test_semgrep_reference_rejects_unpinned_bytes(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "candidate_semgrep_reference", SOURCE.with_name("python_analyzers.py")
    )
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    path = tmp_path / "reference.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="reference"):
        api.load_semgrep_reference(path)


def test_native_semgrep_process_denials():
    import json
    import os
    import tempfile

    selected = os.environ.get("SPECFACT_SEMGREP_CANDIDATE_RECEIPTS")
    if not selected:
        pytest.skip("maintainer-only Semgrep candidate inputs not selected")
    spec = importlib.util.spec_from_file_location("candidate_semgrep_denials", SOURCE.with_name("python_analyzers.py"))
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    roots = json.loads(selected)
    assert set(roots) == {"3.11", "3.12", "3.13"}
    for abi, prepared in roots.items():
        candidate = api.load_candidate(Path(prepared))
        assert candidate["version"] == abi
        root = Path(tempfile.mkdtemp(prefix="sf-semgrep-denial-", dir="/private/tmp"))
        domain = root / "domain"
        domain.mkdir(mode=0o700)
        target = candidate["payload"] / "site-packages/semgrep/bin/semgrep-core"
        from contextlib import redirect_stdout

        with (root / "diagnostics.log").open("w") as output, redirect_stdout(output):
            result = api.execute(
                root,
                candidate,
                domain,
                target,
                ["osemgrep", "scan", "--experimental", "--oss-only", "--version"],
                request={"kind": "native-tool", "plan_id": api.SEMGREP_PLAN_ID},
                assert_process_denied=True,
            )
        assert result["returncode"] == 0 and result["broker_verified"] is True
        assert result["process_denial_verified"] is True
        assert "1.175.0" in result["stdout"]


def test_self_consistent_inventory_cannot_authorize_unknown_ca(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "candidate_semgrep_ca_unknown", SOURCE.with_name("python_analyzers.py")
    )
    assert spec and spec.loader
    api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api)
    certificate = tmp_path / "site-packages/certifi/cacert.pem"
    certificate.parent.mkdir(parents=True)
    certificate.write_bytes(b"unreviewed CA bytes")
    import hashlib

    candidate = {
        "payload": tmp_path,
        "inventory": {
            "site-packages/certifi/cacert.pem": {
                "kind": "file",
                "sha256": hashlib.sha256(certificate.read_bytes()).hexdigest(),
            }
        },
    }
    with pytest.raises(ValueError, match="certificate"):
        api.fixed_environment(candidate, tmp_path)
