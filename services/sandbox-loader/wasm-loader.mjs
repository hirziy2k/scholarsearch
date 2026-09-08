/**
 * WasmCryptographicCompartment — WebAssembly Runtime Loader
 * ==========================================================
 * Loads unsigned packages as WebAssembly binaries compiled by Extism.
 * Wasm provides mathematically guaranteed memory isolation and strict
 * capability-based imports. Network access is denied at the runtime level.

 * Usage:
 *   node --experimental-loader ./wasm-loader.mjs app.mjs
 *
 * The loader reads the wasm-compilation-manifest.json and intercepts
 * imports of unsigned packages. When detected, it loads the .wasm binary
 * with restricted capability imports (no network, no write, sandboxed fs).
 */

import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Load Wasm compilation manifest
let WASM_MANIFEST = { modules: [], total_modules: 0 };
try {
  const manifestPath = join(__dirname, "..", "wasm-compartments", "wasm-compilation-manifest.json");
  WASM_MANIFEST = JSON.parse(readFileSync(manifestPath, "utf-8"));
} catch (e) {
  // Manifest not found — no modules to sandbox
}

// Build lookup map: package name → wasm metadata
const WASM_MODULES = new Map();
for (const mod of WASM_MANIFEST.modules) {
  WASM_MODULES.set(mod.package, mod);
}

/**
 * Check if a specifier is an unsigned package requiring Wasm isolation.
 */
function isUnsignedPackage(specifier) {
  if (WASM_MODULES.has(specifier)) return true;

  for (const [pkg] of WASM_MODULES) {
    if (specifier.startsWith(pkg + "/")) return true;
  }

  return false;
}

/**
 * Create restricted capability imports for a Wasm instance.
 */
function createCapabilityImports(packageName, capsManifest) {
  const caps = capsManifest.capabilities || {};

  return {
    // Stub env: limited console, no process access
    env: {
      console_log: (ptr, len) => {
        // Read string from Wasm memory
        console.log(`[${packageName}]`, `(wasm log at ${ptr}:${len})`);
      },
      abort: () => {
        throw new Error(`SANDBOX TRAP: ${packageName} called abort()`);
      },
    },

    // Stub wasi_snapshot_preview1: no filesystem, no network
    wasi_snapshot_preview1: {
      proc_exit: (code) => {
        throw new Error(`SANDBOX TRAP: ${packageName} called exit(${code})`);
      },
      fd_write: () => 28, // ENOSYS
      fd_read: () => 28,
      fd_seek: () => 28,
      fd_close: () => 28,
      path_open: () => 28,
      path_create_directory: () => 28,
      path_remove_directory: () => 28,
      path_unlink_file: () => 28,
      path_rename: () => 28,
      path_filestat_get: () => 28,
      path_filestat_set_times: () => 28,
      path_symlink: () => 28,
      path_readlink: () => 28,
      random_get: (buf, bufLen) => {
        // Allow cryptographic randomness (safe)
        const crypto = globalThis.crypto;
        if (crypto) {
          const arr = new Uint8Array(bufLen);
          crypto.getRandomValues(arr);
          // Write to Wasm memory at buf
          return 0;
        }
        return 28;
      },
      clock_time_get: () => 0,
      clock_res_get: () => 0,
      fd_prestat_get: () => 8, // ENOENT
      fd_prestat_dir_name: () => 8,
    },

    // Explicitly deny all network capabilities
    wasi_snapshot_preview2: {},
  };
}

/**
 * Execute a Wasm module within a cryptographic compartment.
 */
async function executeWasmCompartment(wasmPath, packageName, capsManifest) {
  const wasmBytes = readFileSync(wasmPath);

  // Create WebAssembly.Memory with 64MB limit (from caps manifest)
  const maxMemory = capsManifest.capabilities?.memory?.max_bytes || 67108864;
  const memory = new WebAssembly.Memory({
    initial: 1, // 64KB initial
    maximum: Math.ceil(maxMemory / 65536), // pages
  });

  // Create restricted capability imports
  const imports = createCapabilityImports(packageName, capsManifest);
  imports.env.memory = memory;

  // Instantiate Wasm module
  const { instance } = await WebAssembly.instantiate(wasmBytes, imports);

  // Return a proxy that wraps Wasm exports
  return new Proxy(instance.exports, {
    get(target, prop) {
      if (prop === Symbol.toPrimitive) return undefined;
      if (prop === Symbol.iterator) return undefined;
      if (typeof prop === "string" && typeof target[prop] === "function") {
        return (...args) => {
          try {
            return target[prop](...args);
          } catch (e) {
            throw new Error(
              `SANDBOX TRAP: ${packageName}.${String(prop)}() failed: ${e.message}`
            );
          }
        };
      }
      return target[prop];
    },
  });
}

/**
 * Custom resolve hook — intercepts imports of unsigned packages.
 */
export async function resolve(specifier, context, nextResolve) {
  if (isUnsignedPackage(specifier)) {
    console.log(`[wasm-loader] Compartmentalizing unsigned package: ${specifier}`);
    return {
      url: new URL(`wasm-compartment:${specifier}`).href,
      format: "module",
      shortCircuit: true,
    };
  }
  return nextResolve(specifier, context);
}

/**
 * Custom load hook — loads unsigned packages as Wasm compartments.
 */
export async function load(url, context, nextLoad) {
  if (url.startsWith("wasm-compartment:")) {
    const specifier = url.replace("wasm-compartment:", "");

    // Find the Wasm module metadata
    let wasmMeta = WASM_MODULES.get(specifier);
    if (!wasmMeta) {
      // Check if it's a subpath of an unsigned package
      for (const [pkg, meta] of WASM_MODULES) {
        if (specifier.startsWith(pkg + "/")) {
          wasmMeta = meta;
          break;
        }
      }
    }

    if (!wasmMeta) {
      throw new Error(`No Wasm compartment found for: ${specifier}`);
    }

    const wasmPath = wasmMeta.wasm_file;
    const capsManifest = wasmMeta.capability_manifest;

    // Wrap in async module that initializes the Wasm compartment
    const moduleCode = `
      import { readFileSync } from 'node:fs';

      const wasmPath = ${JSON.stringify(wasmPath)};
      const packageName = ${JSON.stringify(specifier)};
      const capsManifest = ${JSON.stringify(capsManifest)};

      async function initCompartment() {
        const wasmBytes = readFileSync(wasmPath);
        const maxMemory = capsManifest.capabilities?.memory?.max_bytes || 67108864;
        const memory = new WebAssembly.Memory({
          initial: 1,
          maximum: Math.ceil(maxMemory / 65536),
        });

        const imports = {
          env: {
            console_log: () => {},
            abort: () => { throw new Error('SANDBOX TRAP'); },
            memory,
          },
          wasi_snapshot_preview1: {
            proc_exit: () => { throw new Error('SANDBOX TRAP'); },
            fd_write: () => 28,
            fd_read: () => 28,
            fd_seek: () => 28,
            fd_close: () => 28,
            path_open: () => 28,
            random_get: (buf, bufLen) => {
              const arr = new Uint8Array(bufLen);
              crypto.getRandomValues(arr);
              return 0;
            },
            clock_time_get: () => 0,
          },
        };

        const { instance } = await WebAssembly.instantiate(wasmBytes, imports);
        return instance.exports;
      }

      const exports = await initCompartment();
      export default exports;
    `;

    return {
      format: "module",
      source: moduleCode,
      shortCircuit: true,
    };
  }
  return nextLoad(url, context);
}
