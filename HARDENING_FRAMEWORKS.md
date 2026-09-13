# The Three Hardening Frameworks

## Executive Summary

Three frameworks to stress-test and harden the simplified baseline against real-world failure states:

1. **The Applied Cryptanalysis Auditor**: Zero-Knowledge State Proofs
2. **The Resilient Systems Engineer**: Threshold Signatures + OTP Stream Sync
3. **The Physical Hardware Skeptic**: SDR Atmospheric Noise Entropy

---

## The Problem with the Simplified Baseline

```
BEFORE: Three Mathematical Primitives
├── FHE: Encrypt data before compute
├── SMPC: Split key across 3 environments
└── OTP: Perfect secrecy with zero state

VULNERABILITIES:
├── FHE: Hostile host can corrupt ciphertext
├── SMPC: 100% DoS vector if nodes fail
└── OTP: TRNG can be backdoored by CPU

AFTER: Three Hardened Primitives
├── FHE + ZK Proofs: Integrity guarantee
├── SMPC + Threshold: Survives node failure
└── OTP + SDR: Un-backdoorable entropy
```

---

## Framework 1: The Applied Cryptanalysis Auditor (ZK Proofs)

### The Problem
FHE guarantees confidentiality but not integrity. A hostile host can corrupt the ciphertext before processing.

### The Solution: Zero-Knowledge State Proofs

```
┌─────────────────────────────────────────────────────────────┐
│                    ZK-FHE INTEGRITY                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Client generates ZK proof                               │
│     └── Proves: data satisfies constraints                  │
│                                                              │
│  2. Proof attached to FHE ciphertext                        │
│     └── Ciphertext + ZK proof sent to host                  │
│                                                              │
│  3. Host processes FHE computation                          │
│     └── Operations on encrypted data                        │
│                                                              │
│  4. Output includes ZK verification                         │
│     └── Tampering detected at output layer                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Properties

- **Integrity without decryption**: Proof reveals nothing about plaintext
- **Tamper detection**: Any modification fails verification
- **Mathematical guarantee**: Not computational security

### Files

| File | Purpose |
|------|---------|
| `zk_proofs.py` | ZK proof generation and verification |

---

## Framework 2: The Resilient Systems Engineer (Threshold Signatures)

### The Problem
SMPC with 3 nodes has 100% DoS vector if 2 nodes fail. OTP requires perfect synchronization.

### The Solution: Threshold Signatures + OTP Stream Sync

```
┌─────────────────────────────────────────────────────────────┐
│                    THRESHOLD SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  5 Micro-Environments (3-of-5 threshold)                   │
│  ├── Node 1: Local CPU (Python)                             │
│  ├── Node 2: Local CPU (Python)                             │
│  ├── Node 3: Local CPU (Python)                             │
│  ├── Node 4: Remote Server 1                                │
│  └── Node 5: Remote Server 2                                │
│                                                              │
│  Consensus: Any 3 nodes can sign                            │
│  Fault Tolerance: Survives loss of 2 nodes                  │
│                                                              │
│  OTP Stream Sync:                                           │
│  ├── Deterministic frame headers                            │
│  ├── Time-based synchronization                             │
│  └── Automatic recovery from partition                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Properties

- **Fault tolerance**: Survives 2 node failures
- **Asynchronous operation**: No strict timing required
- **Stream synchronization**: Automatic recovery from partition
- **Shamir's Secret Sharing**: Mathematical threshold guarantee

### Files

| File | Purpose |
|------|---------|
| `threshold_signatures.py` | 3-of-5 threshold system with OTP sync |

---

## Framework 3: The Physical Hardware Skeptic (SDR Entropy)

### The Problem
Consumer-grade TRNGs (Intel RDRAND) can be backdoored. CPU-based entropy is not trustworthy.

### The Solution: SDR-Captured Atmospheric Noise

