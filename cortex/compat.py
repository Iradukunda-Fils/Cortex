"""
Zero-dependency compatibility helpers for Python 3.10+
"""

import sys
from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable[..., object])

if sys.version_info >= (3, 12):
    from typing import override as override
else:
    try:
        from typing_extensions import override as override  # type: ignore[no-redef]
    except ImportError:
        def override(method: F, /) -> F:  # type: ignore[no-redef]
            return method


__all__ = ["override"]

