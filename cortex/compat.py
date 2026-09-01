"""
Zero-dependency compatibility helpers for Python 3.10+
"""

from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])

try:
    from typing_extensions import override as override
except ImportError:
    try:
        from typing import override as override  # type: ignore[attr-defined] # pyright: ignore[reportAttributeAccessIssue]
    except ImportError:

        def override(method: F, /) -> F:  # type: ignore[no-redef]
            return method


__all__ = ["override"]
