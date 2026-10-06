"""Project private sampled stacks onto static public source symbols; never acceptance."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


MAXIMUM_BYTES = 20 * 1024 * 1024
MAXIMUM_SAMPLES = 100_000
MAXIMUM_FRAMES = 100_000
MAXIMUM_DEPTH = 1_000


def tracked_python(root: Path) -> list[Path]:
    """Read tracked Python paths from the subject index without importing its code."""
    result = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"], text=True)
    return [Path(name) for name in result.split("\0") if name.endswith(".py")]


def _public_symbols(root: Path) -> dict[str, set[str]]:
    symbols: dict[str, set[str]] = {}
    for relative in tracked_python(root):
        source = root / relative
        if relative.is_absolute() or ".." in relative.parts or source.is_symlink():
            raise ValueError("invalid tracked source")
        if not source.resolve().is_relative_to(root.resolve()):
            raise ValueError("invalid tracked source")
        tree = ast.parse(source.read_text(encoding="utf-8"))
        symbols[relative.as_posix()] = {
            node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
    return symbols


def _symbol_index(symbols: dict[str, set[str]]) -> dict[str, str | None]:
    index: dict[str, str | None] = {}
    for path in symbols:
        parts = Path(path).parts
        for start in range(len(parts)):
            suffix = "/".join(parts[start:])
            index[suffix] = None if suffix in index else path
    return index


def _public_frame(frame: Any, symbols: dict[str, set[str]], index: dict[str, str | None]) -> tuple[str, str] | None:
    if not isinstance(frame, dict):
        raise ValueError("invalid frame")
    file, function = frame.get("file"), frame.get("name")
    if not isinstance(file, str) or not isinstance(function, str):
        return None
    parts = Path(file).parts
    for start in range(len(parts)):
        suffix = "/".join(parts[start:])
        if suffix not in index:
            continue
        path = index[suffix]
        if path is not None and function in symbols[path]:
            return path, function
        return None
    return None


def _profile_samples(profile: Any, total: int) -> list[Any]:
    if not isinstance(profile, dict) or profile.get("type") != "sampled":
        raise ValueError("invalid sampled profile")
    samples = profile.get("samples")
    if not isinstance(samples, list) or total + len(samples) > MAXIMUM_SAMPLES:
        raise ValueError("invalid sample count")
    return samples


def _sample_symbols(sample: Any, frames: list[tuple[str, str] | None]) -> list[tuple[str, str]]:
    if not isinstance(sample, list) or len(sample) > MAXIMUM_DEPTH:
        raise ValueError("invalid sample depth")
    if any(type(index) is not int or not 0 <= index < len(frames) for index in sample):
        raise ValueError("invalid sample index")
    return [frames[index] for index in sample if frames[index] is not None]


def _sample_counts(profiles: Any, frames: list[Any], symbols: dict[str, set[str]]) -> tuple[int, Counter, Counter]:
    if not isinstance(profiles, list) or len(profiles) > MAXIMUM_FRAMES:
        raise ValueError("invalid sampled profiles")
    index = _symbol_index(symbols)
    public_frames = [_public_frame(frame, symbols, index) for frame in frames]
    counts: Counter = Counter()
    leaves: Counter = Counter()
    total = 0
    for profile in profiles:
        samples = _profile_samples(profile, total)
        for sample in samples:
            stack = _sample_symbols(sample, public_frames)
            counts.update(set(stack))
            leaves.update(stack[-1:])
        total += len(samples)
    return total, counts, leaves


def _rows(counts: Counter, label: str) -> list[dict[str, Any]]:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]
    return [{"file": file, "function": function, label: count} for (file, function), count in ordered]


def summarize(profile: Path, repository: Path) -> dict[str, Any]:
    """Return bounded inclusive/deepest-public sample counts without copying private profile fields."""
    with profile.open("rb") as stream:
        payload = stream.read(MAXIMUM_BYTES + 1)
    if len(payload) > MAXIMUM_BYTES:
        raise ValueError("profile size exceeds limit")
    data = json.loads(payload)
    if not isinstance(data, dict) or not isinstance(data.get("shared"), dict):
        raise ValueError("invalid profile structure")
    frames = data["shared"].get("frames")
    if not isinstance(frames, list) or len(frames) > MAXIMUM_FRAMES:
        raise ValueError("invalid frame count")
    total, counts, leaves = _sample_counts(data.get("profiles"), frames, _public_symbols(repository))
    return {
        "status": "DIAGNOSTIC_ONLY",
        "samples": total,
        "public_frames": _rows(counts, "inclusive_samples"),
        "public_leaf_frames": _rows(leaves, "leaf_samples"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = summarize(args.profile, args.repository)
    except (OSError, ValueError, SyntaxError, RecursionError, subprocess.SubprocessError):
        print(json.dumps({"status": "DIAGNOSTIC_UNAVAILABLE"}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
