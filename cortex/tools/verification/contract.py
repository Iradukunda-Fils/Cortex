"""
YAML Contract Parser & Schema Validator for Verification Runs
"""

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class VerificationContract:
    schema_version: str
    contract_id: str
    description: str
    toolchain_requirements: dict[str, str]
    fuzzing_parameters: dict[str, Any]
    targets: dict[str, str]
    oracle: dict[str, Any]
    output_requirements: dict[str, str]

    @classmethod
    def load(cls, contract_path: str) -> "VerificationContract":
        if not os.path.exists(contract_path):
            raise FileNotFoundError(f"Contract file not found: {contract_path}")

        # Basic lightweight YAML parser without third-party requirement
        data: dict[str, Any] = {}
        current_key = None

        with open(contract_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if ":" in line and not line.startswith("-"):
                    parts = line.split(":", 1)
                    key = parts[0].strip()
                    val = parts[1].strip()

                    if val == "":
                        current_key = key
                        data[current_key] = {}
                    else:
                        # strip quotes if present
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        elif val.lower() == "true":
                            val = True
                        elif val.lower() == "false":
                            val = False
                        elif val.isdigit():
                            val = int(val)

                        if current_key and line.startswith("  "):
                            data[current_key][key] = val
                        else:
                            data[key] = val
                            current_key = None

        return cls(
            schema_version=data.get("schema_version", "1.0.0"),
            contract_id=data.get("contract_id", "default"),
            description=data.get("description", ""),
            toolchain_requirements=data.get("toolchain_requirements", {}),
            fuzzing_parameters=data.get("fuzzing_parameters", {}),
            targets=data.get("targets", {}),
            oracle=data.get("oracle", {}),
            output_requirements=data.get("output_requirements", {}),
        )
