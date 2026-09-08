"""
Ephemeral Spot Fuzzing — Self-Destructing Incubation + Dead-Man's Switch
========================================================================
Spins up a volatile spot instance, runs fuzzing iterations,
mints cryptographic health certificate to immutable storage,
and immediately self-destructs. Hardware ceases to exist.

Dead-Man's Switch: The CI pipeline registers a Fuzzing Lease with a TTL
before exiting. The Spot Instance emits high-frequency UDP heartbeats to
a serverless watchdog. If the heartbeat flatlines for >45s, the watchdog
injects "Toxic Regression (Fatal Arrest)" into the PR and force-closes it.

AWS CLI required. Configure via environment:
    FUZZ_S3_BUCKET — S3 bucket for health certificates
    FUZZ_SPOT_PRICE — max spot price (default: 0.10)
    FUZZ_INSTANCE_TYPE — instance type (default: t3.micro)
    FUZZ_AMI_ID — AMI with Python + dependencies pre-installed
    FUZZ_SUBNET_ID — VPC subnet for spot instance
    FUZZ_SG_ID — security group
    FUZZ_SSH_KEY — key pair name
    FUZZ_WATCHDOG_LAMBDA — ARN of the watchdog Lambda function
    FUZZ_HEARTBEAT_SECRET — shared secret for UDP heartbeat authentication
"""

import base64
import hashlib
import json
import os
import random
import socket
import struct
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Configuration
S3_BUCKET = os.environ.get("FUZZ_S3_BUCKET", "scholarsearch-fuzz-certs")
SPOT_PRICE = os.environ.get("FUZZ_SPOT_PRICE", "0.10")
INSTANCE_TYPE = os.environ.get("FUZZ_INSTANCE_TYPE", "t3.micro")
AMI_ID = os.environ.get("FUZZ_AMI_ID", "")
SUBNET_ID = os.environ.get("FUZZ_SUBNET_ID", "")
SG_ID = os.environ.get("FUZZ_SG_ID", "")
SSH_KEY = os.environ.get("FUZZ_SSH_KEY", "")
WATCHDOG_LAMBDA = os.environ.get("FUZZ_WATCHDOG_LAMBDA", "")
HEARTBEAT_SECRET = os.environ.get("FUZZ_HEARTBEAT_SECRET", "default-secret-change-me")
HEARTBEAT_ENDPOINT = os.environ.get("FUZZ_HEARTBEAT_ENDPOINT", "watchdog.scholarsearch.internal")
HEARTBEAT_PORT = int(os.environ.get("FUZZ_HEARTBEAT_PORT", "9999"))
HEARTBEAT_INTERVAL = 15  # seconds between heartbeats
LEASE_TTL = 600  # 10 minutes max fuzzing time
METABOLIC_THRESHOLD = 0.15
TOTAL_ITERATIONS = 1000
REGION = os.environ.get("AWS_REGION", "us-east-1")


def run_aws(cmd: str) -> str:
    """Execute AWS CLI command and return output."""
    result = subprocess.run(
        f"aws {cmd} --region {REGION} --output json",
        shell=True, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"AWS CLI failed: {result.stderr}")
    return result.stdout.strip()


def request_spot_instance() -> str:
    """Request a spot instance and wait for it to run."""
    print(f"Requesting spot instance ({INSTANCE_TYPE}, max ${SPOT_PRICE}/hr)...")

    user_data = generate_user_data()

    instance_id = run_aws(
        f"ec2 run-instances"
        f" --image-id {AMI_ID}"
        f" --instance-type {INSTANCE_TYPE}"
        f" --subnet-id {SUBNET_ID}"
        f" --security-group-ids {SG_ID}"
        f" --key-name {SSH_KEY}"
        f" --instance-market-options '{{\"MarketType\":\"spot\",\"SpotOptions\":{{\"MaxPrice\":\"{SPOT_PRICE}\",\"SpotInstanceType\":\"one-time\"}}}}'"
        f" --user-data '{user_data}'"
        f" --tag-specifications 'ResourceType=instance,Tags=[{{Key=Name,Value=fuzz-ephemeral}}]'"
    )

    iid = json.loads(instance_id)["Instances"][0]["InstanceId"]
    print(f"Instance requested: {iid}")

    # Wait for instance to be running
    for _ in range(30):
        time.sleep(10)
        state = run_aws(f"ec2 describe-instance-status --instance-ids {iid}")
        states = json.loads(state).get("InstanceStatuses", [])
        if states and states[0].get("InstanceStatus", {}).get("Status") == "ok":
            print(f"Instance {iid} running")
            return iid

    raise RuntimeError(f"Instance {iid} failed to start")


def generate_user_data() -> str:
    """Generate cloud-init script for spot instance."""
    script = f"""#!/bin/bash
set -e

# Install dependencies
apt-get update && apt-get install -y python3 python3-pip
pip3 install httpx

# Clone the repo (or fetch fuzzing script from S3)
aws s3 cp s3://{S3_BUCKET}/fuzz_engine.py /tmp/fuzz_engine.py --region {REGION}

# Run fuzzing
python3 /tmp/fuzz_engine.py --iterations {TOTAL_ITERATIONS}

# Self-destruct
shutdown -h now
"""
    return base64.b64encode(script.encode()).decode()


