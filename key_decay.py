#!/usr/bin/env python3
"""
Key Decay Mechanism
- Master key decays over time without valid heartbeats
- Entropy requires continuous biometric-like input
- Automatic session expiration
- Mathematical polynomial decay model
"""

import os
import sys
import time
import math
import secrets
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone


# Configuration
DECAY_HALF_LIFE_S = 7200  # 2 hours
ENTROPY_REFRESH_RATE = 0.005  # Entropy added per valid heartbeat
MIN_ENTROPY_FOR_USE = 0.1  # Minimum entropy to use key
CRITICAL_ENTROPY_THRESHOLD = 0.05  # Below this, key is wiped


@dataclass
class KeyState:
    """State of a decaying key."""
    key_id: str
    created_at: datetime
    last_refreshed: datetime
    current_entropy: float = 1.0
    is_alive: bool = True
    total_refreshes: int = 0


class ExponentialDecay:
    """
    Exponential decay model for key entropy.
    
    Models key entropy as:
        E(t) = E_0 * exp(-λ * t)
    
    where:
        E_0 = initial entropy (1.0)
        λ = decay rate (ln(2) / half_life)
        t = time since last refresh
    """
    
    def __init__(self, half_life_s: float = DECAY_HALF_LIFE_S):
        self.half_life = half_life_s
        self.decay_constant = math.log(2) / half_life_s
    
    def compute_entropy(self, initial_entropy: float, 
                       elapsed_s: float) -> float:
        """Compute entropy after elapsed time."""
        return initial_entropy * math.exp(-self.decay_constant * elapsed_s)
    
    def compute_time_to_zero(self, initial_entropy: float,
                            threshold: float = MIN_ENTROPY_FOR_USE) -> float:
        """Compute time until entropy drops below threshold."""
        if initial_entropy <= threshold:
            return 0.0
        
        # Solve: threshold = initial * exp(-λ * t)
        # t = -ln(threshold/initial) / λ
        return -math.log(threshold / initial_entropy) / self.decay_constant


class CryptographicBreathing:
    """
    Implements "Cryptographic Breathing" - key material breathes
    in entropy with valid heartbeats and breathes out entropy over time.
    
    The key has a natural half-life that requires continuous
    authentication to maintain.
    """
    
    def __init__(self, key: bytes, half_life_s: float = DECAY_HALF_LIFE_S):
        self.key = key
        self.decay_model = ExponentialDecay(half_life_s)
        self.state = KeyState(
            key_id=secrets.token_hex(8),
            created_at=datetime.now(timezone.utc),
            last_refreshed=datetime.now(timezone.utc),
            current_entropy=1.0
        )
        self._decay_thread = None
        self._running = False
    
    def _decay_loop(self):
        """Background decay computation."""
        while self._running:
            # Compute current entropy
            elapsed = (datetime.now(timezone.utc) - 
                      self.state.last_refreshed).total_seconds()
            
            self.state.current_entropy = self.decay_model.compute_entropy(
                1.0, elapsed
            )
            
            # Check if key is still usable
            if self.state.current_entropy < CRITICAL_ENTROPY_THRESHOLD:
                self.state.is_alive = False
                print(f"[BREATHING] Key {self.state.key_id} has expired!")
            
            time.sleep(1)
    
    def start(self):
        """Start the breathing process."""
        self._running = True
        self._decay_thread = __import__('threading').Thread(
            target=self._decay_loop, daemon=True
        )
        self._decay_thread.start()
    
    def stop(self):
        """Stop the breathing process."""
        self._running = False
    
    def refresh(self, amount: float = ENTROPY_REFRESH_RATE):
        """
        Refresh key entropy (valid heartbeat).
        
        This is like the key "breathing in" entropy.
        """
        if not self.state.is_alive:
            return False
        
        self.state.current_entropy = min(1.0, 
            self.state.current_entropy + amount)
        self.state.last_refreshed = datetime.now(timezone.utc)
        self.state.total_refreshes += 1
        
        return True
    
    def get_entropy(self) -> float:
        """Get current entropy level."""
        elapsed = (datetime.now(timezone.utc) - 
                  self.state.last_refreshed).total_seconds()
        
        return self.decay_model.compute_entropy(1.0, elapsed)
    
    def is_usable(self) -> bool:
        """Check if key is still usable."""
        return (self.state.is_alive and 
                self.get_entropy() >= MIN_ENTROPY_FOR_USE)
    
    def get_time_to_expiry(self) -> float:
        """Get time until key expires."""
        return self.decay_model.compute_time_to_zero(1.0, MIN_ENTROPY_FOR_USE)
    
    def force_decay(self, amount: float = 0.1):
        """Force entropy decay (for testing)."""
        self.state.current_entropy = max(0.0, 
            self.state.current_entropy - amount)


