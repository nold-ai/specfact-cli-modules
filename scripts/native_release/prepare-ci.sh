#!/bin/bash
# Maintainer-only source preparation. This script never reads signing secrets.
set -euo pipefail
MODE="${1:?tools or cp311/cp312/cp313}"
INPUT_ROOT="${2:?fresh absolute input root}"
case "$INPUT_ROOT" in /*) ;; *) exit 2 ;; esac
case "$MODE" in tools|cp311|cp312|cp313) ;; *) exit 2 ;; esac
mkdir -m 700 "$INPUT_ROOT"
fetch_sha256() {
    curl --fail --location --retry 2 --connect-timeout 15 --max-time 300 --max-filesize 250000000 --proto '=https' --tlsv1.2 "$1" --output "$2"
    test "$(shasum -a 256 "$2" | cut -d ' ' -f 1)" = "$3"
}
if [ "$MODE" = tools ]; then
    git init -q "$INPUT_ROOT/uv-source"
    git -C "$INPUT_ROOT/uv-source" fetch --depth=1 https://github.com/astral-sh/uv.git 0ebbd9274a55a8a53a13970be3b97e4209598e17
    git -C "$INPUT_ROOT/uv-source" checkout --detach -q FETCH_HEAD
    rustup toolchain install 1.96.0 --profile minimal
    TOOLCHAIN_ROOT="$(rustup run 1.96.0 rustc --print sysroot)"
    mkdir "$INPUT_ROOT/cargo"
    CARGO_HOME="$INPUT_ROOT/cargo" rustup run 1.96.0 cargo fetch --locked --manifest-path "$INPUT_ROOT/uv-source/Cargo.toml"
    python -m scripts.build_macos_managed_uv --upstream-source "$INPUT_ROOT/uv-source" --output "$INPUT_ROOT/managed-uv" --rust-toolchain "$TOOLCHAIN_ROOT" --cargo-home "$INPUT_ROOT/cargo"
    fetch_sha256 https://www.kernel.org/pub/software/scm/git/git-2.54.0.tar.xz "$INPUT_ROOT/git.tar.xz" f689162364c10de79ef89aa8dbf48731eb057e34edbbd20aca510ce0154681a3
    python -m scripts.build_macos_managed_git --source-archive "$INPUT_ROOT/git.tar.xz" --output "$INPUT_ROOT/managed-git"
    exit 0
fi
case "$MODE" in
    cp311) PY_VERSION=3.11.16; RELEASE_DATE=20260901; CP_SHA=768f05cf200273bbdda9a5955a5a6892a4b22f2a0b1e4b0a9160f5c7fce86816 ;;
    cp312) PY_VERSION=3.12.14; RELEASE_DATE=20260901; CP_SHA=81a359f1cfadd4da11766534c5913791cea55f26e1bb902cacd2a531bb1e4b2b ;;
    cp313) PY_VERSION=3.13.14; RELEASE_DATE=20260805; CP_SHA=f0e634654e1d6b55cf81419eb629caf78f50234d01ede318f78e5091bada6085 ;;
esac
fetch_sha256 "https://github.com/astral-sh/python-build-standalone/releases/download/$RELEASE_DATE/cpython-$PY_VERSION%2B$RELEASE_DATE-aarch64-apple-darwin-install_only_stripped.tar.gz" "$INPUT_ROOT/python.tar.gz" "$CP_SHA"
python - "$INPUT_ROOT" <<'PY'
import sys,tarfile
from pathlib import Path
root=Path(sys.argv[1])
with tarfile.open(root/'python.tar.gz') as archive:
    archive.extractall(root, filter='data')
PY
fetch_sha256 https://nodejs.org/dist/v24.16.0/node-v24.16.0-darwin-arm64.tar.gz "$INPUT_ROOT/node.tar.gz" 39189dab4eeb15706c424af0ac08a3044c9e48f7db12a7d77f6b7aafc7dd5df6
curl --fail --location --connect-timeout 15 --max-time 300 --max-filesize 250000000 --proto '=https' https://registry.npmjs.org/basedpyright/-/basedpyright-1.39.10.tgz --output "$INPUT_ROOT/basedpyright.tgz"
test ! -L "$PWD/.specfact"
mkdir -p -m 700 "$PWD/.specfact"
# The existing packager verifies the reviewed npm SHA-512 integrity value.
python -m scripts.native_node_package --node-archive "$INPUT_ROOT/node.tar.gz" --basedpyright-archive "$INPUT_ROOT/basedpyright.tgz" --output "$PWD/.specfact/native-node-runtime"
fetch_sha256 https://files.pythonhosted.org/packages/01/9a/cdb6db09d6aff6a803a94505aa24666db5e47df7aad0f2b1b0ddcb52ed12/z3_solver-5.1.0.0-py3-none-macosx_13_0_arm64.whl "$INPUT_ROOT/z3.whl" 399a38a85d784105e5df5a05c04a581481bfdb80af7424779cf76fa843b4e66c
fetch_sha256 https://github.com/Z3Prover/z3/releases/download/z3-5.1.0/z3-5.1.0-arm64-osx-13.3.zip "$INPUT_ROOT/z3.zip" 81d29e934fd863079a74af35eecaeaef8047e0e12414d33ca322b358d68383db
python -m scripts.native_z3_wheel "$INPUT_ROOT/z3.whl" "$INPUT_ROOT/z3-projection" --release-archive "$INPUT_ROOT/z3.zip" --darwin-only
"$INPUT_ROOT/python/bin/python3" -m venv "$INPUT_ROOT/venv"
if [ "$MODE" = cp311 ]; then
    # 3.11 venv seeds setuptools; it is absent from the reviewed analyzer lock.
    # Remove only that bootstrap package in this fresh maintainer-owned venv.
    "$INPUT_ROOT/venv/bin/python" -m pip uninstall --yes setuptools
fi
"$INPUT_ROOT/venv/bin/python" -m pip install --require-hashes --find-links "$INPUT_ROOT/z3-projection" -r "scripts/native_analyzer_inputs/darwin-arm64-$MODE.txt"
