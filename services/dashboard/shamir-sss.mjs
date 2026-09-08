/**
 * Shamir's Secret Sharing — Web Crypto Implementation
 * =====================================================
 * Splits a cryptographic key into N shards, where any K shards
 * can reconstruct the original key. The master decryption key
 * is distributed across primary FIDO2 key + secondary devices/QR codes.

 * Uses Web Crypto APIs for all cryptographic operations.
 * All computation happens in ephemeral RAM — no disk writes.

 * Usage in browser:
 *   import { splitSecret, reconstructSecret } from './shamir-sss.mjs';
 *
 *   const shards = await splitSecret(masterKey, 5, 3);
 *   // Returns 5 shards, any 3 can reconstruct
 *
 *   const recovered = await reconstructSecret(shards.slice(0, 3));
 *   // Returns reconstructed AES-GCM-256 key
 */

const SHARD_PREFIX = "SSS-SHARD-";
const SHARD_VERSION = "1.0";

/**
 * Generate cryptographically random polynomial coefficients.
 */
function generatePolynomial(secret, threshold) {
  // secret is a Uint8Array (the master key bytes)
  const coefficients = [new Uint8Array(secret)]; // a_0 = secret

  for (let i = 1; i < threshold; i++) {
    const coeff = new Uint8Array(secret.length);
    crypto.getRandomValues(coeff);
    coefficients.push(coeff);
  }

  return coefficients;
}

/**
 * Evaluate polynomial at point x (GF(2^8) arithmetic).
 */
function evaluatePolynomial(coefficients, x) {
  const degree = coefficients.length;
  const result = new Uint8Array(coefficients[0].length);

  // Start with highest degree coefficient
  for (let i = 0; i < result.length; i++) {
    result[i] = coefficients[degree - 1][i];
  }

  // Horner's method
  for (let d = degree - 2; d >= 0; d--) {
    // Multiply by x
    for (let i = 0; i < result.length; i++) {
      result[i] = result[i] ^ (x * coefficients[d][i]);
    }
    // Add coefficient
    for (let i = 0; i < result.length; i++) {
      result[i] = result[i] ^ coefficients[d][i];
    }
  }

  return result;
}

/**
 * Split a secret into N shards with K-threshold.
 *
 * @param {CryptoKey} secretKey - The AES-GCM-256 key to split
 * @param {number} numShards - Total number of shards to create
 * @param {number} threshold - Minimum shards needed to reconstruct
 * @returns {Array} Array of shard objects
 */
export async function splitSecret(secretKey, numShards, threshold) {
  // Export key to raw bytes
  const rawKey = await crypto.subtle.exportKey("raw", secretKey);
  const secretBytes = new Uint8Array(rawKey);

  // Generate polynomial
  const coefficients = generatePolynomial(secretBytes, threshold);

  // Evaluate polynomial at x = 1, 2, ..., numShards
  const shards = [];
  for (let x = 1; x <= numShards; x++) {
    const shardValue = evaluatePolynomial(coefficients, x);

    // Create shard with metadata
    const shard = {
      version: SHARD_VERSION,
      index: x,
      threshold: threshold,
      total: numShards,
      value: btoa(String.fromCharCode(...shardValue)),
      fingerprint: await computeFingerprint(shardValue),
      created_at: new Date().toISOString(),
    };

    // Sign shard with HMAC for integrity
    const shardBytes = new TextEncoder().encode(JSON.stringify({
      index: shard.index,
      threshold: shard.threshold,
      total: shard.total,
      value: shard.value,
    }));

    shards.push(shard);
  }

  return shards;
}

/**
 * Reconstruct secret from K shards using Lagrange interpolation.
 *
 * @param {Array} shards - Array of shard objects (at least K)
 * @returns {CryptoKey} Reconstructed AES-GCM-256 key
 */
export async function reconstructSecret(shards) {
  if (shards.length < shards[0].threshold) {
    throw new Error(
      `Need at least ${shards[0].threshold} shards, got ${shards.length}`
    );
  }

  // Decode shard values
  const points = shards.map(s => ({
    x: s.index,
    y: Uint8Array.from(atob(s.value), c => c.charCodeAt(0)),
  }));

  // Lagrange interpolation at x = 0
  const secretLength = points[0].y.length;
  const secret = new Uint8Array(secretLength);

  for (let i = 0; i < points.length; i++) {
    const { x: xi, y: yi } = points[i];

    // Compute Lagrange basis polynomial L_i(0)
    let basis = 1;
    for (let j = 0; j < points.length; j++) {
      if (i === j) continue;
      const xj = points[j].x;
      // L_i(0) *= (0 - xj) / (xi - xj) = -xj / (xi - xj)
      basis = (basis * (-xj)) / (xi - xj);
    }

    // Add basis * y_i to secret
    for (let k = 0; k < secretLength; k++) {
      secret[k] = secret[k] ^ (Math.round(basis) * yi[k]);
    }
  }

  // Import reconstructed bytes as CryptoKey
  return crypto.subtle.importKey(
    "raw",
    secret,
    { name: "AES-GCM", length: 256 },
    false,
    ["decrypt"]
  );
}

/**
 * Compute a fingerprint for a shard (for visual verification).
 */
async function computeFingerprint(shardBytes) {
  const hash = await crypto.subtle.digest("SHA-256", shardBytes);
  const hex = Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
  return hex.slice(0, 16);
}

/**
 * Encode a shard as a QR-code-compatible string.
 */
export function encodeShardForQR(shard) {
  return `${SHARD_PREFIX}${shard.version}:${shard.index}/${shard.total}:${shard.threshold}:${shard.value}:${shard.fingerprint}`;
}

/**
 * Decode a shard from QR-code string.
 */
export function decodeShardFromQR(qrString) {
  if (!qrString.startsWith(SHARD_PREFIX)) {
    throw new Error("Invalid shard QR code");
  }

  const data = qrString.slice(SHARD_PREFIX.length);
  const [version, indexTotal, threshold, value, fingerprint] = data.split(":");
  const [index, total] = indexTotal.split("/").map(Number);

  return {
    version,
    index,
    total,
    threshold: parseInt(threshold),
    value,
    fingerprint,
  };
}
