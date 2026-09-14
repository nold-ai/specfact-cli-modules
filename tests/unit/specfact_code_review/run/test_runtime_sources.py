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
