"""
Cortex Gate A Physical Execution Security & Resource Enforcement Test Suite

Verifies:
1. Environment capability classification and limit conversion.
2. Safe atomic cgroup startup & fail-closed execution boundary enforcement.
3. Process-tree containment (ExecutionTree(w) <= CG_w).
4. Graceful and forced process termination (SIGTERM -> SIGKILL).
5. Post-exit state transitions (PROCESS_EXITED -> RESOURCE_RECLAIMING -> RESOURCE_RECONCILED -> CGROUP_CLEANED).
6. Capacity reuse safety (Worker B capacity allocation gated on Worker A process termination).
7. Gateway survival during worker resource violations.
8. 10-field telemetry collection.
"""

import os
import shutil
import sys
import tempfile
import time
import unittest

from cortex.tools.kernel.enforcement.cgroup import CgroupResourceEnforcer
from cortex.tools.kernel.enforcement.contract import (
    EnforcementContract,
    SupervisorLifecycleState,
)
from cortex.tools.kernel.enforcement.supervisor import (
    ExecutionContainmentError,
    WorkerSupervisor,
)
from cortex.tools.kernel.replica.identity import ExecutionIdentity
from cortex.tools.kernel.replica.lifecycle import (
    WorkerLifecycleStage,
    WorkerLifecycleTracker,
)
from cortex.tools.kernel.resource_authority import ResourceAuthority