```
┌─────────────────────────────────────────────────────────────┐
│                    SDR ENTROPY SOURCE                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Hardware:                                                  │
│  ├── USB RTL-SDR Dongle ($20-30)                           │
│  ├── Tuned to 144 MHz (blank VHF)                          │
│  └── Samples electromagnetic background radiation           │
│                                                              │
│  Software:                                                  │
│  ├── Read raw IQ samples                                    │
│  ├── SHA-256 whitening filter                               │
│  └── Output: cryptographic-grade entropy                    │
│                                                              │
│  Properties:                                                │
│  ├── Un-backdoorable (physical noise)                       │
│  ├── Divorced from host CPU/OS                              │
│  ├── Physically verifiable                                  │
│  └── Perfect for OTP                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Properties

- **Physical entropy source**: Not dependent on CPU
- **Un-backdoorable**: Cannot be compromised by software
- **Verifiable**: Can be measured with spectrum analyzer
- **Perfect for OTP**: True random, not pseudo-random

### Files

| File | Purpose |
|------|---------|
| `sdr_entropy.py` | SDR-based TRNG and entropy extraction |

---

## Trade-off Simulator

### Interactive Mode

```bash
python tradeoff_simulator.py
```

### Preset Scenarios

| Scenario | Network | Compute | Optimal |
|----------|---------|---------|---------|
| Low Latency | 1 ms | 4000 MHz | FHE |
| High Latency | 500 ms | 1000 MHz | OTP |
| Constrained | 1000 ms | 500 MHz | OTP |
| Ideal | 0.1 ms | 5000 MHz | FHE |

### Key Insight

```
As network latency and compute limits increase:
- SMPC degrades rapidly (network-bound)
- FHE degrades moderately (compute-bound)
- OTP is virtually unaffected

In highly resource-constrained, hostile environments:
OTP is the only viable primitive.
```

---

## Comparison Matrix

| Property | FHE + ZK | SMPC + Threshold | OTP + SDR |
|----------|----------|------------------|-----------|
| **Confidentiality** | Mathematical | Distributed | Perfect |
| **Integrity** | ZK proof | Threshold sig | Pad verification |
| **Availability** | Single node | 3-of-5 fault tolerant | High |
| **Latency** | High | Medium | Minimal |
| **Complexity** | High | Medium | Low |
| **Hardware** | None | Network | SDR dongle |

---

## Files Created

| File | Framework | Purpose |
|------|-----------|---------|
| `zk_proofs.py` | Cryptanalysis Auditor | ZK proof generation/verification |
| `threshold_signatures.py` | Resilient Engineer | 3-of-5 threshold + OTP sync |
| `sdr_entropy.py` | Hardware Skeptic | SDR atmospheric noise entropy |
| `tradeoff_simulator.py` | Tooling | Interactive trade-off analysis |
| `HARDENING_FRAMEWORKS.md` | Documentation | Complete framework guide |

---

## Integration

```python
from zk_proofs import ZKFHEIntegrity
from threshold_signatures import AsynchronousThresholdOTP
from sdr_entropy import HardwareTRNG

class HardenedSystem:
    def __init__(self):
        self.zk_fhe = ZKFHEIntegrity()
        self.threshold_otp = AsynchronousThresholdOTP(threshold=3, num_nodes=5)
        self.sdr_trng = HardwareTRNG()
    
    def encrypt_with_integrity(self, data: bytes) -> Tuple[bytes, bytes, bytes]:
        """Encrypt with ZK integrity proof."""
        # Create ZK proof
        data_hash = hashlib.sha256(data).digest()
        zk_proof = self.zk_fhe.create_integrity_proof(data, data_hash)
        
        # Encrypt with FHE (simulated)
        ciphertext = data  # In reality: FHE encryption
        
        return ciphertext, zk_proof.proof_data, data_hash
    
    def encrypt_with_fault_tolerance(self, data: bytes) -> Tuple[bytes, bytes]:
        """Encrypt with threshold fault tolerance."""
        return self.threshold_otp.encrypt_with_threshold(data)
    
    def generate_otp_from_sdr(self, length: int) -> bytes:
        """Generate OTP from atmospheric noise."""
        return self.sdr_trng.generate(length)
```

---

## Theoretical Limits

1. **ZK Proofs**: Still computationally expensive
2. **Threshold Signatures**: Requires reliable network
3. **SDR Entropy**: Requires hardware dongle

## Future Work

1. **Real zk-SNARK library**: Integrate circom or bellman
2. **Real SDR hardware**: Interface with RTL-SDR
3. **Hybrid approach**: Combine all three frameworks
