#!/usr/bin/env python3
"""
FIDO2/WebAuthn Hardware Touch Interface
- Physical touch required for authentication
- Uses YubiKey or similar FIDO2 device
- Zero-friction after initial setup
- Hardware-rooted trust
"""

import os
import sys
import json
import hashlib
import time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path


# Try to import fido2 library
try:
    from fido2.server import Fido2Server
    from fido2.webauthn import PublicKeyCredentialRpEntity
    from fido2.client import ClientData
    from fido2.server import AuthData
    from fido2.attestation import Attestation
    from fido2.cose import CoseKey
    HAS_FIDO2 = True
except ImportError:
    HAS_FIDO2 = False
    print("WARNING: fido2 library not installed. Install with: pip install fido2")


class FIDO2Authenticator:
    """
    FIDO2/WebAuthn authenticator interface.
    
    Requires a physical touch on a FIDO2 device (YubiKey, etc.)
    to complete authentication.
    """
    
    def __init__(self, rp_id: str = "zero-trust-local",
                 rp_name: str = "Zero Trust Local Auth"):
        """
        Initialize the FIDO2 authenticator.
        
        Args:
            rp_id: Relying party identifier
            rp_name: Human-readable relying party name
        """
        if not HAS_FIDO2:
            raise RuntimeError("fido2 library not installed")
        
        self.rp_id = rp_id
        self.rp_name = rp_name
        
        # Create relying party
        self.rp = PublicKeyCredentialRpEntity(id=rp_id, name=rp_name)
        
        # Create server
        self.server = Fido2Server(self.rp)
        
        # Storage for credentials
        self._credentials: Dict[str, Any] = {}
        self._challenge = None
        self._user_id = None
    
    def generate_registration_options(self, user_id: bytes, 
                                     username: str) -> Dict[str, Any]:
        """
        Generate options for credential registration.
        
        This creates a challenge that must be signed by the FIDO2 device.
        """
        self._user_id = user_id
        
        # Generate registration options
        options, state = self.server.register_begin(
            user={
                "id": user_id,
                "name": username,
                "displayName": username,
            },
            credentials=[],  # Empty for new registration
            user_verification="required"
        )
        
        self._challenge = state
        
        return {
            "publicKey": options,
            "challenge": state
        }
    
    def complete_registration(self, credential_response: Dict) -> bool:
        """
        Complete the registration process.
        
        Args:
            credential_response: Response from the FIDO2 device
        
        Returns:
            True if registration successful
        """
        try:
            auth_data = self.server.register_complete(
                self._challenge,
                credential_response
            )
            
            # Store the credential
            credential_id = auth_data.credential_data.credential_id
            self._credentials[credential_id] = {
                "public_key": auth_data.credential_data.public_key,
                "sign_count": auth_data.sign_count,
                "user_id": self._user_id
            }
            
            return True
        except Exception as e:
            print(f"Registration failed: {e}")
            return False
    
    def generate_authentication_options(self) -> Dict[str, Any]:
        """
        Generate options for authentication (touch required).
        
        Returns:
            Options dict containing the challenge
        """
        # Get list of registered credential IDs
        allow_credentials = [
            {"type": "public-key", "id": cred_id}
            for cred_id in self._credentials.keys()
        ]
        
        # Generate authentication options
        options, state = self.server.authenticate_begin(
            credentials=self._credentials.values(),
            user_verification="required"
        )
        
        self._challenge = state
        
        return {
            "publicKey": options,
            "challenge": state
        }
    
    def complete_authentication(self, credential_response: Dict) -> Optional[bytes]:
        """
        Complete the authentication process.
        
        Args:
            credential_response: Response from the FIDO2 device (after touch)
        
        Returns:
            User ID if authentication successful, None otherwise
        """
        try:
            auth_data = self.server.authenticate_complete(
                self._challenge,
                self._credentials.values(),
                credential_response
            )
            
            # Get the user ID
            credential_id = auth_data.credential_data.credential_id
            if credential_id in self._credentials:
                return self._credentials[credential_id]["user_id"]
            
            return None
        except Exception as e:
            print(f"Authentication failed: {e}")
            return None
    
    def save_credentials(self, filepath: Path):
        """Save credentials to a file."""
        data = {
            "rp_id": self.rp_id,
            "credentials": {
                cred_id.hex(): {
                    "public_key": list(cred["public_key"]),
                    "sign_count": cred["sign_count"],
                    "user_id": cred["user_id"].hex()
                }
                for cred_id, cred in self._credentials.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f)
    
    def load_credentials(self, filepath: Path):
        """Load credentials from a file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.rp_id = data["rp_id"]
        self._credentials = {
            bytes.fromhex(cred_id): {
                "public_key": bytes(cred["public_key"]),
                "sign_count": cred["sign_count"],
                "user_id": bytes.fromhex(cred["user_id"])
            }
            for cred_id, cred in data["credentials"].items()
        }


class SimulatedFIDO2:
    """
    Simulated FIDO2 for testing when no hardware is available.
    
    WARNING: This is NOT secure - use only for development/testing.
    """
    
    def __init__(self):
        self._registered = False
        self._user_id = None
    
    def generate_registration_options(self, user_id: bytes, 
                                     username: str) -> Dict[str, Any]:
        """Simulate registration options."""
        self._user_id = user_id
        return {
            "publicKey": {"challenge": os.urandom(32).hex()},
            "challenge": "simulated"
        }
    
    def complete_registration(self, credential_response: Dict) -> bool:
        """Simulate successful registration."""
        self._registered = True
        return True
    
    def generate_authentication_options(self) -> Dict[str, Any]:
        """Simulate authentication options."""
        return {
            "publicKey": {"challenge": os.urandom(32).hex()},
            "challenge": "simulated"
        }
    
    def complete_authentication(self, credential_response: Dict) -> Optional[bytes]:
        """Simulate successful authentication."""
        if self._registered:
            return self._user_id
        return None


def create_fido2_authenticator(simulate: bool = False) -> Any:
    """
    Create a FIDO2 authenticator.
    
    Args:
        simulate: If True, use simulated (insecure) authenticator
    
    Returns:
        FIDO2Authenticator or SimulatedFIDO2 instance
    """
    if simulate:
        print("WARNING: Using simulated FIDO2 (NOT SECURE)")
        return SimulatedFIDO2()
    
    if not HAS_FIDO2:
        print("fido2 not available, using simulation")
        return SimulatedFIDO2()
    
    return FIDO2Authenticator()


if __name__ == "__main__":
    print("FIDO2/WebAuthn Hardware Touch Interface")
    print("=" * 60)
    
    # Check for fido2 library
    if not HAS_FIDO2:
        print("\nWARNING: fido2 library not installed")
        print("Install with: pip install fido2")
        print("\nRunning in simulation mode (NOT SECURE)")
    
    # Create authenticator
    auth = create_fido2_authenticator(simulate=not HAS_FIDO2)
    
    # Generate user ID
    user_id = os.urandom(32)
    username = "zero-trust-user"
    
    print("\n1. Registration Phase")
    print("   Touch your FIDO2 device to register...")
    
    options = auth.generate_registration_options(user_id, username)
    print(f"   Challenge: {options['publicKey']['challenge'][:32]}...")
    
    # Simulate device response (in real use, this comes from the device)
    simulated_response = {"challenge": options['publicKey']['challenge']}
    success = auth.complete_registration(simulated_response)
    print(f"   Registration: {'SUCCESS' if success else 'FAILED'}")
    
    print("\n2. Authentication Phase")
    print("   Touch your FIDO2 device to authenticate...")
    
    options = auth.generate_authentication_options()
    print(f"   Challenge: {options['publicKey']['challenge'][:32]}...")
    
    # Simulate device response
    simulated_response = {"challenge": options['publicKey']['challenge']}
    user_id = auth.complete_authentication(simulated_response)
    
    if user_id:
        print(f"   Authentication: SUCCESS")
        print(f"   User ID: {user_id.hex()[:32]}...")
    else:
        print(f"   Authentication: FAILED")
    
    print("\n" + "=" * 60)
    print("FIDO2 test complete.")
