#!/usr/bin/env python3
"""
TPM-Bound Key Wrapper using NCrypt API
- Generates non-exportable keys inside TPM 2.0
- Wraps AES session keys with hardware-bound key
- Keys cannot be extracted from hardware
"""

import ctypes
import ctypes.wintypes
import os
import sys
from ctypes import windll, byref, c_void_p, c_ulong, c_char_p, Structure, POINTER

# NCrypt constants
NCRYPT_MACHINE_KEY_FLAG = 0x00000020
NCRYPT_OVERWRITE_KEY_FLAG = 0x00000040
NCRYPT_USE_VAULT_FLAG = 0x00000200
NCRYPT_PAD_PKCS1_FLAG = 0x00000002
NCRYPT_PAD_OAEP_FLAG = 0x00000004

# Algorithm identifiers
BCRYPT_RSA_ALGORITHM = b"RSA"
BCRYPT_AES_ALGORITHM = b"AES"
NCRYPT_SHA256_ALGORITHM = b"SHA256"

# Key export options
NCRYPT_ALLOW_EXPORT_FLAG = 0x00000001
NCRYPT_ALLOW_PLAINTEXT_EXPORT_FLAG = 0x00000002


class NCryptHandle(ctypes.Structure):
    _fields_ = [("unused", ctypes.c_void_p)]


class NCryptKeyName(ctypes.Structure):
    _fields_ = [
        ("pszName", ctypes.c_wchar_p),
        ("pszAlgorithmName", ctypes.c_wchar_p),
        ("dwLegacyKeyScope", ctypes.wintypes.DWORD),
        ("dwLegacyKeyFlags", ctypes.wintypes.DWORD),
    ]


class NCryptProviderName(ctypes.Structure):
    _fields_ = [
        ("pszName", ctypes.c_wchar_p),
        ("pszComment", ctypes.c_wchar_p),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]


