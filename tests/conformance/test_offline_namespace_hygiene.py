"""
Cortex Offline Namespace Hygiene & Domain Isolation Test Suite
Author: Iradukunda Fils <iradukundafils1@gmail.com>

Enforces the Normative Offline Resolution Policy:
1. `cortex.security` is strictly a RESERVED / FUTURE CANONICAL NAMESPACE IDENTIFIER ($id).
2. Zero network requests, HTTP fetches, DNS resolutions, or TLS connections to cortex.security.
3. Schema validation must resolve 100% locally via relative file paths.
"""

import json
import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class TestOfflineNamespaceHygiene(unittest.TestCase):
    """Programmatic audit of offline namespace hygiene and domain isolation."""

    def test_cortex_security_references_classification(self):
        """Audit all occurrences of 'cortex.security' to confirm zero operational network dependencies."""
        cortex_security_pattern = re.compile(r"https?://[a-zA-Z0-9\.-]*cortex\.security[^\s\"']*")

        found_references = []
        for root, dirs, files in os.walk(REPO_ROOT):
            # Skip VCS and build caches
            dirs[:] = [d for d in dirs if d not in [".git", ".venv", ".ruff_cache", "obj_dir", "__pycache__"]]
            for file in files:
                if file.endswith((".py", ".json", ".md", ".yml", ".yaml", ".sh", ".v", ".sv", ".rs", ".go")):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, REPO_ROOT)
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    for idx, line in enumerate(lines, 1):
                        matches = cortex_security_pattern.findall(line)
                        for match in matches:
                            found_references.append(
                                {"file": rel_path, "line": idx, "match": match, "content": line.strip()}
                            )

        for ref in found_references:
            # Must be either JSON Schema "$id" or explicit documentation markdown/comments
            is_json_schema_id = ('"$id"' in ref["content"] or '"$id":' in ref["content"]) and ref["file"].endswith(
                ".schema.json"
            )
            is_doc_reference = ref["file"].endswith(".md") or ref["file"].endswith(".py")

            self.assertTrue(
                is_json_schema_id or is_doc_reference,
                f"Operational dependency trap! Unauthorized network reference to cortex.security in {ref['file']}:{ref['line']}",
            )
            # Ensure it is NEVER used in a $schema network target or http fetch call
            forbidden_schema_target = '"$schema": ' + '"https://cortex.security'
            self.assertNotIn(forbidden_schema_target, ref["content"])
            self.assertNotIn("curl", ref["content"])
            self.assertNotIn("requests.get", ref["content"])

    def test_manifests_use_local_schema_resolution(self):
        """Assert all manifest $schema fields resolve strictly via relative local paths."""
        manifest_path = os.path.join(REPO_ROOT, "cortex_assurance_manifest.json")
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        schema_target = manifest_data.get("$schema", "")
        self.assertTrue(
            schema_target.startswith("./") or schema_target.startswith("../"),
            f"Manifest $schema MUST resolve locally via relative path, got: {schema_target}",
        )

    def test_ci_workflows_have_zero_cortex_security_network_calls(self):
        """Assert CI workflow files do not attempt to fetch or resolve cortex.security."""
        workflows_dir = os.path.join(REPO_ROOT, ".github", "workflows")
        if not os.path.exists(workflows_dir):
            return

        for file in os.listdir(workflows_dir):
            if file.endswith((".yml", ".yaml")):
                file_path = os.path.join(workflows_dir, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertNotIn(
                    "cortex.security", content, f"CI workflow {file} contains reference to cortex.security!"
                )


if __name__ == "__main__":
    unittest.main()
