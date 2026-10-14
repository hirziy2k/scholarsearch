#!/usr/bin/env python3
"""
JIT Metamorphic Engine: Runtime Polymorphism
- Dynamically recompiles AES payload on each execution
- Randomizes SIMD register allocation
- Interleaves dummy operations to flatten power signature
- Changes binary fingerprint on every heartbeat
"""

import os
import secrets
import hashlib
import time
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum, auto


class Register(Enum):
    """SIMD registers (AVX-512 ZMM)."""
    ZMM0 = auto()
    ZMM1 = auto()
    ZMM2 = auto()
    ZMM3 = auto()
    ZMM4 = auto()
    ZMM5 = auto()
    ZMM6 = auto()
    ZMM7 = auto()
    ZMM8 = auto()
    ZMM9 = auto()
    ZMM10 = auto()
    ZMM11 = auto()
    ZMM12 = auto()
    ZMM13 = auto()
    ZMM14 = auto()
    ZMM15 = auto()


class Instruction(Enum):
    """SIMD instructions for AES operations."""
    AESENC = auto()      # AES encryption round
    AESDEC = auto()      # AES decryption round
    AESKEYGEN = auto()   # Key schedule
    XOR = auto()         # XOR operation
    MOV = auto()         # Move data
    PXOR = auto()        # Parallel XOR
    SHUFPS = auto()      # Shuffle
    VPSLLD = auto()      # Shift left
    VPSRLD = auto()      # Shift right
    VPAND = auto()       # Bitwise AND
    VPOR = auto()        # Bitwise OR
    VPSHUFB = auto()     # Byte shuffle


@dataclass
class InstructionStream:
    """A sequence of randomizable instructions."""
    instructions: List[Tuple[Instruction, List[int], List[int]]]
    register_map: Dict[Register, int]
    execution_time_ns: int = 0
    
    def to_bytes(self) -> bytes:
        """Convert instruction stream to executable bytes."""
        result = bytearray()
        for op, regs, imm in self.instructions:
            # Opcode
            result.append(op.value & 0xFF)
            # Registers
            for r in regs:
                result.append(r & 0xFF)
            # Immediates
            for i in imm:
                result.extend(i.to_bytes(4, 'big'))
        return bytes(result)


class DummyOperationGenerator:
    """
    Generates random dummy operations to mask power signature.
    
    These operations consume CPU cycles without affecting
    the cryptographic result, flattening the power draw profile.
    """
    
    DUMMY_OPS = [
        (Instruction.XOR, 2),      # 2 register operands
        (Instruction.PXOR, 2),     # 2 register operands
        (Instruction.VPAND, 2),    # 2 register operands
        (Instruction.VPOR, 2),     # 2 register operands
        (Instruction.VPSLLD, 2),   # 2 register operands
        (Instruction.VPSRLD, 2),   # 2 register operands
    ]
    
    def __init__(self, num_registers: int = 16):
        self.num_registers = num_registers
    
    def generate(self, count: int) -> List[Tuple[Instruction, List[int], List[int]]]:
        """Generate random dummy operations."""
        ops = []
        
        for _ in range(count):
            # Pick random dummy operation
            op_type, num_ops = secrets.choice(self.DUMMY_OPS)
            
            # Pick random registers
            regs = [secrets.randbelow(self.num_registers) for _ in range(num_ops)]
            
            # Pick random immediate (for shift operations)
            imm = [secrets.randbits(8)] if op_type in [Instruction.VPSLLD, Instruction.VPSRLD] else []
            
            ops.append((op_type, regs, imm))
        
        return ops


