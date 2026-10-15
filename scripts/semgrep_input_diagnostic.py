from __future__ import annotations

import argparse
import contextlib
import ctypes
import hashlib
import json
import os
import selectors
import signal
import sys
import threading
import time
from pathlib import Path, PurePosixPath
from typing import Any


SUBJECT_HEAD = "22c0f92f681aac7d9edbfde305963823866d0a7e"
SUBJECT_BASE = "593656f675eaf4954b609aca51aa6504367dc02e"
ALIAS = "refs/heads/codex/pr510-semgrep-once-25"
RAW_LIMIT = 32 * 1024 * 1024
PUBLIC_LIMIT = 256 * 1024
KEY_SHA256 = "4e54ffb02307e1a85c166c40aba6d1bc40fbb9a8ef40bf756f8870e5bb08d1c8"
PAYLOAD_SHA256 = "d4bcfd8db105c60440b3bdefbe414f1dc148a75c21b8533801d43d888b3d0df4"
LOCK_SHA256 = "395c7eb2d3f4a4dd471840c2c8672a0ec218c4b47fb84c400b875170d4dd7aaa"
RULE_ROOT = "packages/specfact-code-review/src/specfact_code_review/"
CALLS = (("head", "clean"), ("head", "bugs"), ("base", "clean"), ("base", "bugs"))


def admit(event, sha, attempt, parents):
    if not (
        event.get("ref") == ALIAS
        and event.get("created") is True
        and event.get("deleted") is False
        and event.get("before") == "0" * 40
        and event.get("after") == sha
        and attempt == "1"
        and len(sha) == 40
        and all(c in "0123456789abcdef" for c in sha)
        and parents == [SUBJECT_HEAD]
    ):
        raise ValueError("admission")


def private_file(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        return os.fdopen(fd, "wb")
    except BaseException:
        os.close(fd)
        raise


def _children():
    pending, descendants = [os.getpid()], set()
    while pending:
        parent = pending.pop()
        try:
            children = Path(f"/proc/{parent}/task/{parent}/children").read_text().split()
        except FileNotFoundError:
            continue
        for child in children:
            pid = int(child)
            if pid not in descendants:
                descendants.add(pid)
                pending.append(pid)
    return descendants


def _reap_tree(pid):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        children = _children() if sys.platform == "linux" else {pid}
        for child in children:
            with contextlib.suppress(ProcessLookupError, FileNotFoundError):
                before = Path(f"/proc/{child}/stat").read_text().rsplit(")", 1)[1].split()[19]
                handle = os.pidfd_open(child)
                try:
                    after = Path(f"/proc/{child}/stat").read_text().rsplit(")", 1)[1].split()[19]
                    if before == after and child in _children():
                        signal.pidfd_send_signal(handle, signal.SIGKILL)
                finally:
                    os.close(handle)
        with contextlib.suppress(ChildProcessError):
            while os.waitpid(-1, os.WNOHANG)[0]:
                pass
        if sys.platform == "linux" and not _children():
            return True
        if sys.platform != "linux":
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pid, signal.SIGKILL)
            return True
        time.sleep(0.01)
    return False


class _CaptureCancellation:
    def __init__(self):
        self.handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
        self.mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
        self.first_signal = None

    def record(self, signum, _frame):
        if self.first_signal is None:
            self.first_signal = signum

    def install(self):
        for sig in self.handlers:
            signal.signal(sig, self.record)

    def restore(self):
        restored = True
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK, self.mask)
        except BaseException:
            restored = False
        for sig, handler in self.handlers.items():
            try:
                signal.signal(sig, handler)
            except BaseException:
                restored = False
        return restored


def _spawn(command, stdout, stderr, descriptor, sandbox, environment, inherited):
    pid = os.fork()
    if pid:
        return pid
    try:
        for sig, handler in inherited.handlers.items():
            signal.signal(sig, handler)
        signal.pthread_sigmask(signal.SIG_SETMASK, inherited.mask)
        if sandbox is None:
            os.setsid()
        null = os.open(os.devnull, os.O_RDONLY)
        os.dup2(null, 0)
        os.dup2(stdout, 1)
        os.dup2(stderr, 2)
        if descriptor is not None:
            os.set_inheritable(descriptor, True)
        maximum = os.sysconf("SC_OPEN_MAX")
        if descriptor is None:
            os.closerange(3, maximum)
        else:
            os.closerange(3, descriptor)
            os.closerange(descriptor + 1, maximum)
        if sandbox is not None:
            sandbox._request_exec_trace()
        os.execve(command[0], command, environment)
    except BaseException:
        os._exit(125)