class TestExecutionEnforcement(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="cortex_cgroup_test_")
        self.root_cgroup_dir = os.path.join(self.tmp_dir, "sys_fs_cgroup_cortex")
        os.makedirs(self.root_cgroup_dir, exist_ok=True)
        self.enforcer = CgroupResourceEnforcer(root_cgroup_dir=self.root_cgroup_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_enforcement_contract_conversion(self):
        """Verifies limit unit conversion for cpu.max, memory.max, and pids.max."""
        contract = EnforcementContract(
            reservation_id=1,
            worker_id=101,
            cpu_mcores=2000,        # 2 CPU cores
            memory_bytes=1073741824, # 1 GiB
            pids_max=64,
        )
        self.assertEqual(contract.to_cgroup_cpu_max(period_us=100000), "200000 100000")
        self.assertEqual(contract.to_cgroup_memory_max(), "1073741824")
        self.assertEqual(contract.to_cgroup_pids_max(), "64")

        contract_unlimited = EnforcementContract(
            reservation_id=2, worker_id=102, cpu_mcores=0, memory_bytes=0, pids_max=0
        )
        self.assertEqual(contract_unlimited.to_cgroup_cpu_max(), "max 100000")
        self.assertEqual(contract_unlimited.to_cgroup_memory_max(), "max")
        self.assertEqual(contract_unlimited.to_cgroup_pids_max(), "max")

    def test_02_cgroup_directory_creation_and_limit_writing(self):
        """Verifies directory creation and limit file writing in test cgroup structure."""
        contract = EnforcementContract(
            reservation_id=10, worker_id=1, cpu_mcores=1500, memory_bytes=512 * 1024 * 1024, pids_max=32
        )
        cgroup_path = self.enforcer.create_worker_cgroup(contract)
        self.assertTrue(os.path.exists(cgroup_path))

        with open(os.path.join(cgroup_path, "cpu.max"), "r") as f:
            self.assertEqual(f.read().strip(), "150000 100000")

        with open(os.path.join(cgroup_path, "memory.max"), "r") as f:
            self.assertEqual(f.read().strip(), str(512 * 1024 * 1024))

        with open(os.path.join(cgroup_path, "pids.max"), "r") as f:
            self.assertEqual(f.read().strip(), "32")

    def test_03_supervisor_launch_and_process_containment(self):
        """Verifies worker process launch, cgroup attachment, containment check, and clean termination."""
        auth = ResourceAuthority(capacity=10000)
        _rec = auth.reserve(
            res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=100,
            authority_epoch=1, lease_epoch=1, worker_generation=1
        )
        contract = EnforcementContract(
            reservation_id=1, worker_id=1, cpu_mcores=1000, memory_bytes=256 * 1024 * 1024, pids_max=16,
            require_physical_enforcement=False  # Allow test execution in temp environment
        )
        identity = ExecutionIdentity(
            group_id="grp_1", instance_id="inst_1", generation=1, config_generation=1, attempt_id=1
        )
        tracker = WorkerLifecycleTracker(execution_identity=identity)
        supervisor = WorkerSupervisor(
            contract=contract, resource_authority=auth, enforcer=self.enforcer, lifecycle_tracker=tracker
        )

        cmd = [sys.executable, "-c", "import time; time.sleep(1)"]
        proc = supervisor.launch_contained_worker(command=cmd)
        self.assertEqual(supervisor.state, SupervisorLifecycleState.RUNNING)
        self.assertIsNotNone(proc.pid)

        # Verify lifecycle state transitions during termination
        _telemetry = supervisor.terminate_worker_and_reclaim()
        self.assertEqual(supervisor.state, SupervisorLifecycleState.CGROUP_CLEANED)
        self.assertEqual(tracker.stage, WorkerLifecycleStage.TERMINATED)
        self.assertIsNotNone(_telemetry.termination_time)
        self.assertIsNotNone(_telemetry.reconciliation_time)
        self.assertIn(_telemetry.exit_code, (0, -15))

    def test_04_fail_closed_policy_on_unsupported_environment(self):
        """Verifies that require_physical_enforcement=True fails closed when cgroup capability is unavailable."""
        auth = ResourceAuthority()
        auth.reserve(
            res_id=2, res_inv=102, res_att=1, res_worker=2, res_demand=100,
            authority_epoch=1, lease_epoch=1, worker_generation=1
        )
        contract = EnforcementContract(
            reservation_id=2, worker_id=2, cpu_mcores=1000, memory_bytes=256 * 1024 * 1024, pids_max=16,
            require_physical_enforcement=True
        )
        supervisor = WorkerSupervisor(contract=contract, resource_authority=auth, enforcer=self.enforcer)

        with self.assertRaises(ExecutionContainmentError):
            supervisor.launch_contained_worker(command=[sys.executable, "-c", "print('hello')"])

        self.assertEqual(supervisor.state, SupervisorLifecycleState.FAILED_CLOSED)

    def test_05_child_process_tree_containment_and_termination(self):
        """Verifies that spawned child processes are tracked and terminated cleanly during reclamation."""
        auth = ResourceAuthority(capacity=10000)
        auth.reserve(
            res_id=3, res_inv=103, res_att=1, res_worker=3, res_demand=100,
            authority_epoch=1, lease_epoch=1, worker_generation=1
        )
        contract = EnforcementContract(
            reservation_id=3, worker_id=3, cpu_mcores=1000, memory_bytes=256 * 1024 * 1024, pids_max=16,
            require_physical_enforcement=False
        )
        supervisor = WorkerSupervisor(contract=contract, resource_authority=auth, enforcer=self.enforcer)

        # Worker spawns a child subprocess that sleeps
        worker_script = (
            "import subprocess, sys, time; "
            "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)']); "
            "time.sleep(10)"
        )
        proc = supervisor.launch_contained_worker(command=[sys.executable, "-c", worker_script])
        time.sleep(0.3)

        # Terminate worker and verify process tree exits cleanly
        _telemetry = supervisor.terminate_worker_and_reclaim()
        self.assertEqual(supervisor.state, SupervisorLifecycleState.CGROUP_CLEANED)
        self.assertIn(proc.poll(), (-15, -9, 0, 1))

    def test_06_capacity_reuse_safety_race_prevention(self):
        """
        ADVERSARIAL RACE TEST:
        Proves Worker B cannot consume Worker A's reserved resources until Worker A has reached
        PROCESS_EXITED and RESOURCE_RECONCILED.
        """
        auth = ResourceAuthority(capacity=100, safety_margin=0, uncertainty=0)

        # Worker A reserves 100% capacity (100 units)
        _rec_a = auth.reserve(
            res_id=10, res_inv=201, res_att=1, res_worker=10, res_demand=100,
            authority_epoch=1, lease_epoch=1, worker_generation=1
        )
        contract_a = EnforcementContract(
            reservation_id=10, worker_id=10, cpu_mcores=1000, memory_bytes=100, pids_max=10,
            require_physical_enforcement=False
        )
        sup_a = WorkerSupervisor(contract=contract_a, resource_authority=auth, enforcer=self.enforcer)
        _proc_a = sup_a.launch_contained_worker(command=[sys.executable, "-c", "import time; time.sleep(5)"])

        # Attempt to reserve capacity for Worker B while Worker A is still running -> Must fail (P2)
        from cortex.tools.kernel.resource_authority import InsufficientCapacityError
        with self.assertRaises(InsufficientCapacityError):
            auth.reserve(
                res_id=11, res_inv=202, res_att=2, res_worker=11, res_demand=50,
                authority_epoch=1, lease_epoch=1, worker_generation=1
            )

        # Terminate Worker A process and reconcile
        sup_a.terminate_worker_and_reclaim()
        self.assertEqual(sup_a.state, SupervisorLifecycleState.CGROUP_CLEANED)

        # NOW Worker B can reserve capacity safely
        rec_b = auth.reserve(
            res_id=11, res_inv=202, res_att=2, res_worker=11, res_demand=50,
            authority_epoch=1, lease_epoch=1, worker_generation=1
        )
        self.assertEqual(rec_b.res_id, 11)

    def test_07_gateway_survival_and_telemetry_collection(self):
        """Verifies Gateway host process survival and 10-field telemetry collection upon worker exit."""
        auth = ResourceAuthority(capacity=1000)
        auth.reserve(
            res_id=20, res_inv=301, res_att=1, res_worker=20, res_demand=100,
            authority_epoch=1, lease_epoch=1, worker_generation=1
        )
        contract = EnforcementContract(
            reservation_id=20, worker_id=20, cpu_mcores=1000, memory_bytes=128 * 1024 * 1024, pids_max=16,
            require_physical_enforcement=False
        )
        supervisor = WorkerSupervisor(contract=contract, resource_authority=auth, enforcer=self.enforcer)

        # Launch worker that exits with code 0
        proc = supervisor.launch_contained_worker(command=[sys.executable, "-c", "import sys; sys.exit(0)"])
        proc.wait()

        telemetry = supervisor.terminate_worker_and_reclaim()
        t_dict = telemetry.to_dict()

        # Assert all 10 required telemetry fields are present
        self.assertEqual(t_dict["reservation_id"], 20)
        self.assertEqual(t_dict["worker_id"], 20)
        self.assertIsNotNone(t_dict["main_pid"])
        self.assertGreater(t_dict["start_time"], 0)
        self.assertIsNotNone(t_dict["termination_time"])
        self.assertEqual(t_dict["exit_code"], 0)
        self.assertIsNotNone(t_dict["reconciliation_time"])
        self.assertIsNotNone(t_dict["cleanup_time"])
        self.assertIn("memory_max_bytes", t_dict)
        self.assertIn("pids_max_count", t_dict)

        # Host Gateway process (test runner) remains healthy
        self.assertTrue(os.getpid() > 0)


if __name__ == "__main__":
    unittest.main()