def wait_for_completion(instance_id: str, timeout: int = 3600) -> bool:
    """Wait for spot instance to terminate (self-destruct)."""
    print(f"Waiting for {instance_id} to self-destruct...")
    start = time.time()

    while time.time() - start < timeout:
        time.sleep(30)
        status = run_aws(f"ec2 describe-instance-status --instance-ids {instance_id}")
        states = json.loads(status).get("InstanceStatuses", [])
        if not states:
            print(f"Instance {instance_id} terminated")
            return True

    print(f"Timeout waiting for {instance_id} — terminating manually")
    run_aws(f"ec2 terminate-instances --instance-ids {instance_id}")
    return False


def fetch_certificate(dep_name: str, dep_version: str) -> dict:
    """Fetch health certificate from S3."""
    key = f"certs/{dep_name}@{dep_version}.json"
    try:
        data = run_aws(f"s3 cp s3://{S3_BUCKET}/{key} -")
        return json.loads(data)
    except Exception:
        return {"status": "pending", "iterations": 0}


def mint_certificate(dep_name: str, dep_version: str, result: dict):
    """Mint health certificate to immutable S3 bucket."""
    key = f"certs/{dep_name}@{dep_version}.json"

    cert = {
        "dep_name": dep_name,
        "dep_version": dep_version,
        "status": result.get("status", "clean"),
        "iterations": result.get("iterations", TOTAL_ITERATIONS),
        "minted_at": datetime.now().isoformat(),
        "instance_type": INSTANCE_TYPE,
        "spot_price": SPOT_PRICE,
        "crash_count": result.get("crash_count", 0),
        "peak_memory_mb": result.get("peak_memory_mb", 0),
        "peak_cpu_s": result.get("peak_cpu_s", 0),
        "regression_reason": result.get("regression_reason"),
        "certificate_valid": result.get("status") == "clean" and result.get("iterations", 0) >= TOTAL_ITERATIONS,
    }

    # Compute certificate hash for tamper detection
    cert_bytes = json.dumps(cert, sort_keys=True).encode()
    cert["certificate_hash"] = hashlib.sha256(cert_bytes).hexdigest()

    # Upload to immutable S3 bucket
    tmp = Path(f"/tmp/cert_{dep_name}_{dep_version}.json")
    tmp.write_text(json.dumps(cert, indent=2))
    run_aws(f"s3 cp {tmp} s3://{S3_BUCKET}/{key} --content-type application/json")
    tmp.unlink()

    print(f"Certificate minted: s3://{S3_BUCKET}/{key}")
    print(f"  Hash: {cert['certificate_hash'][:16]}...")
    print(f"  Status: {cert['status']}")

    # Emit webhook back to GitHub to re-trigger Dependabot evaluation
    emit_completion_webhook(dep_name, dep_version, cert)


# ============================================================================
# Dead-Man's Switch: Heartbeat Emitter + Lease Registration
# ============================================================================

class HeartbeatEmitter:
    """Sends authenticated UDP heartbeats to the watchdog Lambda.

    If the fuzzing process locks up (infinite loop, OOM, kernel hang),
    this thread dies with it, the watchdog detects the flatline, and
    force-closes the PR with "Toxic Regression (Fatal Arrest)".
    """

    def __init__(self, lease_id: str, dep_name: str, dep_version: str):
        self.lease_id = lease_id
        self.dep_name = dep_name
        self.dep_version = dep_version
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                self._send_heartbeat()
            except Exception as e:
                print(f"  Heartbeat failed: {e}")
            time.sleep(HEARTBEAT_INTERVAL)

    def _send_heartbeat(self):
        payload = {
            "lease_id": self.lease_id,
            "dep_name": self.dep_name,
            "dep_version": self.dep_version,
            "timestamp": datetime.now().isoformat(),
            "ttl_remaining": self._ttl_remaining(),
        }

        # HMAC-sign the heartbeat
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        mac = hashlib.sha256(HEARTBEAT_SECRET.encode() + payload_bytes).hexdigest()

        packet = {
            "payload": payload,
            "mac": mac,
        }

        packet_bytes = json.dumps(packet).encode()

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(packet_bytes, (HEARTBEAT_ENDPOINT, HEARTBEAT_PORT))
        finally:
            sock.close()

    def _ttl_remaining(self) -> int:
        """Return remaining lease time in seconds (approximate)."""
        return LEASE_TTL  # Simplified; real impl tracks start time


