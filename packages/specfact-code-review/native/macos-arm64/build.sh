#!/bin/sh
set -eu

SOURCE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD=${SPECFACT_NATIVE_BUILD_DIR:-"$SOURCE/build"}
PYTHON_REQUIREMENT_FILE=${SPECFACT_PYTHON_REQUIREMENT_FILE:?set to the designated-requirement file for signed capsule CPython}
IMPOSSIBLE_REQUIREMENT='cdhash H"0000000000000000000000000000000000000000"'

test "$(uname -s)" = Darwin
test "$(uname -m)" = arm64
test -f "$PYTHON_REQUIREMENT_FILE"
mkdir -p "$BUILD/bin" "$BUILD/policy"
rm -f "$BUILD/mach_exc.defs" "$BUILD/mach_exc_server.c" "$BUILD/mach_exc_server.h" "$BUILD/mach_exc_user.h"
cp "$SOURCE/profile.sb" "$BUILD/policy/profile.sb"

SDKROOT=$(xcrun --sdk macosx --show-sdk-path)
cp "$SDKROOT/usr/include/mach/mach_exc.defs" "$BUILD/mach_exc.defs"
chmod 0444 "$BUILD/mach_exc.defs"
xcrun mig -DMACH_EXC_SERVER_AUDITTOKEN=1 -I"$SDKROOT/usr/include" \
  -server "$BUILD/mach_exc_server.c" -sheader "$BUILD/mach_exc_server.h" \
  -user /dev/null -header "$BUILD/mach_exc_user.h" "$BUILD/mach_exc.defs"
chmod 0444 "$BUILD"/mach_exc_server.c "$BUILD"/mach_exc_server.h "$BUILD"/mach_exc_user.h
COMMON="-arch arm64 -mmacosx-version-min=14.0 -O2 -fstack-protector-strong -Wall -Wextra -Werror -Wno-deprecated-declarations"
xcrun --sdk macosx clang $COMMON -isysroot "$SDKROOT" "$SOURCE/bootstrap.c" -o "$BUILD/bin/specfact-native-bootstrap" -lsandbox
codesign --force --sign - --options runtime --entitlements "$SOURCE/entitlements.plist" --identifier ai.nold.specfact.native-bootstrap "$BUILD/bin/specfact-native-bootstrap"
xcrun --sdk macosx clang $COMMON -isysroot "$SDKROOT" "$SOURCE/self_test.c" -o "$BUILD/bin/specfact-native-self-test"
codesign --force --sign - --options runtime --entitlements "$SOURCE/entitlements.plist" --identifier ai.nold.specfact.native-self-test "$BUILD/bin/specfact-native-self-test"
xcrun --sdk macosx clang $COMMON -isysroot "$SDKROOT" "$SOURCE/verifier.c" -o "$BUILD/bin/specfact-native-verifier" -framework Security -framework CoreFoundation
codesign --force --sign - --options runtime --entitlements "$SOURCE/entitlements.plist" --identifier ai.nold.specfact.native-verifier "$BUILD/bin/specfact-native-verifier"

BOOTSTRAP_REQUIREMENT=$(codesign --display --requirements - "$BUILD/bin/specfact-native-bootstrap" 2>&1 | sed -n 's/^# designated => //p')
PYTHON_REQUIREMENT=$(cat "$PYTHON_REQUIREMENT_FILE")
RUFF_REQUIREMENT=$IMPOSSIBLE_REQUIREMENT
SEMGREP_REQUIREMENT=$IMPOSSIBLE_REQUIREMENT
NODE_REQUIREMENT=$IMPOSSIBLE_REQUIREMENT
UV_REQUIREMENT=$IMPOSSIBLE_REQUIREMENT
GIT_REQUIREMENT=$IMPOSSIBLE_REQUIREMENT
test -z "${SPECFACT_RUFF_REQUIREMENT_FILE:-}" || RUFF_REQUIREMENT=$(cat "$SPECFACT_RUFF_REQUIREMENT_FILE")
test -z "${SPECFACT_SEMGREP_REQUIREMENT_FILE:-}" || SEMGREP_REQUIREMENT=$(cat "$SPECFACT_SEMGREP_REQUIREMENT_FILE")
test -z "${SPECFACT_NODE_REQUIREMENT_FILE:-}" || NODE_REQUIREMENT=$(cat "$SPECFACT_NODE_REQUIREMENT_FILE")
test -z "${SPECFACT_UV_REQUIREMENT_FILE:-}" || UV_REQUIREMENT=$(cat "$SPECFACT_UV_REQUIREMENT_FILE")
test -z "${SPECFACT_GIT_REQUIREMENT_FILE:-}" || GIT_REQUIREMENT=$(cat "$SPECFACT_GIT_REQUIREMENT_FILE")
SELF_TEST_REQUIREMENT=$(codesign --display --requirements - "$BUILD/bin/specfact-native-self-test" 2>&1 | sed -n 's/^# designated => //p')
test -n "$BOOTSTRAP_REQUIREMENT"
test -n "$PYTHON_REQUIREMENT"
test -n "$SELF_TEST_REQUIREMENT"
/usr/bin/python3 - "$BUILD/generated_requirements.h" "$BOOTSTRAP_REQUIREMENT" "$PYTHON_REQUIREMENT" "$SELF_TEST_REQUIREMENT" "$RUFF_REQUIREMENT" "$SEMGREP_REQUIREMENT" "$NODE_REQUIREMENT" "$UV_REQUIREMENT" "$GIT_REQUIREMENT" <<'PY'
import json
import pathlib
import sys

