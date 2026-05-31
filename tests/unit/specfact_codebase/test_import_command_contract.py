from __future__ import annotations

from typer.testing import CliRunner

from specfact_codebase.import_cmd.commands import app


def test_code_import_legacy_option_order_reports_canonical_invocation(tmp_path) -> None:
    result = CliRunner().invoke(app, ["legacy-api", "--repo", str(tmp_path)])

    assert result.exit_code != 0
    output = result.stdout.lower()
    assert "canonical" in output or "use:" in output
    assert "code import --repo" in output
    assert "no such command '--repo'" not in output
