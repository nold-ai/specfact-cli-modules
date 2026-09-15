"""Source identities bind local dependency code and ignore generated environments."""

from pathlib import Path

from specfact_code_review.run.runtime_sources import source_identity


def test_virtualenv_changes_do_not_replace_project_source_identity(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("VALUE = 1\n")
    before = source_identity(tmp_path)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv/private.txt").write_text("runtime only")
    assert source_identity(tmp_path) == before
    (tmp_path / "app.py").write_text("VALUE = 2\n")
    assert source_identity(tmp_path) != before


def test_directory_presence_and_modes_bind_source_identity(tmp_path: Path) -> None:
    before = source_identity(tmp_path)
    empty = tmp_path / "optional-source"
    empty.mkdir()
    added = source_identity(tmp_path)
    assert added != before
    empty.chmod(0o700)
    private = source_identity(tmp_path)
    empty.chmod(0o755)
    assert source_identity(tmp_path) != private
    empty.rmdir()
    assert source_identity(tmp_path) == before
    tmp_path.chmod(0o755)
    public_root = source_identity(tmp_path)
    tmp_path.chmod(0o700)
    assert source_identity(tmp_path) != public_root
