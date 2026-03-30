"""Tool export smoke tests."""

# pylint: disable=import-outside-toplevel


def test_tools_exports_run_functions() -> None:
    from specfact_code_review import tools as tools_module

    run_ast_clean_code = tools_module.run_ast_clean_code
    run_radon = tools_module.run_radon
    run_semgrep = tools_module.run_semgrep

    assert callable(run_ast_clean_code)
    assert callable(run_radon)
    assert callable(run_semgrep)