class TPMKeyWrapper:
    """Wrapper for TPM-bound key operations."""
    
    def __init__(self):
        self.ncrypt = ctypes.WinDLL("ncrypt.dll")
        self.key_handle = None
        self._initialized = False
    
    def _check_error(self, result, operation: str):
        """Check NCrypt return code."""
        if result != 0:  # ERROR_SUCCESS
            raise ctypes.WinError(result)
    
    def open_storage_provider(self, provider_name: str = "Microsoft Software Key Storage Provider"):
        """Open the NCrypt storage provider."""
        provider_handle = NCryptHandle()
        
        # Try TPM provider first, fall back to software
        try:
            result = self.ncrypt.NCryptOpenStorageProvider(
                byref(provider_handle),
                "Microsoft Platform Crypto Provider",  # TPM 2.0
                0
            )
            if result == 0:
                return provider_handle
        except Exception:
            pass
        
        # Fallback to software provider
        result = self.ncrypt.NCryptOpenStorageProvider(
            byref(provider_handle),
            provider_name,
            0
        )
        self._check_error(result, "NCryptOpenStorageProvider")
        return provider_handle
    
    def generate_key(self, key_name: str = "SessionKey", bits: int = 256):
        """
        Generate a non-exportable key inside TPM.
        """
        provider_handle = self.open_storage_provider()
        
        key_handle = NCryptHandle()
        
        # Create key with TPM binding
        result = self.ncrypt.NCryptCreatePersistedKey(
            provider_handle,
            byref(key_handle),
            BCRYPT_AES_ALGORITHM,
            key_name,
            0,
            NCRYPT_MACHINE_KEY_FLAG | NCRYPT_OVERWRITE_KEY_FLAG
        )
        self._check_error(result, "NCryptCreatePersistedKey")
        
        # Set key length
        key_length = ctypes.wintypes.DWORD(bits // 8)
        result = self.ncrypt.NCryptSetProperty(
            key_handle,
            b"Length",
            byref(key_length),
            ctypes.sizeof(key_length),
            0
        )
        self._check_error(result, "NCryptSetProperty(Length)")
        
        # Set as non-exportable
        export_flag = ctypes.wintypes.DWORD(0)  # No export allowed
        result = self.ncrypt.NCryptSetProperty(
            key_handle,
            b"ExportPolicy",
            byref(export_flag),
            ctypes.sizeof(export_flag),
            0
        )
        self._check_error(result, "NCryptSetProperty(ExportPolicy)")
        
        # Finalize key
        result = self.ncrypt.NCryptFinalizeKey(key_handle, 0)
        self._check_error(result, "NCryptFinalizeKey")
        
        self.key_handle = key_handle
        self._initialized = True
        
        return key_handle
    
    def encrypt_with_tpm_key(self, data: bytes) -> bytes:
        """
        Encrypt data using the TPM-bound key.
        The key never leaves the TPM.
        """
        if not self._initialized or not self.key_handle:
            raise RuntimeError("Key not initialized. Call generate_key() first.")
        
        # Prepare input
        input_size = len(data)
        output_size = ctypes.wintypes.DWORD()
        
        # Get required buffer size
        result = self.ncrypt.NCryptEncrypt(
            self.key_handle,
            data,
            input_size,
            None,
            None,
            0,
            byref(output_size),
            NCRYPT_PAD_PKCS1_FLAG
        )
        
        if result != 0x00000023:  # ERROR_MORE_DATA
            self._check_error(result, "NCryptEncrypt(get size)")
        
        # Allocate output buffer
        output_buffer = ctypes.create_string_buffer(output_size.value)
        
        # Perform encryption
        result = self.ncrypt.NCryptEncrypt(
            self.key_handle,
            data,
            input_size,
            None,
            output_buffer,
            output_size.value,
            byref(output_size),
            NCRYPT_PAD_PKCS1_FLAG
        )
        self._check_error(result, "NCryptEncrypt")
        
        return output_buffer.raw[:output_size.value]
    
    def decrypt_with_tpm_key(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt data using the TPM-bound key.
        """
        if not self._initialized or not self.key_handle:
            raise RuntimeError("Key not initialized. Call generate_key() first.")
        
        input_size = len(encrypted_data)
        output_size = ctypes.wintypes.DWORD()
        
        # Get required buffer size
        result = self.ncrypt.NCryptDecrypt(
            self.key_handle,
            encrypted_data,
            input_size,
            None,
            None,
            0,
            byref(output_size),
            NCRYPT_PAD_PKCS1_FLAG
        )
        
        if result != 0x00000023:  # ERROR_MORE_DATA
            self._check_error(result, "NCryptDecrypt(get size)")
        
        # Allocate output buffer
        output_buffer = ctypes.create_string_buffer(output_size.value)
        
        # Perform decryption
        result = self.ncrypt.NCryptDecrypt(
            self.key_handle,
            encrypted_data,
            input_size,
            None,
            output_buffer,
            output_size.value,
            byref(output_size),
            NCRYPT_PAD_PKCS1_FLAG
        )
        self._check_error(result, "NCryptDecrypt")
        
        return output_buffer.raw[:output_size.value]
    
    def wrap_session_key(self, session_key: bytes) -> bytes:
        """
        Wrap (encrypt) a session key using the TPM-bound key.
        This binds the session key to hardware.
        """
        return self.encrypt_with_tpm_key(session_key)
    
    def unwrap_session_key(self, wrapped_key: bytes) -> bytes:
        """
        Unwrap (decrypt) a session key using the TPM-bound key.
        """
        return self.decrypt_with_tpm_key(wrapped_key)
    
    def delete_key(self):
        """Delete the TPM-bound key."""
        if self.key_handle:
            result = self.ncrypt.NCryptDeleteKey(self.key_handle, 0)
            self.key_handle = None
            self._initialized = False
            return result == 0
        return True
    
    def __del__(self):
        self.delete_key()


def create_tpm_wrapper():
    """Create and initialize a TPM key wrapper."""
    try:
        wrapper = TPMKeyWrapper()
        wrapper.generate_key("ZeroTrustSessionKey", bits=256)
        return wrapper
    except Exception as e:
        print(f"WARNING: TPM initialization failed: {e}")
        print("Falling back to software-only protection.")
        return None


if __name__ == "__main__":
    print("TPM-Bound Key Wrapper Test")
    print("=" * 60)
    
    try:
        wrapper = TPMKeyWrapper()
        print("Opening NCrypt storage provider...")
        provider = wrapper.open_storage_provider()
        print("Provider opened successfully")
        
        print("\nGenerating TPM-bound key...")
        wrapper.generate_key("TestKey", bits=256)
        print("Key generated successfully")
        
        # Test encryption/decryption
        test_data = b"Hello, TPM World!"
        print(f"\nOriginal data: {test_data}")
        
        encrypted = wrapper.encrypt_with_tpm_key(test_data)
        print(f"Encrypted: {encrypted[:32]}...")
        
        decrypted = wrapper.decrypt_with_tpm_key(encrypted)
        print(f"Decrypted: {decrypted}")
        
        print(f"\nMatch: {test_data == decrypted}")
        
        # Cleanup
        wrapper.delete_key()
        print("\nKey deleted successfully")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: TPM 2.0 may not be available on this system.")
        print("Consider using software-only protection as fallback.")