target = pathlib.Path(sys.argv[1])
target.write_text(
    "#define SPECFACT_BOOTSTRAP_REQUIREMENT " + json.dumps(sys.argv[2]) + "\n"
    "#define SPECFACT_PYTHON_REQUIREMENT " + json.dumps(sys.argv[3]) + "\n"
    "#define SPECFACT_SELF_TEST_REQUIREMENT " + json.dumps(sys.argv[4]) + "\n"
    "#define SPECFACT_RUFF_REQUIREMENT " + json.dumps(sys.argv[5]) + "\n"
    "#define SPECFACT_SEMGREP_REQUIREMENT " + json.dumps(sys.argv[6]) + "\n"
    "#define SPECFACT_NODE_REQUIREMENT " + json.dumps(sys.argv[7]) + "\n"
    "#define SPECFACT_UV_REQUIREMENT " + json.dumps(sys.argv[8]) + "\n"
    "#define SPECFACT_GIT_REQUIREMENT " + json.dumps(sys.argv[9]) + "\n",
    encoding="utf-8",
)
PY
xcrun --sdk macosx clang $COMMON -isysroot "$SDKROOT" -I"$SOURCE" -I"$BUILD" "$SOURCE/broker.c" "$BUILD/mach_exc_server.c" -o "$BUILD/bin/specfact-native-broker" -framework Security -framework CoreFoundation
codesign --force --sign - --options runtime --entitlements "$SOURCE/entitlements.plist" --identifier ai.nold.specfact.native-broker "$BUILD/bin/specfact-native-broker"
BROKER_REQUIREMENT=$(codesign --display --requirements - "$BUILD/bin/specfact-native-broker" 2>&1 | sed -n 's/^# designated => //p')
test -n "$BROKER_REQUIREMENT"
codesign --verify --strict --verbose=4 "$BUILD/bin/specfact-native-bootstrap"
codesign --verify --strict --verbose=4 "$BUILD/bin/specfact-native-broker"
codesign --verify --strict --verbose=4 "$BUILD/bin/specfact-native-self-test"
codesign --verify --strict --verbose=4 "$BUILD/bin/specfact-native-verifier"

/usr/bin/python3 - "$SOURCE/component.json" "$BUILD" "$BROKER_REQUIREMENT" <<'PY'
import hashlib
import json
import pathlib
import sys

metadata = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
root = pathlib.Path(sys.argv[2])
metadata["broker_designated_requirement"] = sys.argv[3]
metadata["files"] = {
    name: hashlib.sha256((root / name).read_bytes()).hexdigest()
    for name in ("bin/specfact-native-broker", "bin/specfact-native-bootstrap", "bin/specfact-native-self-test", "bin/specfact-native-verifier", "policy/profile.sb")
}
(root / "component.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

# The component directory is itself an authenticated assembly input. Keep
# compiler/MIG intermediates out of that closure after the binaries are built.
rm -f "$BUILD/generated_requirements.h" "$BUILD/mach_exc.defs" \
  "$BUILD/mach_exc_server.c" "$BUILD/mach_exc_server.h" "$BUILD/mach_exc_user.h"
