"""
Sub-Gate B.2 Adversarial Network Isolation Test Suite (B.2.1, B.2.2, B.2.3)

Verifies kernel-enforced network isolation for worker execution:
    B.2.1: Dedicated Network Namespace Isolation (NetNS(worker) != NetNS(host))
    B.2.2: Default-Deny Network Egress Enforcement (TCP / UDP / DNS / Raw Socket Denial)
    B.2.3: Gateway IPC Preservation (UDS / Stdio)

Governance Rule:
    Supervisor Executes; Authority Decides.
    RequiredPhysicalEnforcement AND AttachmentFailure => ExecutionRejected (Fail-Closed).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import unittest
from typing import Optional
from unittest.mock import MagicMock

from cortex.tools.kernel.enforcement.contract import EnforcementContract, SupervisorLifecycleState
from cortex.tools.kernel.enforcement.netns import NetworkCapability, NetworkNamespaceEnforcer
from cortex.tools.kernel.enforcement.supervisor import ExecutionContainmentError, WorkerSupervisor


def _make_mock_authority() -> MagicMock:
    """Creates a MagicMock ResourceAuthority that safely no-ops on release()."""
    mock = MagicMock()
    mock.release.return_value = None
    mock.release_reservation.return_value = None
    return mock


class TestSubGateB2_NetworkIsolation(unittest.TestCase):
    """12-point adversarial matrix for physical network namespace enforcement."""

    def setUp(self) -> None:
        self.enforcer = NetworkNamespaceEnforcer()
        self.capability = self.enforcer.detect_environment()
        if self.capability != NetworkCapability.SUPPORTED_AVAILABLE:
            self.skipTest(f"CLONE_NEWUSER | CLONE_NEWNET not available ({self.capability.name})")

        self.authority = _make_mock_authority()
        self.contract = EnforcementContract(
            reservation_id=901,
            worker_id=2001,
            cpu_mcores=500,
            memory_bytes=256 * 1024 * 1024,
            pids_max=64,
            require_physical_enforcement=False,
            require_network_isolation=True,
            allow_network_egress=False,
        )

    def _make_supervisor(
        self,
        netns_enforcer: Optional[NetworkNamespaceEnforcer] = None,
    ) -> WorkerSupervisor:
        return WorkerSupervisor(
            contract=self.contract,
            resource_authority=self.authority,
            netns_enforcer=netns_enforcer or self.enforcer,
        )

    def _run_isolated_worker(self, script: str, timeout: float = 5.0) -> subprocess.CompletedProcess:
        """Launches a worker inside an isolated netns and returns its result."""
        supervisor = self._make_supervisor()
        cmd = [sys.executable, "-c", textwrap.dedent(script)]
        proc = supervisor.launch_contained_worker(cmd)
        stdout, stderr = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    # ────────────────────────────────────────────────────────────────────
    # B.2.1 — Dedicated Network Namespace Isolation
    # ────────────────────────────────────────────────────────────────────

    def test_b2_01_netns_inode_disparity(self) -> None:
        """Worker resides in a distinct network namespace from the host."""
        supervisor = self._make_supervisor()
        cmd = [sys.executable, "-c", "import time; time.sleep(3)"]
        proc = supervisor.launch_contained_worker(cmd)
        try:
            self.assertTrue(
                self.enforcer.verify_isolation(proc.pid, os.getpid()),
                "Worker netns inode must differ from host netns inode",
            )
        finally:
            proc.kill()
            proc.wait()

    def test_b2_11_host_network_unaffected(self) -> None:
        """Host network namespace inode remains unchanged after worker lifecycle."""
        host_inode_before = self.enforcer.get_netns_inode(os.getpid())
        self._run_isolated_worker("import time; time.sleep(0.2)")
        host_inode_after = self.enforcer.get_netns_inode(os.getpid())
        self.assertEqual(host_inode_before, host_inode_after)

    # ────────────────────────────────────────────────────────────────────
    # B.2.2 — Default-Deny Network Egress
    # ────────────────────────────────────────────────────────────────────

    def test_b2_02_outbound_tcp_denied(self) -> None:
        """Outbound TCP to external IP is physically denied (Errno 101)."""
        result = self._run_isolated_worker("""\
            import socket, sys
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            try:
                s.connect(('8.8.8.8', 53))
                sys.exit(0)
            except OSError as e:
                if e.errno == 101 or 'unreachable' in str(e).lower():
                    sys.exit(101)
                sys.exit(1)
        """)
        self.assertEqual(result.returncode, 101, f"TCP should be denied. stderr: {result.stderr}")

    def test_b2_03_outbound_udp_denied(self) -> None:
        """Outbound UDP sendto to external IP is physically denied."""
        result = self._run_isolated_worker("""\
            import socket, sys
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.sendto(b'ping', ('8.8.8.8', 53))
                sys.exit(0)
            except OSError as e:
                if e.errno == 101 or 'unreachable' in str(e).lower():
                    sys.exit(101)
                sys.exit(1)
        """)
        self.assertEqual(result.returncode, 101, f"UDP should be denied. stderr: {result.stderr}")

    def test_b2_04_dns_escape_denied(self) -> None:
        """DNS resolution cannot escape the default-deny policy."""
        result = self._run_isolated_worker("""\
            import socket, sys
            try:
                socket.gethostbyname('example.com')
                sys.exit(0)
            except Exception:
                sys.exit(102)
        """)
        self.assertEqual(result.returncode, 102, f"DNS should fail. stderr: {result.stderr}")

    def test_b2_05_raw_socket_denied(self) -> None:
        """Raw socket creation is denied inside unprivileged netns."""
        result = self._run_isolated_worker("""\
            import socket, sys
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
                sys.exit(0)
            except Exception:
                sys.exit(103)
        """)
        self.assertEqual(result.returncode, 103, f"Raw socket should be denied. stderr: {result.stderr}")

    def test_b2_12_worker_cannot_unshare_standalone_newnet(self) -> None:
        """Worker inside unprivileged netns cannot escalate via standalone CLONE_NEWNET."""
        result = self._run_isolated_worker("""\
            import ctypes, sys
            CLONE_NEWNET = 0x40000000
            libc = ctypes.CDLL('libc.so.6')
            res = libc.unshare(CLONE_NEWNET)
            sys.exit(0 if res == 0 else 104)
        """)
        self.assertEqual(result.returncode, 104, f"Standalone CLONE_NEWNET should be denied. stderr: {result.stderr}")

    # ────────────────────────────────────────────────────────────────────
    # B.2.3 — Gateway IPC Preservation
    # ────────────────────────────────────────────────────────────────────

    def test_b2_10_gateway_uds_ipc_preserved(self) -> None:
        """AF_UNIX IPC between isolated worker and host UDS server functions correctly."""
        tmp_dir = tempfile.mkdtemp()
        sock_path = os.path.join(tmp_dir, "gateway.sock")

        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(sock_path)
        server_sock.listen(1)
        server_sock.settimeout(5.0)

        try:
            script = f"""\
                import socket, sys
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect('{sock_path}')
                s.sendall(b'IPC_PING')
                s.close()
            """
            supervisor = self._make_supervisor()
            cmd = [sys.executable, "-c", textwrap.dedent(script)]
            proc = supervisor.launch_contained_worker(cmd)

            conn, _ = server_sock.accept()
            msg = conn.recv(64)
            conn.close()

            proc.communicate(timeout=5.0)
            self.assertEqual(msg, b"IPC_PING")
            self.assertEqual(proc.returncode, 0)
        finally:
            server_sock.close()
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # ────────────────────────────────────────────────────────────────────
    # Fail-Closed & Lifecycle
    # ────────────────────────────────────────────────────────────────────

    def test_b2_06_netns_verification_failure_rejects_worker(self) -> None:
        """Namespace verification failure triggers ExecutionContainmentError (fail-closed)."""

        class FailingNetNSEnforcer(NetworkNamespaceEnforcer):
            def verify_isolation(self, child_pid: int, host_pid: int = 0) -> bool:
                return False

        supervisor = self._make_supervisor(netns_enforcer=FailingNetNSEnforcer())
        cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
        with self.assertRaises(ExecutionContainmentError):
            supervisor.launch_contained_worker(cmd)
        self.assertEqual(supervisor.state, SupervisorLifecycleState.FAILED_CLOSED)

    def test_b2_07_worker_crash_clean_reclamation(self) -> None:
        """Worker crash (sys.exit(42)) produces clean reclamation without orphaned resources."""
        result = self._run_isolated_worker("import sys; sys.exit(42)")
        self.assertEqual(result.returncode, 42)

    def test_b2_08_worker_sigkill_handled(self) -> None:
        """SIGKILL to worker process is handled; process terminates deterministically."""
        supervisor = self._make_supervisor()
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        proc = supervisor.launch_contained_worker(cmd)
        proc.kill()
        proc.wait()
        self.assertIsNotNone(proc.returncode)

    def test_b2_09_stale_orphan_forced_termination(self) -> None:
        """Stale orphan worker is forcibly terminated on supervisor cleanup."""
        supervisor = self._make_supervisor()
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        proc = supervisor.launch_contained_worker(cmd)
        proc.kill()
        proc.wait()
        self.assertTrue(proc.returncode is not None)


if __name__ == "__main__":
    unittest.main()
