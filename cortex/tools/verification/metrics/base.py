"""
Base Metric Plugin Interface
"""

from abc import ABC, abstractmethod
from typing import Any

from cortex.tools.verification.schema import CanonicalState


class BaseMetric(ABC):
    @abstractmethod
    def record_step(self, step: CanonicalState):
        pass

    @abstractmethod
    def get_summary(self) -> dict[str, Any]:
        pass
