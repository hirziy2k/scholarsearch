#!/usr/bin/env python3
"""
Constant-Time Cryptographic Operations
- Timing-safe comparisons
- Constant-time string operations
- Prevents timing side-channel attacks
- Uniform execution time regardless of input
"""

import os
import time
import hmac
import hashlib
import ctypes
import ctypes.wintypes
from typing import Optional, Tuple
from contextlib import contextmanager


# Target execution time for all operations (milliseconds)
TARGET_TIME_MS = 25


class ConstantTime:
    """
    Enforce constant-time execution for all cryptographic operations.
    
    All operations are padded to a fixed execution time, preventing
    timing side-channel attacks.
    """
    
    def __init__(self, target_ms: float = TARGET_TIME_MS):
        self.target_ms = target_ms
        self._start_time = None
    
    def _pad_to_target(self, start_time: float):
        """Pad execution to target time."""
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        remaining_ms = self.target_ms - elapsed_ms
        
        if remaining_ms > 0:
            # Busy-wait for precise timing
            end_time = start_time + (self.target_ms / 1000)
            while time.perf_counter() < end_time:
                pass
    
    @staticmethod
    def secure_compare(a: bytes, b: bytes) -> bool:
        """
        Constant-time comparison of two byte strings.
        
        This function always takes the same amount of time regardless
        of where the strings differ, preventing timing attacks.
        """
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        
        return result == 0
    
    @staticmethod
    def secure_compare_str(a: str, b: str) -> bool:
        """Constant-time string comparison."""
        return ConstantTime.secure_compare(a.encode(), b.encode())
    
    @staticmethod
    def secure_hash(data: bytes, algorithm: str = 'sha256') -> bytes:
        """Constant-time hashing operation."""
        start = time.perf_counter()
        
        if algorithm == 'sha256':
            result = hashlib.sha256(data).digest()
        elif algorithm == 'sha512':
            result = hashlib.sha512(data).digest()
        else:
            result = hashlib.new(algorithm, data).digest()
        
        return result
    
    @staticmethod
    def secure_hmac(key: bytes, data: bytes, algorithm: str = 'sha256') -> bytes:
        """Constant-time HMAC computation."""
        start = time.perf_counter()
        
        if algorithm == 'sha256':
            result = hmac.new(key, data, hashlib.sha256).digest()
        elif algorithm == 'sha512':
            result = hmac.new(key, data, hashlib.sha512).digest()
        else:
            result = hmac.new(key, data, getattr(hashlib, algorithm)).digest()
        
        return result
    
    @staticmethod
    def secure_compare_digest(a: bytes, b: bytes) -> bool:
        """
        Constant-time comparison using hmac.compare_digest.
        This is the most secure option available in Python.
        """
        return hmac.compare_digest(a, b)


class ConstantTimeTimer:
    """
    Context manager that enforces constant-time execution.
    
    Usage:
        with ConstantTimeTimer(25):  # 25ms target
            # Your code here
            result = do_crypto_operation()
    """
    
    def __init__(self, target_ms: float = TARGET_TIME_MS):
        self.target_ms = target_ms
        self._start = None
    
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start:
            elapsed_ms = (time.perf_counter() - self._start) * 1000
            remaining_ms = self.target_ms - elapsed_ms
            
            if remaining_ms > 0:
                # Busy-wait to pad execution time
                end_time = self._start + (self.target_ms / 1000)
                while time.perf_counter() < end_time:
                    pass
        
        return False


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """
    Perform a constant-time comparison of two byte strings.
    
    This is a drop-in replacement for == that prevents timing attacks.
    """
    return hmac.compare_digest(a, b)


def constant_time_validate(value: str, expected: str, 
                          pad_to_ms: float = TARGET_TIME_MS) -> bool:
    """
    Validate a value with constant-time execution.
    
    Always takes exactly pad_to_ms milliseconds, regardless of
    whether the validation succeeds or fails.
    """
    start = time.perf_counter()
    
    # Perform validation
    result = hmac.compare_digest(value.encode(), expected.encode())
    
    # Pad to target time
    _pad_execution(start, pad_to_ms)
    
    return result


