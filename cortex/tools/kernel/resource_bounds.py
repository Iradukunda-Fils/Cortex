"""
Issue #47 (Phase 6.0): Universal Resource Bound & Action Validator
Normative Architecture Baseline: v1.5.1-FINAL-FROZEN
Specification: Section 5 (Complete Memory Dependency Expansion) & Universal Conservation Law

Universal Resource Conservation Law:
For every state container X in U (workers, assignments, quarantine, WAL buffers, readers, thread stacks, caches):
    Count(X) <= B_X and ByteSize(X) <= S_X and GrowthRate(X, t) <= G_X

When any container reaches or exceeds its bound (Count(X) >= B_X or ByteSize(X) >= S_X),
state transition MUST invoke deterministic, resource-specific admission control from P_action:
    P_action = { REJECT, EVICT, COMPACT, SHED, BACKPRESSURE, QUARANTINE, ROTATE }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ResourceAction(str, Enum):
    """Resource admission control action policy set."""

    REJECT = "REJECT"
    EVICT = "EVICT"
    COMPACT = "COMPACT"
    SHED = "SHED"
    BACKPRESSURE = "BACKPRESSURE"
    QUARANTINE = "QUARANTINE"
    ROTATE = "ROTATE"


class ResourceBoundExceededError(Exception):
    """Raised when a resource container exceeds its Count or Byte bounds under REJECT policy."""

    def __init__(self, resource_name: str, current: int, max_bound: int, bound_type: str, action: ResourceAction) -> None:
        super().__init__(
            f"Resource boundary violation for '{resource_name}': {bound_type} {current} >= max {max_bound}. Action: {action.value}"
        )
        self.resource_name = resource_name
        self.current = current
        self.max_bound = max_bound
        self.bound_type = bound_type
        self.action = action


@dataclass(frozen=True)
class ResourceBoundRule:
    """
    Formal boundary rule for a resource container X.
    """

    resource_name: str
    max_count: int
    max_bytes: int
    action: ResourceAction = ResourceAction.REJECT

    def __post_init__(self) -> None:
        if self.max_count <= 0:
            raise ValueError(f"max_count for '{self.resource_name}' must be > 0, got {self.max_count}")
        if self.max_bytes <= 0:
            raise ValueError(f"max_bytes for '{self.resource_name}' must be > 0, got {self.max_bytes}")


class ResourceBoundValidator:
    """
    Universal Resource Bound & Action Validator.
    Enforces dual Count and ByteSize boundary limits across system state containers.
    """

    def __init__(self) -> None:
        self._rules: Dict[str, ResourceBoundRule] = {}

    def register_rule(self, rule: ResourceBoundRule) -> None:
        """Registers a boundary rule for a named resource container."""
        self._rules[rule.resource_name] = rule

    def get_rule(self, resource_name: str) -> Optional[ResourceBoundRule]:
        """Retrieves a registered rule by resource name."""
        return self._rules.get(resource_name)

    def evaluate(self, resource_name: str, current_count: int, current_bytes: int) -> Tuple[bool, Optional[ResourceAction], Optional[str]]:
        """
        Evaluates whether a container violates Count(X) >= B_X or ByteSize(X) >= S_X.
        Returns: (is_violated, ActionToTake, ReasonDescription)
        """
        rule = self._rules.get(resource_name)
        if not rule:
            return False, None, None

        if current_count >= rule.max_count:
            reason = f"Count {current_count} >= max_count {rule.max_count}"
            logger.warning("Resource bound trigger [%s]: %s. Action: %s", resource_name, reason, rule.action.value)
            return True, rule.action, reason

        if current_bytes >= rule.max_bytes:
            reason = f"ByteSize {current_bytes} >= max_bytes {rule.max_bytes}"
            logger.warning("Resource bound trigger [%s]: %s. Action: %s", resource_name, reason, rule.action.value)
            return True, rule.action, reason

        return False, None, None

    def validate_or_raise(self, resource_name: str, prospective_count: int, prospective_bytes: int) -> None:
        """
        Evaluates boundary limits. If violated and action is REJECT or BACKPRESSURE,
        raises ResourceBoundExceededError.
        """
        violated, action, reason = self.evaluate(resource_name, prospective_count, prospective_bytes)
        if violated and action is not None and action in (ResourceAction.REJECT, ResourceAction.BACKPRESSURE):
            rule = self._rules[resource_name]
            bound_type = "count" if prospective_count >= rule.max_count else "bytes"
            current = prospective_count if bound_type == "count" else prospective_bytes
            max_b = rule.max_count if bound_type == "count" else rule.max_bytes
            raise ResourceBoundExceededError(resource_name, current, max_b, bound_type, action)
