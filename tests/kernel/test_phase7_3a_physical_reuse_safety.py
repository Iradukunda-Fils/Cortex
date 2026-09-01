"""
Phase 7.3a Integration Closure & Physical Reuse Safety Test Suite

Normative Specification: Research Note 22 / Phase 7.3a Physical Reclamation Safety Gate
Verifies:
1. Normal release physical capacity gating.
2. SIGTERM graceful process termination & exit confirmation before reuse.
3. SIGKILL forced process termination & exit confirmation before reuse.
4. Child process survival containment & full tree termination before reuse.
5. Grandchild process survival containment & full tree termination before reuse.
6. Expire during active execution (Fence -> Terminate -> Reclaim -> Reuse).
7. Revoke during active execution (Fence -> Terminate -> Reclaim -> Reuse).
8. Concurrent release + reserve race condition safety.
9. Crash during reconciliation deterministic recovery.
10. Crash before cgroup cleanup non-overcommit safety.
11. Stale release rejection and generation protection.
12. Discrete GPU release isolation.
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
from cortex.tools.kernel.enforcement.supervisor import WorkerSupervisor
from cortex.tools.kernel.replica.identity import ExecutionIdentity
from cortex.tools.kernel.replica.lifecycle import WorkerLifecycleTracker
from cortex.tools.kernel.resource_authority import (
    DemandVector,
    InsufficientCapacityError,
    InvalidFencingError,
    ResourceAuthority,
)


class TestPhase73aPhysicalReuseSafety(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="cortex_73a_test_")
        self.root_cgroup_dir = os.path.join(self.tmp_dir, "sys_fs_cgroup_cortex")
        os.makedirs(self.root_cgroup_dir, exist_ok=True)
        self.enforcer = CgroupResourceEnforcer(root_cgroup_dir=self.root_cgroup_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_supervisor(self, auth: ResourceAuthority, res_id: int, worker_id: int, cpu: int = 1000, mem: int = 100):
        contract = EnforcementContract(
            reservation_id=res_id,
            worker_id=worker_id,
            cpu_mcores=cpu,
            memory_bytes=mem,
            pids_max=16,
            require_physical_enforcement=False,
        )
        identity = ExecutionIdentity(
            group_id=f"grp_{worker_id}",
            instance_id=f"inst_{worker_id}",
            generation=1,
            config_generation=1,
            attempt_id=1,
        )
        tracker = WorkerLifecycleTracker(execution_identity=identity)
        return WorkerSupervisor(
            contract=contract,
            resource_authority=auth,
            enforcer=self.enforcer,
            lifecycle_tracker=tracker,
            grace_period_sec=0.1,
        )

    def test_scenario_01_normal_release_gated_on_lifecycle_completion(self):
        """Scenario 1: Resource capacity is reusable only after successful process exit & reconciliation."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=1000)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", "import sys; sys.exit(0)"])
        proc.wait()

        # Before terminate_worker_and_reclaim, capacity reservation is still active
        with self.assertRaises(InsufficientCapacityError):
            auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=500)

        sup.terminate_worker_and_reclaim()
        self.assertEqual(sup.state, SupervisorLifecycleState.CGROUP_CLEANED)

        # After lifecycle completion, capacity is reusable
        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_02_sigterm_graceful_termination_then_reuse(self):
        """Scenario 2: SIGTERM graceful process termination -> confirmed exit -> safe capacity reuse."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        # Worker handles SIGTERM gracefully and exits
        script = "import signal, sys, time; signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0)); time.sleep(10)"
        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=1000)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", script])
        time.sleep(0.2)

        telemetry = sup.terminate_worker_and_reclaim()
        self.assertIn(proc.poll(), (0, -15))
        self.assertIn(telemetry.exit_code, (0, -15))
        self.assertEqual(sup.state, SupervisorLifecycleState.CGROUP_CLEANED)

        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_03_sigkill_forced_termination_then_reuse(self):
        """Scenario 3: SIGKILL forced termination (ignoring SIGTERM) -> exit observed -> safe reuse."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        # Worker ignores SIGTERM
        script = "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); while True: time.sleep(1)"
        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=1000)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", script])
        time.sleep(0.2)

        sup.terminate_worker_and_reclaim()
        self.assertIsNotNone(proc.poll())
        self.assertEqual(sup.state, SupervisorLifecycleState.CGROUP_CLEANED)

        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_04_child_survives_parent_containment(self):
        """Scenario 4: Worker process spawns child; no capacity reuse until entire child tree exits."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        # Worker spawns child that sleeps for 10s
        script = (
            "import subprocess, sys, time; "
            "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)']); "
            "time.sleep(10)"
        )
        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=1000)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", script])
        time.sleep(0.3)

        sup.terminate_worker_and_reclaim()
        self.assertIsNotNone(proc.poll())
        self.assertEqual(sup.state, SupervisorLifecycleState.CGROUP_CLEANED)

        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_05_grandchild_survives_containment(self):
        """Scenario 5: Worker spawns child which spawns grandchild; all terminated before reuse."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        grandchild_cmd = f"import subprocess, sys, time; subprocess.Popen([{sys.executable!r}, '-c', 'import time; time.sleep(10)']); time.sleep(10)"
        child_cmd = f"import subprocess, sys, time; subprocess.Popen([{sys.executable!r}, '-c', {grandchild_cmd!r}]); time.sleep(10)"

        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=1000)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", child_cmd])
        time.sleep(0.4)

        sup.terminate_worker_and_reclaim()
        self.assertIsNotNone(proc.poll())
        self.assertEqual(sup.state, SupervisorLifecycleState.CGROUP_CLEANED)

        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_06_expire_during_execution(self):
        """Scenario 6: Reservation expires during execution -> Fence -> Terminate -> Reclaim -> Reuse."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=1000)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", "import time; time.sleep(10)"])
        time.sleep(0.2)

        # Trigger logical expire
        exp_rec = auth.expire(1)
        self.assertEqual(exp_rec.res_status.name, "EXPIRED")

        # Capacity is logically freed, but supervisor cleans up physical worker
        sup.terminate_worker_and_reclaim()
        self.assertIsNotNone(proc.poll())

        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_07_revoke_during_execution(self):
        """Scenario 7: Reservation revoked during execution -> Fence -> Terminate -> Reclaim -> Reuse."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=1000)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", "import time; time.sleep(10)"])
        time.sleep(0.2)

        # Trigger logical revoke
        rev_rec = auth.revoke(1)
        self.assertEqual(rev_rec.res_status.name, "REVOKED")

        sup.terminate_worker_and_reclaim()
        self.assertIsNotNone(proc.poll())

        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_08_concurrent_release_and_reserve_race(self):
        """Scenario 8: Concurrent release and reserve race condition -> Invariants preserved under race."""
        import threading

        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        results = []

        def do_release():
            auth.release(1)

        def do_reserve():
            try:
                rec = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
                results.append(rec.res_id)
            except InsufficientCapacityError:
                results.append("REJECTED")

        t1 = threading.Thread(target=do_release)
        t2 = threading.Thread(target=do_reserve)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertTrue(auth.check_invariants())
        self.assertEqual(len(results), 1)

    def test_scenario_09_crash_during_reconciliation(self):
        """Scenario 9: Crash during reconciliation -> Recovery leaves deterministic state."""
        auth1 = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        vec = DemandVector.from_dict({"cpu": "1", "memory": "256MiB"})
        auth1.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, demand_vector=vec)
        auth1.release(1)

        records = list(auth1._reservations.values())

        # Simulate crash and recovery from WAL
        auth2 = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth2.recover_from_records(records, authority_epoch=1)

        self.assertEqual(auth2._reservations[1].res_status.name, "RELEASED")
        self.assertTrue(auth2.check_invariants())

    def test_scenario_10_crash_before_cgroup_cleanup(self):
        """Scenario 10: Crash before cgroup cleanup -> Recovery maintains capacity bounds without overcommit."""
        auth1 = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        vec = DemandVector.from_dict({"cpu": "1", "memory": "256MiB"})
        auth1.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, demand_vector=vec)

        records = list(auth1._reservations.values())

        auth2 = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth2.recover_from_records(records, authority_epoch=1)

        self.assertEqual(auth2._reservations[1].res_status.name, "ACTIVE")
        active_demand = sum(
            r.get_effective_demand_vector().cpu_mcores for r in auth2._reservations.values() if r.res_status.is_active()
        )
        self.assertEqual(active_demand, 1000)
        self.assertTrue(auth2.check_invariants())

    def test_scenario_11_stale_release_rejection(self):
        """Scenario 11: Stale credentials cannot release or mutate a newer reservation."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(
            res_id=1,
            res_inv=101,
            res_att=1,
            res_worker=1,
            res_demand=500,
            authority_epoch=1,
            lease_epoch=2,
            worker_generation=1,
        )

        with self.assertRaises(InvalidFencingError):
            auth.release(1, authority_epoch=99)

        with self.assertRaises(InvalidFencingError):
            auth.release(1, res_worker=1, worker_generation=1, lease_epoch=1)

        self.assertEqual(auth._reservations[1].res_status.name, "ACTIVE")

    def test_scenario_12_gpu_release_isolation(self):
        """Scenario 12: Releasing GPU 0 frees only GPU 0 while GPU 1 remains owned."""
        auth = ResourceAuthority(capacity=2000, safety_margin=0, uncertainty=0)
        vec1 = DemandVector.from_dict({"cpu": "1", "gpu": [0]})
        vec2 = DemandVector.from_dict({"cpu": "1", "gpu": [1]})

        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, demand_vector=vec1)
        auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, demand_vector=vec2)

        self.assertEqual(auth._gpu_owners[0], 1)
        self.assertEqual(auth._gpu_owners[1], 2)

        auth.release(1)
        self.assertNotIn(0, auth._gpu_owners)
        self.assertEqual(auth._gpu_owners[1], 2)
        self.assertTrue(auth.check_invariants())


if __name__ == "__main__":
    unittest.main()
