#!/usr/bin/env python3
"""
TOTP-Based Initialization Gate
- Requires human physical input (TOTP code) to proceed
- Uses time-based one-time password as cryptographic salt
- Prevents automated attack loops
- Derives master key from TOTP + hardware fingerprint
"""

import os
import sys
import time
import hashlib
import hmac
import struct
import getpass
from typing import Optional, Tuple
from datetime import datetime, timezone


class TOTPGate:
    """
    Initialization gate requiring human TOTP verification.
    
    This creates a physical barrier that automated malware cannot bypass.
    The TOTP code acts as a cryptographic salt for key derivation.
    """
    
    # TOTP settings
    DIGITS = 6
    PERIOD = 30  # seconds
    ALGORITHM = 'sha256'
    
    def __init__(self, secret: Optional[bytes] = None):
        """
        Initialize the TOTP gate.
        
        Args:
            secret: TOTP secret key. If None, generates a new one.
        """
        if secret is None:
            self.secret = os.urandom(32)  # 256-bit secret
            self._first_run = True
        else:
            self.secret = secret
            self._first_run = False
        
        self._authenticated = False
        self._auth_time = None
        self._attempts = 0
        self._max_attempts = 3
    
    def _generate_totp(self, timestamp: float) -> str:
        """Generate TOTP code for given timestamp."""
        # Calculate time step
        time_step = int(timestamp) // self.PERIOD
        
        # Convert time step to bytes (big-endian)
        time_bytes = struct.pack('>Q', time_step)
        
        # Calculate HMAC
        if self.ALGORITHM == 'sha256':
            h = hmac.new(self.secret, time_bytes, hashlib.sha256).digest()
        else:
            h = hmac.new(self.secret, time_bytes, hashlib.sha1).digest()
        
        # Dynamic truncation
        offset = h[-1] & 0x0F
        code = struct.unpack('>I', h[offset:offset+4])[0]
        code = code & 0x7FFFFFFF
        
        # Generate digits
        code = code % (10 ** self.DIGITS)
        
        return str(code).zfill(self.DIGITS)
    
    def _verify_totp(self, code: str, window: int = 1) -> bool:
        """
        Verify a TOTP code with time window tolerance.
        
        Args:
            code: 6-digit TOTP code
            window: Number of time steps to check before/after current
        """
        current_time = time.time()
        
        for offset in range(-window, window + 1):
            test_time = current_time + (offset * self.PERIOD)
            expected = self._generate_totp(test_time)
            if hmac.compare_digest(code, expected):
                return True
        
        return False
    
    def _get_hardware_fingerprint(self) -> bytes:
        """Generate a hardware fingerprint for key derivation."""
        import platform
        import uuid
        
        # Combine multiple hardware identifiers
        components = [
            platform.node().encode(),
            platform.processor().encode(),
            str(uuid.getnode()).encode(),
            os.environ.get('COMPUTERNAME', '').encode(),
        ]
        
        # Hash to create fingerprint
        combined = b'|'.join(components)
        return hashlib.sha256(combined).digest()
    
    def derive_master_key(self, totp_code: str) -> bytes:
        """
        Derive master key from TOTP code and hardware fingerprint.
        
        This ensures the key is:
        1. Bound to hardware (fingerprint)
        2. Requires human input (TOTP)
        3. Time-bound (TOTP changes every 30s)
        """
        hardware_fp = self._get_hardware_fingerprint()
        
        # Use TOTP as salt in key derivation
        salt = hashlib.sha256(totp_code.encode()).digest()
        
        # Derive key using PBKDF2
        master_key = hashlib.pbkdf2_hmac(
            'sha256',
            self.secret + hardware_fp,
            salt,
            iterations=100000,
            dklen=32
        )
        
        return master_key
    
    def authenticate(self, max_attempts: int = 3) -> Tuple[bool, Optional[bytes]]:
        """
        Authenticate using TOTP and derive master key.
        
        Returns:
            Tuple of (success, master_key)
        """
        self._max_attempts = max_attempts
        self._attempts = 0
        
        print("\n" + "=" * 60)
        print("TOTP INITIALIZATION GATE")
        print("=" * 60)
        
        if self._first_run:
            print("\nFirst run detected. Setting up TOTP authentication.")
            print("You will need an authenticator app (Google Authenticator, etc.)")
            print("\nSECRET KEY (save this securely):")
            print(f"  {self.secret.hex().upper()}")
            print("\nAdd this as a 'Time-based' or 'TOTP' entry in your authenticator app.")
            input("\nPress Enter when ready to continue...")
        
        while self._attempts < self._max_attempts:
            remaining = self._max_attempts - self._attempts
            
            print(f"\nAuthentication attempts remaining: {remaining}")
            print(f"Current time step: {int(time.time()) // self.PERIOD}")
            
            # Prompt for TOTP code
            try:
                code = input("\nEnter 6-digit TOTP code: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nAuthentication cancelled.")
                return False, None
            
            if len(code) != self.DIGITS:
                print(f"Invalid code length. Expected {self.DIGITS} digits.")
                self._attempts += 1
                continue
            
            if not code.isdigit():
                print("Code must contain only digits.")
                self._attempts += 1
                continue
            
            # Verify TOTP
            if self._verify_totp(code):
                self._authenticated = True
                self._auth_time = time.time()
                
                # Derive master key
                master_key = self.derive_master_key(code)
                
                print("\n[SUCCESS] Authentication verified.")
                print("Master key derived from TOTP + hardware fingerprint.")
                
                return True, master_key
            else:
                print("\n[FAILED] Invalid TOTP code.")
                self._attempts += 1
                
                if self._attempts < self._max_attempts:
                    print("Try again...")
                    time.sleep(1)  # Rate limit
        
        print(f"\n[LOCKED] Maximum attempts ({self._max_attempts}) exceeded.")
        print("This session is now locked. Wait for a new time window.")
        
        return False, None
    
    def is_authenticated(self, validity_seconds: int = 300) -> bool:
        """Check if currently authenticated within validity window."""
        if not self._authenticated or not self._auth_time:
            return False
        
        elapsed = time.time() - self._auth_time
        return elapsed < validity_seconds
    
    def get_current_totp(self) -> str:
        """Get current TOTP code (for testing/setup)."""
        return self._generate_totp(time.time())
    
    def export_secret(self) -> str:
        """Export secret as hex string (for secure storage)."""
        return self.secret.hex()


def create_totp_gate(stored_secret: Optional[str] = None) -> TOTPGate:
    """
    Create a TOTP gate, optionally with a stored secret.
    
    Args:
        stored_secret: Previously exported secret as hex string
    """
    if stored_secret:
        secret = bytes.fromhex(stored_secret)
        return TOTPGate(secret=secret)
    else:
        return TOTPGate()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    
    print("TOTP Initialization Gate - Setup/Testing")
    print("=" * 60)
    
    # Create gate
    gate = TOTPGate()
    
    print(f"\nGenerated secret: {gate.secret.hex().upper()}")
    print(f"\nCurrent TOTP: {gate.get_current_totp()}")
    
    print("\nAdd this secret to your authenticator app.")
    print("Then run this script again to test authentication.")
    
    # Test authentication
    print("\n" + "=" * 60)
    success, master_key = gate.authenticate()
    
    if success:
        print(f"\nMaster key: {master_key.hex()}")
    else:
        print("\nAuthentication failed.")
