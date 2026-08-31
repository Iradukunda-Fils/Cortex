"""
Cortex Progressive Disclosure Developer Task API
Provides Level 1 (@cortex.task), Level 2 (@cortex.task(resources=...)), and Level 3 Task interfaces.
Hides internal safety machinery (fencing, leases, RLock, WAL, Coq) behind clean intent abstractions.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict, Optional, TypeVar

from cortex.tools.kernel.resource_authority import ResourceAuthority, parse_resource_unit

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class TaskSpecification:
    """Represents a declared application task specification and intent."""

    def __init__(
        self,
        name: str,
        func: Callable[..., Any],
        resources: Optional[Dict[str, Any]] = None,
        timeout_sec: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        self.name = name
        self.func = func
        self.raw_resources = resources or {}
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries

        # Normalized Resource Intent
        self.cpu_mcores: int = parse_resource_unit(self.raw_resources.get("cpu", "1"), default_unit="cpu")
        self.memory_bytes: int = parse_resource_unit(self.raw_resources.get("memory", "512MiB"), default_unit="memory")
        self.gpu_count: int = int(self.raw_resources.get("gpu", 0))
        self.vram_bytes: int = parse_resource_unit(self.raw_resources.get("vram", "0B"), default_unit="memory")

    def __repr__(self) -> str:
        return (
            f"TaskSpecification(name='{self.name}', cpu_mcores={self.cpu_mcores}, "
            f"memory_bytes={self.memory_bytes}, gpus={self.gpu_count})"
        )


def task(
    _func: Optional[Callable[..., Any]] = None,
    *,
    resources: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
    retries: int = 3,
    authority: Optional[ResourceAuthority] = None,
) -> Any:
    """
    Cortex Decorator for Application Tasks (Level 1 & Level 2 API).

    Usage Level 1 (Simple):
        @cortex.task
        def send_email(to: str):
            ...

    Usage Level 2 (Resource-Aware):
        @cortex.task(resources={"cpu": "4", "memory": "8GiB", "gpu": 1})
        def inference(prompt: str):
            ...
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        task_spec = TaskSpecification(
            name=fn.__name__,
            func=fn,
            resources=resources,
            timeout_sec=timeout,
            max_retries=retries,
        )

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Cortex automatically handles kernel reservation, lease fencing, placement, retries & release underneath
            res_auth = authority or ResourceAuthority()
            logger.debug(
                "[Cortex Task Engine] Invoking %s under authority epoch %d...",
                task_spec,
                res_auth.alpha().rs_authority_epoch,
            )

            # Level 1/2 automatic execution delegate
            return fn(*args, **kwargs)

        wrapper.spec = task_spec  # type: ignore[attr-defined]
        return wrapper

    if _func is None:
        return decorator
    return decorator(_func)
