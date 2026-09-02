"""
Cortex Physical Network Isolation Enforcer (Gate B.2)

Provides kernel-enforced network namespace isolation for worker processes using
unshare(CLONE_NEWUSER | CLONE_NEWNET). Enforces Default-Deny Network Egress.

Governance Rule:
    Supervisor Executes; Authority Decides.
    RequiredPhysicalEnforcement AND AttachmentFailure => ExecutionRejected (Fail-Closed).
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from enum import Enum, auto
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# C Library constants for Linux namespaces
CLONE_NEWUSER: int = 0x10000000
CLONE_NEWNET: int = 0x40000000

try:
    _libc: Optional[ctypes.CDLL] = ctypes.CDLL("libc.so.6") if sys.platform.startswith("linux") else None
except Exception:
    _libc = None


class NetworkCapability(Enum):
    """Classification of OS-level network namespace isolation capabilities."""

    SUPPORTED_AVAILABLE = auto()
    SUPPORTED_UNAVAILABLE = auto()
    PERMISSION_DENIED = auto()
    UNSUPPORTED = auto()


class NetworkNamespaceEnforcer:
    """
    Physical Linux Network Namespace Enforcer.
    Isolates worker processes into unprivileged network namespaces with default-deny egress.
    """

    def detect_environment(self) -> NetworkCapability:
        """Detects whether CLONE_NEWUSER | CLONE_NEWNET unshare is supported in the runtime environment."""
        if not sys.platform.startswith("linux") or _libc is None:
            return NetworkCapability.UNSUPPORTED

        pid = os.fork()
        if pid == 0:
            try:
                res = _libc.unshare(CLONE_NEWUSER | CLONE_NEWNET)
                if res == 0:
                    os._exit(0)
                else:
                    err = ctypes.get_errno()
                    os._exit(13 if err == 1 else 1)  # 13 = EPERM
            except Exception:
                os._exit(1)
        else:
            _, status = os.waitpid(pid, 0)
            exit_code = os.waitstatus_to_exitcode(status)
            if exit_code == 0:
                return NetworkCapability.SUPPORTED_AVAILABLE
            elif exit_code == 13:
                return NetworkCapability.PERMISSION_DENIED
            else:
                return NetworkCapability.SUPPORTED_UNAVAILABLE

    def get_netns_inode(self, pid: int = 0) -> Optional[int]:
        """Returns the stat inode number of /proc/<pid>/ns/net."""
        pid_str = "self" if pid == 0 else str(pid)
        netns_path = f"/proc/{pid_str}/ns/net"
        try:
            st = os.stat(netns_path)
            return st.st_ino
        except Exception as e:
            logger.debug(f"Failed stating {netns_path}: {e}")
            return None

    def verify_isolation(self, child_pid: int, host_pid: int = 0) -> bool:
        """
        Verifies that child_pid resides in a distinct network namespace from host_pid.
        """
        child_inode = self.get_netns_inode(child_pid)
        host_inode = self.get_netns_inode(host_pid)

        if child_inode is None or host_inode is None:
            return False

        return child_inode != host_inode

    @staticmethod
    def unshare_netns_preexec() -> None:
        """
        Target function to be run inside preexec_fn for child processes.
        Unshares user and network namespaces before process execution starts.
        """
        if _libc is not None:
            res = _libc.unshare(CLONE_NEWUSER | CLONE_NEWNET)
            if res != 0:
                err = ctypes.get_errno()
                raise OSError(err, f"unshare(CLONE_NEWUSER | CLONE_NEWNET) failed with errno {err}")

    def get_preexec_fn(self) -> Callable[[], None]:
        """Returns the preexec function for process launch."""
        return self.unshare_netns_preexec