def capture(command, directory, name, seconds, limit, *, descriptor=None, sandbox=None, environment=None):
    started = time.monotonic()
    if threading.current_thread() is not threading.main_thread() or threading.active_count() != 1:
        raise ValueError("single_thread_required")
    if sys.platform == "linux" and ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) != 0:
        raise ValueError("subreaper")
    result = {"returncode": None, "bytes": 0, "gap": None, "cleaned": False}
    cancellation = _CaptureCancellation()

    def checkpoint():
        if cancellation.first_signal is not None:
            result["gap"] = result["gap"] or "supervision_failed"
        elif time.monotonic() - started >= seconds:
            result["gap"] = result["gap"] or "deadline"
        if result["gap"]:
            raise InterruptedError("capture_stopped")

    try:
        cancellation.install()
        with contextlib.ExitStack() as stack:
            pipes = []
            pid = None
            try:
                outputs = []
                for stream in ("stdout", "stderr"):
                    checkpoint()
                    outputs.append(stack.enter_context(private_file(directory / f"{name}.{stream}")))
                checkpoint()
                selector = stack.enter_context(selectors.DefaultSelector())
                for _ in range(2):
                    checkpoint()
                    read, write = os.pipe()
                    pipes.extend((read, write))
                checkpoint()
                signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
                checkpoint()
                pid = _spawn(command, pipes[1], pipes[3], descriptor, sandbox, environment or {}, cancellation)
                signal.pthread_sigmask(signal.SIG_SETMASK, cancellation.mask)
                checkpoint()
                for index, output in zip((0, 2), outputs, strict=True):
                    checkpoint()
                    os.close(pipes[index + 1])
                    pipes[index + 1] = None
                    checkpoint()
                    os.set_blocking(pipes[index], False)
                    selector.register(pipes[index], selectors.EVENT_READ, output)
                observed = sandbox is None
                exited = False
                while True:
                    checkpoint()
                    if not exited:
                        waited, status = os.waitpid(pid, os.WNOHANG | os.WUNTRACED)
                        checkpoint()
                        if waited:
                            if os.WIFSTOPPED(status):
                                if observed or sandbox is None or os.WSTOPSIG(status) != signal.SIGTRAP:
                                    result["gap"] = "exec_identity"
                                    break
                                observation = sandbox._observe_pre_namespace_objects(pid, descriptor)
                                checkpoint()
                                check = sandbox.validate_pre_namespace_objects(observation)
                                checkpoint()
                                if check.status != "PASS":
                                    result["gap"] = "exec_identity"
                                    break
                                sandbox._ptrace(sandbox._PTRACE_DETACH, pid)
                                checkpoint()
                                observed = True
                            else:
                                result["returncode"] = os.waitstatus_to_exitcode(status)
                                exited = True
                                if not observed:
                                    result["gap"] = "exec_identity"
                                    break
                    for key, _mask in selector.select(0.01):
                        checkpoint()
                        chunk = os.read(key.fd, min(65536, max(1, limit - result["bytes"] + 1)))
                        if not chunk:
                            selector.unregister(key.fd)
                            continue
                        remaining = limit - result["bytes"]
                        key.data.write(chunk[:remaining])
                        result["bytes"] += min(len(chunk), remaining)
                        if len(chunk) > remaining:
                            result["gap"] = "output_limit"
                            break
                    checkpoint()
                    if exited and not selector.get_map():
                        break
            except FileExistsError:
                raise
            except BaseException:
                result["gap"] = result["gap"] or "supervision_failed"
            finally:
                try:
                    result["cleaned"] = pid is None or _reap_tree(pid)
                except BaseException:
                    result["cleaned"] = False
                if cancellation.first_signal is not None:
                    result["gap"] = result["gap"] or "supervision_failed"
                if not result["cleaned"]:
                    result["gap"] = result["gap"] or "cleanup_failed"
                for fd in pipes:
                    if fd is not None:
                        try:
                            os.close(fd)
                        except BaseException:
                            result["cleaned"] = False
                            result["gap"] = result["gap"] or (
                                "supervision_failed" if cancellation.first_signal is not None else "cleanup_failed"
                            )
    except FileExistsError:
        raise
    except BaseException:
        result["gap"] = result["gap"] or "supervision_failed"
        result["cleaned"] = False
    finally:
        if cancellation.first_signal is not None:
            result["gap"] = result["gap"] or "supervision_failed"
        if not cancellation.restore():
            result["gap"] = result["gap"] or "supervision_failed"
        if cancellation.first_signal is not None:
            result["gap"] = result["gap"] or "supervision_failed"
    return result


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json")
        result[key] = value
    return result


def _positions(location, content) -> dict[str, int] | None:
    start, end = location.get("start", {}), location.get("end", {})
    values = (start.get("line"), start.get("col"), end.get("line"), end.get("col"))
    lines = content.splitlines() or [b""]
    if content.endswith(b"\n"):
        lines.append(b"")
    if not all(type(v) is int and v > 0 for v in values):
        return None
    first, column, last, end_column = values
    if (last, end_column) < (first, column) or last > len(lines):
        return None
    if column > len(lines[first - 1]) + 1 or end_column > len(lines[last - 1]) + 1:
        return None
    return dict(zip(("line", "column", "end_line", "end_column"), values, strict=True))


def project_native(raw, sources, rules, side, member):
    public = {"status": "INCOMPLETE", "acceptance": False, "errors": [], "accounted": []}
    inputs = {f"/opt/specfact/snapshot/{path}": (path, "source", data) for path, data in sources.items()}
    inputs.update({f"/opt/specfact/config/0/{path}": (path, "rule", data) for path, data in rules.items()})
    inputs.update({path: (path, "source", data) for path, data in sources.items()})
    accounted: dict[str, set[str]] = {}
    valid = True
    try:
        data = json.loads(raw, object_pairs_hook=_unique)
        if data.get("version") != "1.144.0" or not isinstance(data.get("results"), list):
            return public
        paths = data["paths"]
        if not isinstance(paths["scanned"], list) or not isinstance(paths.get("skipped", []), list):
            return public
        dispositions = [(path, "scanned") for path in paths["scanned"]]
        dispositions.extend((row["path"], "skipped") for row in paths.get("skipped", []))
        for path, disposition in dispositions:
            identity = inputs.get(path)
            if identity is None or identity[1] != "source":
                valid = False
            else:
                accounted.setdefault(identity[0], set()).add(disposition)
        if not isinstance(data["errors"], list):
            return public
        for error in data["errors"]:
            kind = error.get("type")
            category = (
                {"Syntax error": "syntax_error", "Rule parse error": "rule_parse_error"}.get(kind, "other")
                if isinstance(kind, str)
                else "other"
            )
            known = {
                "Lexical error",
                "Syntax error",
                "Other syntax error",
                "AST builder error",
                "Rule parse error",
                "SemgrepWarning",
                "SemgrepError",
                "InvalidRuleSchemaError",
                "UnknownLanguageError",
                "Invalid YAML",
                "Internal matching error",
                "Semgrep match found",
                "Too many matches",
                "Fatal error",
                "Timeout",
                "Out of memory",
                "Fixpoint timeout",
                "Stack overflow",
                "Timeout during interfile analysis",
                "OOM during interfile analysis",
                "Missing plugin",
                "Pattern parse error",
                "Incompatible rule",
            }
            if not (isinstance(kind, str) and kind in known) and not (
                isinstance(kind, list) and len(kind) == 2 and kind[0] == "PartialParsing" and isinstance(kind[1], list)
            ):
                valid = False
            locations = error.get("spans") or [error]
            if isinstance(kind, list) and len(kind) == 2 and kind[0] == "PartialParsing":
                category = "partial_parsing"
                locations = kind[1]
                if not isinstance(locations, list) or not locations:
                    valid, locations = False, [{}]
            if not isinstance(locations, list):
                return public
            for location in locations:
                if not isinstance(location, dict):
                    valid, location = False, {}
                native_path = location.get("file", location.get("path"))
                identity = inputs.get(native_path) if isinstance(native_path, str) else None
                row: dict[str, Any] = {"side": side, "member": member, "category": category}
                code = error.get("code")
                if type(code) is int and code in {0, 1, 2, 3, 4, 5, 7, 8, 13, 14}:
                    row["code"] = code
                elif code is not None:
                    valid = False
                if identity is None:
                    valid = False
                    public["errors"].append(row)
                    continue
                path, role, content = identity
                row.update(path=path, role=role)
                if role == "source":
                    accounted.setdefault(path, set()).add("error")
                if location is not error:
                    positions = _positions(location, content)
                    if positions is None:
                        valid = False
                    else:
                        row.update(positions)
                public["errors"].append(row)
        public["accounted"] = [
            {"path": path, "dispositions": sorted(values)} for path, values in sorted(accounted.items())
        ]
        if valid and set(accounted) == set(sources):
            public["status"] = "DIAGNOSTIC_COMPLETE"
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError):
        pass
    if len(json.dumps(public).encode()) > PUBLIC_LIMIT:
        return {"status": "INCOMPLETE", "acceptance": False, "errors": [], "accounted": []}
    return public


