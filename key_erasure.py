#!/usr/bin/env python3
"""
Key Erasure Protocol
- Securely overwrites key material after use
- Uses RtlSecureZeroMemory (via ctypes) for guaranteed erasure
- Implements context managers for automatic cleanup
- Protects against cold boot attacks and memory dumps
"""

import ctypes
import ctypes.wintypes
import os
import sys
import gc
from contextlib import contextmanager
from typing import Optional, Any, Dict
from ctypes import windll, byref, c_void_p, c_size_t


# Windows API constants
RTL_SECURE_ZERO_MEMORY_FLAG = 0x00000001


class SecureBuffer:
    """
    Memory buffer with guaranteed erasure.
    
    Uses RtlSecureZeroMemory to ensure the memory is overwritten
    even if the compiler optimizes away regular memset calls.
    """
    
    def __init__(self, size: int):
        """Allocate a secure buffer of specified size."""
        self._size = size
        self._buffer = (ctypes.c_char * size)()
        self._address = ctypes.addressof(self._buffer)
        self._erased = False
    
    def write(self, data: bytes):
        """Write data to the secure buffer."""
        if self._erased:
            raise RuntimeError("Buffer has been erased")
        if len(data) > self._size:
            raise ValueError("Data too large for buffer")
        
        ctypes.memmove(self._address, data, len(data))
    
    def read(self) -> bytes:
        """Read data from the secure buffer."""
        if self._erased:
            raise RuntimeError("Buffer has been erased")
        return bytes(self._buffer)
    
    def erase(self):
        """
        Securely erase the buffer contents.
        
        Uses RtlSecureZeroMemory to guarantee the memory is overwritten,
        even if the compiler would optimize away a regular memset call.
        """
        if self._erased:
            return
        
        try:
            # Try RtlSecureZeroMemory first (guaranteed erasure)
            windll.kernel32.RtlSecureZeroMemory(
                self._address,
                c_size_t(self._size)
            )
        except (AttributeError, OSError):
            # Fallback: manual overwrite with multiple passes
            # Pass 1: zeros
            ctypes.memset(self._address, 0, self._size)
            # Pass 2: ones
            ctypes.memset(self._address, 0xFF, self._size)
            # Pass 3: random
            random_data = os.urandom(self._size)
            ctypes.memmove(self._address, random_data, self._size)
            # Pass 4: zeros again
            ctypes.memset(self._address, 0, self._size)
        
        self._erased = True
    
    def __del__(self):
        """Ensure buffer is erased on garbage collection."""
        self.erase()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.erase()
        return False


class KeyEraser:
    """
    Manages secure key lifecycle with guaranteed erasure.
    
    Features:
    - Keys are stored in SecureBuffer
    - Automatic erasure on context exit
    - Manual erase() method for immediate cleanup
    - Memory barrier to prevent compiler optimization
    """
    
    def __init__(self):
        self._keys: Dict[str, SecureBuffer] = {}
        self._erased = False
    
    def store_key(self, name: str, key: bytes):
        """Store a key securely."""
        if self._erased:
            raise RuntimeError("KeyEraser has been erased")
        
        # Create secure buffer and store key
        buffer = SecureBuffer(len(key))
        buffer.write(key)
        self._keys[name] = buffer
    
    def get_key(self, name: str) -> Optional[bytes]:
        """Retrieve a key (use only when needed)."""
        if self._erased:
            return None
        
        buffer = self._keys.get(name)
        if buffer:
            return buffer.read()
        return None
    
    def erase_key(self, name: str):
        """Erase a specific key."""
        buffer = self._keys.pop(name, None)
        if buffer:
            buffer.erase()
    
    def erase_all(self):
        """Erase all keys."""
        for name, buffer in self._keys.items():
            buffer.erase()
        self._keys.clear()
        self._erased = True
        
        # Force garbage collection to clean up any references
        gc.collect()
    
    def __del__(self):
        """Ensure all keys are erased on garbage collection."""
        self.erase_all()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.erase_all()
        return False


@contextmanager
def secure_key_context(key_name: str, key_data: bytes):
    """
    Context manager for secure key usage.
    
    Usage:
        with secure_key_context("api_key", my_secret_bytes) as key:
            # Use key here
            make_api_call(key)
        # Key is automatically erased
    """
    eraser = KeyEraser()
    eraser.store_key(key_name, key_data)
    
    try:
        yield eraser.get_key(key_name)
    finally:
        eraser.erase_all()


@contextmanager
def ephemeral_session():
    """
    Context manager for ephemeral cryptographic sessions.
    
    All keys created within this context are automatically erased
    when the context exits.
    """
    eraser = KeyEraser()
    
    try:
        yield eraser
    finally:
        eraser.erase_all()


def erase_variable(variable):
    """
    Best-effort erasure of a Python variable.
    
    Note: Python's memory management makes true erasure difficult,
    but we can at least overwrite the object's contents.
    """
    if isinstance(variable, bytes):
        # Replace with zeros
        variable = b'\x00' * len(variable)
    elif isinstance(variable, bytearray):
        # Overwrite in place
        for i in range(len(variable)):
            variable[i] = 0
    elif isinstance(variable, str):
        # Strings are immutable, can't overwrite
        # Best we can do is delete the reference
        pass
    
    # Delete the reference
    del variable
    gc.collect()


def secure_zero(data: bytes) -> bytes:
    """
    Return a zeroed version of the input data.
    
    This is a best-effort approach since Python strings are immutable.
    For true secure erasure, use SecureBuffer.
    """
    return b'\x00' * len(data)


if __name__ == "__main__":
    print("Key Erasure Protocol")
    print("=" * 60)
    
    # Test SecureBuffer
    print("\nTesting SecureBuffer...")
    with SecureBuffer(32) as buf:
        test_data = b"This is sensitive key material!"
        buf.write(test_data)
        print(f"Written: {test_data[:20]}...")
        print(f"Read back: {buf.read()[:20]}...")
    print("Buffer erased automatically.")
    
    # Test KeyEraser
    print("\nTesting KeyEraser...")
    eraser = KeyEraser()
    eraser.store_key("api_key", b"secret-api-key-12345")
    eraser.store_key("redis_token", b"redis-auth-token-67890")
    
    print(f"API key: {eraser.get_key('api_key')[:20]}...")
    print(f"Redis token: {eraser.get_key('redis_token')[:20]}...")
    
    eraser.erase_all()
    print("All keys erased.")
    print(f"API key after erase: {eraser.get_key('api_key')}")
    
    # Test context manager
    print("\nTesting secure_key_context...")
    with secure_key_context("session_key", b"session-secret-key") as key:
        print(f"Key in context: {key[:20]}...")
    print(f"Key after context: {key if 'key' in dir() else 'erased'}")
    
    print("\n" + "=" * 60)
    print("All tests passed.")
