"""
Linux cgroups v2 Resource Enforcer Implementation (Gate A)

Interacts directly with Linux cgroup v2 filesystem (/sys/fs/cgroup) to enforce CPU, Memory, and Task/PID bounds.
"""

from __future__ import annotations

import logging
import os
import platform
import shutil
import time
from typing import Dict, Set

from cortex.tools.kernel.enforcement.contract import (
    EnforcementContract,
    EnvironmentCapability,
)

logger = logging.getLogger(__name__)

# Explicit Named Constants
DEFAULT_CORTEX_ROOT_CGROUP_DIR: str = "/sys/fs/cgroup/cortex"
DEFAULT_CGROUP_V2_MOUNT: str = "/sys/fs/cgroup"
REQUIRED_CGROUP_CONTROLLERS: Set[str] = {"cpu", "memory", "pids"}
DEFAULT_MAX_REMOVAL_RETRIES: int = 5
REMOVAL_RETRY_BACKOFF_BASE_SEC: float = 0.05
WORKER_DIR_NAME: str = "workers"
GATEWAY_DIR_NAME: str = "gateway"


class CgroupResourceEnforcer:
    """
    Manages cgroup v2 sub-hierarchies and physical resource boundary enforcement.
    """

    def __init__(self, root_cgroup_dir: str = DEFAULT_CORTEX_ROOT_CGROUP_DIR) -> None:
        self.root_cgroup_dir = os.path.abspath(root_cgroup_dir)
        self.workers_dir = os.path.join(self.root_cgroup_dir, WORKER_DIR_NAME)
        self.gateway_dir = os.path.join(self.root_cgroup_dir, GATEWAY_DIR_NAME)

    @staticmethod
    def detect_environment() -> EnvironmentCapability:
        """
        Detects host OS cgroup v2 environment capabilities and permissions.
        """
        if platform.system() != "Linux":
            return EnvironmentCapability.UNSUPPORTED

        cgroup_mount = DEFAULT_CGROUP_V2_MOUNT
        if not os.path.exists(cgroup_mount):
            return EnvironmentCapability.UNSUPPORTED

        # Verify cgroups v2 unified hierarchy
        controllers_file = os.path.join(cgroup_mount, "cgroup.controllers")
        if not os.path.exists(controllers_file):
            return EnvironmentCapability.UNSUPPORTED

        # Check write permissions
        if not os.access(cgroup_mount, os.W_OK):
            return EnvironmentCapability.PERMISSION_DENIED

        try:
            with open(controllers_file, "r") as f:
                available_controllers = set(f.read().strip().split())

            if not REQUIRED_CGROUP_CONTROLLERS.issubset(available_controllers):
                logger.warning(
                    f"cgroups v2 mounted, but missing required controllers. Available: {available_controllers}"
                )
                return EnvironmentCapability.SUPPORTED_UNAVAILABLE

            return EnvironmentCapability.SUPPORTED_AVAILABLE
        except Exception as e:
            logger.error(f"Error checking cgroup v2 environment: {e}")
            return EnvironmentCapability.PERMISSION_DENIED

    def initialize_hierarchy(self) -> bool:
        """
        Initializes top-level Cortex cgroup directories (/cortex/gateway and /cortex/workers).
        """
        capability = self.detect_environment()
        if capability != EnvironmentCapability.SUPPORTED_AVAILABLE:
            return False

        try:
            os.makedirs(self.workers_dir, exist_ok=True)
            os.makedirs(self.gateway_dir, exist_ok=True)

            # Enable child controllers in workers parent group
            subtree_control = os.path.join(self.root_cgroup_dir, "cgroup.subtree_control")
            if os.path.exists(subtree_control):
                try:
                    with open(subtree_control, "w") as f:
                        f.write("+cpu +memory +pids")
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error(f"Failed to initialize cgroup hierarchy at {self.root_cgroup_dir}: {e}")
            return False

    def create_worker_cgroup(self, contract: EnforcementContract) -> str:
        """
        Creates an isolated cgroup directory for a worker and writes CPU, RAM, and PID bounds.
        Returns the absolute cgroup directory path.
        """
        worker_cgroup_path = os.path.join(self.workers_dir, f"worker_{contract.worker_id}")
        os.makedirs(worker_cgroup_path, exist_ok=True)

        # Write CPU limit
        cpu_max_path = os.path.join(worker_cgroup_path, "cpu.max")
        try:
            with open(cpu_max_path, "w") as f:
                f.write(contract.to_cgroup_cpu_max())
        except Exception as e:
            logger.error(f"Failed writing cpu.max to {cpu_max_path}: {e}")
            raise

        # Write Memory limit
        memory_max_path = os.path.join(worker_cgroup_path, "memory.max")
        try:
            with open(memory_max_path, "w") as f:
                f.write(contract.to_cgroup_memory_max())
        except Exception as e:
            logger.error(f"Failed writing memory.max to {memory_max_path}: {e}")
            raise

        # Write PIDs limit
        pids_max_path = os.path.join(worker_cgroup_path, "pids.max")
        try:
            with open(pids_max_path, "w") as f:
                f.write(contract.to_cgroup_pids_max())
        except Exception as e:
            logger.error(f"Failed writing pids.max to {pids_max_path}: {e}")
            raise

        return worker_cgroup_path

    def attach_process(self, worker_cgroup_path: str, pid: int) -> bool:
        """
        Attaches a process PID to the target worker cgroup.
        """
        procs_path = os.path.join(worker_cgroup_path, "cgroup.procs")
        try:
            with open(procs_path, "w") as f:
                f.write(str(pid))
            return True
        except Exception as e:
            logger.error(f"Failed attaching PID {pid} to cgroup {procs_path}: {e}")
            return False

    def verify_process_membership(self, worker_cgroup_path: str, pid: int) -> bool:
        """
        Verifies that a process PID is contained within the expected worker cgroup.
        """
        procs_path = os.path.join(worker_cgroup_path, "cgroup.procs")
        if not os.path.exists(procs_path):
            return False
        try:
            with open(procs_path, "r") as f:
                pids = {int(p.strip()) for p in f.read().split() if p.strip().isdigit()}
            return pid in pids
        except Exception as e:
            logger.error(f"Error reading cgroup.procs at {procs_path}: {e}")
            return False

    def get_cgroup_pids(self, worker_cgroup_path: str) -> Set[int]:
        """
        Returns all process IDs currently belonging to the target cgroup.
        """
        procs_path = os.path.join(worker_cgroup_path, "cgroup.procs")
        if not os.path.exists(procs_path):
            return set()
        try:
            with open(procs_path, "r") as f:
                return {int(p.strip()) for p in f.read().split() if p.strip().isdigit()}
        except Exception:
            return set()

    def get_statistics(self, worker_cgroup_path: str) -> Dict[str, int]:
        """
        Reads real-time execution statistics (CPU usage us, current RAM bytes, current task count).
        """
        stats = {
            "cpu_usage_us": 0,
            "memory_current_bytes": 0,
            "pids_current_count": 0,
        }
        if not os.path.exists(worker_cgroup_path):
            return stats

        # Read CPU stat
        cpu_stat_path = os.path.join(worker_cgroup_path, "cpu.stat")
        if os.path.exists(cpu_stat_path):
            try:
                with open(cpu_stat_path, "r") as f:
                    for line in f:
                        if line.startswith("usage_usec"):
                            parts = line.strip().split()
                            if len(parts) == 2:
                                stats["cpu_usage_us"] = int(parts[1])
            except Exception:
                pass

        # Read Current Memory
        mem_current_path = os.path.join(worker_cgroup_path, "memory.current")
        if os.path.exists(mem_current_path):
            try:
                with open(mem_current_path, "r") as f:
                    val = f.read().strip()
                    if val.isdigit():
                        stats["memory_current_bytes"] = int(val)
            except Exception:
                pass

        # Read Current PIDs
        pids_current_path = os.path.join(worker_cgroup_path, "pids.current")
        if os.path.exists(pids_current_path):
            try:
                with open(pids_current_path, "r") as f:
                    val = f.read().strip()
                    if val.isdigit():
                        stats["pids_current_count"] = int(val)
            except Exception:
                pass

        return stats

    def remove_worker_cgroup(
        self, worker_cgroup_path: str, max_retries: int = DEFAULT_MAX_REMOVAL_RETRIES
    ) -> bool:
        """
        Deletes the worker cgroup directory. Handles Linux kernel async page freeing retries.
        """
        if not os.path.exists(worker_cgroup_path):
            return True

        for attempt in range(max_retries):
            try:
                os.rmdir(worker_cgroup_path)
                return True
            except OSError:
                # Kernel might still be freeing page cache
                time.sleep(REMOVAL_RETRY_BACKOFF_BASE_SEC * (attempt + 1))

        # Final attempt
        try:
            if os.path.exists(worker_cgroup_path):
                shutil.rmtree(worker_cgroup_path, ignore_errors=True)
            return True
        except Exception as e:
            logger.error(f"Failed to remove worker cgroup at {worker_cgroup_path}: {e}")
            return False