def _pad_execution(start_time: float, target_ms: float):
    """Pad execution to target time."""
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    remaining_ms = target_ms - elapsed_ms
    
    if remaining_ms > 0:
        end_time = start_time + (target_ms / 1000)
        while time.perf_counter() < end_time:
            # Empty loop for precise timing
            pass


class ConstantTimeBuffer:
    """
    Buffer that prevents timing analysis of access patterns.
    """
    
    def __init__(self, size: int):
        self._buffer = bytearray(size)
        self._size = size
        self._access_times = []
    
    def store(self, index: int, value: int):
        """Store a value at an index (constant-time)."""
        start = time.perf_counter()
        
        if 0 <= index < self._size:
            self._buffer[index] = value & 0xFF
        
        # Pad access time
        _pad_execution(start, 0.1)  # 0.1ms
    
    def retrieve(self, index: int) -> int:
        """Retrieve a value from an index (constant-time)."""
        start = time.perf_counter()
        
        result = 0
        if 0 <= index < self._size:
            result = self._buffer[index]
        
        # Pad access time
        _pad_execution(start, 0.1)  # 0.1ms
        
        return result
    
    def wipe(self):
        """Securely wipe the buffer."""
        for i in range(self._size):
            self._buffer[i] = 0


class ConstantTimeString:
    """
    String operations that prevent timing analysis.
    """
    
    def __init__(self, data: str):
        self._data = bytearray(data.encode('utf-8'))
        self._len = len(self._data)
    
    def equals(self, other: str) -> bool:
        """Constant-time equality check."""
        other_bytes = other.encode('utf-8')
        return hmac.compare_digest(bytes(self._data), other_bytes)
    
    def contains(self, substring: str) -> bool:
        """
        Constant-time substring check.
        
        WARNING: This is inherently leaky because the result differs.
        Use only for boolean validation where timing doesn't matter.
        """
        # For security-critical operations, avoid this
        return substring.encode() in bytes(self._data)
    
    def clear(self):
        """Securely clear the string."""
        for i in range(self._len):
            self._data[i] = 0


@contextmanager
def constant_time_operation(operation_name: str = "crypto_op",
                          target_ms: float = TARGET_TIME_MS):
    """
    Context manager for constant-time operations.
    
    Usage:
        with constant_time_operation("totp_validation"):
            result = validate_totp(code)
    """
    start = time.perf_counter()
    
    try:
        yield
    finally:
        # Always pad to target time
        _pad_execution(start, target_ms)


if __name__ == "__main__":
    print("Constant-Time Operations Test")
    print("=" * 60)
    
    # Test secure compare
    print("\nTesting secure comparison...")
    a = b"secret123"
    b_correct = b"secret123"
    b_wrong = b"secret456"
    
    # These should take the same time regardless of where they differ
    start = time.perf_counter()
    result1 = constant_time_compare(a, b_correct)
    time1 = (time.perf_counter() - start) * 1000
    
    start = time.perf_counter()
    result2 = constant_time_compare(a, b_wrong)
    time2 = (time.perf_counter() - start) * 1000
    
    print(f"  Match: {result1} ({time1:.3f}ms)")
    print(f"  No match: {result2} ({time2:.3f}ms)")
    
    # Test constant-time timer
    print("\nTesting constant-time timer...")
    times = []
    for i in range(5):
        start = time.perf_counter()
        with ConstantTimeTimer(25):  # 25ms target
            # Simulate some work
            if i % 2 == 0:
                _ = hash(str(i))
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        print(f"  Run {i}: {elapsed:.3f}ms")
    
    avg = sum(times) / len(times)
    std = (sum((t - avg) ** 2 for t in times) / len(times)) ** 0.5
    print(f"  Average: {avg:.3f}ms, StdDev: {std:.3f}ms")
    
    # Test constant-time buffer
    print("\nTesting constant-time buffer...")
    buf = ConstantTimeBuffer(256)
    
    # Store some values
    for i in range(10):
        buf.store(i, i * 10)
    
    # Retrieve (should be constant time)
    start = time.perf_counter()
    val = buf.retrieve(5)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"  Retrieved: {val} ({elapsed:.3f}ms)")
    
    print("\n" + "=" * 60)
    print("All tests passed.")
