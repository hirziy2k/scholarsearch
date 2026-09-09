/**
 * Kinematic Anti-Fraud NFC Enclave
 * ==================================
 * NTAG 424 DNA NFC tags with tamper-evident capacitive loops
 * and micro-accelerometers. The hardware monitors its own physical
 * mounting state. If peeled off or movement exceeds baseline
 * vibration, it physically severs the TOTP seed circuit, permanently
 * bricking the tag.

 * Security properties:
 *   - Capacitive loop detects physical contact/peeling
 *   - Accelerometer detects movement beyond facility baseline
 *   - Tamper event = permanent hardware destruction (OTP fuses blown)
 *   - TOTP seed burned into fuse — destroyed on tamper
 *   - Dashboard shows crimson for tampered tags, demands new hardware

 * Usage in browser:
 *   import { KinematicNFCEnclave } from './kinematic-nfc-enclave.mjs';
 *   const enclave = new KinematicNFCEnclave();
 *   const shard = await enclave.readShard(tagId);
 */

const TOTP_INTERVAL = 30;
const TOTP_DIGITS = 6;

// Facility baseline vibration profile (in m/s²)
const FACILITY_BASELINE = {
  accelX: { min: -0.05, max: 0.05 },
  accelY: { min: -0.05, max: 0.05 },
  accelZ: { min: 9.78, max: 9.82 }, // Gravity
};

// Movement threshold beyond baseline (3x tolerance)
const MOVEMENT_THRESHOLD = 0.15;

/**
 * Compute TOTP using Web Crypto APIs (RFC 6238).
 */
async function computeTOTP(secret, time) {
  const timeStep = Math.floor(time / TOTP_INTERVAL);
  const timeBuffer = new ArrayBuffer(8);
  const timeView = new DataView(timeBuffer);
  timeView.setUint32(4, timeStep, false);

  const key = await crypto.subtle.importKey(
    "raw", secret, { name: "HMAC", hash: "SHA-1" }, false, ["sign"]
  );

  const hmac = await crypto.subtle.sign("HMAC", key, timeBuffer);
  const hmacBytes = new Uint8Array(hmac);
  const offset = hmacBytes[hmacBytes.length - 1] & 0x0f;

  return (
    ((hmacBytes[offset] & 0x7f) << 24) |
    ((hmacBytes[offset + 1] & 0xff) << 16) |
    ((hmacBytes[offset + 2] & 0xff) << 8) |
    (hmacBytes[offset + 3] & 0xff)
  ) % Math.pow(10, TOTP_DIGITS);
}

/**
 * Verify TOTP with 1-step window tolerance.
 */
async function verifyTOTP(secret, code, currentTime) {
  const current = await computeTOTP(secret, currentTime);
  if (code === current) return true;
  const prev = await computeTOTP(secret, currentTime - TOTP_INTERVAL);
  if (code === prev) return true;
  const next = await computeTOTP(secret, currentTime + TOTP_INTERVAL);
  if (code === next) return true;
  return false;
}

/**
 * Kinematic Anti-Fraud NFC Tag — hardware-level tamper detection.
 *
 * This class simulates the hardware behavior. In production,
 * the actual NTAG 424 DNA tag with capacitive loop and
 * accelerometer firmware handles this natively.
 */
export class KinematicNFCTag {
  constructor(tagId, totpSecret, facilityGPS) {
    this.tagId = tagId;
    this.totpSecret = totpSecret;
    this.facilityGPS = facilityGPS;
    this.tampered = false;
    this.bricked = false;
    this.mountState = "mounted"; // mounted | peeled | moving
    this.lastAccel = { x: 0, y: 0, z: 9.8 };
    this.capacitiveState = "intact"; // intact | broken
  }

