"""
Gate H-4: Controlled Actuation Boundary Integration Test Suite
Author: Iradukunda Fils <iradukundafils1@gmail.com>
"""

import unittest
from tests.conformance.test_gate_h_adversarial import (
    TokenRegistry,
    mint_valid_token,
    verify_actuation_boundary,
    SecurityTrapException,
)


class MockFileSystemActuatorDriver:
    """Mock File System Driver implementing the controlled actuation boundary."""
    def __init__(self, registry: TokenRegistry):
        self.registry = registry
        self.executed_writes: list[tuple[str, str]] = []

    def execute_write(self, token, payload: dict) -> bool:
        """Driver entry point with embedded Gate H verification."""
        # 1. Gate H Actuation Boundary Verification
        verify_actuation_boundary(token, payload, self.registry)
        
        # 2. Perform Concrete Side-Effect Actuation
        path = payload["path"]
        data = payload["data"]
        self.executed_writes.append((path, data))
        return True


class TestGateHActuationBoundary(unittest.TestCase):
    """Integration test suite proving cryptographic intent-parity at actuation boundary."""

    def test_h4_end_to_end_authorized_actuation(self):
        """Verify authorized intent successfully executes through driver boundary."""
        registry = TokenRegistry()
        driver = MockFileSystemActuatorDriver(registry)

        payload = {"action": "fs_write", "path": "/tmp/authorized.dat", "data": "VALID_DATA"}
        token, payload = mint_valid_token(payload)

        # Execute through driver
        success = driver.execute_write(token, payload)
        self.assertTrue(success)
        self.assertEqual(len(driver.executed_writes), 1)
        self.assertEqual(driver.executed_writes[0], ("/tmp/authorized.dat", "VALID_DATA"))

    def test_h4_single_byte_tampering_traps_before_actuation(self):
        """Verify modifying a single payload byte traps BEFORE driver actuation occurs."""
        registry = TokenRegistry()
        driver = MockFileSystemActuatorDriver(registry)

        payload = {"action": "fs_write", "path": "/tmp/authorized.dat", "data": "VALID_DATA"}
        token, payload = mint_valid_token(payload)

        # Tamper payload by 1 character
        tampered_payload = {"action": "fs_write", "path": "/tmp/authorized.dat", "data": "MALICIOUS_DATA"}

        with self.assertRaisesRegex(SecurityTrapException, "INTENT_EXECUTION_PARITY_MISMATCH"):
            driver.execute_write(token, tampered_payload)

        # Assert driver state remains untouched (ZERO side effects executed)
        self.assertEqual(len(driver.executed_writes), 0, "No actuation must occur on digest mismatch!")


if __name__ == "__main__":
    unittest.main()
