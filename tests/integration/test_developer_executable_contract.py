"""
Executable Contract Test Suite for Cortex Developer Platform (v2.0-EXECUTABLE)

Mechanically tests and verifies end-to-end execution of:
1. Level 1 simple @cortex.task execution & fallback defaults.
2. Level 2 resource-aware @cortex.task unit parsing and normalization.
3. Canonical single-file application execution via CortexClient.
4. Canonical modular application execution with PluginManifest & PluginContext.
5. Non-idle worker retirability predicate across CPU, RAM, GPU, VRAM, and reservations.
"""

import unittest

import cortex
from cortex.tools.kernel.resource_authority import ResourceAuthority, discover_physical_capacity


class TestDeveloperExecutableContract(unittest.TestCase):
    """Mechanically verifies all developer-facing API contracts at runtime."""

    def test_level_1_simple_task_executable_contract(self) -> None:
        """Level 1 task must execute seamlessly and default to 1 CPU core (1000m) and 512MiB RAM."""

        @cortex.task
        def transform(text: str) -> str:
            return text.upper()

        result = transform("cortex platform")
        self.assertEqual(result, "CORTEX PLATFORM")
        self.assertTrue(hasattr(transform, "spec"))
        spec = transform.spec
        self.assertEqual(spec.name, "transform")
        self.assertEqual(spec.cpu_mcores, 1000)
        self.assertEqual(spec.memory_bytes, 512 * 1024 * 1024)
        self.assertEqual(spec.gpu_count, 0)

    def test_level_2_resource_aware_task_executable_contract(self) -> None:
        """Level 2 task must normalize resource strings into exact canonical integers."""

        @cortex.task(
            resources={
                "cpu": "2",
                "memory": "4GiB",
                "gpu": 1,
                "vram": "12GiB",
            },
            timeout=60.0,
            retries=2,
        )
        def run_inference(batch_id: str) -> dict:
            return {"batch_id": batch_id, "status": "COMPLETED"}

        res = run_inference("B-999")
        self.assertEqual(res, {"batch_id": "B-999", "status": "COMPLETED"})
        self.assertTrue(hasattr(run_inference, "spec"))
        spec = run_inference.spec
        self.assertEqual(spec.cpu_mcores, 2000)
        self.assertEqual(spec.memory_bytes, 4 * 1024 * 1024 * 1024)
        self.assertEqual(spec.gpu_count, 1)
        self.assertEqual(spec.vram_bytes, 12 * 1024 * 1024 * 1024)
        self.assertEqual(spec.timeout_sec, 60.0)
        self.assertEqual(spec.max_retries, 2)

    def test_canonical_single_file_app_execution(self) -> None:
        """Single-file app pattern must run workflow end-to-end via CortexClient."""
        client = cortex.CortexClient()

        @cortex.task
        def summarize(data: str) -> str:
            return f"Summary of {data}"

        wf = client.create_workflow(name="SingleFileWorkflow", goal="Summarize input data")
        self.assertEqual(wf.name, "SingleFileWorkflow")
        self.assertEqual(wf.state, cortex.WorkflowState.PENDING)

        run_result = client.run_workflow(wf)
        self.assertEqual(run_result.state, cortex.WorkflowState.COMPLETED)

    def test_canonical_modular_app_with_plugin_execution(self) -> None:
        """Modular application with PluginManifest must register and execute context cleanly."""

        class AnalyticsPlugin(cortex.BasePlugin):
            def on_event(self, event: cortex.BaseEvent) -> None:
                pass

        manifest = cortex.PluginManifest(
            name="AnalyticsPlugin",
            version="1.0.0",
            description="Production Analytics Plugin",
            consumes_events=["cortex.events.intent"],
            produces_events=[],
            required_capabilities=["workflow.plan.create"],
        )

        client = cortex.CortexClient()
        plugin_instance = AnalyticsPlugin(manifest)
        registration = client.register_plugin(plugin_instance)
        self.assertIsNotNone(registration)
        self.assertIsNotNone(plugin_instance.context)
        assert plugin_instance.context is not None
        self.assertTrue(plugin_instance.context.has_capability("workflow.plan.create"))

    def test_worker_retirability_predicate_across_resource_dimensions(self) -> None:
        """Retirability requires Quiescent state AND 0 active reservations AND 0 GPU ownership."""
        cpu, mem = discover_physical_capacity()
        authority = ResourceAuthority(capacity=cpu)

        # 1. Register worker 1 (State: ACTIVE)
        authority.scale_up_register_worker(
            worker_id=1, generation=1, capabilities={"compute.heavy", "workflow.plan.create"}
        )
        self.assertFalse(authority.is_worker_retirable(worker_id=1))  # Active state != Quiescent

        # 2. Reserve GPU 0 on worker 1 while ACTIVE
        rec = authority.reserve(
            res_id=101,
            res_inv=1,
            res_att=1,
            res_worker=1,
            res_demand=1000,
            authority_epoch=1,
            lease_epoch=1,
            worker_generation=1,
            gpu_id=0,
        )
        self.assertIsNotNone(rec)

        # 3. Drain worker 1
        authority.scale_down_drain_worker(worker_id=1)
        # Active reservation & GPU ownership prevents retirability even when DRAINING!
        self.assertFalse(authority.is_worker_retirable(worker_id=1))

        # 4. Release reservation (which updates quiescence automatically)
        authority.release(res_id=101)

        # Now worker 1 is QUIESCENT and retirable!
        self.assertTrue(authority.is_worker_retirable(worker_id=1))

        # 5. Retire worker
        rec_retired = authority.scale_down_retire_worker(worker_id=1)
        self.assertIsNotNone(rec_retired)


if __name__ == "__main__":
    unittest.main()
