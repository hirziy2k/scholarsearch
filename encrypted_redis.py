#!/usr/bin/env python3
"""
Encrypted Redis Wrapper (AES-GCM)
- Transparently encrypts all values before writing to Redis
- Decrypts all values on read
- Session-derived keys (never stored in Redis)
- Protects against unauthenticated Redis local access
"""

import os
import sys
import json
import hashlib
import secrets
from typing import Optional, Any, Dict
from datetime import datetime, timezone
from pathlib import Path

# Attempt to import cryptography
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    print("WARNING: cryptography package not installed. Using fallback (insecure).")

# Fallback encryption (XOR — NOT secure, just obfuscation)
class FallbackCipher:
    """XOR-based obfuscation (NOT cryptographically secure)."""
    
    def __init__(self, key: bytes):
        self._key = key
    
    def encrypt(self, data: bytes) -> bytes:
        nonce = os.urandom(12)
        encrypted = bytes(a ^ b for a, b in zip(data, self._key * len(data)))
        return nonce + encrypted
    
    def decrypt(self, data: bytes) -> bytes:
        nonce = data[:12]
        encrypted = data[12:]
        decrypted = bytes(a ^ b for a, b in zip(encrypted, self._key * len(encrypted)))
        return decrypted


class EncryptedRedisWrapper:
    """Redis client wrapper with AES-GCM encryption."""
    
    def __init__(self, redis_client, session_key: Optional[bytes] = None):
        """
        Initialize with a redis client and optional session key.
        
        Args:
            redis_client: A redis.Redis client instance
            session_key: Optional 256-bit key for encryption. Generated if not provided.
        """
        self._redis = redis_client
        self._session_key = session_key or secrets.token_bytes(32)
        
        if HAS_CRYPTOGRAPHY:
            self._cipher = AESGCM(self._session_key)
        else:
            self._cipher = FallbackCipher(self._session_key)
        
        # Derive separate keys for different purposes
        self._key_prefix = hashlib.sha256(self._session_key + b"prefix").digest()[:16]
    
    def _derive_key(self, context: str) -> bytes:
        """Derive a context-specific key."""
        return hashlib.sha256(self._session_key + context.encode()).digest()[:16]
    
    def _encrypt_value(self, value: str, context: str = "default") -> bytes:
        """Encrypt a string value."""
        data = value.encode('utf-8')
        if HAS_CRYPTOGRAPHY:
            nonce = os.urandom(12)
            encrypted = self._cipher.encrypt(nonce, data, context.encode())
            return nonce + encrypted
        else:
            return self._cipher.encrypt(data)
    
    def _decrypt_value(self, data: bytes, context: str = "default") -> str:
        """Decrypt bytes to string."""
        if HAS_CRYPTOGRAPHY:
            nonce = data[:12]
            encrypted = data[12:]
            decrypted = self._cipher.decrypt(nonce, encrypted, context.encode())
        else:
            decrypted = self._cipher.decrypt(data)
        return decrypted.decode('utf-8')
    
    def set(self, key: str, value: str, **kwargs) -> bool:
        """Set an encrypted key-value pair."""
        encrypted_value = self._encrypt_value(value, context=key)
        return self._redis.set(key, encrypted_value, **kwargs)
    
    def get(self, key: str) -> Optional[str]:
        """Get and decrypt a value."""
        data = self._redis.get(key)
        if data is None:
            return None
        try:
            return self._decrypt_value(data, context=key)
        except Exception:
            return None
    
    def setex(self, key: str, time: int, value: str) -> bool:
        """Set with expiration (encrypted)."""
        encrypted_value = self._encrypt_value(value, context=key)
        return self._redis.setex(key, time, encrypted_value)
    
    def hset(self, name: str, key: str, value: str) -> int:
        """Set a field in a hash (encrypted)."""
        encrypted_value = self._encrypt_value(value, context=f"{name}:{key}")
        return self._redis.hset(name, key, encrypted_value)
    
    def hget(self, name: str, key: str) -> Optional[str]:
        """Get a field from a hash (decrypted)."""
        data = self._redis.hget(name, key)
        if data is None:
            return None
        try:
            return self._decrypt_value(data, context=f"{name}:{key}")
        except Exception:
            return None
    
    def hgetall(self, name: str) -> Dict[str, str]:
        """Get all fields from a hash (decrypted)."""
        data = self._redis.hgetall(name)
        result = {}
        for key, value in data.items():
            try:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                result[key_str] = self._decrypt_value(value, context=f"{name}:{key_str}")
            except Exception:
                continue
        return result
    
    def xadd(self, name: str, fields: Dict[str, str], **kwargs) -> str:
        """Add to a stream (encrypted fields)."""
        encrypted_fields = {}
        for key, value in fields.items():
            encrypted_fields[key] = self._encrypt_value(value, context=f"{name}:{key}")
        return self._redis.xadd(name, encrypted_fields, **kwargs)
    
    def xread(self, streams: Dict[str, int], **kwargs) -> list:
        """Read from a stream (decrypted fields)."""
        result = self._redis.xread(streams, **kwargs)
        decrypted_result = []
        
        for stream_name, messages in result:
            decrypted_messages = []
            for msg_id, fields in messages:
                decrypted_fields = {}
                for key, value in fields.items():
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    try:
                        decrypted_fields[key_str] = self._decrypt_value(
                            value, context=f"{stream_name.decode() if isinstance(stream_name, bytes) else stream_name}:{key_str}"
                        )
                    except Exception:
                        decrypted_fields[key_str] = value
                decrypted_messages.append((msg_id, decrypted_fields))
            decrypted_result.append((stream_name, decrypted_messages))
        
        return decrypted_result
    
    def __getattr__(self, name):
        """Proxy all other methods to the underlying Redis client."""
        return getattr(self._redis, name)


def create_encrypted_redis(host='127.0.0.1', port=6379, password=None, **kwargs):
    """
    Create an encrypted Redis connection.
    
    Returns:
        EncryptedRedisWrapper instance
    """
    try:
        import redis
        client = redis.Redis(host=host, port=port, password=password, **kwargs)
        # Test connection
        client.ping()
    except ImportError:
        print("ERROR: redis package not installed. Run: pip install redis")
        return None
    except Exception as e:
        print(f"ERROR: Could not connect to Redis: {e}")
        return None
    
    return EncryptedRedisWrapper(client)


if __name__ == "__main__":
    print("Encrypted Redis Wrapper")
    print("=" * 40)
    
    if not HAS_CRYPTOGRAPHY:
        print("WARNING: Using fallback XOR obfuscation (NOT secure)")
        print("Install cryptography: pip install cryptography")
    else:
        print("Using AES-GCM encryption")
    
    # Test with a mock Redis client
    class MockRedis:
        def __init__(self):
            self._store = {}
        
        def set(self, key, value, **kwargs):
            self._store[key] = value
            return True
        
        def get(self, key):
            return self._store.get(key)
        
        def ping(self):
            return True
    
    mock = MockRedis()
    wrapper = EncryptedRedisWrapper(mock)
    
    # Test encryption
    test_key = "test:secret"
    test_value = "my-secret-api-key-12345"
    
    print(f"\nOriginal: {test_value}")
    wrapper.set(test_key, test_value)
    print(f"Stored (encrypted): {wrapper._store[test_key][:32]}...")
    retrieved = wrapper.get(test_key)
    print(f"Retrieved (decrypted): {retrieved}")
    print(f"Match: {test_value == retrieved}")
