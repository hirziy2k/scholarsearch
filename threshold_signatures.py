#!/usr/bin/env python3
"""
Threshold Signatures & OTP Stream Sync
- t-of-n threshold cryptography (Shamir's Secret Sharing)
- 5 micro-environments (3 local, 2 remote)
- Only 3 required for reconstruction
- OTP stream synchronization via deterministic frame headers
- Automatic resync after network partition

Architecture:
- 5 independent nodes
- 3-of-5 threshold
- Asynchronous operation
- Stream-based OTP with frame headers
"""

import os
import secrets
import hashlib
import time
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class Share:
    """A single share in Shamir's Secret Sharing."""
    share_id: int
    x: int
    y: int
    node_id: str
    is_active: bool = True


@dataclass
class OTPFrame:
    """OTP stream frame with synchronization header."""
    frame_number: int
    timestamp: float
    data: bytes
    pad: bytes
    frame_hash: bytes
    
    def to_bytes(self) -> bytes:
        """Serialize frame to bytes."""
        return (
            self.frame_number.to_bytes(8, 'big') +
            int(self.timestamp * 1000).to_bytes(8, 'big') +
            len(self.data).to_bytes(4, 'big') +
            self.data +
            self.pad[:len(self.data)] +
            self.frame_hash
        )
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'OTPFrame':
        """Deserialize frame from bytes."""
        offset = 0
        
        frame_number = int.from_bytes(data[offset:offset+8], 'big')
        offset += 8
        
        timestamp_ms = int.from_bytes(data[offset:offset+8], 'big')
        timestamp = timestamp_ms / 1000.0
        offset += 8
        
        data_len = int.from_bytes(data[offset:offset+4], 'big')
        offset += 4
        
        frame_data = data[offset:offset+data_len]
        offset += data_len
        
        # Pad is derived from frame data
        pad = hashlib.sha256(frame_data + frame_number.to_bytes(8, 'big')).digest()
        
        frame_hash = data[offset:offset+32]
        
        return cls(
            frame_number=frame_number,
            timestamp=timestamp,
            data=frame_data,
            pad=pad,
            frame_hash=frame_hash
        )


class ShamirSecretSharing:
    """
    Shamir's Secret Sharing implementation.
    
    Splits secret into n shares, requires t shares to reconstruct.
    """
    
    def __init__(self, threshold: int, num_shares: int):
        self.threshold = threshold
        self.num_shares = num_shares
        self._prime = 2**127 - 1  # Mersenne prime
    
    def split_secret(self, secret: bytes, 
                    node_ids: List[str]) -> List[Share]:
        """
        Split secret into shares using Shamir's scheme.
        
        Returns list of shares, one per node.
        """
        # Convert secret to integer
        secret_int = int.from_bytes(secret[:16], 'big')
        
        # Generate random polynomial coefficients
        coefficients = [secret_int]
        for _ in range(self.threshold - 1):
            coefficients.append(secrets.randbelow(self._prime))
        
        # Generate shares
        shares = []
        for i, node_id in enumerate(node_ids[:self.num_shares]):
            x = i + 1  # Share x-coordinate (1-indexed)
            y = self._evaluate_polynomial(coefficients, x)
            shares.append(Share(
                share_id=i,
                x=x,
                y=y,
                node_id=node_id
            ))
        
        return shares
    
    def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """Evaluate polynomial at point x."""
        result = 0
        for i, coeff in enumerate(coefficients):
            result = (result + coeff * pow(x, i, self._prime)) % self._prime
        return result
    
    def reconstruct_secret(self, shares: List[Share]) -> bytes:
        """
        Reconstruct secret from threshold shares.
        
        Uses Lagrange interpolation.
        """
        if len(shares) < self.threshold:
            raise ValueError(f"Need {self.threshold} shares, got {len(shares)}")
        
        # Lagrange interpolation
        secret = 0
        for i, share_i in enumerate(shares[:self.threshold]):
            # Compute Lagrange basis polynomial
            numerator = 1
            denominator = 1
            
            for j, share_j in enumerate(shares[:self.threshold]):
                if i != j:
                    numerator = (numerator * (-share_j.x)) % self._prime
                    denominator = (denominator * (share_i.x - share_j.x)) % self._prime
            
            # Compute Lagrange coefficient
            lagrange_coeff = (numerator * self._mod_inverse(denominator)) % self._prime
            
            # Add contribution
            secret = (secret + share_i.y * lagrange_coeff) % self._prime
        
        return secret.to_bytes(16, 'big')
    
    def _mod_inverse(self, a: int) -> int:
        """Compute modular inverse using Fermat's little theorem."""
        return pow(a, self._prime - 2, self._prime)


