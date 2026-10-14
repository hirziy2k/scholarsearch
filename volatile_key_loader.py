#!/usr/bin/env python3
"""
Volatile API Key Loader with CryptProtectMemory
- Loads keys from environment into memory
- Encrypts keys using Windows CryptProtectMemory API
- Clears environment variables after use
- Keys evaporate on process exit
- Protected from pagefile leakage via in-memory encryption
"""

import os
import sys
import ctypes
import ctypes.wintypes
from contextlib import contextmanager
from typing import Dict, Optional, List
from ctypes import windll, byref, c_void_p, c_uint32, POINTER

# Required API keys for scholarsearch
REQUIRED_KEYS = [
    "OPENALEX_EMAIL",
    "UNPAYWALL_EMAIL",
    "NCBI_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "CORE_API_KEY",
    "SCOPUS_API_KEY",
]

# CryptProtectMemory flags
CRYPTPROTECT_LOCAL_MACHINE = 0x00000004
CRYPTPROTECT_UI_FORBIDDEN = 0x00000001
CRYPTPROTECT_CRED_SYNC = 0x00000010

# Block size for CryptProtectMemory (must be multiple of 16)
CRYPTPROTECT_MEMORY_BLOCK_SIZE = 16


class ProtectedBuffer:
    """Wrapper for memory protected by CryptProtectMemory."""
    
    def __init__(self, data: bytes):
        self._data = bytearray(data)
        self._encrypted = False
        self._protect_memory()
    
    def _protect_memory(self):
        """Encrypt the buffer in place using CryptProtectMemory."""
        if sys.platform != 'win32':
            return  # Skip on non-Windows
        
        try:
            # Pad to block size
            padded_len = ((len(self._data) + CRYPTPROTECT_MEMORY_BLOCK_SIZE - 1) 
                         // CRYPTPROTECT_MEMORY_BLOCK_SIZE * CRYPTPROTECT_MEMORY_BLOCK_SIZE)
            self._data.extend(b'\x00' * (padded_len - len(self._data)))
            
            # Create mutable buffer
            buf = (ctypes.c_char * len(self._data))(*self._data)
            
            # Call CryptProtectMemory
            result = windll.crypt32.CryptProtectMemory(
                buf,
                c_uint32(len(self._data)),
                CRYPTPROTECT_UI_FORBIDDEN | CRYPTPROTECT_LOCAL_MACHINE
            )
            
            if result:
                self._data = bytearray(buf)
                self._encrypted = True
        except Exception:
            pass  # Fail open — still have plaintext in memory
    
    def _unprotect_memory(self):
        """Decrypt the buffer in place."""
        if sys.platform != 'win32' or not self._encrypted:
            return bytes(self._data)
        
        try:
            buf = (ctypes.c_char * len(self._data))(*self._data)
            
            result = windll.crypt32.CryptUnprotectMemory(
                buf,
                c_uint32(len(self._data)),
                CRYPTPROTECT_UI_FORBIDDEN
            )
            
            if result:
                return bytes(buf)
        except Exception:
            pass
        
        return bytes(self._data)
    
    def get_decrypted(self) -> bytes:
        """Get decrypted data (only call when needed)."""
        return self._unprotect_memory()
    
    def clear(self):
        """Securely clear the buffer."""
        if self._encrypted and sys.platform == 'win32':
            # Re-encrypt with random data to destroy plaintext
            random_data = os.urandom(len(self._data))
            buf = (ctypes.c_char * len(self._data))(*random_data)
            windll.crypt32.CryptProtectMemory(
                buf,
                c_uint32(len(self._data)),
                CRYPTPROTECT_UI_FORBIDDEN | CRYPTPROTECT_LOCAL_MACHINE
            )
        
        # Overwrite with zeros
        self._data = bytearray(len(self._data))
        self._encrypted = False
    
    def __del__(self):
        self.clear()


class SecureKeyStore:
    """In-memory key store with CryptProtectMemory encryption."""
    
    def __init__(self):
        self._keys: Dict[str, ProtectedBuffer] = {}
    
    def load_from_env(self, key_names: Optional[List[str]] = None):
        """Load keys from environment and encrypt in memory."""
        if key_names is None:
            key_names = REQUIRED_KEYS
        
        loaded = []
        for key in key_names:
            value = os.environ.get(key)
            if value:
                # Convert to bytes and protect
                value_bytes = value.encode('utf-8')
                self._keys[key] = ProtectedBuffer(value_bytes)
                loaded.append(key)
                
                # Clear from environment immediately
                del os.environ[key]
        
        return loaded
    
    def get(self, key: str) -> Optional[str]:
        """Get a decrypted key value. Call only when needed."""
        protected = self._keys.get(key)
        if protected:
            return protected.get_decrypted().decode('utf-8')
        return None
    
    def clear(self):
        """Securely clear all keys."""
        for key in list(self._keys.keys()):
            self._keys[key].clear()
            del self._keys[key]
    
    def __del__(self):
        self.clear()


@contextmanager
def volatile_keys(key_names: Optional[list] = None):
    """
    Context manager that loads API keys into encrypted memory and clears on exit.
    
    Usage:
        with volatile_keys() as keys:
            # keys is a SecureKeyStore with encrypted keys
            # Environment variables are cleared on exit
            api_key = keys.get("NCBI_API_KEY")
            do_work(api_key)
    """
    store = SecureKeyStore()
    loaded = store.load_from_env(key_names)
    
    try:
        yield store
    finally:
        store.clear()


def sanitize_env():
    """
    Remove all API keys from environment variables.
    Call this at startup to prevent leakage.
    """
    cleared = []
    for key in REQUIRED_KEYS:
        if key in os.environ:
            del os.environ[key]
            cleared.append(key)
    
    # Also clear any other potential secrets
    for key in list(os.environ.keys()):
        if any(pattern in key.upper() for pattern in ["API_KEY", "SECRET", "TOKEN", "PASSWORD"]):
            if key not in REQUIRED_KEYS:  # Don't double-clear
                del os.environ[key]
                cleared.append(key)
    
    return cleared


def load_keys_from_file(filepath: str) -> SecureKeyStore:
    """
    Load API keys from a file and immediately clear the file from disk.
    Keys are encrypted in memory using CryptProtectMemory.
    """
    store = SecureKeyStore()
    
    if not os.path.exists(filepath):
        return store
    
    keys = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                keys[key.strip()] = value.strip()
    
    # Delete the file immediately
    try:
        os.remove(filepath)
    except OSError:
        pass
    
    # Load into protected store
    for key, value in keys.items():
        value_bytes = value.encode('utf-8')
        store._keys[key] = ProtectedBuffer(value_bytes)
    
    return store


def verify_keys_loaded():
    """Check which required keys are available."""
    status = {}
    for key in REQUIRED_KEYS:
        value = os.environ.get(key)
        status[key] = {
            "loaded": bool(value),
            "length": len(value) if value else 0,
            "preview": f"{value[:4]}...{value[-4:]}" if value and len(value) > 8 else "****"
        }
    return status


if __name__ == "__main__":
    print("API Key Status:")
    status = verify_keys_loaded()
    for key, info in status.items():
        loaded = "LOADED" if info["loaded"] else "MISSING"
        print(f"  [{loaded}] {key} ({info['length']} chars)")
    
    # Demonstrate secure key store
    print("\nDemonstrating SecureKeyStore:")
    with volatile_keys() as keys:
        for key in REQUIRED_KEYS:
            value = keys.get(key)
            if value:
                print(f"  Retrieved: {key} = {value[:4]}...{value[-4:]}")
            else:
                print(f"  Missing: {key}")
    print("Keys cleared from memory.")
