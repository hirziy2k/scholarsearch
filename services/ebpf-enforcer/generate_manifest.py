"""
eBPF Runtime Manifest Generator
================================
Generates a cryptographic manifest of unsigned modules during build.
This manifest is injected into the production Docker image.
The eBPF daemon reads this manifest and enforces syscall-level sandboxing.

Usage:
    python generate_manifest.py --node-modules ./node_modules --output ./unsigned-manifest.json

The manifest lists every module that lacks Sigstore provenance.
At runtime, the eBPF daemon blocks connect() and write() syscalls
from these modules.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def check_provenance(package_path: Path) -> bool:
    """Check if a package has valid Sigstore provenance."""
    pkg_json = package_path / "package.json"
    if not pkg_json.exists():
        return False

    try:
        pkg = json.loads(pkg_json.read_text())
        name = pkg.get("name", "")
        version = pkg.get("version", "")

        if not name or not version:
            return False

        # Check for provenance attestation
        result = subprocess.run(
            f"npm provenance verify {name}@{version} --json 2>/dev/null || echo '{{\"verified\":false}}'",
            shell=True, capture_output=True, text=True, timeout=10
        )

        provenance = json.loads(result.stdout.strip())
        return provenance.get("verified", False)
    except Exception:
        return False


def compute_module_hash(module_path: Path) -> str:
    """Compute SHA-256 hash of module directory."""
    hasher = hashlib.sha256()
    for f in sorted(module_path.rglob("*")):
        if f.is_file():
            hasher.update(f.read_bytes())
    return hasher.hexdigest()


def scan_unsigned_modules(node_modules_path: Path) -> list:
    """Scan node_modules for packages lacking Sigstore provenance."""
    unsigned = []

    if not node_modules_path.exists():
        return unsigned

    for item in node_modules_path.iterdir():
        if item.name.startswith("."):
            continue

        if item.name.startswith("@"):
            # Scoped package — scan inner directory
            for scoped_item in item.iterdir():
                if scoped_item.is_dir():
                    full_path = item / scoped_item.name
                    if not check_provenance(full_path):
                        unsigned.append({
                            "name": f"{item.name}/{scoped_item.name}",
                            "path": str(full_path),
                            "hash": compute_module_hash(full_path),
                            "trust_penalty": {
                                "read_only_fs": True,
                                "no_network": True,
                                "no_write": True,
                                "sandbox_mode": "strict",
                            },
                        })
        else:
            if item.is_dir() and not check_provenance(item):
                unsigned.append({
                    "name": item.name,
                    "path": str(item),
                    "hash": compute_module_hash(item),
                    "trust_penalty": {
                        "read_only_fs": True,
                        "no_network": True,
                        "no_write": True,
                        "sandbox_mode": "strict",
                    },
                })

    return unsigned


def generate_manifest(unsigned_modules: list) -> dict:
    """Generate the eBPF enforcement manifest."""
    manifest = {
        "version": "1.0.0",
        "generated_at": datetime.now().isoformat(),
        "total_unsigned": len(unsigned_modules),
        "modules": unsigned_modules,
        "enforcement": {
            "blocked_syscalls": ["connect", "write", "sendto", "sendmsg"],
            "log_violations": True,
            "kill_on_violation": False,
        },
    }

    # Compute manifest hash for tamper detection
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    manifest["manifest_hash"] = hashlib.sha256(manifest_bytes).hexdigest()

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate eBPF unsigned module manifest")
    parser.add_argument("--node-modules", required=True, help="Path to node_modules")
    parser.add_argument("--output", required=True, help="Output manifest path")
    args = parser.parse_args()

    node_modules_path = Path(args.node_modules)
    output_path = Path(args.output)

    print(f"Scanning {node_modules_path} for unsigned modules...")

    unsigned = scan_unsigned_modules(node_modules_path)
    print(f"Found {len(unsigned)} unsigned modules")

    manifest = generate_manifest(unsigned)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest written to {output_path}")
    print(f"Manifest hash: {manifest['manifest_hash'][:16]}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