INPUT_ROWS = json.loads("""[
["head","packages/specfact-code-review/src/specfact_code_review/review/commands.py","100644","137bc88b08727f150e5f1211757cc92273f7dcf1","846c5ba81c567ce5905ad1c291adfe8a7d1daf247e4a66258f4768912814fbf1",16903],
["head","packages/specfact-code-review/src/specfact_code_review/run/commands.py","100644","2beb272b367de27f886246dd93b60e6e820ffad2","2cd18b85fd449b9726e5d71cfb04c65557731924378989718a8769384b8839dc",51914],
["head","packages/specfact-code-review/src/specfact_code_review/run/differential.py","100644","f5679bd81de1da7aed9b091f8029cab7cb6ecd7b","a05818e44b05e441a97a23ac2505cb4dd04f2de7e61dc2ef1568050378dd61d4",64431],
["head","packages/specfact-code-review/src/specfact_code_review/run/findings.py","100644","89f085373d62263338f92b55975573d7ca898b3e","b0cdf032c2d18c6e98666ef0936a26e54be0a2a12cec82b495a19b432e3b0bf8",46401],
["head","packages/specfact-code-review/src/specfact_code_review/run/portable_worker.py","100644","dfbcd193d39fac6b7bb75ee957dfff3f62bc029a","8c5c1251c2a946ff7e41ccf5a10152be7bbd70d792b9a22adfbd3a1eadaebc3e",25142],
["head","packages/specfact-code-review/src/specfact_code_review/run/runner.py","100644","f5e60236414d8716f43995199c23df67056a2e08","40e2c022af6ac86250e5d3ca2258b4ee9edf215476be9d9025bfc94727b21c29",356276],
["head","packages/specfact-code-review/src/specfact_code_review/tools/semgrep_runner.py","100644","b90172c7226739d968ffee8974dba1395ef42170","112bd6b44b73c1d3f67c42988735ddf493518fdaeaa309b1f7e042724c57b534",35481],
["head","scripts/independent_review_diagnostic.py","100644","b379505e2669c562d238e91a8d763cc624c530a3","fc357f81c8b8c60bd52cd975dcd292a23654626ad3e77656a084dfbdc8b7c8cd",28017],
["head","tests/host/proof_capsule_deferred_review_ci.py","100644","24899c60acce0cf2f6eb1dce66511cf991ac9453","963c22906367733a189e45587a84a29dfa91cda3f3f07b966287be767d06fe62",9680],
["head","tests/host/proof_independent_review_diagnostic.py","100644","54a2285195d11b8ed823b7ea602d7a392678fbda","00c28964d91998b929340d71558615ddf8e15e5b616592b44837587b48f6b675",49208],
["head","tests/support/capsule_review_fixtures.py","100644","13b12f039d23f7374ce38b7d86f302e9129f5824","1d1251902a58ea0c7bb9d8a102fdc09a720b4402e3a6ca3f6c43b819a21decf6",20063],
["head","tests/unit/specfact_code_review/ledger/test_commands.py","100644","33e7678d0873e509e59979a711b18e2cb8aa1da5","0b23f550aff5bd1e6b460d13c322052c596f88063bf7366a12e0044ebdcdbb40",9802],
["head","tests/unit/specfact_code_review/review/test_commands.py","100644","063cc435e3b54d068189754a6fcc18d24049b9e7","11188cb18b4cb58d79a460662c554dfbb83229afe33d35b22e29943ee9d50780",10506],
["head","tests/unit/specfact_code_review/run/test_commands.py","100644","da8ccd8e881a6f6700c401f90c9d28f4a80e444f","66d89942f3dd33bb232a2b2b16ce2fd69bb79fcd0af5e39b34794b6f88107603",68883],
["head","tests/unit/specfact_code_review/run/test_correspondence_candidate_prefilter.py","100644","01088a77abe7d8a9622e12ad29cc47da6c4fb57a","b080231e4009285fcf13c6557ec67ec2467797efe4d531b77dbb9ec852145656",15088],
["head","tests/unit/specfact_code_review/run/test_crosshair_diagnostics.py","100644","40566f9846515052826eaa4cad10151f952e925e","e1b92fe5b31e08be04b3898d1de6923357a3eafcb3d05e7b7dff8ebe9fc98182",4008],
["head","tests/unit/specfact_code_review/run/test_installed_coverage.py","100644","6f2c7c326eb3246652c9cdf2c0da2a153cad0cf0","b90ea91c8c28d824f4c7da49c87af00e031b8391af125fe996fc6350114e6b4b",32555],
["head","tests/unit/specfact_code_review/run/test_linux_pytest_budget.py","100644","8432b0f71fe7c0056561970d62d557f2e5865e3f","14cb969aa7bfd89ba90aa33238b4d1b14379508166648d87922851c3e32b9e06",9076],
["head","tests/unit/specfact_code_review/run/test_portable_pytest_evidence.py","100644","3fb3051cd330b0eb05f6f506938edda50f151ac5","03dd5d9ce3b38537cdcf00faf8885c780f50e148f5a40b217dac62b50094e2ec",13031],
["head","tests/unit/specfact_code_review/run/test_portable_worker.py","100644","f6f7fe3f1f2e880234e21848b9ca55597ab52dbc","52259231431a7cf2acbd6c78e42435e3db5cbda200a5129096aad2167922c166",35288],
["head","tests/unit/specfact_code_review/run/test_reviewer_bootstrap.py","100644","6ec834fed18596f43f17ffbca6a30d9c37c0f806","21ea0e347b68a14ef4cf149273ee0ee3387669ce2121516f1f9a3cc3da519c4d",7520],
["head","tests/unit/specfact_code_review/run/test_runner.py","100644","601412d4caee077145b1b27b92340ed578a04fea","e3cbf194bf93119b36e612f713adff73dd0bedf53568f89fe15d5f85c6cb16d8",344959],
["head","tests/unit/specfact_code_review/run/test_runner_native.py","100644","a7ac5e6509e27f4a0782e493473f3f6641201bef","8b2dd895cb4994e22299c602fc5f915b3719cf4d5f4d88309f62f7f91c630e07",50119],
["head","tests/unit/specfact_code_review/tools/test_semgrep_runner.py","100644","7242b7b9f7c2163bd229d0e82bc19424ddb27348","31c91c5252a1e219caee7f1fa3d13604025e71038141a3bb3c94438be714a95a",44539],
["head","tests/unit/test_capsule_proof_contexts.py","100644","86bf172253dd78db5156d9968d8992acebfd4f99","ab31fc9f02ba119b7a2f2afb8f89ec82f03aa42c431e11f6408e237a6b70a2a8",11398],
["head","tests/unit/test_capsule_review_projection.py","100644","e8b5ce2289bcdb49c8c6c3cf53c4ebf917c529b0","eaf6e09471f5d20e98c14f9a960ea14e6dc78780de6e1ff88d70f71afd3a8481",76420],
["head","tests/unit/test_independent_diagnostic_controller.py","100644","79cf75553921729ed9bfe05e62ce16b76126d475","b5ac708b9d3dbe93b36a2c31c7ddcc395fd1913bfe436559ed245ae1a3fd5d4a",14927],
["head","tests/unit/test_independent_member_observation.py","100644","562bf795d5e960d9b469b9a2d2bd8b4099478346","71eced6cc20f464648146969f77aa927c17ef26ec44115b96f17ce0a164719b3",23306],
["head","tests/unit/test_independent_review_diagnostic.py","100644","5ed048cf9f41c28c3e5316fd5e42f30bd3184a74","45f74b9dce3f816bb159c08dead5c4a94b42a39bf73c0bb38c30fe158ff5ba71",12041],
["head","tools/smart_test_coverage.py","100755","8c373d57cc2cd2ee050dc21772c8a0813769fd6c","79a16118fc81bcb444e35d450741893a0a468e3ba1251c41809c461f06a448d1",2009],
["base","packages/specfact-code-review/src/specfact_code_review/review/commands.py","100644","8a36e743eb570fefbf49f7da3491ce57758b4b4e","3678c7504849697ce15fce7285d1ec078fe1f11bdbf2fbae6d31678cc79720fe",16440],
["base","packages/specfact-code-review/src/specfact_code_review/run/commands.py","100644","8fb1c4d736283d55f043f9afe496553f738ebe4d","476763f92e6cc3ee6bde1b0cf129cca9427695c100a4c82c5b13fe9e5e74f7ec",51091],
["base","packages/specfact-code-review/src/specfact_code_review/run/differential.py","100644","ae13fb0f40a91e3840f190dea9f7cd0bc6e50c58","aa60b0854e31fad55b2c8efa53ffb32c92ab772ffbf8c8e565c2d8b6e45988e9",63616],
["base","packages/specfact-code-review/src/specfact_code_review/run/findings.py","100644","e7e55e64ff162c97aefd2612457a8964f026ddd6","c10e861efc142aa8804e346fccb12d6ad238dc9e82124fba93cdbe9c03871e45",40336],
["base","packages/specfact-code-review/src/specfact_code_review/run/portable_worker.py","100644","1d92f6103d23de0a969d3838330c1739db7a1dcb","595413b33782c913dc32e303513f68c30a1b74fe8b7727d309f1678ae2ae5f70",19395],
["base","packages/specfact-code-review/src/specfact_code_review/run/runner.py","100644","f6922071734583d5eea489cec3c30066dcc373dd","93eae46ca15483da82a8f761e041edcc6d9f07cfac954bb55bc20305f92840ce",351390],
["base","packages/specfact-code-review/src/specfact_code_review/tools/semgrep_runner.py","100644","dfacd0ac3a44959d8d7a197536bdc8be2f51fe7c","db15246edaea37cb40009133bb898a3dc65a6580623bfd49ee20f8699ab7fedd",29890],
["base","scripts/independent_review_diagnostic.py",null,null,null,null],
["base","tests/host/proof_capsule_deferred_review_ci.py","100644","bf55633a261ecf3b09238203bbc392d19af6af31","7fe33f2d6b008239fda4b754d531881b282f342a8d4406025121354b094b617b",9236],
["base","tests/host/proof_independent_review_diagnostic.py",null,null,null,null],
["base","tests/support/capsule_review_fixtures.py","100644","24d9f169ae66c46afb96ce4266cd796291666193","9c1d88f52bc2ab82b7bac10878cf8ef0d49840dd3b061258ddc890b1f8d74b2e",18107],
["base","tests/unit/specfact_code_review/ledger/test_commands.py","100644","c523da455f8c64af10e75a095985b7c41a5124d5","643700351793c703ccd2b2ede000fac75ee2b3ad3f4deed30659b458377351a4",8597],
["base","tests/unit/specfact_code_review/review/test_commands.py","100644","29b8ec515cfbf48de22eb5bc7c43099cea7e2650","7eae243e8a88eaa191cd922f58685831cac484f6bbed927492ab63400a84e931",9463],
["base","tests/unit/specfact_code_review/run/test_commands.py","100644","c1fc94925604e8bdad4a44f1fc2e118fdcbd167a","6656e2f7dcaef00ebf04b947cf1e72d377cc83312cca48dc034fca4fa7f11938",68449],
["base","tests/unit/specfact_code_review/run/test_correspondence_candidate_prefilter.py",null,null,null,null],
["base","tests/unit/specfact_code_review/run/test_crosshair_diagnostics.py","100644","6ca4b6fb5a4524fa51264dcaae0b6285c0cfc970","35c5b7713b857cc39d787c6e17896a952ef08a815e735e95d2927a943e94517b",3994],
["base","tests/unit/specfact_code_review/run/test_installed_coverage.py","100644","21beef8b3781ebdcedd4a928fac6b3a19156c12a","18f3af6b6e72ddb85cc79e729d06da5bfa3d570a57a6d899c8e811950a1f6675",32320],
["base","tests/unit/specfact_code_review/run/test_linux_pytest_budget.py",null,null,null,null],
["base","tests/unit/specfact_code_review/run/test_portable_pytest_evidence.py","100644","7772b3aee6d23788909b5e7c96357ed46fe3ed43","18eacb09b1aebc71271678070c3b0340e51a139d3d95fe9885b60df6ba095d2a",12942],
["base","tests/unit/specfact_code_review/run/test_portable_worker.py","100644","3c15c1e68e633a82300fc0036eb144ffcadb9299","de0e032c8c64857947be99d107f919474c808bc0c486f21a1eb6ecc27b0b0add",29510],
["base","tests/unit/specfact_code_review/run/test_reviewer_bootstrap.py","100644","86d5086fecd2d79589166cb0a95b6f27d91fb32e","cc1ad35ef6a6a45cd2ef0e001559352a4859456105cdf126903928a3f2ac0ac9",7441],
["base","tests/unit/specfact_code_review/run/test_runner.py","100644","bd559a2cfc7f55e369dd2b72f513971aa0ea26a7","384b98fc2d0068d140554cd7b78b0d3ec0767bccda7bd772649b0e1c509e7572",344632],
["base","tests/unit/specfact_code_review/run/test_runner_native.py","100644","2eb6faf1c223db3005b102c582744a92584bb8fc","acd2a6fda5102a4084b0982ca9f0e6a7f3f86ddc426dfb7b6f073784686eee53",42768],
["base","tests/unit/specfact_code_review/tools/test_semgrep_runner.py","100644","4c35ef7861be84966d1a2f46270ff57edad81342","e82db38fe377f263b4cddb122d99fd14044f8c792829122703e9245fd97e4db9",29855],
["base","tests/unit/test_capsule_proof_contexts.py","100644","407bb58c244b198b5e9afdb3a02c109081ae28ec","0e0dcc72afe19d8dedbd82425a11894bb634f85a957e0d185cb49874e54670e1",9078],
["base","tests/unit/test_capsule_review_projection.py","100644","113abd300c0fa27023bbee6f572414422c40782f","0b02b8d0c9943f7930a099e7c165ce05df42d9b25965e6fa7fd4850e784764d3",63087],
["base","tests/unit/test_independent_diagnostic_controller.py",null,null,null,null],
["base","tests/unit/test_independent_member_observation.py",null,null,null,null],
["base","tests/unit/test_independent_review_diagnostic.py",null,null,null,null],
["base","tools/smart_test_coverage.py","100755","1f8a571f72f85d623bce5a3d4d750eaf083683da","9fd7b7f427dbf2eb4bd6470d5ac4175d3daddeacbb38c7f48880eb995ab54dc3",1885]
]""")
INPUTS = {
    side: {
        row[1]: (
            {"status": "absent"}
            if row[2] is None
            else {"status": "present", "mode": row[2], "git_blob": row[3], "sha256": row[4], "bytes": row[5]}
        )
        for row in INPUT_ROWS
        if row[0] == side
    }
    for side in ("head", "base")
}
RULES = json.loads(
    """{"base":{"packages/specfact-code-review/src/specfact_code_review/.semgrep/clean_code.yaml":{"status":"present","mode":"100644","type":"blob","git_blob":"ffc57e6a72c4d7da8c0f057181a437f8ebc938c0","sha256":"5f279f456c0b13acc281e6b39a7aca24fa7af352e569bba72ff738cb9335ecea","bytes":2370},"packages/specfact-code-review/src/specfact_code_review/.semgrep/bugs.yaml":{"status":"present","mode":"100644","type":"blob","git_blob":"bb66f91bf5a7a245526a64daf7c51567de0f950b","sha256":"0d207b87d5ecedae4a8273b0a57a8db693a1765b66ab714363d8a689de4e36b2","bytes":1915},"packages/specfact-code-review/src/specfact_code_review/resources/semgrep-rules/ai-bloat.yaml":{"status":"present","mode":"100644","type":"blob","git_blob":"fbcd4739685baba883f2af7b7be6117f4dbe5249","sha256":"1d0a2b1010848b862cdb27061522904e570092fcb557766549e79e766e6d1089","bytes":1525}},"head":{"packages/specfact-code-review/src/specfact_code_review/.semgrep/clean_code.yaml":{"status":"present","mode":"100644","type":"blob","git_blob":"ffc57e6a72c4d7da8c0f057181a437f8ebc938c0","sha256":"5f279f456c0b13acc281e6b39a7aca24fa7af352e569bba72ff738cb9335ecea","bytes":2370},"packages/specfact-code-review/src/specfact_code_review/.semgrep/bugs.yaml":{"status":"present","mode":"100644","type":"blob","git_blob":"bb66f91bf5a7a245526a64daf7c51567de0f950b","sha256":"0d207b87d5ecedae4a8273b0a57a8db693a1765b66ab714363d8a689de4e36b2","bytes":1915},"packages/specfact-code-review/src/specfact_code_review/resources/semgrep-rules/ai-bloat.yaml":{"status":"present","mode":"100644","type":"blob","git_blob":"fbcd4739685baba883f2af7b7be6117f4dbe5249","sha256":"1d0a2b1010848b862cdb27061522904e570092fcb557766549e79e766e6d1089","bytes":1525}}}"""
)


