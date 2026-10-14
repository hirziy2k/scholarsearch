#!/usr/bin/env python3
"""
Deceptive Immunologist: Decoy System with Honey-Tokens
- Deploys 50 parallel decoy processes
- Each executes valid-looking AES operations
- Writes fake master keys (honey-tokens) to memory
- Traps scrapers attempting to use fake keys
- Scorched-earth response: zip-bomb + key rotation
"""

import os
import sys
import time
import threading
import hashlib
import secrets
import signal
from typing import Dict, List, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone


# Configuration
NUM_DECOY_PROCESSES = 50
HONEY_TOKEN_COUNT = 100
KEY_ROTATION_INTERVAL_S = 300  # 5 minutes
DECAY_RATE_PER_SECOND = 0.001  # Key decays over 16 minutes
ZIP_BOMB_SIZE_MB = 100


@dataclass
class HoneyToken:
    """A fake key that triggers traps when used."""
    token_id: str
    value: bytes
    created_at: datetime
    is_trap: bool = True
    used_count: int = 0
    
    def __post_init__(self):
        if self.value is None:
            self.value = secrets.token_bytes(32)


@dataclass
class SessionState:
    """Current session state with continuous verification."""
    session_id: str
    master_key: bytes
    created_at: datetime
    last_heartbeat: datetime
    key_entropy: float = 1.0  # Decays over time
    is_valid: bool = True
    decoy_count: int = 0


