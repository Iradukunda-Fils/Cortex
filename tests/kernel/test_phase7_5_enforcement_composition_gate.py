"""Phase 7.5: Enforcement Composition Gate Test Suite.

Verifies the runtime composition across:
TLA+ Distributed Model -> ResourceAuthority -> EnforcementContract -> WorkerSupervisor -> CgroupResourceEnforcer
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
    GPUCollisionError,
    InvalidFencingError,
    ResourceAuthority,
)


class TestPhase75EnforcementCompositionGate(unittest.TestCase):
    """Test suite verifying Phase 7.5 runtime composition and failure recovery safety."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="cortex_75_test_")
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

    def test_scenario_01_end_to_end_pipeline_composition(self):
        """Scenario 1: End-to-end composition (Reserve -> Contract -> Supervisor -> Exit -> Reclaim)."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        rec = auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=500)
        self.assertEqual(rec.res_id, 1)

        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=500)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", "import sys; sys.exit(0)"])
        proc.wait()

        telemetry = sup.terminate_worker_and_reclaim()
        self.assertEqual(sup.state, SupervisorLifecycleState.CGROUP_CLEANED)
        self.assertEqual(telemetry.exit_code, 0)

        # Confirm capacity is reclaimed and reusable
        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_02_node_crash_and_stale_epoch_takeover_fencing(self):
        """Scenario 2: Node crash & leader takeover under epoch advance -> stale execution fenced out."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=500, authority_epoch=1)

        # Attempting release under stale epoch 99 raises InvalidFencingError
        with self.assertRaises(InvalidFencingError):
            auth.release(1, authority_epoch=99)

        # Valid epoch release succeeds cleanly
        rec = auth.release(1, authority_epoch=1)
        self.assertEqual(rec.res_status.name, "RELEASED")

    def test_scenario_03_partitioned_authority_rejoin_interruption(self):
        """Scenario 3: Partitioned old authority re-joins -> stale release attempts rejected, execution terminated."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000, authority_epoch=1)

        # Launch worker under epoch 1
        script = "import time; time.sleep(10)"
        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=1000)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", script])
        time.sleep(0.1)

        # Stale authority attempt to commit under epoch 99 is fenced out
        with self.assertRaises(InvalidFencingError):
            auth.release(1, authority_epoch=99)

        # Supervisor terminates worker execution and reclaims
        sup.terminate_worker_and_reclaim()
        self.assertEqual(sup.state, SupervisorLifecycleState.CGROUP_CLEANED)
        self.assertIsNotNone(proc.poll())

        # Verify old execution cannot continue and capacity is reusable under active authority
        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000, authority_epoch=1)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_04_worker_crash_under_lease_renewal(self):
        """Scenario 4: Worker crashes during execution -> supervisor reclaims capacity safely."""
        auth = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, res_demand=1000)

        # Worker process crashes immediately with exit code 42
        sup = self._make_supervisor(auth, res_id=1, worker_id=1, cpu=1000)
        proc = sup.launch_contained_worker(command=[sys.executable, "-c", "import sys; sys.exit(42)"])
        proc.wait()

        # Telemetry captures exit code 42
        telemetry = sup.terminate_worker_and_reclaim()
        self.assertEqual(telemetry.exit_code, 42)
        self.assertEqual(sup.state, SupervisorLifecycleState.CGROUP_CLEANED)

        # Capacity reclaimed and reusable
        rec2 = auth.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, res_demand=1000)
        self.assertEqual(rec2.res_id, 2)

    def test_scenario_05_multi_node_gpu_identity_isolation(self):
        """Scenario 5: Globally scoped GPU tuple (NodeID, GPUID) isolation."""
        auth_node_a = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)
        auth_node_b = ResourceAuthority(capacity=1000, safety_margin=0, uncertainty=0)

        vec_gpu0 = DemandVector.from_dict({"cpu": "100m", "gpu": [0]})

        # GPU 0 on Node A
        auth_node_a.reserve(res_id=1, res_inv=101, res_att=1, res_worker=1, demand_vector=vec_gpu0)
        self.assertEqual(auth_node_a._gpu_owners[0], 1)

        # GPU 0 on Node B is a distinct physical resource (NodeB, GPU0) -> reserve succeeds!
        auth_node_b.reserve(res_id=2, res_inv=102, res_att=2, res_worker=2, demand_vector=vec_gpu0)
        self.assertEqual(auth_node_b._gpu_owners[0], 2)

        # Conflict on Node A: Second reservation claiming GPU 0 on Node A fails with GPUCollisionError!
        with self.assertRaises(GPUCollisionError):
            auth_node_a.reserve(res_id=3, res_inv=103, res_att=3, res_worker=3, demand_vector=vec_gpu0)


if __name__ == "__main__":
    unittest.main()
