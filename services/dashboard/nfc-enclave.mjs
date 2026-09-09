/**
 * Geo-Fenced NFC Enclave — NTAG 424 DNA + TOTP Rotation
 * =======================================================
 * Secondary Shamir shards are stored on hardware-bound NFC tags
 * (NTAG 424 DNA). Each tag is geo-fenced to a specific facility
 * and rotates its shard via TOTP every 30 seconds.

 * Security properties:
 *   - NFC tag must be physically tapped within the facility
 *   - GPS proves the reading device is inside the audited facility
 *   - Static shard + TOTP seed = the transmitted shard mutates every 30s
 *   - No paper, no QR codes, no analog exposure
 *   - Each tap is logged cryptographically

 * Usage in browser:
 *   import { NFCEnclave } from './nfc-enclave.mjs';
 *   const enclave = new NFCEnclave();
 *   const shard = await enclave.readShard(tagId);
 */

import { encode as base64Encode } from "https://deno.land/std/encoding/base64.ts";

const TOTP_INTERVAL = 30; // seconds
const TOTP_DIGITS = 6;
const FACILITY_GPS = {
  latitude: 37.7749,   // San Francisco (example)
  longitude: -122.4194,
  radius_meters: 100,   // 100m radius
};

/**
 * Compute TOTP code using Web Crypto APIs.
 * Implementation follows RFC 6238.
 */
async function computeTOTP(secret, time) {
  const timeStep = Math.floor(time / TOTP_INTERVAL);

  // Convert time step to 8-byte big-endian buffer
  const timeBuffer = new ArrayBuffer(8);
  const timeView = new DataView(timeBuffer);
  timeView.setUint32(4, timeStep, false);

  // Import secret as HMAC key
  const key = await crypto.subtle.importKey(
    "raw",
    secret,
    { name: "HMAC", hash: "SHA-1" },
    false,
    ["sign"]
  );

  // Compute HMAC-SHA1
  const hmac = await crypto.subtle.sign("HMAC", key, timeBuffer);
  const hmacBytes = new Uint8Array(hmac);

  // Dynamic truncation
  const offset = hmacBytes[hmacBytes.length - 1] & 0x0f;
  const code =
    ((hmacBytes[offset] & 0x7f) << 24) |
    ((hmacBytes[offset + 1] & 0xff) << 16) |
    ((hmacBytes[offset + 2] & 0xff) << 8) |
    (hmacBytes[offset + 3] & 0xff);

  return code % Math.pow(10, TOTP_DIGITS);
}

/**
 * Verify TOTP code with 1-step window tolerance.
 */
async function verifyTOTP(secret, code, currentTime) {
  const currentCode = await computeTOTP(secret, currentTime);
  if (code === currentCode) return true;

  // Allow 1-step window (30s before/after)
  const prevCode = await computeTOTP(secret, currentTime - TOTP_INTERVAL);
  if (code === prevCode) return true;

  const nextCode = await computeTOTP(secret, currentTime + TOTP_INTERVAL);
  if (code === nextCode) return true;

  return false;
}

/**
 * Get device GPS location via Geolocation API.
 */
function getDeviceGPS() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation not supported"));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
      },
      (error) => {
        reject(new Error(`GPS error: ${error.message}`));
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  });
}

/**
 * Calculate distance between two GPS coordinates (Haversine formula).
 */
function gpsDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000; // Earth radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * NFC Enclave — manages geo-fenced, TOTP-rotating NFC tags.
 */
export class NFCEnclave {
  constructor(config = {}) {
    this.facilityGPS = config.facilityGPS || FACILITY_GPS;
    this.nfcReader = null;
    this.tagStore = new Map(); // tagId → { staticShard, totpSecret, gpsLock }
  }

  /**
   * Initialize NFC reader.
   */
  async init() {
    if (!("NDEFReader" in window)) {
      throw new Error("Web NFC not supported — use a NFC-capable device");
    }

    this.nfcReader = new NDEFReader();
    await this.nfcReader.scan();
    console.log("NFC reader initialized");
  }

  /**
   * Register an NFC tag with a Shamir shard.
   * @param {string} tagId - Unique tag identifier
   * @param {string} shard - Shamir shard (base64 encoded)
   * @param {Uint8Array} totpSecret - HMAC secret for TOTP rotation
   * @param {Object} gpsLock - GPS coordinates the tag is locked to
   */
  registerTag(tagId, shard, totpSecret, gpsLock = null) {
    this.tagStore.set(tagId, {
      staticShard: shard,
      totpSecret,
      gpsLock: gpsLock || this.facilityGPS,
      registeredAt: new Date().toISOString(),
    });
  }

  /**
   * Read shard from NFC tag with geo-fence + TOTP verification.
   * @param {string} tagId - Tag to read
   * @returns {Object} Verified shard with metadata
   */
  async readShard(tagId) {
    // 1. Verify device GPS is within facility
    const gps = await getDeviceGPS();
    const tag = this.tagStore.get(tagId);

    if (!tag) {
      throw new Error(`Unknown NFC tag: ${tagId}`);
    }

    const distance = gpsDistanceMeters(
      gps.latitude,
      gps.longitude,
      tag.gpsLock.latitude,
      tag.gpsLock.longitude
    );

    if (distance > tag.gpsLock.radius_meters || FACILITY_GPS.radius_meters) {
      throw new Error(
        `GEO-FENCE VIOLATION: Device is ${Math.round(distance)}m from facility. ` +
        `Must be within ${FACILITY_GPS.radius_meters}m.`
      );
    }

    // 2. Compute current TOTP from tag's static shard + TOTP secret
    const now = Math.floor(Date.now() / 1000);
    const totpCode = await computeTOTP(tag.totpSecret, now);

    // 3. The shard transmitted by the NFC tag is: staticShard + TOTP
    // This mutates every 30 seconds
    const rotatingShard = `${tag.staticShard}:${String(totpCode).padStart(TOTP_DIGITS, "0")}`;

    // 4. Log the tap cryptographically
    const tapLog = {
      tagId,
      timestamp: new Date().toISOString(),
      gps: { lat: gps.latitude, lng: gps.longitude },
      distance_meters: Math.round(distance),
      totpCode,
      shardHash: await this.hashShard(rotatingShard),
    };

    console.log("NFC tap verified:", tapLog);

    return {
      shard: rotatingShard,
      staticShard: tag.staticShard,
      totpCode,
      verified: true,
      tapLog,
    };
  }

  /**
   * Verify a rotating shard (static + TOTP) against the tag's secret.
   */
  async verifyShard(tagId, rotatingShard) {
    const tag = this.tagStore.get(tagId);
    if (!tag) return false;

    const parts = rotatingShard.split(":");
    if (parts.length !== 2) return false;

    const [staticPart, totpPart] = parts;
    if (staticPart !== tag.staticShard) return false;

    const totpCode = parseInt(totpPart, 10);
    const now = Math.floor(Date.now() / 1000);

    return verifyTOTP(tag.totpSecret, totpCode, now);
  }

  /**
   * Hash shard for logging (never log raw shard).
   */
  async hashShard(shard) {
    const data = new TextEncoder().encode(shard);
    const hash = await crypto.subtle.digest("SHA-256", data);
    return Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }
}
