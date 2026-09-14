"""Target namespaces cannot write their supervisor results."""


def test_target_worker_cannot_write_controller_output_or_share_pid_namespace() -> None:
    from specfact_code_review.run.target_launch import target_command

    argv = target_command("pylint", ["app.py"])
    assert "--unshare-all" in argv
    assert "--share-net" not in argv
    assert argv[argv.index("--ro-bind") + 1 : argv.index("--ro-bind") + 3] == ["/", "/"]
    assert argv[argv.index("/opt/specfact/output") - 1 : argv.index("/opt/specfact/output") + 1] == [
        "--tmpfs",
        "/opt/specfact/output",
    ]
    assert "/opt/specfact/builtin/specfact_code_review/run/target_bootstrap.py" in argv


def test_project_python_preserves_extensionless_script_arguments(monkeypatch) -> None:
    from specfact_code_review.run import target_launch

    captured = []
    monkeypatch.setattr(target_launch.sys, "argv", ["python", "manage", "--version"])
    monkeypatch.setattr(target_launch.os, "execv", lambda executable, argv: captured.append(argv))
    target_launch.main()
    assert captured[0][-3:] == ["python-argv", "manage", "--version"]
