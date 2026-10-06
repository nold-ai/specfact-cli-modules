import pytest

from scripts.native_release import cli


def test_command_does_not_load_environment_key_in_local_shell(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("SPECFACT_NATIVE_CAPSULE_PRIVATE_SIGN_KEY", "never parse this")
    with pytest.raises(ValueError, match="protected"):
        cli.main(
            [
                "sign",
                "--artifacts",
                str(tmp_path),
                "--receipts",
                str(tmp_path / "receipts.json"),
                "--output",
                str(tmp_path / "release"),
            ]
        )


def test_collector_rejects_duplicate_receipt_cells(tmp_path):
    root = tmp_path / "receipts"
    root.mkdir()
    data = '[{"environment_id":"darwin-arm64-cp312","runner":"macos-14"}]'
    (root / "one.json").write_text(data)
    (root / "two.json").write_text(data)
    with pytest.raises(ValueError, match="duplicate"):
        cli.collect_receipts(root, tmp_path / "matrix.json")
    assert not (tmp_path / "matrix.json").exists()


def test_collector_rejects_duplicate_json_fields_before_output(tmp_path):
    root = tmp_path / "receipts"
    root.mkdir()
    (root / "one.json").write_text('{"environment_id":"darwin-arm64-cp312","runner":"macos-14","runner":"macos-15"}')
    with pytest.raises(ValueError, match="duplicate"):
        cli.collect_receipts(root, tmp_path / "matrix.json")
    assert not (tmp_path / "matrix.json").exists()
