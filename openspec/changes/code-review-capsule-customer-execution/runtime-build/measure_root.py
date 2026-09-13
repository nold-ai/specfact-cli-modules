import hashlib
import importlib
import json
import os
import stat
import sys
from pathlib import Path


def _digest(value):
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
    )


def _entries(root, include_root):
    paths = list(root.rglob("*")) + ([root] if include_root else [])
    result = []
    size = 0
    for path in sorted(paths, key=lambda p: p.relative_to(root.parent).as_posix().encode()):
        info = path.lstat()
        item = {
            "mode": stat.S_IMODE(info.st_mode),
            "path": path.relative_to(root.parent if include_root else root).as_posix(),
        }
        if stat.S_ISDIR(info.st_mode):
            item["type"] = "directory"
        elif stat.S_ISREG(info.st_mode):
            with path.open("rb") as stream:
                checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            item.update(type="regular_file", size=info.st_size, sha256="sha256:" + checksum)
            size += info.st_size
        elif stat.S_ISLNK(info.st_mode):
            item.update(type="symlink", target=os.readlink(path))
        else:
            raise ValueError(str(path))
        result.append(item)
    return {"entry_count": len(result), "regular_file_bytes": size, "manifest_digest": _digest(result)}


def _main():
    root = Path("/opt/specfact")
    report = _entries(root, False)
    report["subroots"] = {path.name: _entries(path, True) for path in sorted(root.iterdir())}
    sys.path.insert(0, "/opt/specfact/analyzers")
    beartype = importlib.import_module("beartype")

    assert beartype.__version__ == "0.22.9"
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    _main()
