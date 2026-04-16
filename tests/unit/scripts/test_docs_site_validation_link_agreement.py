"""Tests for published vs filesystem agreement in ``docs_site_validation``."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import docs_site_validation as dsv  # noqa: E402


def _ctx_for(docs: Path) -> dsv.DocsLinkResolutionContext:
    route_to_path, path_to_route = dsv.build_route_mappings(docs)
    return dsv.DocsLinkResolutionContext(docs, route_to_path, path_to_route, dsv.MODULES_DOCS_HOST)


def test_hybrid_rejects_repo_relative_when_disk_and_browser_targets_diverge(tmp_path: Path) -> None:
    """``../..`` from a deep ``/bundles/.../`` permalink must not pass on filesystem match alone."""
    docs = tmp_path / "docs"
    (docs / "bundles" / "deep").mkdir(parents=True)
    (docs / "guides").mkdir(parents=True)
    (docs / "bundles" / "deep" / "page.md").write_text(
        """---
layout: default
title: Deep page
permalink: /bundles/deep/here/
---
[bad](../../guides/target/)
""",
        encoding="utf-8",
    )
    (docs / "guides" / "target.md").write_text(
        """---
layout: default
title: Target
permalink: /guides/target/
---
""",
        encoding="utf-8",
    )
    ctx = _ctx_for(docs)
    source = docs / "bundles" / "deep" / "page.md"
    target, err = dsv.resolve_internal_link_hybrid(
        source=source,
        ctx=ctx,
        published_page_route="/bundles/deep/here/",
        raw_link="../../guides/target/",
    )
    assert target is None
    assert err is not None
    assert "missing published route" in err or "root-absolute" in err


def test_hybrid_accepts_root_absolute_when_target_exists(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "bundles" / "deep").mkdir(parents=True)
    (docs / "guides").mkdir(parents=True)
    (docs / "bundles" / "deep" / "page.md").write_text(
        """---
layout: default
title: Deep page
permalink: /bundles/deep/here/
---
[ok](/guides/target/)
""",
        encoding="utf-8",
    )
    (docs / "guides" / "target.md").write_text(
        """---
layout: default
title: Target
permalink: /guides/target/
---
""",
        encoding="utf-8",
    )
    ctx = _ctx_for(docs)
    source = docs / "bundles" / "deep" / "page.md"
    target, err = dsv.resolve_internal_link_hybrid(
        source=source,
        ctx=ctx,
        published_page_route="/bundles/deep/here/",
        raw_link="/guides/target/",
    )
    assert err is None
    assert target == (docs / "guides" / "target.md").resolve()


def test_parent_traversal_outside_bundles_keeps_filesystem_first_semantics(tmp_path: Path) -> None:
    """``../`` from non-``/bundles/`` permalinks must not require published agreement (legacy)."""
    docs = tmp_path / "docs"
    (docs / "adapters").mkdir(parents=True)
    (docs / "guides").mkdir(parents=True)
    (docs / "adapters" / "page.md").write_text(
        """---
layout: default
title: Adapter page
permalink: /adapters/page/
---
[guide](../guides/target.md)
""",
        encoding="utf-8",
    )
    (docs / "guides" / "target.md").write_text(
        """---
layout: default
title: Guide
permalink: /guides/target/
---
""",
        encoding="utf-8",
    )
    ctx = _ctx_for(docs)
    source = docs / "adapters" / "page.md"
    target, err = dsv.resolve_internal_link_hybrid(
        source=source,
        ctx=ctx,
        published_page_route="/adapters/page/",
        raw_link="../guides/target.md",
    )
    assert err is None
    assert target == (docs / "guides" / "target.md").resolve()


def test_hybrid_uses_published_semantics_when_filesystem_misses(tmp_path: Path) -> None:
    """Sibling ``../run/`` style links often miss on disk but are valid on the site URL."""
    docs = tmp_path / "docs"
    (docs / "bundles" / "cr").mkdir(parents=True)
    (docs / "bundles" / "cr" / "overview.md").write_text(
        """---
layout: default
title: Overview
permalink: /bundles/cr/here/
---
[run](../run/)
""",
        encoding="utf-8",
    )
    (docs / "bundles" / "cr" / "run.md").write_text(
        """---
layout: default
title: Run
permalink: /bundles/cr/run/
---
""",
        encoding="utf-8",
    )
    ctx = _ctx_for(docs)
    source = docs / "bundles" / "cr" / "overview.md"
    target, err = dsv.resolve_internal_link_hybrid(
        source=source,
        ctx=ctx,
        published_page_route="/bundles/cr/here/",
        raw_link="../run/",
    )
    assert err is None
    assert target == (docs / "bundles" / "cr" / "run.md").resolve()
