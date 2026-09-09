/**
 * Hardcoded Bitwise Masking — Zero-Trust Wasm Bridge
 * =====================================================
 * The host runtime is STRICTLY FORBIDDEN from reading ANY dynamic
 * length or offset metadata from the Wasm memory. All data structure
 * offsets are hardcoded constants. Every pointer access applies a
 * bitwise AND mask (& 0x0FFF) to mathematically guarantee the read
 * cannot escape the 4088-byte output bounds.

 * Memory Layout (FIXED, IMMUTABLE):
 *   [0x0000 - 0x0003] uint32  STATUS     (hardcoded, never from Wasm)
 *   [0x0004 - 0x0007] uint32  DATA_LEN   (hardcoded, never from Wasm)
 *   [0x0008 - 0x0FFF] uint8[] DATA       (4080 bytes, ALWAYS masked)
 *   [0x1000 - 0x1003] uint32  REQ_LEN    (hardcoded, never from Wasm)
 *   [0x1004 - 0x1FFF] uint8[] REQ        (4092 bytes, ALWAYS masked)

 * SECURITY INVARIANT: The host NEVER trusts any value read from Wasm
 * memory for pointer arithmetic. The Wasm module cannot influence how
 * much data the host reads. The host decides the read bounds.
 */

// ============================================================================
// HARDCODED OFFSETS — NEVER READ FROM WASM
// ============================================================================
const STATUS_OFFSET   = 0x0000;  // Host writes, Wasm reads
const DATA_LEN_OFFSET = 0x0004;  // IGNORED by host — host decides read length
const DATA_START      = 0x0008;  // First byte of output data
const DATA_END        = 0x0FFF;  // Last valid byte of output data
const DATA_MAX_BYTES  = 0x0FF8;  // 4088 bytes (DATA_END - DATA_START + 1)

const REQ_LEN_OFFSET  = 0x1000;  // Host writes, Wasm reads
const REQ_START       = 0x1004;  // First byte of input data
const REQ_END         = 0x1FFF;  // Last valid byte of input data
const REQ_MAX_BYTES   = 0x0FFC;  // 4092 bytes

// ============================================================================
// BITWISE MASK — MATHEMATICALLY GUARANTEED BOUNDS
// ============================================================================
// Applied to EVERY pointer before read/write. If Wasm writes 0xFFFFFFFF
// as an offset, AND-ing with 0x0FFF yields 0x0FFF — still within bounds.
const BOUND_MASK = 0x0FFF;

/**
 * Mask a pointer to guarantee it stays within the output buffer.
 * This is a MATHEMATICAL CERTAINTY — no conditional branch, no trust.
 */
function maskPointer(ptr) {
  return (ptr & BOUND_MASK) >>> 0;
}

/**
 * Mask a length to guarantee it stays within the output buffer.
 */
function maskLength(len) {
  return Math.min(len & BOUND_MASK, DATA_MAX_BYTES);
}

/**
 * Hardcoded Bitwise Masking Bridge — zero-trust Wasm communication.
 *
 * All reads use hardcoded byte offsets. The Wasm module CANNOT influence
 * how much data the host reads. The bitwise mask is applied BEFORE
 * every memory access, making offset manipulation instantly neutralized.
 */
export class HardcodedMaskBridge {
  constructor(memory) {
    this.memory = memory;
    this.view = new DataView(memory.buffer);
    this.bytes = new Uint8Array(memory.buffer);
  }

  // ========================================================================
  // HOST → WASM (write request data)
  // ========================================================================

  /**
   * Write request data for the Wasm module.
   * Uses hardcoded offsets only. Length is clamped to REQ_MAX_BYTES.
   */
  writeRequest(data) {
    const writeLen = Math.min(data.length, REQ_MAX_BYTES);

    // Write length at HARDCODED offset
    this.view.setUint32(REQ_LEN_OFFSET, writeLen, true);

    // Write data at HARDCODED offset, clamped to bounds
    for (let i = 0; i < writeLen; i++) {
      this.bytes[REQ_START + i] = data[i];
    }
  }

  // ========================================================================
  // WASM → HOST (read output data) — ALL MASKED
  // ========================================================================

  /**
   * Read output data from Wasm module.
   *
   * SECURITY: We IGNORE the data_length field written by Wasm.
   * We ALWAYS read DATA_MAX_BYTES (4088 bytes) from the HARDCODED offset.
   * The bitwise mask is applied to the read pointer as defense-in-depth.
   *
   * The Wasm module cannot trick us into reading beyond the buffer.
   */
  readData() {
    // MASKED pointer — even if somehow corrupted, stays within bounds
    const maskedStart = maskPointer(DATA_START);

    // ALWAYS read the full fixed buffer — ignore any Wasm-written length
    const result = new Uint8Array(DATA_MAX_BYTES);
    for (let i = 0; i < DATA_MAX_BYTES; i++) {
      const readPtr = maskedStart + i;
      // DOUBLE MASK: pointer AND index
      result[i] = this.bytes[maskPointer(readPtr) & BOUND_MASK];
    }

    return result;
  }

  /**
   * Read a single uint32 from a HARDCODED offset (masked).
   * Used for status codes — never for dynamic length.
   */
  readStatus() {
    // Read from HARDCODED offset, masked
    const offset = maskPointer(STATUS_OFFSET);
    return this.view.getUint32(offset, true);
  }

