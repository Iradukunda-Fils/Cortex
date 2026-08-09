"""
Zero-dependency compatibility helpers for Python 3.10+
"""

from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])

try:
    from typing import override  # type: ignore[attr-defined]
except ImportError:
    try:
        from typing_extensions import override  # type: ignore[no-redef]
    except ImportError:
        def override(method: F, /) -> F:
            return method


__all__ = ["override"]
