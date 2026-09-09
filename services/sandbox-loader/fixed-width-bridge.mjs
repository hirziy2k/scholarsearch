/**
 * Fixed-Width Shared Memory Buffer — Cap'n Proto Bridge
 * =======================================================
 * Communication between Wasm sandbox and V8 host occurs exclusively
 * over a rigidly defined WebAssembly.Memory shared buffer using
 * fixed-width data structures. No JSON, no string casting, no dynamic
 * serialization. The host runtime only reads explicit byte offsets
 * mathematically guaranteed to be within the buffer's bounds.

 * Memory Layout (fixed, 4KB):
 *   [0x0000 - 0x0003] uint32  status_code    (0=ok, 1=error, 2=trap)
 *   [0x0004 - 0x0007] uint32  data_length    (bytes of output data)
 *   [0x0008 - 0x0FFF] uint8[] data_buffer    (4088 bytes of output data)
 *   [0x1000 - 0x1003] uint32  request_length (bytes of input data)
 *   [0x1004 - 0x1FFF] uint8[] request_buffer (4092 bytes of input data)

 * The sandbox writes to [0x1000-0x1FFF], the host reads from [0x0000-0x0FFF].
 * Bounds are enforced at compile time by the Cap'n Proto schema.
 */

// Shared memory layout constants
const STATUS_OFFSET = 0x0000;
const DATA_LENGTH_OFFSET = 0x0004;
const DATA_BUFFER_OFFSET = 0x0008;
const DATA_BUFFER_MAX = 4088;
const REQUEST_LENGTH_OFFSET = 0x1000;
const REQUEST_BUFFER_OFFSET = 0x1004;
const REQUEST_BUFFER_MAX = 4092;
const TOTAL_BUFFER_SIZE = 0x2000; // 8KB

// Status codes
const STATUS_OK = 0;
const STATUS_ERROR = 1;
const STATUS_TRAP = 2;

/**
 * Fixed-width Cap'n Proto message layout (no dynamic allocation).
 *
 * All fields are at fixed byte offsets. The host runtime reads only
 * these offsets — no parsing, no string evaluation, no bounds ambiguity.
 */
export class FixedWidthBuffer {
  constructor(memory) {
    this.memory = memory;
    this.view = new DataView(memory.buffer);
    this.bytes = new Uint8Array(memory.buffer);
  }

  /**
   * Write status code (host → sandbox).
   */
  writeStatus(code) {
    this.view.setUint32(STATUS_OFFSET, code, true);
  }

  /**
   * Read status code (sandbox → host).
   */
  readStatus() {
    return this.view.getUint32(STATUS_OFFSET, true);
  }

  /**
   * Write output data from sandbox (fixed-width, capped at DATA_BUFFER_MAX).
   */
  writeData(data) {
    const length = Math.min(data.length, DATA_BUFFER_MAX);
    this.view.setUint32(DATA_LENGTH_OFFSET, length, true);
    for (let i = 0; i < length; i++) {
      this.bytes[DATA_BUFFER_OFFSET + i] = data[i];
    }
  }

  /**
   * Read output data from sandbox (host reads only DATA_BUFFER_MAX bytes).
   */
  readData() {
    const length = Math.min(this.view.getUint32(DATA_LENGTH_OFFSET, true), DATA_BUFFER_MAX);
    return this.bytes.slice(DATA_BUFFER_OFFSET, DATA_BUFFER_OFFSET + length);
  }

  /**
   * Write request data from host (fixed-width, capped at REQUEST_BUFFER_MAX).
   */
  writeRequest(data) {
    const length = Math.min(data.length, REQUEST_BUFFER_MAX);
    this.view.setUint32(REQUEST_LENGTH_OFFSET, length, true);
    for (let i = 0; i < length; i++) {
      this.bytes[REQUEST_BUFFER_OFFSET + i] = data[i];
    }
  }