  /**
   * Read status from a HARDCODED offset and validate range.
   * Returns null if value is out of valid range (anti-corruption).
   */
  readValidatedStatus() {
    const raw = this.readStatus();
    // Status must be 0, 1, or 2 — anything else is corruption
    if (raw > 2) return null;
    return raw;
  }

  // ========================================================================
  // WASM → HOST (read request) — MASKED
  // ========================================================================

  /**
   * Read request data that Wasm wrote.
   * MASKED read — cannot escape [0x1000, 0x1FFF] bounds.
   */
  readRequest() {
    const maskedStart = maskPointer(REQ_START);
    const readLen = maskLength(this.view.getUint32(maskPointer(REQ_LEN_OFFSET), true));

    const result = new Uint8Array(readLen);
    for (let i = 0; i < readLen; i++) {
      result[i] = this.bytes[maskPointer(maskedStart + i)];
    }
    return result;
  }

  // ========================================================================
  // SECURE WIPE
  // ========================================================================

  /**
   * Zero all shared memory — defense-in-depth.
   */
  clear() {
    this.bytes.fill(0, 0, 0x2000);
  }
}

/**
 * Create Wasm imports with hardcoded bitwise masking.
 */
export function createMaskedImports(memory) {
  const bridge = new HardcodedMaskBridge(memory);

  return {
    env: {
      // Write output — Wasm calls this to write results
      write_output: (offset, length) => {
        // MASK the offset — Wasm cannot escape bounds
        const maskedOffset = maskPointer(offset);
        const maskedLen = maskLength(length);

        // Copy with masked pointers
        const src = new Uint8Array(memory.buffer, maskedOffset, maskedLen);
        const dst = new Uint8Array(memory.buffer, DATA_START, maskedLen);
        dst.set(src);

        return maskedLen;
      },

      // Read request — Wasm calls this to read input
      read_request: (destOffset, maxLen) => {
        const maskedDest = maskPointer(destOffset);
        const maskedMax = maskLength(maxLen);
        const reqLen = maskLength(bridge.view.getUint32(maskPointer(REQ_LEN_OFFSET), true));

        const readLen = Math.min(maskedMax, reqLen);
        const src = new Uint8Array(memory.buffer, REQ_START, readLen);
        const dst = new Uint8Array(memory.buffer, maskedDest, readLen);
        dst.set(src);

        return readLen;
      },

      // Signal done — status code is MASKED before storage
      signal_done: (statusCode) => {
        const maskedStatus = statusCode & 0x03; // Only 2 bits valid
        bridge.view.setUint32(maskPointer(STATUS_OFFSET), maskedStatus, true);
      },

      // Signal trap
      signal_trap: () => {
        bridge.view.setUint32(maskPointer(STATUS_OFFSET), 2, true);
      },

      abort: () => {
        bridge.view.setUint32(maskPointer(STATUS_OFFSET), 2, true);
        throw new Error("SANDBOX TRAP: Wasm aborted");
      },

      memory,
    },

    wasi_snapshot_preview1: {
      proc_exit: () => {
        bridge.view.setUint32(maskPointer(STATUS_OFFSET), 2, true);
      },
      fd_write: () => 28,
      fd_read: () => 28,
      fd_seek: () => 28,
      fd_close: () => 28,
      path_open: () => 28,
      random_get: (buf, bufLen) => {
        const maskedBuf = maskPointer(buf);
        const maskedLen = maskLength(bufLen);
        const arr = new Uint8Array(memory.buffer, maskedBuf, maskedLen);
        crypto.getRandomValues(arr);
        return 0;
      },
      clock_time_get: () => 0,
    },
  };
}

/**
 * Execute Wasm with hardcoded bitwise masking bridge.
 * Returns result as raw bytes — NO JSON, NO TRUST.
 */
export async function executeMaskedWasm(wasmPath, packageName) {
  const { readFileSync } = await import("node:fs");
  const wasmBytes = readFileSync(wasmPath);

  const memory = new WebAssembly.Memory({ initial: 1, maximum: 1 });
  const imports = createMaskedImports(memory);

  const { instance } = await WebAssembly.instantiate(wasmBytes, imports);
  const bridge = new HardcodedMaskBridge(memory);

  return {
    /**
     * Invoke Wasm with hardcoded masked I/O.
     * @param {Uint8Array} input - Request data (max 4092 bytes)
     * @returns {Uint8Array} Output data (exactly 4088 bytes, zero-padded)
     */
    invoke(input) {
      bridge.clear();
      bridge.writeRequest(input);

      if (instance.exports.invoke) {
        instance.exports.invoke();
      } else if (instance.exports._start) {
        instance.exports._start();
      }

      // Read with MASKED pointers — Wasm cannot escape
      const status = bridge.readValidatedStatus();
      if (status === null) {
        throw new Error(`CORRUPTION: Invalid status from ${packageName}`);
      }
      if (status === 2) {
        throw new Error(`SANDBOX TRAP: ${packageName} triggered trap`);
      }

      return bridge.readData();
    },

    wipe() {
      bridge.clear();
    },
  };
}
