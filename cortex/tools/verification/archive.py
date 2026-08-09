"""
Index-backed Counterexample Database Archiver
"""

import hashlib
import json
import os
from typing import Any


class CounterexampleArchive:
    def __init__(self, archive_dir: str = "artifacts/counterexamples/"):
        self.archive_dir = archive_dir
        self.index_path = os.path.join(self.archive_dir, "index.json")
        os.makedirs(self.archive_dir, exist_ok=True)
        if not os.path.exists(self.index_path):
            with open(self.index_path, "w") as f:
                json.dump({"counterexamples": []}, f, indent=2)

    def archive_failure(
        self,
        scenario: dict[str, Any],
        diagnostic: dict[str, Any],
        seed: str,
        commit_id: str = "a484b94"
    ) -> str:
        payload_str = json.dumps(scenario, sort_keys=True).encode("utf-8")
        entry_hash = hashlib.sha256(payload_str).hexdigest()[:12]

        case_dir = os.path.join(self.archive_dir, entry_hash)
        os.makedirs(case_dir, exist_ok=True)

        case_file = os.path.join(case_dir, "scenario.json")
        diag_file = os.path.join(case_dir, "diagnostic.json")

        with open(case_file, "w") as f:
            json.dump(scenario, f, indent=2)

        with open(diag_file, "w") as f:
            json.dump(diagnostic, f, indent=2)

        # Update index.json
        with open(self.index_path, "r") as f:
            index_data = json.load(f)

        index_data["counterexamples"].append({
            "hash": entry_hash,
            "seed": seed,
            "commit_id": commit_id,
            "error_type": diagnostic.get("error_type", "Unknown"),
            "mismatched_field": diagnostic.get("mismatched_field", "Unknown"),
            "failing_step": diagnostic.get("failing_step", 0)
        })

        with open(self.index_path, "w") as f:
            json.dump(index_data, f, indent=2)

        return entry_hash