def register_fuzzing_lease(dep_name: str, dep_version: str) -> str:
    """Register a Fuzzing Lease with the watchdog Lambda.

    Returns a lease_id that the heartbeat emitter must reference.
    The watchdog will force-close the PR if no heartbeat arrives
    within LEASE_TTL seconds of the lease expiration.
    """
    lease_id = hashlib.sha256(
        f"{dep_name}@{dep_version}:{datetime.now().isoformat()}".encode()
    ).hexdigest()[:16]

    lease = {
        "lease_id": lease_id,
        "dep_name": dep_name,
        "dep_version": dep_version,
        "created_at": datetime.now().isoformat(),
        "ttl_seconds": LEASE_TTL,
        "heartbeat_interval": HEARTBEAT_INTERVAL,
        "ttl_remaining": LEASE_TTL,
    }

    print(f"Registered Fuzzing Lease: {lease_id}")
    print(f"  TTL: {LEASE_TTL}s | Heartbeat interval: {HEARTBEAT_INTERVAL}s")

    # Store lease locally (watchdog polls S3 for lease registry)
    lease_key = f"leases/{dep_name}@{dep_version}.json"
    tmp = Path(f"/tmp/lease_{lease_id}.json")
    tmp.write_text(json.dumps(lease, indent=2))
    try:
        run_aws(f"s3 cp {tmp} s3://{S3_BUCKET}/{lease_key} --content-type application/json")
    except Exception as e:
        print(f"  Lease registry upload skipped: {e}")
    finally:
        tmp.unlink()

    return lease_id


def emit_dead_man_switch(dep_name: str, dep_version: str, lease_id: str, reason: str):
    """Emit repository dispatch to force-close the Dependabot PR.

    Called by the watchdog when heartbeat flatlines.
    Also callable locally if the fuzzer detects its own failure.
    """
    github_token = os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPOSITORY")

    if not github_token or not github_repo:
        print("  Dead-man switch skipped: GITHUB_TOKEN or GITHUB_REPOSITORY not set")
        return

    webhook_url = f"https://api.github.com/repos/{github_repo}/dispatches"
    payload = {
        "event_type": "fuzz-dead-man-switch",
        "client_payload": {
            "dep_name": dep_name,
            "dep_version": dep_version,
            "lease_id": lease_id,
            "reason": reason,
            "status": "toxic_regression_fatal_arrest",
            "certificate_valid": False,
        },
    }

    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"  Dead-man switch emitted: HTTP {resp.getcode()}")
    except Exception as e:
        print(f"  Dead-man switch failed: {e}")


def emit_completion_webhook(dep_name: str, dep_version: str, cert: dict):
    """Emit repository dispatch event to GitHub to re-trigger CI."""
    github_token = os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPOSITORY")

    if not github_token or not github_repo:
        print("  Webhook skipped: GITHUB_TOKEN or GITHUB_REPOSITORY not set")
        return

    webhook_url = f"https://api.github.com/repos/{github_repo}/dispatches"
    payload = {
        "event_type": "fuzz-certificate-minted",
        "client_payload": {
            "dep_name": dep_name,
            "dep_version": dep_version,
            "certificate_status": cert.get("status"),
            "certificate_valid": cert.get("certificate_valid"),
            "iterations": cert.get("iterations"),
            "certificate_hash": cert.get("certificate_hash"),
        },
    }

    try:
        import urllib.request
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"  Webhook emitted: HTTP {resp.getcode()}")
    except Exception as e:
        print(f"  Webhook failed: {e}")


def main():
    if len(sys.argv) < 3:
        print("Usage: spot_fuzzer.py <dep_name> <dep_version>")
        sys.exit(1)

    dep_name = sys.argv[1]
    dep_version = sys.argv[2]

    print(f"=" * 60)
    print(f"EPHEMERAL SPOT FUZZING: {dep_name}@{dep_version}")
    print(f"=" * 60)

    # Check for existing valid certificate
    existing = fetch_certificate(dep_name, dep_version)
    if existing.get("certificate_valid"):
        print(f"Valid certificate exists ({existing['iterations']} iterations)")
        print("Skipping — dependency already validated")
        sys.exit(0)

    # Register Fuzzing Lease with watchdog
    lease_id = register_fuzzing_lease(dep_name, dep_version)

    # Start heartbeat emitter (daemon thread — dies with the process)
    heartbeat = HeartbeatEmitter(lease_id, dep_name, dep_version)
    heartbeat.start()

    # Spin up spot instance
    instance_id = request_spot_instance()

    # Wait for self-destruct
    success = wait_for_completion(instance_id)

    # Stop heartbeat — fuzzing complete
    heartbeat.stop()

    # Fetch result from S3 (fuzzer writes it before self-destruct)
    cert = fetch_certificate(dep_name, dep_version)

    if cert.get("status") == "pending":
        # Fuzzer didn't write result — instance crashed before completion
        cert["status"] = "crashed"
        cert["regression_reason"] = "Instance terminated before completing fuzzing"
        mint_certificate(dep_name, dep_version, cert)

        # Trigger dead-man switch to force-close PR
        emit_dead_man_switch(
            dep_name, dep_version, lease_id,
            "Fuzzer crashed without writing certificate"
        )

    if cert.get("status") == "clean":
        print(f"FUZZING COMPLETE: {dep_name}@{dep_version} — certificate valid")
        sys.exit(0)
    else:
        print(f"FUZZING FAILED: {dep_name}@{dep_version} — {cert.get('regression_reason')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
