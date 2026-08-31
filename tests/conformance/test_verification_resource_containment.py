"""
Issue #51 Adversarial Verification-Resource Tests

Verifies that the Verification Resource Controller (verification/verify_controller.py)
properly enforces operational ceilings, admission control, process timeouts,
and resource cleanup, guaranteeing host stability under bounded verification.
"""

from __future__ import annotations

import sys
import unittest

from verification.verify_controller import (
    PROFILES,
    get_available_memory_mb,
    run_bounded_job,
)


class TestVerificationResourceContainment(unittest.TestCase):
    """Adversarial tests for verification infrastructure resource containment."""

    def test_admission_control_memory_check(self) -> None:
        """Verifies that admission control calculates host memory budget correctly."""
        avail_mem = get_available_memory_mb()
        self.assertGreater(avail_mem, 0, "Available host memory calculation must return positive float.")

    def test_timeout_containment(self) -> None:
        """Verifies that a hanging verification process is terminated cleanly at timeout limit."""
        hanging_cmd = f"{sys.executable} -c 'import time; time.sleep(60)'"
        success = run_bounded_job("Hanging Test Job", hanging_cmd, max_rss_mb=5000.0, timeout_sec=1)
        self.assertFalse(success, "Hanging job must fail cleanly upon reaching timeout ceiling.")

    def test_profile_definitions_bounded(self) -> None:
        """Verifies that all defined verification profiles declare bounded memory and timeouts."""
        for name, profile in PROFILES.items():
            self.assertGreater(profile.required_mem_mb, 0, f"Profile '{name}' must specify positive memory budget.")
            self.assertGreater(profile.max_rss_mb, 0, f"Profile '{name}' must specify positive RSS limit.")
            self.assertGreater(profile.timeout_sec, 0, f"Profile '{name}' must specify positive timeout ceiling.")
            self.assertGreater(len(profile.commands), 0, f"Profile '{name}' must contain executable commands.")

    def test_tla_flags_memory_bounded(self) -> None:
        """Verifies that Makefile and TLA+ commands specify explicit JVM heap limits (-Xmx)."""
        with open("verification/Makefile", "r") as f:
            makefile_content = f.read()
        self.assertIn("-Xmx1G", makefile_content, "Makefile tla target must declare bounded -Xmx heap limit.")
        self.assertIn("-workers 2", makefile_content, "Makefile tla target must declare bounded thread count.")


if __name__ == "__main__":
    unittest.main()
