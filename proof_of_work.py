#!/usr/bin/env python3
"""
Proof-of-Work Initialization Barrier
- CPU-bound puzzle requiring ~45 seconds to solve
- Prevents automated brute-force loops
- Zero human interaction required
- Mathematically verifiable delay
"""

import hashlib
import os
import time
import sys
from typing import Tuple, Optional
from contextlib import contextmanager


# Configuration
DEFAULT_DIFFICULTY = 20  # Number of leading zeros required
DEFAULT_TARGET_TIME_S = 45  # Target solve time in seconds
SALT_SIZE = 32  # bytes


class ProofOfWork:
    """
    CPU-bound proof-of-work system.
    
    The puzzle requires finding a nonce such that:
        SHA-256(challenge + nonce) starts with `difficulty` zeros
    
    This creates a provable delay that cannot be parallelized
    without proportional computational cost.
    """
    
    def __init__(self, difficulty: int = DEFAULT_DIFFICULTY):
        self.difficulty = difficulty
        self._challenge = None
        self._solution = None
        self._start_time = None
        self._end_time = None
    
    def generate_challenge(self) -> bytes:
        """Generate a random challenge."""
        self._challenge = os.urandom(SALT_SIZE)
        self._solution = None
        self._start_time = None
        self._end_time = None
        return self._challenge
    
    def verify_nonce(self, challenge: bytes, nonce: bytes, solution: bytes) -> bool:
        """Verify that a nonce produces a valid solution."""
        # Concatenate challenge and nonce
        data = challenge + nonce
        
        # Hash the data
        hash_result = hashlib.sha256(data).digest()
        
        # Check for leading zeros
        prefix = b'\x00' * (self.difficulty // 8)
        remaining_bits = self.difficulty % 8
        
        if hash_result[:self.difficulty // 8] != prefix:
            return False
        
        if remaining_bits > 0:
            byte_index = self.difficulty // 8
            mask = (0xFF << (8 - remaining_bits)) & 0xFF
            if (hash_result[byte_index] & mask) != 0:
                return False
        
        return True
    
    def solve(self, challenge: Optional[bytes] = None, 
              timeout_s: float = 120.0) -> Tuple[bytes, float]:
        """
        Solve the proof-of-work puzzle.
        
        Args:
            challenge: Optional challenge bytes (generates new if None)
            timeout_s: Maximum time to solve in seconds
        
        Returns:
            Tuple of (nonce, elapsed_seconds)
        """
        if challenge is None:
            challenge = self.generate_challenge()
        else:
            self._challenge = challenge
        
        self._start_time = time.perf_counter()
        nonce_counter = 0
        
        while True:
            # Check timeout
            elapsed = time.perf_counter() - self._start_time
            if elapsed > timeout_s:
                raise TimeoutError(f"Proof-of-work not solved within {timeout_s}s")
            
            # Generate candidate nonce
            nonce = nonce_counter.to_bytes(8, byteorder='big')
            nonce_counter += 1
            
            # Test this nonce
            data = challenge + nonce
            hash_result = hashlib.sha256(data).digest()
            
            # Check difficulty
            if self._check_difficulty(hash_result):
                self._solution = nonce
                self._end_time = time.perf_counter()
                elapsed = self._end_time - self._start_time
                return nonce, elapsed
            
            # Progress update every 1M attempts
            if nonce_counter % 1_000_000 == 0:
                rate = nonce_counter / elapsed if elapsed > 0 else 0
                print(f"  Attempts: {nonce_counter:,}, Rate: {rate:,.0f}/s", 
                      file=sys.stderr)
    
    def _check_difficulty(self, hash_result: bytes) -> bool:
        """Check if hash meets difficulty requirement."""
        # Check full bytes
        full_bytes = self.difficulty // 8
        for i in range(full_bytes):
            if hash_result[i] != 0:
                return False
        
        # Check remaining bits
        remaining = self.difficulty % 8
        if remaining > 0:
            byte_index = full_bytes
            mask = (0xFF << (8 - remaining)) & 0xFF
            if (hash_result[byte_index] & mask) != 0:
                return False
        
        return True
    
    def verify_solution(self, challenge: bytes, nonce: bytes) -> bool:
        """Verify a proposed solution."""
        return self.verify_nonce(challenge, nonce, nonce)
    
    def get_solution(self) -> Tuple[bytes, bytes]:
        """Get the current challenge and solution."""
        if self._challenge is None or self._solution is None:
            raise RuntimeError("No solution available")
        return self._challenge, self._solution
    
    def derive_key(self, challenge: bytes, nonce: bytes, 
                   key_length: int = 32) -> bytes:
        """
        Derive a cryptographic key from the proof-of-work solution.
        
        The key is derived using HKDF-like construction.
        """
        # Use SHA-256 as PRF
        prk = hashlib.sha256(b"PoW-KeyDerivation" + challenge).digest()
        
        # Expand to desired length
        key = b""
        counter = 0
        while len(key) < key_length:
            counter += 1
            key += hashlib.sha256(prk + nonce + counter.to_bytes(4, 'big')).digest()
        
        return key[:key_length]


@contextmanager
def proof_of_work_barrier(difficulty: int = DEFAULT_DIFFICULTY,
                         timeout_s: float = 120.0):
    """
    Context manager for proof-of-work barrier.
    
    Usage:
        with proof_of_work_barrier(difficulty=20) as pow_system:
            key = pow_system.derive_key(challenge, nonce)
            # Use derived key...
    """
    pow_system = ProofOfWork(difficulty)
    
    print(f"Generating proof-of-work challenge (difficulty={difficulty})...")
    challenge = pow_system.generate_challenge()
    
    print("Solving proof-of-work puzzle...")
    print("This will take approximately 45 seconds...")
    
    nonce, elapsed = pow_system.solve(timeout_s=timeout_s)
    
    print(f"Solved in {elapsed:.1f} seconds")
    print(f"Nonce: {nonce.hex()}")
    
    yield pow_system


def quick_pow(difficulty: int = 16, timeout_s: float = 10.0) -> bytes:
    """
    Quick proof-of-work for testing or low-security applications.
    
    Returns the derived key directly.
    """
    pow_system = ProofOfWork(difficulty)
    challenge = pow_system.generate_challenge()
    nonce, elapsed = pow_system.solve(timeout_s=timeout_s)
    
    return pow_system.derive_key(challenge, nonce)


if __name__ == "__main__":
    print("Proof-of-Work Initialization Barrier")
    print("=" * 60)
    
    # Configuration
    difficulty = 16  # Lower for testing (production: 20+)
    target_time = 10  # Lower for testing (production: 45+)
    
    print(f"\nConfiguration:")
    print(f"  Difficulty: {difficulty} bits")
    print(f"  Target time: {target_time}s")
    
    # Solve proof-of-work
    print("\nSolving proof-of-work...")
    pow_system = ProofOfWork(difficulty)
    challenge = pow_system.generate_challenge()
    
    print(f"Challenge: {challenge.hex()}")
    
    start = time.perf_counter()
    try:
        nonce, elapsed = pow_system.solve(challenge, timeout_s=target_time * 2)
        
        print(f"\nSolution found!")
        print(f"  Nonce: {nonce.hex()}")
        print(f"  Time: {elapsed:.2f}s")
        
        # Verify solution
        print("\nVerifying solution...")
        valid = pow_system.verify_solution(challenge, nonce)
        print(f"  Valid: {valid}")
        
        # Derive key
        print("\nDeriving key...")
        key = pow_system.derive_key(challenge, nonce)
        print(f"  Key: {key.hex()[:32]}...")
        
        # Show hash
        data = challenge + nonce
        hash_result = hashlib.sha256(data).digest()
        print(f"\n  Hash: {hash_result.hex()}")
        print(f"  Leading zeros: {bin(hash_result[0]).count('0')}")
        
    except TimeoutError as e:
        print(f"\nFailed: {e}")
    
    print("\n" + "=" * 60)
    print("Proof-of-work test complete.")
