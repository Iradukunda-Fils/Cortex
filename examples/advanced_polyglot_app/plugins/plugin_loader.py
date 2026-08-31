"""
Centralized Lightweight Plugin FFI Loader for Cortex Polyglot Engine.

Eliminates runtime compilation overhead on low-resource systems by loading
pre-built native binaries with zero-overhead Python fallbacks when binaries are missing.
"""

import ctypes
import math
import os
from typing import Any, Dict, List


class CentralPluginLoader:
    """Centralized loader for native C, C++, and Rust plugins."""

    _handles: Dict[str, Any] = {}

    @classmethod
    def load_c_math(cls, vec_a: List[float], vec_b: List[float]) -> float:
        """Low-resource C dot product handle."""
        dir_path = os.path.dirname(os.path.abspath(__file__))
        so_path = os.path.join(dir_path, "c_fast_math", "fast_math.so")

        if "c_fast_math" not in cls._handles and os.path.exists(so_path):
            try:
                lib = ctypes.CDLL(so_path)
                lib.c_dot_product.argtypes = [
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.c_size_t,
                ]
                lib.c_dot_product.restype = ctypes.c_double
                cls._handles["c_fast_math"] = lib
            except Exception:
                cls._handles["c_fast_math"] = None

        lib = cls._handles.get("c_fast_math")
        if lib and len(vec_a) == len(vec_b):
            n = len(vec_a)
            arr_a = (ctypes.c_double * n)(*vec_a)
            arr_b = (ctypes.c_double * n)(*vec_b)
            return float(lib.c_dot_product(arr_a, arr_b, n))

        # Lightweight zero-overhead fallback
        return sum(a * b for a, b in zip(vec_a, vec_b))

    @classmethod
    def load_cpp_rms(cls, values: List[float]) -> float:
        """Low-resource C++ SIMD RMS handle."""
        dir_path = os.path.dirname(os.path.abspath(__file__))
        so_path = os.path.join(dir_path, "cpp_tensor_engine", "tensor_engine.so")

        if "cpp_tensor_engine" not in cls._handles and os.path.exists(so_path):
            try:
                lib = ctypes.CDLL(so_path)
                lib.cpp_simd_rms.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_size_t]
                lib.cpp_simd_rms.restype = ctypes.c_double
                cls._handles["cpp_tensor_engine"] = lib
            except Exception:
                cls._handles["cpp_tensor_engine"] = None

        lib = cls._handles.get("cpp_tensor_engine")
        if lib and values:
            n = len(values)
            arr = (ctypes.c_double * n)(*values)
            return float(lib.cpp_simd_rms(arr, n))

        if not values:
            return 0.0
        return math.sqrt(sum(x * x for x in values) / len(values))

    @classmethod
    def load_rust_checksum(cls, text: str) -> int:
        """Low-resource Rust FNV-1a checksum handle."""
        dir_path = os.path.dirname(os.path.abspath(__file__))
        so_path = os.path.join(dir_path, "rust_secure_checksum", "librust_checksum.so")

        if "rust_secure_checksum" not in cls._handles and os.path.exists(so_path):
            try:
                lib = ctypes.CDLL(so_path)
                lib.rust_fnv1a_hash.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
                lib.rust_fnv1a_hash.restype = ctypes.c_uint64
                cls._handles["rust_secure_checksum"] = lib
            except Exception:
                cls._handles["rust_secure_checksum"] = None

        lib = cls._handles.get("rust_secure_checksum")
        raw_bytes = text.encode("utf-8")
        if lib and raw_bytes:
            n = len(raw_bytes)
            arr = (ctypes.c_uint8 * n)(*raw_bytes)
            return int(lib.rust_fnv1a_hash(arr, n))

        # Lightweight Python fallback
        hash_val = 0xCBF29CE484222325
        for b in raw_bytes:
            hash_val ^= b
            hash_val = (hash_val * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        return hash_val