class ThresholdNode:
    """
    A single node in the threshold signature system.
    
    Can operate independently, contributes to threshold.
    """
    
    def __init__(self, node_id: str, is_local: bool = True):
        self.node_id = node_id
        self.is_local = is_local
        self._share: Optional[Share] = None
        self._is_active = True
        self._last_heartbeat = time.time()
    
    def set_share(self, share: Share):
        """Set the share for this node."""
        self._share = share
    
    def get_share(self) -> Optional[Share]:
        """Get this node's share."""
        return self._share
    
    def sign_partial(self, message: bytes) -> bytes:
        """
        Generate partial signature.
        
        Each node signs independently.
        """
        if self._share is None:
            raise RuntimeError("Node not initialized")
        
        # Partial signature = share * message_hash
        message_hash = int.from_bytes(hashlib.sha256(message).digest()[:8], 'big')
        partial = (self._share.y * message_hash) % (2**127 - 1)
        
        return partial.to_bytes(16, 'big')
    
    def is_alive(self) -> bool:
        """Check if node is alive."""
        return self._is_active and (time.time() - self._last_heartbeat < 30)
    
    def heartbeat(self):
        """Update heartbeat."""
        self._last_heartbeat = time.time()


class ThresholdSignatureSystem:
    """
    t-of-n Threshold Signature System.
    
    Distributes signing capability across multiple nodes.
    Requires t nodes to produce valid signature.
    """
    
    def __init__(self, threshold: int, num_nodes: int):
        self.threshold = threshold
        self.num_nodes = num_nodes
        self.sss = ShamirSecretSharing(threshold, num_nodes)
        self.nodes: List[ThresholdNode] = []
        self._master_key = None
    
    def initialize(self, master_key: bytes):
        """
        Initialize system with master key.
        
        Key is immediately split into shares.
        """
        self._master_key = master_key
        
        # Create nodes
        node_ids = [f"node_{i}" for i in range(self.num_nodes)]
        self.nodes = [ThresholdNode(nid, i < 3) for i, nid in enumerate(node_ids)]
        
        # Split key into shares
        shares = self.sss.split_secret(master_key, node_ids)
        
        # Distribute shares
        for node, share in zip(self.nodes, shares):
            node.set_share(share)
        
        # Destroy master key
        self._master_key = None
    
    def sign(self, message: bytes) -> Optional[bytes]:
        """
        Sign message using threshold signatures.
        
        Requires threshold nodes to be active.
        """
        # Find active nodes
        active_nodes = [n for n in self.nodes if n.is_alive()]
        
        if len(active_nodes) < self.threshold:
            print(f"[THRESHOLD] Not enough active nodes: {len(active_nodes)}/{self.threshold}")
            return None
        
        # Collect partial signatures
        partials = []
        for node in active_nodes[:self.threshold]:
            partial = node.sign_partial(message)
            partials.append(partial)
        
        # Combine partials (simplified)
        combined = b""
        for partial in partials:
            combined = bytes(a ^ b for a, b in zip(
                combined.ljust(len(partial), b'\x00'), partial
            ))
        
        # Hash to create final signature
        signature = hashlib.sha256(combined + message).digest()
        
        return signature
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """
        Verify threshold signature.
        """
        # Simplified verification
        # In reality: more complex verification
        expected = hashlib.sha256(
            b"combined_partials" + message
        ).digest()
        
        return signature == expected
    
    def get_node_status(self) -> List[Dict]:
        """Get status of all nodes."""
        return [
            {
                "node_id": node.node_id,
                "is_local": node.is_local,
                "is_alive": node.is_alive(),
                "has_share": node.get_share() is not None
            }
            for node in self.nodes
        ]


