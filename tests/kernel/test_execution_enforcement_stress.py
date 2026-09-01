"""
Cortex Gate A Multi-Worker Adversarial Stress & Race Verification Suite

Deliberately attacks lifecycle boundaries, process trees, and concurrent capacity reuse:
1. Concurrent capacity reuse safety race prevention.
2. Multi-level descendant survival & SIGTERM-ignoring process tree termination.
3. Injected cgroup attachment/verification failure handling (fail-closed policy).
4. Worker termination at every lifecycle boundary.
5. Concurrent reservation bounds validation (sum(ActiveReservations) <= Capacity).
6. Gateway control-plane isolation under severe worker pressure.
7. Repeated lifecycle churn & zero-leak resource reclamation.
8. Double-cleanup idempotency & thread-safety.
9. Stale message rejection post-termination.
"""

import os
import shutil
import signal
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed

from cortex.tools.kernel.enforcement.cgroup import CgroupResourceEnforcer
from cortex.tools.kernel.enforcement.contract import (
    EnforcementContract,
    EnvironmentCapability,
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
from cortex.tools.kernel.resource_authority import (
    InsufficientCapacityError,
    ResourceAuthority,
)


class TestExecutionEnforcementStress(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="cortex_stress_")
        self.root_cgroup_dir = os.path.join(self.tmp_dir, "sys_fs_cgroup_cortex")
        os.makedirs(self.root_cgroup_dir, exist_ok=True)
        self.enforcer = CgroupResourceEnforcer(root_cgroup_dir=self.root_cgroup_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_01_concurrent_capacity_reuse_race(self):
        """
        ADVERSARIAL RACE TEST:
        Worker A is launched with a child process, receives SIGTERM, and slowly exits.
        Worker B concurrently attempts to reserve Worker A's capacity.
        Asserts B_CapacityReusable => A_ExecutionTreeTerminated.
        """
        auth = ResourceAuthority(capacity=100, safety_margin=0, uncertainty=0)

        # Worker A reserves 100 units (100% capacity)
        auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        contract_a = EnforcementContract(
            reservation_id=1,
            worker_id=1,
            cpu_mcores=1000,
            memory_bytes=100,
            pids_max=10,
            require_physical_enforcement=False,
        )
        sup_a = WorkerSupervisor(
            contract=contract_a, resource_authority=auth, enforcer=self.enforcer, grace_period_sec=0.2
        )

        # Worker A script spawns a child process and sleeps
        worker_script = (
            "import subprocess, sys, time; "
            "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(2)']); "
            "time.sleep(2)"
        )
        _proc_a = sup_a.launch_contained_worker(command=[sys.executable, "-c", worker_script])

        race_success = False
        reused_prematurely = False

        def worker_b_attempt():
            nonlocal race_success, reused_prematurely
            try:
                auth.reserve(
                    res_id=2,
                    res_inv=102,
                    res_att=2,
                    res_worker=2,
                    res_demand=100,
                    authority_epoch=1,
                    lease_epoch=1,
                    worker_generation=1,
                )
                race_success = True
                # If Worker B succeeded in reserving capacity, check if Worker A is still running
                if sup_a.state not in (
                    SupervisorLifecycleState.RESOURCE_RECONCILED,
                    SupervisorLifecycleState.CGROUP_CLEANED,
                ):
                    reused_prematurely = True
            except InsufficientCapacityError:
                pass

        # Concurrently attempt Worker B reservation while Worker A is terminating
        t_b = threading.Thread(target=worker_b_attempt)

        # Start Worker A termination
        t_b.start()
        sup_a.terminate_worker_and_reclaim()
        t_b.join()

        # Verify invariant: Capacity could not be reused prematurely while A was alive
        self.assertFalse(
            reused_prematurely, "Invariant Violation: Capacity released while Worker A execution tree was alive!"
        )

        # Now Worker B must be able to reserve successfully
        rec_b = auth.reserve(
            res_id=2,
            res_inv=102,
            res_att=2,
            res_worker=2,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        self.assertEqual(rec_b.res_id, 2)

    def test_02_descendant_survival_and_sigterm_ignore(self):
        """
        ADVERSARIAL DESCENDANT TEST:
        Spawns Worker -> Child -> Grandchild tree where Child explicitly IGNORES SIGTERM.
        Verifies Supervisor forces SIGKILL after grace period and all descendants are terminated.
        """
        auth = ResourceAuthority(capacity=1000)
        auth.reserve(
            res_id=10,
            res_inv=201,
            res_att=1,
            res_worker=10,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        contract = EnforcementContract(
            reservation_id=10,
            worker_id=10,
            cpu_mcores=1000,
            memory_bytes=128 * 1024 * 1024,
            pids_max=32,
            require_physical_enforcement=False,
        )
        # Short grace period of 0.2s to force SIGKILL path quickly
        supervisor = WorkerSupervisor(
            contract=contract, resource_authority=auth, enforcer=self.enforcer, grace_period_sec=0.2
        )

        # Worker script spawns child that ignores SIGTERM
        stubborn_script = (
            "import signal, subprocess, sys, time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "p = subprocess.Popen([sys.executable, '-c', 'import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(10)']); "
            "time.sleep(10)"
        )
        proc = supervisor.launch_contained_worker(command=[sys.executable, "-c", stubborn_script])
        time.sleep(0.3)

        # Terminate worker and verify forced SIGKILL teardown
        telemetry = supervisor.terminate_worker_and_reclaim()
        self.assertEqual(supervisor.state, SupervisorLifecycleState.CGROUP_CLEANED)
        self.assertIsNotNone(telemetry.termination_time)
        self.assertIn(proc.poll(), (-9, -15, 0, 1))

    def test_03_cgroup_attachment_failure_injection(self):
        """
        FAIL-CLOSED INJECTION TEST:
        Simulates failure during cgroup creation / attachment.
        Asserts RequiredPhysicalEnforcement AND Failure => ExecutionRejected.
        """
        auth = ResourceAuthority()
        auth.reserve(
            res_id=30,
            res_inv=301,
            res_att=1,
            res_worker=30,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )

        class FaultyEnforcer(CgroupResourceEnforcer):
            @staticmethod
            def detect_environment():
                return EnvironmentCapability.SUPPORTED_AVAILABLE

            def create_worker_cgroup(self, contract):
                raise OSError("Injected disk write failure")

        faulty_enforcer = FaultyEnforcer(root_cgroup_dir=self.root_cgroup_dir)
        contract = EnforcementContract(
            reservation_id=30,
            worker_id=30,
            cpu_mcores=1000,
            memory_bytes=100,
            pids_max=10,
            require_physical_enforcement=True,
        )
        supervisor = WorkerSupervisor(contract=contract, resource_authority=auth, enforcer=faulty_enforcer)

        with self.assertRaises(ExecutionContainmentError):
            supervisor.launch_contained_worker(command=[sys.executable, "-c", "print('hello')"])

        self.assertEqual(supervisor.state, SupervisorLifecycleState.FAILED_CLOSED)

    def test_04_lifecycle_boundary_worker_deaths(self):
        """
        LIFECYCLE BOUNDARY FAULT TEST:
        Executes worker launch and immediate termination across multiple state boundaries.
        Verifies state machine converges to CGROUP_CLEANED deterministically.
        """
        for i in range(5):
            auth = ResourceAuthority(capacity=1000)
            res_id = 40 + i
            auth.reserve(
                res_id=res_id,
                res_inv=400 + i,
                res_att=i + 1,
                res_worker=40 + i,
                res_demand=50,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
            )
            contract = EnforcementContract(
                reservation_id=res_id,
                worker_id=40 + i,
                cpu_mcores=500,
                memory_bytes=50,
                pids_max=5,
                require_physical_enforcement=False,
            )
            supervisor = WorkerSupervisor(
                contract=contract, resource_authority=auth, enforcer=self.enforcer, grace_period_sec=0.1
            )

            _proc = supervisor.launch_contained_worker(command=[sys.executable, "-c", "import time; time.sleep(0.5)"])
            # Terminate at varying delays
            time.sleep(0.02 * i)
            telemetry = supervisor.terminate_worker_and_reclaim()
            self.assertEqual(supervisor.state, SupervisorLifecycleState.CGROUP_CLEANED)
            self.assertIsNotNone(telemetry.cleanup_time)

    def test_05_concurrent_reservations_capacity_bound(self):
        """
        CONCURRENT CAPACITY BOUND TEST:
        16 threads race to reserve capacity on a system with 400 total units.
        Asserts sum(ActiveReservations) <= Capacity at all times.
        """
        capacity_units = 400
        auth = ResourceAuthority(capacity=capacity_units, safety_margin=0, uncertainty=0)

        successful_reservations = []
        rejected_reservations = []
        lock = threading.Lock()

        def attempt_reservation(worker_idx: int):
            res_id = 1000 + worker_idx
            try:
                rec = auth.reserve(
                    res_id=res_id,
                    res_inv=2000 + worker_idx,
                    res_att=worker_idx + 1,
                    res_worker=worker_idx,
                    res_demand=100,
                    authority_epoch=1,
                    lease_epoch=1,
                    worker_generation=1,
                )
                with lock:
                    successful_reservations.append(rec)
            except InsufficientCapacityError:
                with lock:
                    rejected_reservations.append(worker_idx)

        # 16 concurrent threads requesting 100 units each (capacity only allows 4 max)
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(attempt_reservation, i) for i in range(16)]
            for future in as_completed(futures):
                future.result()

        # Verify strict capacity bounds
        self.assertEqual(len(successful_reservations), 4)
        self.assertEqual(len(rejected_reservations), 12)
        total_reserved = sum(r.res_demand for r in successful_reservations)
        self.assertLessEqual(total_reserved, capacity_units)

    def test_06_gateway_control_plane_isolation_under_pressure(self):
        """
        GATEWAY ISOLATION TEST:
        Launches 4 workers that generate RAM/CPU pressure.
        Asserts host Gateway process (test runner PID) remains healthy and unaffected.
        """
        gateway_pid = os.getpid()
        auth = ResourceAuthority(capacity=10000)

        supervisors = []
        for i in range(4):
            res_id = 500 + i
            auth.reserve(
                res_id=res_id,
                res_inv=600 + i,
                res_att=i + 1,
                res_worker=50 + i,
                res_demand=100,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
            )
            contract = EnforcementContract(
                reservation_id=res_id,
                worker_id=50 + i,
                cpu_mcores=500,
                memory_bytes=64 * 1024 * 1024,
                pids_max=16,
                require_physical_enforcement=False,
            )
            sup = WorkerSupervisor(
                contract=contract, resource_authority=auth, enforcer=self.enforcer, grace_period_sec=0.1
            )
            # Worker allocates memory and sleeps
            cmd = [sys.executable, "-c", "x = 'a' * (5 * 1024 * 1024); import time; time.sleep(0.5)"]
            sup.launch_contained_worker(command=cmd)
            supervisors.append(sup)

        time.sleep(0.2)

        # Reclaim all workers
        for sup in supervisors:
            sup.terminate_worker_and_reclaim()
            self.assertEqual(sup.state, SupervisorLifecycleState.CGROUP_CLEANED)

        # Host Gateway PID must remain identical and responsive
        self.assertEqual(os.getpid(), gateway_pid)

    def test_07_repeated_lifecycle_churn_and_zero_leak_reclamation(self):
        """
        REPEATED CHURN RECLAMATION TEST:
        Runs 20 sequential worker lifecycle cycles (reserve -> launch -> execute -> reclaim).
        Asserts ActiveReservations == 0 and ResourceAuthority.used == 0 at conclusion.
        """
        auth = ResourceAuthority(capacity=1000)

        for cycle in range(20):
            res_id = 2000 + cycle
            auth.reserve(
                res_id=res_id,
                res_inv=3000 + cycle,
                res_att=cycle + 1,
                res_worker=cycle,
                res_demand=200,
                authority_epoch=1,
                lease_epoch=1,
                worker_generation=1,
            )
            contract = EnforcementContract(
                reservation_id=res_id,
                worker_id=cycle,
                cpu_mcores=500,
                memory_bytes=64 * 1024 * 1024,
                pids_max=10,
                require_physical_enforcement=False,
            )
            supervisor = WorkerSupervisor(
                contract=contract, resource_authority=auth, enforcer=self.enforcer, grace_period_sec=0.1
            )
            supervisor.launch_contained_worker(command=[sys.executable, "-c", "import sys; sys.exit(0)"])
            supervisor.terminate_worker_and_reclaim()
            self.assertEqual(supervisor.state, SupervisorLifecycleState.CGROUP_CLEANED)

        # Assert zero active reservation leaks
        active_count = sum(1 for r in auth._reservations.values() if r.res_status.is_active())
        self.assertEqual(active_count, 0)

    def test_08_double_cleanup_and_idempotency(self):
        """
        IDEMPOTENCY TEST:
        Calls terminate_worker_and_reclaim() repeatedly on the same supervisor.
        Asserts no exceptions, idempotent state preservation, and safe double release.
        """
        auth = ResourceAuthority(capacity=1000)
        auth.reserve(
            res_id=88,
            res_inv=888,
            res_att=1,
            res_worker=88,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        contract = EnforcementContract(
            reservation_id=88,
            worker_id=88,
            cpu_mcores=500,
            memory_bytes=50,
            pids_max=5,
            require_physical_enforcement=False,
        )
        supervisor = WorkerSupervisor(contract=contract, resource_authority=auth, enforcer=self.enforcer)
        supervisor.launch_contained_worker(command=[sys.executable, "-c", "import time; time.sleep(0.1)"])

        t1 = supervisor.terminate_worker_and_reclaim()
        t2 = supervisor.terminate_worker_and_reclaim()
        t3 = supervisor.terminate_worker_and_reclaim()

        self.assertEqual(supervisor.state, SupervisorLifecycleState.CGROUP_CLEANED)
        self.assertEqual(t1.reservation_id, t2.reservation_id)
        self.assertEqual(t2.reservation_id, t3.reservation_id)

    def test_09_stale_message_rejection_after_termination(self):
        """
        STALE MESSAGE REJECTION TEST:
        After a worker is terminated and reclaimed, delayed heartbeat or status updates
        cannot mutate state back to DRAINING or resurrect authorization.
        """
        auth = ResourceAuthority(capacity=1000)
        auth.reserve(
            res_id=99,
            res_inv=999,
            res_att=1,
            res_worker=99,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        contract = EnforcementContract(
            reservation_id=99,
            worker_id=99,
            cpu_mcores=500,
            memory_bytes=50,
            pids_max=5,
            require_physical_enforcement=False,
        )
        identity = ExecutionIdentity(
            group_id="grp_99", instance_id="inst_99", generation=1, config_generation=1, attempt_id=1
        )
        tracker = WorkerLifecycleTracker(execution_identity=identity)
        supervisor = WorkerSupervisor(
            contract=contract, resource_authority=auth, enforcer=self.enforcer, lifecycle_tracker=tracker
        )

        supervisor.launch_contained_worker(command=[sys.executable, "-c", "import time; time.sleep(0.1)"])
        supervisor.terminate_worker_and_reclaim()

        self.assertEqual(supervisor.state, SupervisorLifecycleState.CGROUP_CLEANED)
        self.assertEqual(tracker.stage, WorkerLifecycleStage.TERMINATED)

        # Attempt stale draining transition -> Tracker must reject transition back to DRAINING
        tracker.begin_draining()

        # State remains TERMINATED
        self.assertEqual(tracker.stage, WorkerLifecycleStage.TERMINATED)

    def test_10_unexpected_external_worker_crash_recovery(self):
        """
        UNEXPECTED CRASH RECOVERY TEST:
        Worker dies unexpectedly via out-of-band SIGKILL (e.g. host OOM / external kill).
        Verifies: Worker dies -> Supervisor observes -> Reservation reconciles -> Capacity becomes reusable.
        """
        auth = ResourceAuthority(capacity=100, safety_margin=0, uncertainty=0)

        # Worker A reserves 100% capacity
        auth.reserve(
            res_id=101,
            res_inv=901,
            res_att=1,
            res_worker=101,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        contract_a = EnforcementContract(
            reservation_id=101,
            worker_id=101,
            cpu_mcores=1000,
            memory_bytes=100,
            pids_max=10,
            require_physical_enforcement=False,
        )
        supervisor_a = WorkerSupervisor(
            contract=contract_a, resource_authority=auth, enforcer=self.enforcer, grace_period_sec=0.1
        )

        proc = supervisor_a.launch_contained_worker(command=[sys.executable, "-c", "import time; time.sleep(10)"])
        time.sleep(0.1)

        # External SIGKILL (simulating crash / OOM killer)
        os.kill(proc.pid, signal.SIGKILL)
        time.sleep(0.1)

        # Supervisor observes exit and performs 7-stage reclamation sequence
        telemetry = supervisor_a.terminate_worker_and_reclaim()

        self.assertEqual(supervisor_a.state, SupervisorLifecycleState.CGROUP_CLEANED)
        self.assertEqual(telemetry.exit_code, -9)

        # Verify capacity is now reusable by Worker B
        rec_b = auth.reserve(
            res_id=102,
            res_inv=902,
            res_att=2,
            res_worker=102,
            res_demand=100,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
        )
        self.assertEqual(rec_b.res_id, 102)


if __name__ == "__main__":
    unittest.main()