class RollingKeyPolynomial:
    """
    Rolling key that is a function of time and biometric input.
    
    The key K(t) = f(t, B(t)) where:
        t = current time
        B(t) = biometric hash at time t
    
    Without continuous biometric feed, the key becomes invalid.
    """
    
    def __init__(self, seed: bytes):
        self.seed = seed
        self._last_biometric = None
        self._last_time = time.time()
        self._key_polynomial = seed
    
    def update_with_biometric(self, biometric_hash: bytes) -> bytes:
        """
        Update key polynomial with new biometric input.
        
        The key becomes a function of both time and biometrics.
        """
        current_time = time.time()
        time_delta = current_time - self._last_time
        
        # Compute new polynomial value
        # K(t) = SHA256(K(t-1) || B(t) || t)
        data = (self._key_polynomial + 
                biometric_hash + 
                int(current_time * 1000).to_bytes(8, 'big'))
        
        self._key_polynomial = __import__('hashlib').sha256(data).digest()
        
        self._last_biometric = biometric_hash
        self._last_time = current_time
        
        return self._key_polynomial
    
    def get_current_key(self) -> bytes:
        """Get current key value."""
        return self._key_polynomial
    
    def invalidate(self):
        """Immediately invalidate the key."""
        self._key_polynomial = secrets.token_bytes(32)


class ContinuousBiometricStream:
    """
    Simulates continuous biometric authentication stream.
    
    In a real implementation, this would:
    - Capture keystroke dynamics
    - Analyze mouse movement patterns
    - Monitor terminal command cadence
    - Compute biometric hash from patterns
    """
    
    def __init__(self):
        self._biometric_history = []
        self._confidence = 1.0
    
    def capture_biometric(self) -> bytes:
        """
        Capture current biometric state.
        
        Returns a hash representing the current behavioral pattern.
        """
        # Simulate biometric capture
        # In reality: keystroke timing, mouse velocity, etc.
        import hashlib
        
        timestamp = int(time.time() * 1000)
        simulated_pattern = f"biometric_{timestamp}".encode()
        
        biometric_hash = hashlib.sha256(simulated_pattern).digest()
        
        self._biometric_history.append(biometric_hash)
        
        return biometric_hash
    
    def get_confidence(self) -> float:
        """Get confidence that current user is the original human."""
        # In reality: compare to baseline
        # For simulation: always confident
        return 0.99


class SessionWithDecay:
    """
    Complete session with key decay and continuous verification.
    """
    
    def __init__(self, master_key: bytes):
        self.master_key = master_key
        self.breathing = CryptographicBreathing(master_key)
        self.biometric_stream = ContinuousBiometricStream()
        self.rolling_key = RollingKeyPolynomial(master_key)
        self._active = False
    
    def start(self):
        """Start the decaying session."""
        self.breathing.start()
        self._active = True
    
    def heartbeat(self) -> bool:
        """
        Process a heartbeat with biometric update.
        
        Returns True if session is still valid.
        """
        if not self._active:
            return False
        
        # Capture biometric
        biometric = self.biometric_stream.capture_biometric()
        
        # Update rolling key
        self.rolling_key.update_with_biometric(biometric)
        
        # Refresh breathing key
        self.breathing.refresh()
        
        return self.is_valid()
    
    def is_valid(self) -> bool:
        """Check if session is currently valid."""
        return (self._active and 
                self.breathing.is_usable() and
                self.biometric_stream.get_confidence() > 0.8)
    
    def get_session_info(self):
        """Get current session information."""
        return {
            "active": self._active,
            "breathing_entropy": self.breathing.get_entropy(),
            "time_to_expiry_s": self.breathing.get_time_to_expiry(),
            "biometric_confidence": self.biometric_stream.get_confidence(),
            "is_valid": self.is_valid()
        }
    
    def stop(self):
        """Stop the session."""
        self.breathing.stop()
        self._active = False


if __name__ == "__main__":
    print("Key Decay Mechanism")
    print("=" * 60)
    
    # Generate master key
    master_key = secrets.token_bytes(32)
    print(f"Master key: {master_key.hex()[:32]}...")
    
    # Create session with decay (short half-life for testing)
    print("\nCreating session with 30-second half-life...")
    session = SessionWithDecay(master_key)
    session.breathing = CryptographicBreathing(master_key, half_life_s=30)
    
    session.start()
    
    # Simulate heartbeats
    print("\nSimulating heartbeats...")
    for i in range(10):
        time.sleep(1)
        
        # Heartbeat
        valid = session.heartbeat()
        
        # Get info
        info = session.get_session_info()
        
        print(f"  [{i+1}s] Valid: {info['is_valid']}, "
              f"Entropy: {info['breathing_entropy']:.3f}, "
              f"Time to expiry: {info['time_to_expiry_s']:.1f}s")
    
    # Stop heartbeats and watch decay
    print("\nStopping heartbeats, watching decay...")
    for i in range(10):
        time.sleep(1)
        
        info = session.get_session_info()
        print(f"  [{i+1}s] Valid: {info['is_valid']}, "
              f"Entropy: {info['breathing_entropy']:.3f}, "
              f"Time to expiry: {info['time_to_expiry_s']:.1f}s")
    
    # Show final state
    info = session.get_session_info()
    print(f"\nFinal state:")
    print(f"  Valid: {info['is_valid']}")
    print(f"  Entropy: {info['breathing_entropy']:.3f}")
    
    session.stop()
    
    print("\n" + "=" * 60)
    print("Key decay test complete.")
