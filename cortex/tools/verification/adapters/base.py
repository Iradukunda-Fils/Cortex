"""
Abstract Base Adapter for Target Output Normalization
"""

from abc import ABC, abstractmethod
from typing import Any

from cortex.tools.verification.schema import CanonicalState


class BaseAdapter(ABC):
    @abstractmethod
    def parse_trace(self, trace_input: Any) -> list[CanonicalState]:
        """Converts raw engine trace into list of CanonicalState objects."""
