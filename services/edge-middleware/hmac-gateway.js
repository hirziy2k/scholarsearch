/**
 * Edge-Compute Middleware: Deterministic HMAC Validation
 * ======================================================
 * Intercepts webhook payloads, validates HMAC-SHA256 signature,
 * then forwards valid payloads to the database.
 *
 * The CI trusts the Edge. The Edge protects the Database.
 * No jittered polling — synchronous 200 OK at the edge.
 *
 * Deploy as: Cloudflare Worker / Vercel Edge Function / Deno Deploy
 *
 * Environment variables:
 *   PAYLOAD_HMAC_SECRET — shared secret for HMAC computation
 *   DATABASE_WEBHOOK_URL — downstream database webhook endpoint
 */

const encoder = new TextEncoder();

function computeHmac(secret, payload) {
  const key = crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  return key.then((k) =>
    crypto.subtle.sign("HMAC", k, encoder.encode(payload)).then((sig) =>
      Array.from(new Uint8Array(sig))
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("")
    )
  );
}

export default {
  async fetch(request, env) {
    // Only accept POST
    if (request.method !== "POST") {
      return new Response(JSON.stringify({ error: "Method not allowed" }), {
        status: 405,
        headers: { "Content-Type": "application/json" },
      });
    }

    const HMAC_SECRET = env.PAYLOAD_HMAC_SECRET;
    const DATABASE_URL = env.DATABASE_WEBHOOK_URL;

    if (!HMAC_SECRET || !DATABASE_URL) {
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

    // Extract signature from payload
    const inboundSignature = payload._signature;
    if (!inboundSignature) {
      return new Response(JSON.stringify({ error: "Missing _signature field" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Compute expected HMAC from payload (excluding _signature and _timestamp)
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

    // HMAC validated — forward to database
    try {
      const dbResponse = await fetch(DATABASE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const dbBody = await dbResponse.text();

      // Return database response directly to CI
      return new Response(dbBody, {
        status: dbResponse.status,
        headers: { "Content-Type": "application/json" },
      });
    } catch (e) {
      return new Response(
        JSON.stringify({ error: "Database forward failed", detail: e.message }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }
  },
};
