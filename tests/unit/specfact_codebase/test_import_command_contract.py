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


def test_explicit_bridge_help_describes_its_flags() -> None:
    result = CliRunner().invoke(app, ["from-bridge", "--help"])

    assert result.exit_code == 0, result.output
    assert "from-bridge" in result.output
    assert "--write" in result.output
    assert "--dry-run" in result.output
