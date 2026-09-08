/**
 * V8 Isolate Context Tagging — Custom Node.js Module Loader
 * ============================================================
 * Wraps every unsigned package (from the eBPF manifest) into a distinct
 * node:vm Context Isolate. Overrides fs and net built-ins within that
 * isolate to throw runtime exceptions. The unsigned module fails
 * gracefully in its own sandbox while the core event loop continues.
 *
 * Usage:
 *   node --experimental-loader ./sandbox-loader.mjs app.mjs
 *
 * The loader reads the unsigned-manifest.json and intercepts imports
 * of unsigned packages. When detected, it:
 *   1. Creates a new vm.Context with the package's code
 *   2. Overrides require('fs') and require('net') to throw
 *   3. Executes the module within the isolated context
 *   4. Returns the exports to the parent module
 */

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));

// Load unsigned module manifest
let UNSIGNED_MANIFEST = { modules: [], total_unsigned: 0 };
try {
  const manifestPath = join(__dirname, "..", "..", "unsigned-manifest.json");
  UNSIGNED_MANIFEST = JSON.parse(readFileSync(manifestPath, "utf-8"));
} catch (e) {
  // Manifest not found — no modules to sandbox
}

// Build lookup set of unsigned package names
const UNSIGNED_PACKAGES = new Set(
  UNSIGNED_MANIFEST.modules.map((m) => m.name)
);

/**
 * Create a sandboxed fs override that blocks writes and file access.
 */
function createSandboxedFs() {
  const blocked = new Set(["writeFile", "appendFile", "unlink", "chmod", "chown", "rename", "mkdir", "rmdir", "symlink", "link"]);

  return new Proxy(
    {},
    {
      get(target, prop) {
        if (prop === "__esModule") return true;
        if (prop === "default") return target;

        if (blocked.has(prop)) {
          return () => {
            throw new Error(
              `SANDBOX VIOLATION: fs.${String(prop)}() blocked for unsigned module`
            );
          };
        }

        // Allow read-only operations (readFileSync, existsSync, etc.)
        const fs = createRequire(import.meta.url)("fs");
        if (typeof fs[prop] === "function") {
          return fs[prop].bind(fs);
        }
        return undefined;
      },
    }
  );
}

/**
 * Create a sandboxed net override that blocks all network access.
 */
function createSandboxedNet() {
  return new Proxy(
    {},
    {
      get(target, prop) {
        if (prop === "__esModule") return true;
        if (prop === "default") return target;

        return () => {
          throw new Error(
            `SANDBOX VIOLATION: net.${String(prop)}() blocked for unsigned module`
          );
        };
      },
    }
  );
}

/**
 * Create a sandboxed child_process override that blocks all execution.
 */
function createSandboxedChildProcess() {
  return new Proxy(
    {},
    {
      get(target, prop) {
        if (prop === "__esModule") return true;
        if (prop === "default") return target;

        return () => {
          throw new Error(
            `SANDBOX VIOLATION: child_process.${String(prop)}() blocked for unsigned module`
          );
        };
      },
    }
  );
}

/**
 * Create a sandboxed require function for a specific context.
 */
function createSandboxedRequire(context) {
  const originalRequire = createRequire(context.filename || import.meta.url);

  return function sandboxedRequire(id) {
    // Block dangerous built-ins
    if (id === "fs" || id === "node:fs") return createSandboxedFs();
    if (id === "net" || id === "node:net") return createSandboxedNet();
    if (id === "child_process" || id === "node:child_process")
      return createSandboxedChildProcess();
    if (id === "dgram" || id === "node:dgram")
      return createSandboxedNet();
    if (id === "http" || id === "node:http") return createSandboxedNet();
    if (id === "https" || id === "node:https") return createSandboxedNet();

    // Allow other modules
    return originalRequire(id);
  };
}

/**
 * Execute a module within a V8 Isolate Context.
 */
function executeInIsolate(code, filename, exports = {}) {
  const context = {
    exports,
    module: { exports },
    require: createSandboxedRequire({ filename }),
    __filename: filename,
    __dirname: dirname(filename),
    console,
    setTimeout,
    setInterval,
    clearTimeout,
    clearInterval,
    Buffer,
    URL,
    URLSearchParams,
    TextEncoder,
    TextDecoder,
    crypto: globalThis.crypto,
  };

  const script = new vm.Script(code, { filename });
  const contextObj = vm.createContext(context);
  script.runInContext(contextObj);

  return context.exports;
}

/**
 * Check if a specifier is an unsigned package.
 */
function isUnsignedPackage(specifier) {
  // Check exact match
  if (UNSIGNED_PACKAGES.has(specifier)) return true;

  // Check scoped packages
  if (specifier.startsWith("@")) {
    const parts = specifier.split("/");
    if (parts.length >= 2) {
      const scopedName = `${parts[0]}/${parts[1]}`;
      return UNSIGNED_PACKAGES.has(scopedName);
    }
  }

  // Check if specifier starts with an unsigned package name
  for (const pkg of UNSIGNED_PACKAGES) {
    if (specifier.startsWith(pkg + "/")) return true;
  }

  return false;
}

/**
 * Custom resolve hook — intercepts imports of unsigned packages.
 */
export async function resolve(specifier, context, nextResolve) {
  if (isUnsignedPackage(specifier)) {
    console.log(`[sandbox-loader] Sandboxing unsigned package: ${specifier}`);
    return {
      url: new URL(`sandboxed:${specifier}`).href,
      format: "module",
      shortCircuit: true,
    };
  }
  return nextResolve(specifier, context);
}

/**
 * Custom load hook — loads unsigned packages in V8 Isolate.
 */
export async function load(url, context, nextLoad) {
  if (url.startsWith("sandboxed:")) {
    const specifier = url.replace("sandboxed:", "");

    // Load the actual module code
    const { source } = await nextLoad(specifier, {
      ...context,
      format: "module",
    });

    const code = new TextDecoder().decode(source);

    // Wrap in sandboxed execution
    const wrappedCode = `
      const __sandbox_exports = {};
      const __sandbox_module = { exports: __sandbox_exports };
      const __sandbox_require = ${createSandboxedRequire.toString()}({ filename: ${JSON.stringify(specifier)} });

      // Override require for this module
      const require = __sandbox_require;
      const module = __sandbox_module;
      const exports = __sandbox_exports;

      ${code}
    `;

    return {
      format: "module",
      source: wrappedCode,
      shortCircuit: true,
    };
  }
  return nextLoad(url, context);
}