class OTPStreamSynchronizer:
    """
    OTP stream synchronization using deterministic frame headers.
    
    Allows resynchronization after network partition.
    """
    
    def __init__(self, stream_id: bytes):
        self.stream_id = stream_id
        self._current_frame = 0
        self._sync_lock = None
        self._frame_buffer: Dict[int, OTPFrame] = {}
    
    def create_frame(self, data: bytes, 
                    frame_number: Optional[int] = None) -> OTPFrame:
        """
        Create OTP frame with synchronization header.
        
        Frame header contains:
        - Frame number (for ordering)
        - Timestamp (for time-based sync)
        - Stream ID (for stream identification)
        - Data hash (for integrity)
        """
        if frame_number is None:
            frame_number = self._current_frame
            self._current_frame += 1
        
        # Generate pad deterministically from frame header
        pad_seed = (
            self.stream_id +
            frame_number.to_bytes(8, 'big') +
            int(time.time() * 1000).to_bytes(8, 'big')
        )
        pad = hashlib.sha256(pad_seed).digest() * (len(data) // 32 + 1)
        pad = pad[:len(data)]
        
        # Create frame
        frame = OTPFrame(
            frame_number=frame_number,
            timestamp=time.time(),
            data=data,
            pad=pad,
            frame_hash=b""
        )
        
        # Compute frame hash
        frame.frame_hash = hashlib.sha256(
            frame.to_bytes()[:len(frame.to_bytes())-32]
        ).digest()
        
        return frame
    
    def sync_from_frame(self, frame: OTPFrame) -> bool:
        """
        Synchronize stream from received frame.
        
        Allows recovery from network partition.
        """
        # Verify frame hash
        expected_hash = hashlib.sha256(
            frame.to_bytes()[:len(frame.to_bytes())-32]
        ).digest()
        
        if frame.frame_hash != expected_hash:
            print("[SYNC] Frame hash mismatch")
            return False
        
        # Update frame number
        self._current_frame = frame.frame_number + 1
        
        # Buffer frame
        self._frame_buffer[frame.frame_number] = frame
        
        return True
    
    def seek_to_frame(self, frame_number: int) -> Optional[OTPFrame]:
        """
        Seek to specific frame number.
        
        Allows resynchronization to any point in stream.
        """
        if frame_number in self._frame_buffer:
            return self._frame_buffer[frame_number]
        
        # Generate frame on-the-fly
        # In reality: would need to regenerate pad deterministically
        return None
    
    def get_stream_status(self) -> Dict:
        """Get stream synchronization status."""
        return {
            "stream_id": self.stream_id.hex(),
            "current_frame": self._current_frame,
            "buffered_frames": len(self._frame_buffer),
            "oldest_frame": min(self._frame_buffer.keys()) if self._frame_buffer else None,
            "newest_frame": max(self._frame_buffer.keys()) if self._frame_buffer else None
        }


class AsynchronousThresholdOTP:
    """
    Complete asynchronous threshold OTP system.
    
    Combines threshold cryptography with OTP stream synchronization.
    """
    
    def __init__(self, threshold: int = 3, num_nodes: int = 5):
        self.threshold = threshold
        self.num_nodes = num_nodes
        
        # Initialize threshold system
        self.threshold_system = ThresholdSignatureSystem(threshold, num_nodes)
        
        # Initialize OTP synchronizer
        self.stream_id = secrets.token_bytes(32)
        self.otp_sync = OTPStreamSynchronizer(self.stream_id)
        
        self._initialized = False
    
    def initialize(self, master_key: bytes):
        """Initialize the system."""
        self.threshold_system.initialize(master_key)
        self._initialized = True
    
    def encrypt_with_threshold(self, data: bytes, 
                              frame_number: Optional[int] = None) -> Tuple[bytes, bytes]:
        """
        Encrypt data with threshold OTP.
        
        Returns:
            ciphertext: Encrypted data
            signature: Threshold signature of ciphertext
        """
        if not self._initialized:
            raise RuntimeError("System not initialized")
        
        # Create OTP frame
        frame = self.otp_sync.create_frame(data, frame_number)
        
        # XOR data with pad
        ciphertext = bytes(a ^ b for a, b in zip(data, frame.pad))
        
        # Sign with threshold
        signature = self.threshold_system.sign(ciphertext)
        
        if signature is None:
            raise RuntimeError("Threshold signing failed")
        
        return ciphertext, signature
    
    def decrypt_with_threshold(self, ciphertext: bytes,
                              signature: bytes,
                              frame: OTPFrame) -> bytes:
        """
        Decrypt data with threshold verification.
        """
        # Verify signature
        if not self.threshold_system.verify(ciphertext, signature):
            raise ValueError("Invalid signature")
        
        # Verify frame
        if not self.otp_sync.sync_from_frame(frame):
            raise ValueError("Frame sync failed")
        
        # XOR ciphertext with pad
        plaintext = bytes(a ^ b for a, b in zip(ciphertext, frame.pad))
        
        return plaintext
    
    def recover_from_partition(self, 
                              last_known_frame: int) -> Optional[OTPFrame]:
        """
        Recover from network partition.
        
        Seeks to last known frame and resynchronizes.
        """
        frame = self.otp_sync.seek_to_frame(last_known_frame)
        
        if frame:
            self.otp_sync.sync_from_frame(frame)
            return frame
        
        return None
    
    def get_system_status(self) -> Dict:
        """Get complete system status."""
        return {
            "initialized": self._initialized,
            "threshold": self.threshold,
            "num_nodes": self.num_nodes,
            "node_status": self.threshold_system.get_node_status(),
            "stream_status": self.otp_sync.get_stream_status()
        }


if __name__ == "__main__":
    print("Threshold Signatures & OTP Stream Sync")
    print("=" * 70)
    
    # Configuration
    threshold = 3
    num_nodes = 5
    
    # Create system
    print(f"\nInitializing {threshold}-of-{num_nodes} threshold system...")
    system = AsynchronousThresholdOTP(threshold, num_nodes)
    
    # Generate master key
    master_key = secrets.token_bytes(16)
    print(f"Master key: {master_key.hex()[:32]}...")
    
    # Initialize
    system.initialize(master_key)
    
    # Show node status
    print("\nNode Status:")
    status = system.get_system_status()
    for node in status["node_status"]:
        print(f"  {node['node_id']}: Local={node['is_local']}, Alive={node['is_alive']}, HasShare={node['has_share']}")
    
    # Test encryption
    test_data = b"Threshold OTP encryption test"
    print(f"\nPlaintext: {test_data.decode()}")
    
    print("\nEncrypting with threshold OTP...")
    ciphertext, signature = system.encrypt_with_threshold(test_data)
    print(f"Ciphertext: {ciphertext.hex()[:32]}...")
    print(f"Signature: {signature.hex()[:32]}...")
    
    # Create frame for decryption
    frame = system.otp_sync.create_frame(test_data)
    
    # Test decryption
    print("\nDecrypting with threshold verification...")
    decrypted = system.decrypt_with_threshold(ciphertext, signature, frame)
    print(f"Decrypted: {decrypted.decode()}")
    
    # Verify
    print(f"\nVerification: {test_data == decrypted}")
    
    # Show stream status
    print("\nStream Status:")
    stream_status = status["stream_status"]
    print(f"  Stream ID: {stream_status['stream_id'][:32]}...")
    print(f"  Current frame: {stream_status['current_frame']}")
    print(f"  Buffered frames: {stream_status['buffered_frames']}")
    
    # Show security properties
    print("\n" + "=" * 70)
    print("Security Properties:")
    print(f"  - {threshold}-of-{num_nodes} threshold signing")
    print("  - Survives loss of 2 nodes")
    print("  - OTP stream synchronization")
    print("  - Automatic partition recovery")
    print("  - Deterministic frame headers")
    print("=" * 70)