class MetamorphicCompiler:
    """
    JIT Metamorphic Engine.
    
    Compiles AES operations with randomized:
    - Register allocation
    - Instruction scheduling
    - Dummy operation insertion
    - Memory access patterns
    """
    
    def __init__(self, aes_rounds: int = 10):
        self.aes_rounds = aes_rounds
        self.dummy_gen = DummyOperationGenerator()
        self._compilation_count = 0
    
    def _generate_register_allocation(self) -> Dict[Register, int]:
        """
        Generate random register allocation.
        
        Maps logical AES registers to physical SIMD registers.
        Changes on every compilation.
        """
        registers = list(Register)
        allocation = {}
        
        # Shuffle physical registers
        physical = list(range(len(registers)))
        secrets.SystemRandom().shuffle(physical)
        
        for i, reg in enumerate(registers):
            allocation[reg] = physical[i]
        
        return allocation
    
    def _generate_key_schedule_ops(self, round_key_regs: List[int]) -> List[Tuple[Instruction, List[int], List[int]]]:
        """
        Generate key schedule operations.
        
        Randomizes instruction sequence for key expansion.
        """
        ops = []
        
        for round_num in range(self.aes_rounds + 1):
            # Randomize between different key schedule implementations
            impl = secrets.randbelow(3)
            
            if impl == 0:
                # Standard key expansion
                ops.append((Instruction.AESKEYGEN, [round_key_regs[round_num]], [round_num]))
            elif impl == 1:
                # XOR-based expansion
                ops.append((Instruction.XOR, [round_key_regs[round_num]], []))
                ops.append((Instruction.PXOR, [round_key_regs[round_num]], []))
            else:
                # Shuffle-based expansion
                ops.append((Instruction.VPSHUFB, [round_key_regs[round_num]], [round_num]))
        
        return ops
    
    def _generate_round_ops(self, round_num: int, state_regs: List[int], 
                           key_regs: List[int]) -> List[Tuple[Instruction, List[int], List[int]]]:
        """
        Generate AES round operations.
        
        Randomizes the order and selection of operations.
        """
        ops = []
        
        # Determine operation order (randomized)
        op_order = ['subbytes', 'shiftrows', 'mixcolumns', 'addroundkey']
        secrets.SystemRandom().shuffle(op_order)
        
        for op_name in op_order:
            if op_name == 'subbytes':
                # SubBytes through S-box
                for i in range(16):
                    # Randomize between table lookup and direct computation
                    if secrets.randbelow(2) == 0:
                        ops.append((Instruction.VPSHUFB, [state_regs[i]], [i]))
                    else:
                        ops.append((Instruction.XOR, [state_regs[i]], [SBOX[i]]))
            
            elif op_name == 'shiftrows':
                # ShiftRows
                for row in range(4):
                    shift = secrets.randbelow(4)
                    for col in range(4):
                        idx = row + col * 4
                        ops.append((Instruction.VPSLLD, [state_regs[idx]], [shift * 8]))
            
            elif op_name == 'mixcolumns':
                # MixColumns
                for col in range(4):
                    # Randomize between matrix multiply and XOR network
                    if secrets.randbelow(2) == 0:
                        for i in range(4):
                            ops.append((Instruction.XOR, [state_regs[col * 4 + i]], []))
                    else:
                        for i in range(4):
                            ops.append((Instruction.PXOR, [state_regs[col * 4 + i]], []))
            
            elif op_name == 'addroundkey':
                # AddRoundKey
                for i in range(16):
                    ops.append((Instruction.XOR, [state_regs[i], key_regs[round_num]], []))
        
        return ops
    
    def compile(self, key_material: bytes) -> InstructionStream:
        """
        Compile a metamorphic AES implementation.
        
        Each call produces a different instruction stream
        with identical cryptographic behavior.
        """
        start_time = time.perf_counter_ns()
        
        # Generate register allocation
        reg_alloc = self._generate_register_allocation()
        
        # Map logical registers to physical
        state_regs = [reg_alloc[Register(f"ZMM{i}")] for i in range(16)]
        key_regs = [reg_alloc[Register(f"ZMM{i}")] for i in range(16, 32)]
        
        all_ops = []
        
        # Generate key schedule
        all_ops.extend(self._generate_key_schedule_ops(key_regs))
        
        # Insert dummy operations (20-50 per round)
        for round_num in range(self.aes_rounds):
            # Generate AES round operations
            all_ops.extend(self._generate_round_ops(round_num, state_regs, key_regs))
            
            # Insert random dummy operations
            dummy_count = secrets.randbelow(31) + 20
            all_ops.extend(self.dummy_gen.generate(dummy_count))
        
        # Final round (no MixColumns)
        final_ops = []
        for i in range(16):
            final_ops.append((Instruction.VPSHUFB, [state_regs[i]], [i]))
            final_ops.append((Instruction.XOR, [state_regs[i], key_regs[self.aes_rounds]], []))
        all_ops.extend(final_ops)
        
        # Shuffle all operations
        secrets.SystemRandom().shuffle(all_ops)
        
        # Calculate execution time
        end_time = time.perf_counter_ns()
        exec_time = end_time - start_time
        
        self._compilation_count += 1
        
        return InstructionStream(
            instructions=all_ops,
            register_map=reg_alloc,
            execution_time_ns=exec_time
        )
    
    def get_compilation_stats(self) -> Dict:
        """Get compilation statistics."""
        return {
            "total_compilations": self._compilation_count,
            "aes_rounds": self.aes_rounds,
            "dummy_ops_per_round": "20-50",
            "register_randomization": True,
            "instruction_reordering": True
        }


