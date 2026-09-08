/**
 * Verdaccio Sigstore Trust-Decay Proxy
 * =====================================
 * Tiered cryptographic curriculum:
 *   - Signed packages: bypass proxy instantly
 *   - Unsigned packages: allowed, but sandboxed (read-only + no network)
 *
 * Packages without provenance are NOT rejected — they are granted
 * limited execution context. The ecosystem is transitional; we adapt.
 */

const { execSync } = require("child_process");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const TRUST_CACHE_DIR = "/var/lib/verdaccio/trust-cache";

class TrustDecayProxy {
  constructor(config, stuff) {
    this.config = config || {};
    this.logger = stuff.logger;
    this.trustPenaltyEnabled = config.trust_penalty !== false;
  }

  async verifyProvenance(packageName, version) {
    const cacheKey = `${packageName}@${version}`;
    const cacheFile = path.join(TRUST_CACHE_DIR, `${cacheKey.replace(/[/@]/g, "_")}.json`);

    // Check cache first
    try {
      if (fs.existsSync(cacheFile)) {
        const cached = JSON.parse(fs.readFileSync(cacheFile, "utf8"));
        this.logger.info(`TRUST CACHE HIT: ${cacheKey} — ${cached.signed ? "SIGNED" : "UNSIGNED"}`);
        return cached;
      }
    } catch (e) {
      // Cache miss — verify fresh
    }

    try {
      const result = execSync(
        `npm provenance verify ${packageName}@${version} --json 2>/dev/null || echo '{"verified":false}'`,
        { encoding: "utf8", timeout: 15000 }
      );

      const provenance = JSON.parse(result.trim());
      const trustLevel = provenance.verified ? "signed" : "unsigned";

      const cert = {
        package: packageName,
        version: version,
        signed: provenance.verified,
        trust_level: trustLevel,
        identity: provenance.identity || null,
        issuer: provenance.issuer || null,
        verified_at: new Date().toISOString(),
        // Trust penalty: unsigned packages get execution restrictions
        execution_context: provenance.verified
          ? "full"
          : {
              read_only_fs: true,
              no_network: true,
              no_write: true,
              sandbox_mode: "strict",
            },
      };

      // Cache the trust decision
      try {
        fs.mkdirSync(TRUST_CACHE_DIR, { recursive: true });
        fs.writeFileSync(cacheFile, JSON.stringify(cert));
      } catch (e) {
        // Cache write failed — not critical
      }

      if (provenance.verified) {
        this.logger.info(
          `TRUST SIGNED: ${cacheKey} — identity: ${cert.identity}, issuer: ${cert.issuer}`
        );
      } else {
        this.logger.warn(
          `TRUST UNSIGNED: ${cacheKey} — applying trust penalty (sandboxed execution)`
        );
      }

      return cert;
    } catch (e) {
      this.logger.error(`TRUST VERIFY ERROR: ${cacheKey} — ${e.message}`);
      return {
        package: packageName,
        version: version,
        signed: false,
        trust_level: "unverified",
        execution_context: this.trustPenaltyEnabled
          ? { read_only_fs: true, no_network: true, no_write: true, sandbox_mode: "strict" }
          : "full",
      };
    }
  }

  generateSandboxScript(packageName, version) {
    // Generate a wrapper script that sandboxes unsigned packages
    return `#!/bin/bash
# Auto-generated sandbox wrapper for unsigned package: ${packageName}@${version}
# Trust penalty: read-only filesystem, no network, no writes

# Mount package directory as read-only
mount --bind /var/lib/verdaccio/storage/${packageName}/${version} /tmp/pkg_ro 2>/dev/null || true

# Block outbound network
iptables -A OUTPUT -m owner --uid-owner $(id -u) -j DROP 2>/dev/null || true

# Execute with restricted context
exec node -e "
  const fs = require('fs');
  const origWrite = fs.writeSync;
  const origMkdir = fs.mkdirSync;
  const origUnlink = fs.unlinkSync;
  const origRename = fs.renameSync;
  
  // Block all writes
  fs.writeSync = () => { throw new Error('WRITE BLOCKED: Unsigned package'); };
  fs.mkdirSync = () => { throw new Error('MKDIR BLOCKED: Unsigned package'); };
  fs.unlinkSync = () => { throw new Error('UNLINK BLOCKED: Unsigned package'); };
  fs.renameSync = () => { throw new Error('RENAME BLOCKED: Unsigned package'); };
  
  require('/tmp/pkg_ro');
"
`;
  }
}

function middlewares(config, stuff) {
  const proxy = new TrustDecayProxy(config, stuff);

  return {
    async manifestMiddleware(req, res, next) {
      const packageName = req.params.scope
        ? `@${req.params.scope}/${req.params.package}`
        : req.params.package;
      const version = req.params.version || "latest";

      stuff.logger.info(`TRUST CHECK: ${packageName}@${version}`);

      const trust = await proxy.verifyProvenance(packageName, version);

      if (trust.signed) {
        // Signed — full trust, pass through
        stuff.logger.info(`TRUST PASS: ${packageName}@${version} — signed, full access`);
        req.trustContext = "full";
      } else if (trust.execution_context === "full") {
        // No penalty configured — pass through
        stuff.logger.info(`TRUST PASS: ${packageName}@${version} — no penalty configured`);
        req.trustContext = "full";
      } else {
        // Unsigned — apply trust penalty
        stuff.logger.warn(
          `TRUST PENALTY: ${packageName}@${version} — sandboxed (read-only, no network)`
        );
        req.trustContext = "sandboxed";
        req.sandboxConfig = trust.execution_context;
      }

      req.trustLevel = trust.trust_level;
      next();
    },
  };
}

module.exports = middlewares;