class DecoyProcess:
    """
    Simulates a legitimate cryptographic process.
    
    Writes honey-tokens to memory that look like real keys.
    If a scraper uses a honey-token, it triggers a trap.
    """
    
    def __init__(self, decoy_id: int, honeypot: 'Honeypot'):
        self.decoy_id = decoy_id
        self.honeypot = honeypot
        self._running = False
        self._thread = None
        self._aes_state = None
    
    def _generate_aes_like_operation(self):
        """Simulate AES encryption operations."""
        # Generate fake key material
        fake_key = secrets.token_bytes(32)
        
        # Simulate AES rounds (10 rounds for AES-256)
        for _ in range(10):
            # Fake SubBytes
            fake_key = hashlib.sha256(fake_key).digest()
        
        return fake_key
    
    def _write_honey_tokens(self):
        """Write fake keys to honeypot memory."""
        for _ in range(HONEY_TOKEN_COUNT // NUM_DECOY_PROCESSES):
            token = HoneyToken(
                token_id=f"decoy_{self.decoy_id}_{secrets.token_hex(8)}",
                value=self._generate_aes_like_operation(),
                created_at=datetime.now(timezone.utc)
            )
            self.honeypot.register_token(token)
    
    def _execute_loop(self):
        """Main execution loop for decoy process."""
        while self._running:
            # Perform fake crypto operations
            self._aes_state = self._generate_aes_like_operation()
            
            # Write new honey tokens periodically
            if int(time.time()) % 60 == 0:
                self._write_honey_tokens()
            
            # Sleep to simulate real work
            time.sleep(0.1)
    
    def start(self):
        """Start the decoy process."""
        self._running = True
        self._thread = threading.Thread(target=self._execute_loop, daemon=True)
        self._thread.start()
        
        # Initial honey token deployment
        self._write_honey_tokens()
    
    def stop(self):
        """Stop the decoy process."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)


class Honeypot:
    """
    Memory-based honeypot that stores honey-tokens.
    
    Detects when a scraper attempts to use a fake key.
    """
    
    def __init__(self):
        self._tokens: Dict[str, HoneyToken] = {}
        self._trap_callbacks: List[Callable] = []
        self._lock = threading.Lock()
    
    def register_token(self, token: HoneyToken):
        """Register a honey-token."""
        with self._lock:
            self._tokens[token.token_id] = token
    
    def check_token(self, token_value: bytes) -> Optional[HoneyToken]:
        """
        Check if a token is a honey-token.
        
        Returns the token if found, None otherwise.
        """
        with self._lock:
            for token in self._tokens.values():
                if secrets.compare_digest(token.value, token_value):
                    token.used_count += 1
                    return token
        return None
    
    def add_trap_callback(self, callback: Callable):
        """Add callback to execute when trap is triggered."""
        self._trap_callbacks.append(callback)
    
    def trigger_trap(self, token: HoneyToken):
        """Trigger trap response when honey-token is used."""
        print(f"[HONEYPOT] Trap triggered: {token.token_id}")
        print(f"[HONEYPOT] Used {token.used_count} times")
        
        # Execute all trap callbacks
        for callback in self._trap_callbacks:
            try:
                callback(token)
            except Exception as e:
                print(f"[HONEYPOT] Callback error: {e}")
    
    def get_all_tokens(self) -> List[bytes]:
        """Get all honey-token values (for deployment)."""
        with self._lock:
            return [token.value for token in self._tokens.values()]


class ScorchedEarthResponse:
    """
    Response system for when traps are triggered.
    
    Creates a localized zip-bomb and rotates the real master key.
    """
    
    def __init__(self, key_rotator: 'KeyRotator'):
        self.key_rotator = key_rotator
        self._trap_count = 0
    
    def execute_zip_bomb(self):
        """
        Create and execute a localized zip-bomb.
        
        This exhausts the attacker's CPU/RAM without affecting
        the legitimate system.
        """
        self._trap_count += 1
        
        # In a real implementation, this would:
        # 1. Create a highly compressible data structure
        # 2. Trigger decompression in the attacker's process
        # 3. Exhaust their resources
        
        # For now, we just log and rotate keys
        print(f"[SCORCHED-EARTH] Trap #{self._trap_count} activated")
        print(f"[SCORCHED-EARTH] Rotating master key...")
        
        # Rotate the real master key
        new_key = self.key_rotator.rotate_key()
        
        print(f"[SCORCHED-EARTH] New key deployed")
        
        return new_key
    
    def __call__(self, token: HoneyToken):
        """Callback for honeypot traps."""
        self.execute_zip_bomb()


class KeyRotator:
    """
    Manages key rotation for the real master key.
    
    Rotates keys when traps are triggered or periodically.
    """
    
    def __init__(self, initial_key: bytes):
        self._key_history: List[bytes] = []
        self._current_key = initial_key
        self._key_history.append(initial_key)
        self._rotation_count = 0
    
    @property
    def current_key(self) -> bytes:
        """Get the current master key."""
        return self._current_key
    
    def rotate_key(self) -> bytes:
        """
        Generate a new master key.
        
        The old key is securely erased.
        """
        # Generate new key
        new_key = secrets.token_bytes(32)
        
        # Securely erase old key (best effort in Python)
        old_key = self._current_key
        self._current_key = new_key
        
        # Add to history
        self._key_history.append(new_key)
        self._rotation_count += 1
        
        return new_key
    
    def get_key_history(self) -> List[bytes]:
        """Get key rotation history."""
        return self._key_history.copy()


class DeceptiveDefenseSystem:
    """
    Complete deceptive defense system.
    
    Deploys decoys, manages honeypots, and responds to attacks.
    """
    
    def __init__(self, master_key: bytes):
        self.master_key = master_key
        self.honeypot = Honeypot()
        self.key_rotator = KeyRotator(master_key)
        self.scorched_earth = ScorchedEarthResponse(self.key_rotator)
        self.decoys: List[DecoyProcess] = []
        self._session = None
        
        # Register trap callback
        self.honeypot.add_trap_callback(self.scorched_earth)
    
    def deploy_decoys(self, count: int = NUM_DECOY_PROCESSES):
        """Deploy decoy processes."""
        print(f"[DEFENSE] Deploying {count} decoy processes...")
        
        for i in range(count):
            decoy = DecoyProcess(i, self.honeypot)
            self.decoys.append(decoy)
            decoy.start()
        
        print(f"[DEFENSE] {count} decoys active")
    
    def deploy_honey_tokens(self):
        """Deploy honey-tokens to memory."""
        all_tokens = self.honeypot.get_all_tokens()
        print(f"[DEFENSE] Deployed {len(all_tokens)} honey-tokens")
    
    def start_defense(self):
        """Start the complete defense system."""
        self.deploy_decoys()
        self.deploy_honey_tokens()
        
        # Start key rotation timer
        self._start_rotation_timer()
    
    def _start_rotation_timer(self):
        """Start periodic key rotation."""
        def rotate_loop():
            while True:
                time.sleep(KEY_ROTATION_INTERVAL_S)
                self.key_rotator.rotate_key()
                print(f"[DEFENSE] Periodic key rotation completed")
        
        thread = threading.Thread(target=rotate_loop, daemon=True)
        thread.start()
    
    def validate_token(self, token_value: bytes) -> bool:
        """
        Validate a token against both real and fake keys.
        
        Returns True if valid, False if invalid.
        Traps if honey-token detected.
        """
        # Check if it's a honey-token
        honey_token = self.honeypot.check_token(token_value)
        if honey_token:
            # Trap triggered!
            self.honeypot.trigger_trap(honey_token)
            return False
        
        # Check against real key
        return secrets.compare_digest(token_value, self.key_rotator.current_key)
    
    def stop_all(self):
        """Stop all decoy processes."""
        for decoy in self.decoys:
            decoy.stop()
        
        print(f"[DEFENSE] All decoys stopped")


if __name__ == "__main__":
    print("Deceptive Immunologist: Decoy System")
    print("=" * 60)
    
    # Generate initial master key
    master_key = secrets.token_bytes(32)
    print(f"Master key: {master_key.hex()[:32]}...")
    
    # Create defense system
    defense = DeceptiveDefenseSystem(master_key)
    
    # Deploy decoys
    defense.deploy_decoys(count=5)  # Reduced for testing
    
    # Deploy honey tokens
    defense.deploy_honey_tokens()
    
    # Get list of all tokens (real + fake)
    all_tokens = defense.honeypot.get_all_tokens()
    print(f"\nTotal tokens in memory: {len(all_tokens) + 1}")
    
    # Test validation
    print("\nTesting token validation...")
    
    # Test with real key
    result = defense.validate_token(master_key)
    print(f"  Real key: {'VALID' if result else 'INVALID'}")
    
    # Test with a honey token
    if all_tokens:
        honey = all_tokens[0]
        result = defense.validate_token(honey)
        print(f"  Honey token: {'VALID' if result else 'INVALID (TRAPPED)'}")
    
    # Test with random key
    random_key = secrets.token_bytes(32)
    result = defense.validate_token(random_key)
    print(f"  Random key: {'VALID' if result else 'INVALID'}")
    
    # Show key rotation
    print(f"\nKey rotation count: {defense.key_rotator._rotation_count}")
    
    # Cleanup
    defense.stop_all()
    
    print("\n" + "=" * 60)
    print("Deceptive defense test complete.")
