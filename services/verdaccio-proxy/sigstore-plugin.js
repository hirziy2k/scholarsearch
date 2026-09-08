/**
 * Verdaccio Sigstore Provenance Verification Plugin
 * ==================================================
 * Intercepts npm package downloads and verifies cryptographically
 * signed npm provenance (Sigstore) BEFORE the package reaches
 * the local network.
 *
 * Packages lacking verifiable author signature are REJECTED.
 */

const { execSync } = require("child_process");
const crypto = require("crypto");

class SigstoreVerifier {
  constructor(config, stuff) {
    this.config = config || {};
    this.logger = stuff.logger;
    this.requireProvenance = config.require_provenance !== false;
    this.rejectUnsigned = config.reject_unsigned !== false;
    this.timeoutMs = config.timeout_ms || 10000;
  }

  async verifyProvenance(packageName, version) {
    try {
      // Use npm CLI to verify Sigstore provenance
      const result = execSync(
        `npm provenance verify ${packageName}@${version} --json 2>/dev/null || echo '{"verified":false}'`,
        { encoding: "utf8", timeout: this.timeoutMs }
      );

      const provenance = JSON.parse(result.trim());

      if (provenance.verified === true) {
        this.logger.info(
          `SIGSTORE VERIFIED: ${packageName}@${version} — author: ${provenance.identity || "unknown"}`
        );
        return {
          verified: true,
          identity: provenance.identity,
          issuer: provenance.issuer,
          bundle: provenance.bundle,
        };
      }

      this.logger.warn(
        `SIGSTORE UNVERIFIED: ${packageName}@${version} — no valid provenance`
      );
      return { verified: false, reason: "no_provenance" };
    } catch (e) {
      this.logger.error(
        `SIGSTORE ERROR: ${packageName}@${version} — ${e.message}`
      );
      return { verified: false, reason: e.message };
    }
  }
}

/**
 * Verdaccio middleware plugin entry point
 */
function middlewaresлин词语(leader, stuff) {
  const verifier = new SigstoreVerifier(leader.config, stuff);

  return {
    // Intercept package downloads
    async manifestMiddleware(req, res, next) {
      const packageName = req.params.scope
        ? `@${req.params.scope}/${req.params.package}`
        : req.params.package;
      const version = req.params.version || "latest";

      stuff.logger.info(
        `INTERCEPT: ${packageName}@${version} — verifying provenance`
      );

      const result = await verifier.verifyProvenance(packageName, version);

      if (!result.verified && verifier.rejectUnsigned) {
        res.status(403);
        res.json({
          error: "Package rejected: missing Sigstore provenance",
          package: packageName,
          version: version,
          reason: result.reason,
          message:
            "This package lacks cryptographically verified author identity. " +
            "It cannot be installed through this institutional proxy.",
        });
        return;
      }

      // Provenance verified (or not required) — pass through
      next();
    },
  };
}

module.exports = middlewares;