  /**
   * Read tag data with kinematic anti-fraud verification.
   * Returns shard if hardware is intact and tag is stationary.
   */
  async read() {
    // 1. Check if tag is bricked (tamper detected previously)
    if (this.bricked) {
      return {
        success: false,
        error: "TAG_BRICKED",
        message: "Tag permanently destroyed by tamper detection",
        status: "crimson",
      };
    }

    // 2. Check capacitive loop
    if (this.capacitiveState === "broken") {
      this._brickTag("Capacitive loop broken — tag was peeled");
      return {
        success: false,
        error: "CAPACITIVE_BREACH",
        message: "Capacitive loop integrity check failed",
        status: "crimson",
      };
    }

    // 3. Check accelerometer readings
    const accelValid = this._validateAcceleration();
    if (!accelValid) {
      this._brickTag("Accelerometer detects movement beyond baseline");
      return {
        success: false,
        error: "KINEMATIC_BREACH",
        message: "Movement detected beyond facility baseline",
        status: "crimson",
      };
    }

    // 4. Verify GPS is within facility
    const gpsValid = await this._verifyGPS();
    if (!gpsValid) {
      return {
        success: false,
        error: "GEO_FENCE_BREACH",
        message: "Device GPS outside facility perimeter",
        status: "crimson",
      };
    }

    // 5. All checks passed — generate rotating shard
    const now = Math.floor(Date.now() / 1000);
    const totpCode = await computeTOTP(this.totpSecret, now);
    const rotatingShard = `${this.tagId}:${String(totpCode).padStart(TOTP_DIGITS, "0")}`;

    return {
      success: true,
      shard: rotatingShard,
      totpCode,
      verified: true,
      status: "verified",
    };
  }

  /**
   * Simulate accelerometer reading from hardware.
   */
  _validateAcceleration() {
    // In production, this reads from the actual accelerometer
    // For simulation, check against baseline
    const { x, y, z } = this.lastAccel;

    if (x < FACILITY_BASELINE.accelX.min - MOVEMENT_THRESHOLD ||
        x > FACILITY_BASELINE.accelX.max + MOVEMENT_THRESHOLD) {
      return false;
    }
    if (y < FACILITY_BASELINE.accelY.min - MOVEMENT_THRESHOLD ||
        y > FACILITY_BASELINE.accelY.max + MOVEMENT_THRESHOLD) {
      return false;
    }
    if (z < FACILITY_BASELINE.accelZ.min - MOVEMENT_THRESHOLD ||
        z > FACILITY_BASELINE.accelZ.max + MOVEMENT_THRESHOLD) {
      return false;
    }

    return true;
  }

  /**
   * Simulate GPS verification (in production, uses device GPS).
   */
  async _verifyGPS() {
    try {
      const pos = await new Promise((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 5000,
        });
      });

      const dist = this._gpsDistance(
        pos.coords.latitude, pos.coords.longitude,
        this.facilityGPS.latitude, this.facilityGPS.longitude
      );

      return dist <= this.facilityGPS.radius_meters;
    } catch {
      return false;
    }
  }

  _gpsDistance(lat1, lon1, lat2, lon2) {
    const R = 6371000;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) * Math.sin(dLon/2)**2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  }

  /**
   * Permanently brick the tag — destroy OTP fuses.
   * In production, this sends a command to blow the physical fuses.
   */
  _brickTag(reason) {
    this.bricked = true;
    this.tampered = true;
    this.mountState = "destroyed";
    this.capacitiveState = "destroyed";

    console.error(`TAG ${this.tagId} BRICKED: ${reason}`);

    // In production: command to blow OTP fuses
    // This is IRREVERSIBLE — the tag is physically destroyed
    return {
      tagId: this.tagId,
      action: "OTP_FUSE_BLOWN",
      reason,
      timestamp: new Date().toISOString(),
      permanent: true,
    };
  }
}

/**
 * Kinematic NFC Enclave — manages anti-fraud NFC tags.
 */
export class KinematicNFCEnclave {
  constructor(config = {}) {
    this.facilityGPS = config.facilityGPS || {
      latitude: 37.7749,
      longitude: -122.4194,
      radius_meters: 100,
    };
    this.tags = new Map();
  }

  /**
   * Register a kinematic NFC tag.
   */
  registerTag(tagId, totpSecret, gpsLock = null) {
    this.tags.set(tagId, new KinematicNFCTag(
      tagId, totpSecret, gpsLock || this.facilityGPS
    ));
  }

  /**
   * Read shard from tag with full anti-fraud verification.
   */
  async readShard(tagId) {
    const tag = this.tags.get(tagId);
    if (!tag) {
      return {
        success: false,
        error: "UNKNOWN_TAG",
        message: `No registered tag: ${tagId}`,
        status: "crimson",
      };
    }

    return tag.read();
  }

  /**
   * Get hardware status for all tags.
   */
  getHardwareStatus() {
    const status = {};
    for (const [id, tag] of this.tags) {
      status[id] = {
        mounted: tag.mountState,
        capacitive: tag.capacitiveState,
        bricked: tag.bricked,
        tampered: tag.tampered,
      };
    }
    return status;
  }
}
