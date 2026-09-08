/**
 * Edge-Compute Middleware: HMAC Validation + AES-GCM-256 Encryption
 * =================================================================
 * Validates HMAC-SHA256 signature, encrypts payload with AES-GCM-256,
 * writes ciphertext to S3/R2. Dashboard decrypts client-side.
 *
 * The S3 bucket is public, but the data is mathematically dark.
 * Only holders of the private key can decrypt.
 *
 * Environment variables:
 *   PAYLOAD_HMAC_SECRET — shared secret for HMAC computation
 *   ENCRYPTION_KEY — AES-256 encryption key (hex-encoded, 64 chars)
 *   S3_BUCKET — S3/R2 bucket name
 *   S3_PREFIX — key prefix (default: "payloads")
 */

const encoder = new TextEncoder();

async function computeHmac(secret, payload) {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(payload));
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function encryptPayload(plaintext, hexKey) {
  // Derive AES-256-GCM key from hex key
  const keyBytes = new Uint8Array(
    hexKey.match(/.{2}/g).map((byte) => parseInt(byte, 16))
  );

  const key = await crypto.subtle.importKey(
    "raw",
    keyBytes,
    { name: "AES-GCM" },
    false,
    ["encrypt"]
  );

  // Generate random IV (96 bits for AES-GCM)
  const iv = crypto.getRandomValues(new Uint8Array(12));

  // Encrypt
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    encoder.encode(plaintext)
  );

  // Return IV + ciphertext as base64
  const combined = new Uint8Array(iv.length + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), iv.length);

  return btoa(String.fromCharCode(...combined));
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { "Content-Type": "application/json" },
      });
    }

    const HMAC_SECRET = env.PAYLOAD_HMAC_SECRET;
    const ENCRYPTION_KEY = env.ENCRYPTION_KEY;
    const S3_BUCKET = env.S3_BUCKET;
    const S3_PREFIX = env.S3_PREFIX || "payloads";

    if (!HMAC_SECRET || !ENCRYPTION_KEY || !S3_BUCKET) {
      return new Response(JSON.stringify({ error: "Edge middleware not configured" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Parse inbound payload
    let payload;
    try {
      payload = await request.json();
    } catch (e) {
      return new Response(JSON.stringify({ error: "Invalid JSON" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Extract signature
    const inboundSignature = payload._signature;
    if (!inboundSignature) {
      return new Response(JSON.stringify({ error: "Missing _signature field" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Compute expected HMAC
    const payloadForSign = { ...payload };
    delete payloadForSign._signature;
    delete payloadForSign._timestamp;

    const canonical = JSON.stringify(
      payloadForSign,
      Object.keys(payloadForSign).sort()
    );

    const expectedSignature = await computeHmac(HMAC_SECRET, canonical);

    // Timing-safe comparison
    if (inboundSignature.length !== expectedSignature.length) {
      return new Response(JSON.stringify({ error: "Invalid signature" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    let mismatch = 0;
    for (let i = 0; i < inboundSignature.length; i++) {
      mismatch |= inboundSignature.charCodeAt(i) ^ expectedSignature.charCodeAt(i);
    }

    if (mismatch !== 0) {
      return new Response(JSON.stringify({ error: "Signature mismatch" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    // HMAC validated — encrypt and write to S3/R2
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      const payloadId = crypto.randomUUID();
      const s3Key = `${S3_PREFIX}/${timestamp}_${payloadId}.json`;

      // Encrypt payload with AES-GCM-256
      const plaintext = JSON.stringify(payload);
      const ciphertext = await encryptPayload(plaintext, ENCRYPTION_KEY);

      // Write ciphertext to R2
      if (env.R2_BUCKET) {
        await env.R2_BUCKET.put(s3Key, ciphertext, {
          httpMetadata: { contentType: "text/plain" },
        });

        return new Response(
          JSON.stringify({
            status: "encrypted_stored",
            id: payloadId,
            s3_key: s3Key,
            bucket: S3_BUCKET,
            public_url: `https://${S3_BUCKET}.r2.dev/${s3Key}`,
            encryption: "AES-256-GCM",
            message: "Payload encrypted and stored in public bucket",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }
        );
      }

      return new Response(
        JSON.stringify({ error: "No blob storage configured" }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    } catch (e) {
      return new Response(
        JSON.stringify({ error: "Encryption/storage failed", detail: e.message }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }
  },
};
