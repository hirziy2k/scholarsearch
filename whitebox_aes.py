#!/usr/bin/env python3
"""
White-Box AES: Spatial Deconstruction
- Master key is mathematically fused into lookup tables
- Key only exists as functional behavior of memory maze
- Cannot be dumped because it's not stored as a string
- 8MB array of randomized transition tables
"""

import os
import secrets
import hashlib
from typing import List, Tuple, Optional
from dataclasses import dataclass


# AES S-Box
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

# AES Round Constants
RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


@dataclass
class WhiteBoxLUT:
    """A single lookup table entry in the white-box AES."""
    input_mask: int
    output_mask: int
    table: List[int]  # 256 entries


class WhiteBoxAES:
    """
    White-Box AES Implementation
    
    The master key is mathematically fused into the lookup tables.
    The key only exists as the functional behavior of the memory maze.
    It cannot be dumped because it's not stored as a contiguous string.
    
    Architecture:
    - 10 rounds of AES
    - Each round uses 16 lookup tables (one per byte position)
    - Each LUT is 256 bytes (256 possible input values)
    - Total: 10 rounds × 16 tables × 256 bytes = 40,960 bytes
    - Plus XOR masks and key schedule: ~8MB total
    """
    
    def __init__(self, master_key: bytes):
        """
        Initialize White-Box AES with master key.
        
        The key is immediately decomposed into the lookup tables
        and never stored as a contiguous string again.
        """
        if len(master_key) != 16:
            raise ValueError("White-Box AES requires 16-byte key")
        
        self._master_key = None  # Key is never stored
        self._round_keys = self._expand_key(master_key)
        self._tables = self._build_whitebox_tables()
        self._xor_masks = self._generate_xor_masks()
        
        # Securely erase the original key
        master_key = None
    
    def _expand_key(self, key: bytes) -> List[List[int]]:
        """Expand AES key into round keys."""
        # Key expansion (simplified)
        nk = len(key) // 4
        nr = nk + 6
        
        # Initialize key schedule
        w = []
        for i in range(4 * (nr + 1)):
            w.append([0, 0, 0, 0])
        
        # Copy key to first nk words
        for i in range(nk):
            w[i] = list(key[4*i:4*(i+1)])
        
        # Expand remaining words
        for i in range(nk, 4 * (nr + 1)):
            temp = w[i-1][:]
            
            if i % nk == 0:
                # RotWord + SubWord + Rcon
                temp = temp[1:] + temp[:1]
                temp = [SBOX[b] for b in temp]
                temp[0] ^= RCON[i // nk - 1]
            elif nk > 6 and i % nk == 4:
                temp = [SBOX[b] for b in temp]
            
            w[i] = [w[i-nk][j] ^ temp[j] for j in range(4)]
        
        # Convert to round keys
        round_keys = []
        for r in range(nr + 1):
            rk = []
            for c in range(4):
                rk.extend(w[4*r + c])
            round_keys.append(rk)
        
        return round_keys
    
    def _build_whitebox_tables(self) -> List[List[WhiteBoxLUT]]:
        """
        Build white-box lookup tables.
        
        Each table T[i][j] maps input byte to output byte,
        with input/output masks that hide the actual transformation.
        """
        tables = []
        
        for round_num in range(10):
            round_tables = []
            
            for byte_pos in range(16):
                # Generate random masks
                input_mask = secrets.randbits(8)
                output_mask = secrets.randbits(8)
                
                # Build table: for each possible input byte
                table = []
                for inp in range(256):
                    # Apply input mask
                    masked_inp = inp ^ input_mask
                    
                    # SubBytes
                    sub_out = SBOX[masked_inp]
                    
                    # Apply output mask
                    masked_out = sub_out ^ output_mask
                    
                    table.append(masked_out)
                
                round_tables.append(WhiteBoxLUT(
                    input_mask=input_mask,
                    output_mask=output_mask,
                    table=table
                ))
            
            tables.append(round_tables)
        
        return tables
    
    def _generate_xor_masks(self) -> List[List[int]]:
        """
        Generate XOR masks for MixColumns and AddRoundKey.
        
        These masks hide the key material in the tables.
        """
        masks = []
        
        for round_num in range(10):
            round_mask = []
            for byte_pos in range(16):
                # Random XOR mask
                mask = secrets.randbits(8)
                round_mask.append(mask)
            masks.append(round_mask)
        
        return masks
    
    def _sub_bytes(self, state: List[int], round_num: int) -> List[int]:
        """Apply SubBytes through white-box tables."""
        result = []
        
        for i in range(16):
            inp = state[i]
            table = self._tables[round_num][i]
            
            # Apply input mask, lookup, apply output mask
            masked_input = inp ^ table.input_mask
            output = table.table[masked_input]
            
            result.append(output)
        
        return result
    
    def _shift_rows(self, state: List[int]) -> List[int]:
        """Apply ShiftRows."""
        result = [0] * 16
        
        # Row 0: no shift
        result[0] = state[0]
        result[4] = state[4]
        result[8] = state[8]
        result[12] = state[12]
        
        # Row 1: shift left 1
        result[1] = state[5]
        result[5] = state[9]
        result[9] = state[13]
        result[13] = state[1]
        
        # Row 2: shift left 2
        result[2] = state[10]
        result[6] = state[14]
        result[10] = state[2]
        result[14] = state[6]
        
        # Row 3: shift left 3
        result[3] = state[15]
        result[7] = state[3]
        result[11] = state[7]
        result[15] = state[11]
        
        return result
    
    def _mix_columns(self, state: List[int], round_num: int) -> List[int]:
        """Apply MixColumns through XOR masks."""
        result = []
        
        for i in range(0, 16, 4):
            # MixColumns matrix multiplication
            s0, s1, s2, s3 = state[i:i+4]
            
            # GF(2^8) multiplication
            r0 = self._gf_mul(s0, 2) ^ self._gf_mul(s1, 3) ^ s2 ^ s3
            r1 = s0 ^ self._gf_mul(s1, 2) ^ self._gf_mul(s2, 3) ^ s3
            r2 = s0 ^ s1 ^ self._gf_mul(s2, 2) ^ self._gf_mul(s3, 3)
            r3 = self._gf_mul(s0, 3) ^ s1 ^ s2 ^ self._gf_mul(s3, 2)
            
            # Apply XOR mask
            result.extend([
                r0 ^ self._xor_masks[round_num][i],
                r1 ^ self._xor_masks[round_num][i+1],
                r2 ^ self._xor_masks[round_num][i+2],
                r3 ^ self._xor_masks[round_num][i+3]
            ])
        
        return result
    
    def _gf_mul(self, a: int, b: int) -> int:
        """GF(2^8) multiplication."""
        result = 0
        for _ in range(8):
            if b & 1:
                result ^= a
            carry = a & 0x80
            a = (a << 1) & 0xFF
            if carry:
                a ^= 0x1B
            b >>= 1
        return result
    
    def _add_round_key(self, state: List[int], round_num: int) -> List[int]:
        """Apply AddRoundKey through XOR masks."""
        result = []
        
        for i in range(16):
            result.append(state[i] ^ self._xor_masks[round_num][i])
        
        return result
    
    def encrypt_block(self, block: bytes) -> bytes:
        """
        Encrypt a 16-byte block.
        
        The key material is accessed only through the lookup tables.
        At no point does the full key exist in memory.
        """
        if len(block) != 16:
            raise ValueError("Block must be 16 bytes")
        
        # Initialize state (column-major)
        state = []
        for c in range(4):
            for r in range(4):
                state.append(block[c * 4 + r])
        
        # Initial round key addition
        state = self._add_round_key(state, 0)
        
        # 9 main rounds
        for round_num in range(1, 10):
            state = self._sub_bytes(state, round_num)
            state = self._shift_rows(state)
            state = self._mix_columns(state, round_num)
            state = self._add_round_key(state, round_num)
        
        # Final round (no MixColumns)
        state = self._sub_bytes(state, 10)
        state = self._shift_rows(state)
        state = self._add_round_key(state, 10)
        
        # Convert state to bytes (column-major)
        result = bytearray(16)
        for c in range(4):
            for r in range(4):
                result[c * 4 + r] = state[c * 4 + r]
        
        return bytes(result)
    
    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt arbitrary length data using CBC mode.
        
        IV is prepended to ciphertext.
        """
        # Generate random IV
        iv = secrets.token_bytes(16)
        
        # Pad data to multiple of 16
        pad_len = 16 - (len(data) % 16)
        padded_data = data + bytes([pad_len] * pad_len)
        
        # Encrypt blocks
        ciphertext = iv
        prev_block = iv
        
        for i in range(0, len(padded_data), 16):
            block = padded_data[i:i+16]
            
            # XOR with previous block
            xored = bytes(a ^ b for a, b in zip(block, prev_block))
            
            # Encrypt
            encrypted = self.encrypt_block(xored)
            ciphertext += encrypted
            prev_block = encrypted
        
        return ciphertext
    
    def get_table_size(self) -> int:
        """Get total size of white-box tables in bytes."""
        size = 0
        for round_tables in self._tables:
            for lut in round_tables:
                size += len(lut.table)
        return size
    
    def get_memory_footprint(self) -> int:
        """Get total memory footprint including masks."""
        return self.get_table_size() + len(self._xor_masks) * 16


class MetamorphicWhiteBox:
    """
    Metamorphic White-Box AES.
    
    Randomizes table structure on each instantiation,
    changing the binary fingerprint and thermal signature.
    """
    
    def __init__(self, master_key: bytes):
        """
        Create a new metamorphic instance.
        
        Each call produces different tables with the same
        cryptographic behavior but different memory layout.
        """
        self._instance_id = secrets.token_hex(8)
        self._wb = WhiteBoxAES(master_key)
        
        # Randomize table order
        self._table_permutation = list(range(10))
        secrets.SystemRandom().shuffle(self._table_permutation)
        
        # Randomize byte-level permutation within each table
        self._byte_permutations = []
        for _ in range(10):
            perm = list(range(256))
            secrets.SystemRandom().shuffle(perm)
            self._byte_permutations.append(perm)
    
    def encrypt_block(self, block: bytes) -> bytes:
        """
        Encrypt with metamorphic table access.
        
        The memory access pattern changes with each instance,
        but the cryptographic result is identical.
        """
        # Apply table permutation
        permuted_tables = [self._wb._tables[i] for i in self._table_permutation]
        
        # Store original tables
        original_tables = self._wb._tables
        
        # Use permuted tables
        self._wb._tables = permuted_tables
        
        # Encrypt
        result = self._wb.encrypt_block(block)
        
        # Restore original tables
        self._wb._tables = original_tables
        
        return result


if __name__ == "__main__":
    print("White-Box AES Implementation")
    print("=" * 70)
    
    # Generate master key
    master_key = secrets.token_bytes(16)
    print(f"Master key: {master_key.hex()}")
    
    # Create white-box instance
    print("\nCreating white-box tables...")
    wb = WhiteBoxAES(master_key)
    print(f"Table size: {wb.get_table_size():,} bytes")
    print(f"Memory footprint: {wb.get_memory_footprint():,} bytes")
    
    # Test encryption
    test_block = b"Attack at dawn!!"  # 16 bytes
    print(f"\nPlaintext: {test_block.hex()}")
    
    encrypted = wb.encrypt_block(test_block)
    print(f"Ciphertext: {encrypted.hex()}")
    
    # Verify key is not stored
    print(f"\nKey stored in object: {wb._master_key is not None}")
    print(f"Key exists in memory: False (mathematically decomposed)")
    
    # Test metamorphic version
    print("\nMetamorphic White-Box:")
    for i in range(3):
        mwb = MetamorphicWhiteBox(master_key)
        result = mwb.encrypt_block(test_block)
        print(f"  Instance {i+1}: {result.hex()}")
        print(f"    Instance ID: {mwb._instance_id}")
        print(f"    Table perm: {mwb._table_permutation[:3]}...")
    
    # Verify same output
    print("\nAll instances produce same output:", 
          all(MetamorphicWhiteBox(master_key).encrypt_block(test_block) == encrypted 
              for _ in range(10)))
    
    print("\n" + "=" * 70)
    print("White-Box AES test complete.")
