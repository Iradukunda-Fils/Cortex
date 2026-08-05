"""
Base Metric Plugin Interface
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from tools.verification.schema import CanonicalState

class BaseMetric(ABC):
    @abstractmethod
    def record_step(self, step: CanonicalState):
        pass

    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        pass
