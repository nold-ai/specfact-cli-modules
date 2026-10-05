"""Check the experimental npm input graph without installing or executing tools."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


INPUTS = Path(__file__).resolve().parents[2] / "scripts/native_node_inputs"
BASEDPYRIGHT_INTEGRITY = (
    "sha512-9NTfbegeSey8Trhaf+Tr8++Uo/UFCtsUMzpvXA/seDfSTN3kOwfmPJ4lf/tjxPjVlr/fsHo34W9/qW+ZF+b6kg=="
)
FSEVENTS_INTEGRITY = "sha512-5xoDfX+fL7faATnagmWPpbFtwh/R77WmMMqqHGS65C3vvB0YHrgF+B1YmZ3441tMj5n63k0212XNoJwzlhffQw=="


class NativeNodeInputPinsTests(unittest.TestCase):
    """Keep the bounded input graph pinned and optional build hooks uninstalled."""

    def setUp(self) -> None:
        self.package = json.loads((INPUTS / "package.json").read_text())
        self.lock = json.loads((INPUTS / "package-lock.json").read_text())
        self.packages = self.lock["packages"]

    def test_private_exact_basedpyright_dependency(self) -> None:
        self.assertTrue(self.package["private"])
        self.assertEqual(self.package["dependencies"], {"basedpyright": "1.39.10"})
        self.assertNotIn("scripts", self.package)
        self.assertEqual(self.lock["lockfileVersion"], 3)
        self.assertEqual(self.packages[""]["dependencies"], self.package["dependencies"])

    def test_graph_excludes_python_wheel_and_unreviewed_packages(self) -> None:
        self.assertEqual(set(self.packages), {"", "node_modules/basedpyright", "node_modules/fsevents"})
        for entry in self.packages.values():
            self.assertNotIn("nodejs-wheel-binaries", entry.get("dependencies", {}))

    def test_basedpyright_identity_and_no_mandatory_transitives(self) -> None:
        entry = self.packages["node_modules/basedpyright"]
        self.assertEqual(entry["version"], "1.39.10")
        self.assertEqual(entry["resolved"], "https://registry.npmjs.org/basedpyright/-/basedpyright-1.39.10.tgz")
        self.assertEqual(entry["integrity"], BASEDPYRIGHT_INTEGRITY)
        self.assertEqual(entry["license"], "MIT")
        self.assertFalse(entry.get("dependencies"))
        self.assertEqual(entry["optionalDependencies"], {"fsevents": "~2.3.3"})
        self.assertEqual(entry["bin"]["basedpyright"], "index.js")

    def test_optional_fsevents_audit_preserved(self) -> None:
        entry = self.packages["node_modules/fsevents"]
        self.assertEqual(entry["version"], "2.3.3")
        self.assertEqual(entry["resolved"], "https://registry.npmjs.org/fsevents/-/fsevents-2.3.3.tgz")
        self.assertEqual(entry["integrity"], FSEVENTS_INTEGRITY)
        self.assertEqual(entry["license"], "MIT")
        self.assertTrue(entry["optional"])
        self.assertTrue(entry["hasInstallScript"])
        self.assertEqual(entry["os"], ["darwin"])

    def test_install_policy_omits_optional_and_disables_scripts(self) -> None:
        config = dict(line.split("=", 1) for line in (INPUTS / ".npmrc").read_text().splitlines() if line.strip())
        self.assertEqual(config["ignore-scripts"], "true")
        self.assertEqual(config["omit"], "optional")


if __name__ == "__main__":
    unittest.main()
