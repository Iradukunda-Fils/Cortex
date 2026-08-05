"""
Abstract Base Adapter for Target Output Normalization
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from tools.verification.schema import CanonicalState

class BaseAdapter(ABC):
    @abstractmethod
    def parse_trace(self, trace_input: Any) -> List[CanonicalState]:
        """Converts raw engine trace into list of CanonicalState objects."""
        pass