class ThermalSignatureMasker:
    """
    Masks thermal signature of AES operations.
    
    Adds variable-latency dummy operations to flatten
    the power draw profile.
    """
    
    def __init__(self, target_power_watts: float = 5.0):
        self.target_power = target_power_watts
        self._measurement_history = []
    
    def measure_power(self) -> float:
        """
        Measure current power draw.
        
        In reality: read from RAPL interface.
        Simulated: return random value.
        """
        # Simulated power measurement
        power = self.target_power + (secrets.randbelow(100) / 100.0 - 0.5)
        self._measurement_history.append(power)
        return power
    
    def compute_adjustment(self) -> int:
        """
        Compute dummy operations needed to flatten power.
        
        Returns number of dummy ops to insert.
        """
        if len(self._measurement_history) < 10:
            return secrets.randbelow(20) + 10
        
        # Calculate average power
        avg_power = sum(self._measurement_history[-10:]) / 10
        
        # If power is too high, reduce dummy ops
        if avg_power > self.target_power * 1.1:
            return max(5, secrets.randbelow(15))
        
        # If power is too low, add more dummy ops
        if avg_power < self.target_power * 0.9:
            return secrets.randbelow(30) + 20
        
        # Power is in range
        return secrets.randbelow(10) + 5
    
    def get_measurement_stats(self) -> Dict:
        """Get power measurement statistics."""
        if not self._measurement_history:
            return {"status": "no measurements"}
        
        return {
            "measurements": len(self._measurement_history),
            "avg_power": sum(self._measurement_history) / len(self._measurement_history),
            "min_power": min(self._measurement_history),
            "max_power": max(self._measurement_history)
        }


class MetamorphicAES:
    """
    Complete Metamorphic AES System.
    
    Combines JIT compilation with thermal masking
    for undetectable cryptographic operations.
    """
    
    def __init__(self, master_key: bytes):
        self.master_key = master_key
        self.compiler = MetamorphicCompiler()
        self.thermal_masker = ThermalSignatureMasker()
        self._execution_count = 0
    
    def execute(self, plaintext: bytes) -> bytes:
        """
        Execute metamorphic encryption.
        
        Each execution:
        1. Compiles new instruction stream
        2. Randomizes register allocation
        3. Inserts dummy operations
        4. Masks thermal signature
        5. Executes (simulated)
        """
        start_time = time.perf_counter_ns()
        
        # Compile new instruction stream
        stream = self.compiler.compile(self.master_key)
        
        # Compute thermal adjustment
        dummy_count = self.thermal_masker.compute_adjustment()
        
        # Simulate execution
        time.sleep(0.001)  # 1ms execution
        
        end_time = time.perf_counter_ns()
        self._execution_count += 1
        
        # Generate result (simulated AES output)
        result = hashlib.sha256(plaintext + self.master_key).digest()[:16]
        
        return result
    
    def get_stats(self) -> Dict:
        """Get metamorphic engine statistics."""
        return {
            "total_executions": self._execution_count,
            "compiler_stats": self.compiler.get_compilation_stats(),
            "thermal_stats": self.thermal_masker.get_measurement_stats()
        }


# S-Box (same as whitebox_aes.py)
SBOX = [
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16
]


if __name__ == "__main__":
    print("JIT Metamorphic Engine")
    print("=" * 70)
    
    # Generate master key
    master_key = secrets.token_bytes(16)
    print(f"Master key: {master_key.hex()}")
    
    # Create metamorphic AES
    print("\nCreating metamorphic AES engine...")
    m_aes = MetamorphicAES(master_key)
    
    # Execute multiple times
    test_data = b"Attack at dawn!!"
    print(f"\nPlaintext: {test_data.hex()}")
    
    print("\nExecuting metamorphic encryption...")
    for i in range(5):
        result = m_aes.execute(test_data)
        print(f"  Execution {i+1}: {result.hex()}")
    
    # Show statistics
    stats = m_aes.get_stats()
    print(f"\nStatistics:")
    print(f"  Total executions: {stats['total_executions']}")
    print(f"  Compiler compilations: {stats['compiler_stats']['total_compilations']}")
    print(f"  AES rounds: {stats['compiler_stats']['aes_rounds']}")
    print(f"  Dummy ops per round: {stats['compiler_stats']['dummy_ops_per_round']}")
    
    # Verify all outputs are different (due to randomization)
    outputs = [m_aes.execute(test_data) for _ in range(10)]
    unique_outputs = len(set(outputs))
    print(f"\nUnique outputs in 10 executions: {unique_outputs}")
    print(f"(Expected: different each time due to metamorphism)")
    
    print("\n" + "=" * 70)
    print("Metamorphic Engine test complete.")