class CommandFailureError(ValueError):
    def __init__(self, stage, captured):
        super().__init__("bounded_command_failed")
        self.stage = (
            stage if stage in {"setup-0", "setup-1", "setup-2", "setup-3", "setup-4", "experiment-worker"} else "git"
        )
        self.captured = captured


def failure_record(phase, error):
    categories = {
        "admission",
        "single_thread_required",
        "subreaper",
        "input_path",
        "absent_input_changed",
        "input_identity",
        "input_digest",
        "host_platform",
        "core_identity",
        "package_paths",
        "package_size",
        "package_identity",
        "package_signature",
        "lock_identity",
        "loaded_owner",
        "runtime_unavailable",
        "runtime_changed",
        "launcher_identity",
        "setup_deadline",
        "cancelled",
    }
    category = (
        error.args[0]
        if len(error.args) == 1 and isinstance(error.args[0], str) and error.args[0] in categories
        else "UNKNOWN"
    )
    result = {"status": "INCOMPLETE", "acceptance": False, "phase": phase, "category": category}
    if isinstance(error, CommandFailureError):
        capture_result = error.captured
        result.update(
            stage=error.stage,
            capture={
                "returncode": capture_result.get("returncode")
                if type(capture_result.get("returncode")) is int
                else None,
                "bytes": capture_result.get("bytes")
                if type(capture_result.get("bytes")) is int and 0 <= capture_result["bytes"] <= RAW_LIMIT
                else 0,
                "gap": capture_result.get("gap")
                if capture_result.get("gap")
                in {None, "deadline", "output_limit", "exec_identity", "supervision_failed", "cleanup_failed"}
                else "UNKNOWN",
                "cleaned": capture_result.get("cleaned") is True,
            },
        )
    return result


