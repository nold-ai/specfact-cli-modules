import pytest

from scripts.native_release import publish


def test_publication_rejects_unsigned_bytes_before_any_upload(release_inputs, tmp_path, monkeypatch):
    directories, _receipts, _key, public, context = release_inputs
    root = tmp_path / "unsigned"
    (root / "archives").mkdir(parents=True)
    import shutil

    for directory in directories:
        shutil.copytree(directory, root / "archives" / directory.name)
    monkeypatch.setattr(
        publish.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("unsigned bytes reached publisher")
    )
    with pytest.raises((ValueError, FileNotFoundError)):
        publish.publish_release(root, public, context)


def test_publication_rejects_local_context_before_any_upload(tmp_path, monkeypatch):
    monkeypatch.setattr(
        publish.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("local process reached publisher")
    )
    with pytest.raises(ValueError, match="protected"):
        publish.publish_release(tmp_path, b"public", {})


@pytest.mark.parametrize("mutation", ["state_integer", "catalog_float"])
def test_publication_rejects_ambiguous_json_value_types(release_inputs, tmp_path, mutation):
    import json

    from scripts.native_release import release

    directories, receipts, key, public, context = release_inputs
    root = tmp_path / "release"
    release.stage_release(release.StageRequest(directories, receipts, root, public, context), lambda: key)
    if mutation == "state_integer":
        target = root / "release.json"
        document = json.loads(target.read_bytes())
        document["production_eligible"] = 0
    else:
        target = root / "module/resources/contracts/native-capsule-catalog-v1.json"
        document = json.loads(target.read_bytes())
        document["entries"]["darwin-arm64-cp312"]["ghcr"]["max_redirects"] = 4.0
    target.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="publication"):
        publish._signed_inputs(root, public, context["GITHUB_SHA"])