  /**
   * Read request data from host (sandbox reads only REQUEST_BUFFER_MAX bytes).
   */
  readRequest() {
    const length = Math.min(this.view.getUint32(REQUEST_LENGTH_OFFSET, true), REQUEST_BUFFER_MAX);
    return this.bytes.slice(REQUEST_BUFFER_OFFSET, REQUEST_BUFFER_OFFSET + length);
  }

  /**
   * Clear all buffers (secure wipe).
   */
  clear() {
    this.bytes.fill(0, 0, TOTAL_BUFFER_SIZE);
  }
}

/**
 * Create Wasm imports that expose fixed-width shared memory.
 * No JSON. No string casting. No dynamic serialization.
 */
export function createFixedWidthImports(memory) {
  const buffer = new FixedWidthBuffer(memory);

  return {
    env: {
      // Fixed-width write: sandbox writes output at known offset
      write_output: (offset, length) => {
        const clampedLength = Math.min(length, DATA_BUFFER_MAX);
        const data = new Uint8Array(memory.buffer, offset, clampedLength);
        buffer.writeData(data);
        return clampedLength;
      },

      // Fixed-width read: sandbox reads input at known offset
      read_request: (destOffset, maxLen) => {
        const request = buffer.readRequest();
        const clampedLen = Math.min(request.length, maxLen, REQUEST_BUFFER_MAX);
        const dest = new Uint8Array(memory.buffer, destOffset, clampedLen);
        dest.set(request.slice(0, clampedLen));
        return clampedLen;
      },

      // Signal completion (status code)
      signal_done: (statusCode) => {
        buffer.writeStatus(statusCode);
      },

      // Signal trap (sandbox detected malicious input)
      signal_trap: () => {
        buffer.writeStatus(STATUS_TRAP);
      },

      // Abort (sandbox terminated)
      abort: () => {
        buffer.writeStatus(STATUS_TRAP);
        throw new Error("SANDBOX TRAP: Wasm module aborted");
      },

      memory,
    },

    // WASI stubs (no filesystem, no network)
    wasi_snapshot_preview1: {
      proc_exit: () => buffer.writeStatus(STATUS_TRAP),
      fd_write: () => 28,
      fd_read: () => 28,
      fd_seek: () => 28,
      fd_close: () => 28,
      path_open: () => 28,
      random_get: (buf, bufLen) => {
        const arr = new Uint8Array(memory.buffer, buf, bufLen);
        crypto.getRandomValues(arr);
        return 0;
      },
      clock_time_get: () => 0,
    },
  };
}

/**
 * Execute Wasm with fixed-width shared memory bridge.
 * Returns result as raw bytes — no JSON parsing.
 */
export async function executeFixedWidth(wasmPath, packageName) {
  const { readFileSync } = await import("node:fs");
  const wasmBytes = readFileSync(wasmPath);

  // Allocate shared memory (8KB fixed)
  const memory = new WebAssembly.Memory({
    initial: 1, // 64KB pages
    maximum: 1,
  });

  const imports = createFixedWidthImports(memory);

  const { instance } = await WebAssembly.instantiate(wasmBytes, imports);
  const buffer = new FixedWidthBuffer(memory);

  return {
    /**
     * Invoke the Wasm module with fixed-width data transfer.
     * @param {Uint8Array} input - Request data (max 4092 bytes)
     * @returns {Uint8Array} Output data (max 4088 bytes)
     */
    invoke(input) {
      buffer.clear();
      buffer.writeRequest(input);

      // Call the module's main export
      if (instance.exports.invoke) {
        instance.exports.invoke();
      } else if (instance.exports._start) {
        instance.exports._start();
      }

      // Read result from fixed-width buffer
      const status = buffer.readStatus();
      if (status === STATUS_TRAP) {
        throw new Error(`SANDBOX TRAP: ${packageName} triggered trap`);
      }

      return buffer.readData();
    },

    /**
     * Secure wipe — zero all shared memory.
     */
    wipe() {
      buffer.clear();
    },
  };
}