def checked(command, directory, name, seconds: float = 10, limit=RAW_LIMIT, environment=None):
    result = capture(command, directory, name, seconds, limit, environment=environment)
    if result["gap"] or result["returncode"] != 0 or not result["cleaned"]:
        raise CommandFailureError(name, result)
    return (directory / f"{name}.stdout").read_bytes()


def git(repository, directory, name, *arguments):
    return checked(
        ["/usr/bin/git", "-C", str(repository), "-c", "core.hooksPath=/dev/null", *arguments],
        directory,
        name,
        environment={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1"},
    )


def admission(repository, directory, phase):
    sha = os.environ.get("GITHUB_SHA", "")
    with Path(os.environ["GITHUB_EVENT_PATH"]).open("rb") as event_file:
        raw = event_file.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("admission")
    event = json.loads(raw)
    parents = (
        git(repository, directory, phase + "-parents", "rev-list", "--parents", "-n", "1", "HEAD").decode().split()
    )
    if not parents or parents[0] != sha or os.environ.get("GITHUB_EVENT_NAME") != "push":
        raise ValueError("admission")
    admit(event, sha, os.environ.get("GITHUB_RUN_ATTEMPT"), parents[1:])


def materialize(repository, directory):
    sides = {}
    for side, revision in (("head", SUBJECT_HEAD), ("base", SUBJECT_BASE)):
        root = directory / side
        root.mkdir(mode=0o700)
        configs = directory / (side + "-rules")
        configs.mkdir(mode=0o700)
        sources, rules = {}, {}
        for index, (relative, expected) in enumerate({**INPUTS[side], **RULES[side]}.items()):
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
                raise ValueError("input_path")
            prefix = f"{side}-input-{index}"
            record = git(repository, directory, prefix + "-tree", "ls-tree", "-z", revision, "--", relative)
            if expected["status"] == "absent":
                if record:
                    raise ValueError("absent_input_changed")
                continue
            wanted = f"{expected['mode']} blob {expected['git_blob']}\t{relative}\0".encode()
            if record != wanted or expected["mode"] not in {"100644", "100755"}:
                raise ValueError("input_identity")
            content = git(repository, directory, prefix + "-blob", "cat-file", "blob", expected["git_blob"])
            if len(content) != expected["bytes"] or hashlib.sha256(content).hexdigest() != expected["sha256"]:
                raise ValueError("input_digest")
            is_rule = relative in RULES[side]
            destination = relative.removeprefix(RULE_ROOT) if is_rule else relative
            target = (configs if is_rule else root) / destination
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with private_file(target) as output:
                output.write(content)
            (rules if is_rule else sources)[destination] = content
        sides[side] = (root, configs, sources, rules)
    return sides


def authenticate(root):
    sys.dont_write_bytecode = True
    import specfact_cli
    import yaml
    from specfact_cli.registry.crypto_validator import verify_signature
    from specfact_cli.registry.module_installer import _bundled_public_key_path, _module_artifact_payload_stable

    if sys.platform != "linux" or os.getuid() == 0 or sys.version_info[:2] != (3, 12):
        raise ValueError("host_platform")
    if specfact_cli.__version__ != "0.55.4" or not Path(specfact_cli.__file__).resolve().is_relative_to(root / "venv"):
        raise ValueError("core_identity")
    package = root / "home/.specfact/modules/specfact-code-review"
    paths = list(package.rglob("*"))
    if package.is_symlink() or len(paths) > 2048 or any(p.is_symlink() for p in paths):
        raise ValueError("package_paths")
    if sum(p.stat().st_size for p in paths if p.is_file()) > RAW_LIMIT:
        raise ValueError("package_size")
    metadata = yaml.safe_load((package / "module-package.yaml").read_bytes())
    key = _bundled_public_key_path().read_bytes()
    payload = _module_artifact_payload_stable(package)
    if hashlib.sha256(key).hexdigest() != KEY_SHA256 or hashlib.sha256(payload).hexdigest() != PAYLOAD_SHA256:
        raise ValueError("package_identity")
    if (
        metadata["version"] != "0.51.2"
        or metadata["integrity"]["checksum"] != "sha256:" + PAYLOAD_SHA256
        or not verify_signature(payload, metadata["integrity"]["signature"], key.decode())
    ):
        raise ValueError("package_signature")
    lock = package / "src/specfact_code_review/resources/contracts/pr-range-v1-toolchain-lock.json"
    if hashlib.sha256(lock.read_bytes()).hexdigest() != LOCK_SHA256:
        raise ValueError("lock_identity")
    sys.path.insert(0, str(package / "src"))
    from specfact_code_review.run import runner, sandbox

    if not Path(runner.__file__).resolve().is_relative_to(package) or not Path(
        sandbox.__file__
    ).resolve().is_relative_to(package):
        raise ValueError("loaded_owner")
    return runner, sandbox


def root_digest(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            content = os.readlink(path).encode()
        elif path.is_file():
            content_hash = hashlib.sha256()
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    content_hash.update(chunk)
            content = content_hash.digest()
        else:
            content = b"directory"
        digest.update(relative.encode() + b"\0" + str(path.lstat().st_mode).encode() + b"\0" + content)
    return digest.hexdigest()


def prepare(root, directory):
    from dataclasses import asdict

    runner, _sandbox = authenticate(root)
    runtime, reason = runner._prepare_capsule_runtime(environment_id="linux-x86_64-cp312")
    if runtime is None or reason or runtime.environment_id != "linux-x86_64-cp312":
        raise ValueError("runtime_unavailable")
    record = {
        "root": str(runtime.root),
        "identity": runtime.identity,
        "interpreter": runtime.interpreter,
        "bootstrap": runtime.bootstrap,
        "bubblewrap": asdict(runtime.bubblewrap),
        "prepared_root_digest": root_digest(runtime.root),
        "lock_sha256": LOCK_SHA256,
        "payload_sha256": PAYLOAD_SHA256,
    }
    with private_file(directory / "runtime.private.json") as output:
        output.write(json.dumps(record, sort_keys=True).encode())


def experiment(root, directory, repository):
    _runner, sandbox = authenticate(root)
    record = json.loads((directory / "runtime.private.json").read_bytes())
    runtime = Path(record["root"])
    if (
        not runtime.resolve().is_relative_to(root / "cache/invocations")
        or root_digest(runtime) != record["prepared_root_digest"]
    ):
        raise ValueError("runtime_changed")
    sides = materialize(repository, directory)
    public = {"status": "INCOMPLETE", "acceptance": False, "original_guest": "UNKNOWN", "calls": []}
    remaining = RAW_LIMIT
    for side, member in CALLS:
        snapshot, configs, sources, rules = sides[side]
        name = f"{side}-{member}"
        output, temporary = directory / (name + "-output"), directory / (name + "-tmp")
        output.mkdir(mode=0o700)
        temporary.mkdir(mode=0o700)
        context = sandbox.SnapshotInvocationContext(
            member="semgrep-" + member,
            snapshot_root=snapshot,
            config_roots=(configs,),
            output_root=output,
            temporary_root=temporary,
            capsule_root=runtime,
            interpreter=record["interpreter"],
            bootstrap=record["bootstrap"],
            project_runtime_root=None,
            network="none",
            control_root=None,
            environment_id="linux-x86_64-cp312",
        )
        plan = sandbox.build_launch_plan(context)
        identity = sandbox.BubblewrapIdentity(**record["bubblewrap"])
        if sandbox.validate_bubblewrap(identity).status != "PASS":
            raise ValueError("launcher_identity")
        selected = (
            (".semgrep/clean_code.yaml", "resources/semgrep-rules/ai-bloat.yaml")
            if member == "clean"
            else (".semgrep/bugs.yaml",)
        )
        argv = [
            "semgrep.console_scripts.pysemgrep",
            "--disable-version-check",
            "--quiet",
            "--disable-nosem",
            "--metrics",
            "off",
        ]
        for rule in selected:
            argv.extend(("--config", "/opt/specfact/config/0/" + rule))
        argv.extend(("--json", *("/opt/specfact/snapshot/" + path for path in sources)))
        descriptor = sandbox._verified_bubblewrap_descriptor(runtime, identity)
        try:
            command = sandbox._bubblewrap_command(descriptor, plan, extra_argv=tuple(argv))
            with private_file(directory / (name + "-launch.private.json")) as evidence:
                evidence.write(
                    json.dumps(
                        {
                            "argv": command,
                            "context": context.digest,
                            "mounts": [(m.destination, str(m.source), m.read_only) for m in plan.mounts],
                        }
                    ).encode()
                )
            captured = capture(command, directory, name, 90, remaining, descriptor=descriptor, sandbox=sandbox)
        finally:
            os.close(descriptor)
        remaining -= captured["bytes"]
        stdout_available = True
        try:
            raw = (directory / (name + ".stdout")).read_bytes()
        except FileNotFoundError:
            if not captured["gap"]:
                raise
            stdout_available = False
            raw = b""
        projected = project_native(raw, sources, rules, side, member)
        if captured["gap"] or not captured["cleaned"] or captured["returncode"] not in {0, 1, 2, 3, 4, 5, 7, 8, 13, 14}:
            projected["status"] = "INCOMPLETE"
        projected["capture"] = captured
        public["calls"].append(projected)
        with private_file(directory / (name + "-capture.private.json")) as evidence:
            stderr_available = True
            try:
                stderr = (directory / (name + ".stderr")).read_bytes()
            except FileNotFoundError:
                if not captured["gap"]:
                    raise
                stderr_available = False
                stderr = b""
            evidence.write(
                json.dumps(
                    {
                        **captured,
                        "stdout_sha256": hashlib.sha256(raw).hexdigest() if stdout_available else None,
                        "stderr_sha256": hashlib.sha256(stderr).hexdigest() if stderr_available else None,
                        "stdout_bytes": len(raw) if stdout_available else None,
                        "stderr_bytes": len(stderr) if stderr_available else None,
                    }
                ).encode()
            )
        if captured["gap"]:
            break
    unchanged = root_digest(runtime) == record["prepared_root_digest"]
    for _side, (snapshot, configs, sources, rules) in sides.items():
        unchanged &= all((snapshot / p).read_bytes() == value for p, value in sources.items())
        unchanged &= all((configs / p).read_bytes() == value for p, value in rules.items())
    if unchanged and len(public["calls"]) == 4 and all(c["status"] == "DIAGNOSTIC_COMPLETE" for c in public["calls"]):
        public["status"] = "DIAGNOSTIC_COMPLETE"
    encoded = json.dumps(public, sort_keys=True).encode()
    if len(encoded) > PUBLIC_LIMIT - 1024:
        encoded = b'{"status":"INCOMPLETE","acceptance":false,"gap":"public_limit"}'
    with private_file(directory / "public.json") as output:
        output.write(encoded)


def setup(root, directory, repository):
    started = float((directory / "setup-start.private").read_text())
    for name in ("home", "tmp", "cache"):
        (root / name).mkdir(mode=0o700)
    python = root / "venv/bin/python"
    environment = {
        "HOME": str(root / "home"),
        "TMPDIR": str(root / "tmp"),
        "PATH": str(root / "venv/bin") + ":/usr/bin:/bin",
        "SPECFACT_MODULES_BRANCH": "main",
        "SPECFACT_CODE_REVIEW_CAPSULE_CACHE": str(root / "cache"),
        **{
            key: value
            for key, value in os.environ.items()
            if key
            in {
                "GITHUB_SHA",
                "GITHUB_EVENT_PATH",
                "GITHUB_EVENT_NAME",
                "GITHUB_RUN_ATTEMPT",
                "GITHUB_REPOSITORY",
                "GITHUB_ACTIONS",
            }
        },
    }
    profile = root / "capsule.apparmor"
    profile.write_text(
        "abi <abi/4.0>,\ninclude <tunables/global>\n"
        f'profile specfact-semgrep-diagnostic "{root}/cache/**/opt/specfact/bin/bwrap-static" flags=(unconfined) {{\n userns,\n}}\n'
    )
    commands = [
        [sys.executable, "-I", "-m", "venv", str(root / "venv")],
        [str(python), "-I", "-m", "pip", "install", "--no-cache-dir", "specfact-cli==0.55.4"],
        [
            str(python),
            "-I",
            "-m",
            "specfact_cli.cli",
            "module",
            "install",
            "nold-ai/specfact-code-review",
            "--scope",
            "user",
            "--version",
            "0.51.2",
            "--source",
            "marketplace",
        ],
        ["/usr/bin/sudo", "/sbin/apparmor_parser", "-r", str(profile)],
        [
            str(python),
            "-I",
            str(Path(__file__).resolve()),
            "--phase",
            "prepare",
            "--root",
            str(root),
            "--repository",
            str(repository),
        ],
    ]
    with private_file(directory / "setup-argv.private.json") as output:
        output.write(json.dumps(commands).encode())
    for index, command in enumerate(commands):
        remaining = 1200 - (time.monotonic() - started)
        if remaining <= 0:
            raise ValueError("setup_deadline")
        checked(command, directory, f"setup-{index}", remaining, environment=environment)
    checked(
        [
            str(python),
            "-I",
            str(Path(__file__).resolve()),
            "--phase",
            "experiment",
            "--root",
            str(root),
            "--repository",
            str(repository),
        ],
        directory,
        "experiment-worker",
        390,
        environment=environment,
    )


def cancel(_signal, _frame):
    raise InterruptedError("cancelled")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("admit", "setup", "prepare", "experiment"), required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    arguments = parser.parse_args()
    os.umask(0o077)
    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    root, repository = arguments.root.resolve(), arguments.repository.resolve()
    directory = root / "evidence"
    if arguments.phase == "admit":
        root.mkdir(mode=0o700)
        directory.mkdir(mode=0o700)
        with private_file(directory / "setup-start.private") as output:
            output.write(str(time.monotonic()).encode())
    primary = None
    try:
        admission(repository, directory, arguments.phase)
        os.chdir(root)
        if arguments.phase == "setup":
            setup(root, directory, repository)
        elif arguments.phase == "prepare":
            prepare(root, directory)
        elif arguments.phase == "experiment":
            experiment(root, directory, repository)
    except BaseException as error:
        primary = failure_record(arguments.phase, error)
    if primary is not None:
        with (
            contextlib.suppress(OSError),
            private_file(directory / (arguments.phase + "-failure.public.json")) as output,
        ):
            output.write(json.dumps(primary, sort_keys=True).encode())
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
