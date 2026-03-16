from __future__ import annotations

import sys
from pathlib import Path

from specfact_cli.utils.yaml_utils import load_yaml
from specfact_cli.validators.schema import SchemaValidator


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    schema_dir = repo_root / "resources" / "schemas"
    validator = SchemaValidator(schema_dir)
    scenario_files = sorted((repo_root / "tests" / "cli-contracts").glob("*.scenarios.yaml"))

    if not scenario_files:
        print("No CLI contract scenario files found.", file=sys.stderr)
        return 1

    for scenario_file in scenario_files:
        payload = load_yaml(scenario_file)
        report = validator.validate_json_schema(payload, "cli-contract.schema.json")
        if report.passed:
            continue
        print(f"Schema validation failed for {scenario_file}:", file=sys.stderr)
        for deviation in report.deviations:
            print(f"- {deviation.location}: {deviation.description}", file=sys.stderr)
        return 1

    print(f"Validated {len(scenario_files)} CLI contract scenario files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
