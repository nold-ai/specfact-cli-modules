import hashlib
import json

import pytest

from scripts.native_release import boundary


@pytest.fixture
def delivered_component(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "provenance").mkdir()
    records = {}
    for name in boundary.COMPONENT_FILES:
        path = source / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(name.encode())
        records[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (source / "provenance/native-component.json").write_text(json.dumps({"files": records}))
    return source


def test_delivered_component_copy_rejects_substitution_before_launch(delivered_component, tmp_path):
    source = delivered_component
    (source / "bin/specfact-native-broker").write_bytes(b"substitution")
    with pytest.raises(ValueError, match="component"):
        boundary.copy_component(source, tmp_path / "copy")
    assert not (tmp_path / "copy").exists()


def test_delivered_component_has_broker_required_private_readonly_modes(delivered_component, tmp_path):
    destination = tmp_path / "copy"
    boundary.copy_component(delivered_component, destination)
    for path in [destination, *destination.rglob("*")]:
        expected = 0o700 if path.is_dir() else 0o500 if path.parent.name == "bin" else 0o400
        assert path.stat().st_mode & 0o777 == expected


def test_worker_cleanup_rejects_observation_after_five_seconds(monkeypatch, tmp_path):
    from types import SimpleNamespace

    clock = [0.0]
    killed = [False]
    lines = iter([json.dumps({"worker": 11, "broker": 12}), "WAIT_SENT"])

    def kill():
        killed[0] = True

    def wait(*, timeout):
        clock[0] = 2.0

    def identity(pid):
        if killed[0]:
            clock[0] = 6.0
            return None
        return str(pid)

    monkeypatch.setattr(boundary.harness, "_line", lambda *_args: next(lines))
    monkeypatch.setattr(boundary.harness, "_identity", identity)
    monkeypatch.setattr(boundary.time, "monotonic", lambda: clock[0])
    controller = SimpleNamespace(kill=kill, wait=wait)
    with pytest.raises(ValueError, match="controller loss"):
        boundary._assert_worker_cleanup(controller, tmp_path, exception_probe=False)
