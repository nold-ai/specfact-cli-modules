"""Runtime plans can relocate while retaining their dependency identity."""

from pathlib import Path

from specfact_code_review.run.runtime_models import ProjectPlan


def test_plan_identity_excludes_checkout_location(tmp_path: Path) -> None:
    first = ProjectPlan(root=tmp_path / "first", manager="pip", inputs={"requirements.txt": "sha256:" + "a" * 64})
    second = ProjectPlan(root=tmp_path / "second", manager="pip", inputs=dict(first.inputs))
    assert first.identity == second.identity
    assert "root" not in first.document()
