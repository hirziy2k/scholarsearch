"""
Watchdog Lambda — Dead-Man's Switch Monitor
=============================================
Monitors UDP heartbeats from Spot Fuzzer instances.
If heartbeat flatlines for >45 seconds, triggers the dead-man's switch:
  1. Injects "Toxic Regression (Fatal Arrest)" status into Dependabot PR
  2. Force-closes the PR via GitHub API

Deployed as AWS Lambda with a CloudWatch Events rule (every 30s)
that invokes this function. The function checks the last heartbeat
timestamp for each active lease.

Environment variables:
    FUZZ_S3_BUCKET — S3 bucket containing lease registry + certificates
    GITHUB_TOKEN — GitHub personal access token
    GITHUB_REPO — owner/repo
    HEARTBEAT_TIMEOUT — seconds without heartbeat before flatline (default: 45)
"""

import hashlib
import json
import os
import time
from datetime import datetime, timedelta

import boto3

S3_BUCKET = os.environ.get("FUZZ_S3_BUCKET", "scholarsearch-fuzz-certs")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
HEARTBEAT_TIMEOUT = int(os.environ.get("HEARTBEAT_TIMEOUT", "45"))

s3 = boto3.client("s3")


def lambda_handler(event, context):
    """CloudWatch Events invokes this every 30s."""
    print("Watchdog scan started")

    # List all active leases
    leases = list_active_leases()
    print(f"Found {len(leases)} active leases")

    for lease in leases:
        check_heartbeat(lease)

    return {"statusCode": 200, "checked": len(leases)}


def list_active_leases() -> list:
    """List all lease files from S3."""
    leases = []
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="leases/")
        for obj in response.get("Contents", []):
            try:
                data = s3.get_object(Bucket=S3_BUCKET, Key=obj["Key"])
                lease = json.loads(data["Body"].read().decode())
                leases.append(lease)
            except Exception:
                continue
    except Exception as e:
        print(f"Failed to list leases: {e}")
    return leases


def check_heartbeat(lease: dict):
    """Check if heartbeat has flatlined for this lease."""
    lease_id = lease.get("lease_id")
    dep_name = lease.get("dep_name")
    dep_version = lease.get("dep_version")
    created_at = lease.get("created_at")

    if not lease_id or not created_at:
        return

    # Calculate lease expiry
    lease_created = datetime.fromisoformat(created_at)
    lease_ttl = lease.get("ttl_seconds", 600)
    lease_expiry = lease_created + timedelta(seconds=lease_ttl)

    # If lease hasn't expired yet, check heartbeat freshness
    now = datetime.now()
    if now < lease_expiry:
        # Lease is still active — check last heartbeat
        last_heartbeat_key = f"heartbeats/{lease_id}.json"
        try:
            data = s3.get_object(Bucket=S3_BUCKET, Key=last_heartbeat_key)
            hb = json.loads(data["Body"].read().decode())
            last_hb_time = datetime.fromisoformat(hb.get("timestamp", created_at))

            if (now - last_hb_time).total_seconds() < HEARTBEAT_TIMEOUT:
                print(f"  Lease {lease_id}: heartbeat OK ({dep_name}@{dep_version})")
                return
            else:
                print(f"  Lease {lease_id}: HEARTBEAT FLATLINED ({dep_name}@{dep_version})")
                trigger_dead_man_switch(lease, "Heartbeat flatline — fuzzer likely killed by payload")
                return
        except Exception:
            # No heartbeat file — lease just created, give grace period
            if (now - lease_created).total_seconds() > HEARTBEAT_TIMEOUT:
                print(f"  Lease {lease_id}: NO HEARTBEAT FILE ({dep_name}@{dep_version})")
                trigger_dead_man_switch(lease, "No heartbeat received — fuzzer failed to start")
                return

    else:
        # Lease expired — check if certificate was minted
        cert_key = f"certs/{dep_name}@{dep_version}.json"
        try:
            data = s3.get_object(Bucket=S3_BUCKET, Key=cert_key)
            cert = json.loads(data["Body"].read().decode())
            if cert.get("certificate_valid"):
                print(f"  Lease {lease_id}: expired but cert valid — cleaning up")
                cleanup_lease(lease_id, dep_name, dep_version)
                return
        except Exception:
            pass

        # Lease expired and no valid certificate — fatal arrest
        print(f"  Lease {lease_id}: EXPIRED + NO CERT ({dep_name}@{dep_version})")
        trigger_dead_man_switch(lease, "Lease expired without certificate — toxic regression")


def trigger_dead_man_switch(lease: dict, reason: str):
    """Force-close the Dependabot PR with toxic regression status."""
    dep_name = lease.get("dep_name")
    dep_version = lease.get("dep_version")
    lease_id = lease.get("lease_id")

    print(f"  DEAD-MAN SWITCH: {dep_name}@{dep_version} — {reason}")

    # Mint a "fatal arrest" certificate
    cert = {
        "dep_name": dep_name,
        "dep_version": dep_version,
        "status": "toxic_regression_fatal_arrest",
        "iterations": 0,
        "minted_at": datetime.now().isoformat(),
        "regression_reason": reason,
        "certificate_valid": False,
        "lease_id": lease_id,
        "dead_man_switch": True,
    }

    cert_bytes = json.dumps(cert, sort_keys=True).encode()
    cert["certificate_hash"] = hashlib.sha256(cert_bytes).hexdigest()

    # Upload certificate
    cert_key = f"certs/{dep_name}@{dep_version}.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=cert_key,
        Body=json.dumps(cert, indent=2).encode(),
        ContentType="application/json",
    )

    # Emit dead-man switch webhook
    emit_dead_man_webhook(dep_name, dep_version, lease_id, reason)

    # Force-close the PR
    force_close_pr(dep_name, dep_version, reason)

    # Cleanup lease
    cleanup_lease(lease_id, dep_name, dep_version)


def emit_dead_man_webhook(dep_name: str, dep_version: str, lease_id: str, reason: str):
    """Emit repository dispatch event for dead-man switch."""
    import urllib.request

    webhook_url = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"
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
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            },
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"  Webhook failed: {e}")


def force_close_pr(dep_name: str, dep_version: str, reason: str):
    """Find and force-close the Dependabot PR."""
    import urllib.request

    # List open PRs
    prs_url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls?state=open&per_page=100"
    req = urllib.request.Request(prs_url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    })

    try:
        resp = urllib.request.urlopen(req, timeout=10)
        prs = json.loads(resp.read().decode())

        for pr in prs:
            if pr.get("user", {}).get("login") != "dependabot[bot]":
                continue
            if dep_name not in pr.get("title", ""):
                continue
            if dep_version not in pr.get("title", ""):
                continue

            pr_number = pr["number"]

            # Add toxic regression comment
            comment_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{pr_number}/comments"
            comment_body = {
                "body": (
                    f"## TOXIC REGRESSION (FATAL ARREST)\n\n"
                    f"**Dead-Man Switch Triggered**\n\n"
                    f"| Field | Value |\n"
                    f"|-------|-------|\n"
                    f"| Dependency | {dep_name}@{dep_version} |\n"
                    f"| Reason | {reason} |\n"
                    f"| Status | `toxic_regression_fatal_arrest` |\n\n"
                    f"This PR has been force-closed by the watchdog. "
                    f"The dependency update poses a catastrophic risk.\n\n"
                    f"---\n*Auto-generated by dead-man's switch telemetry*"
                ),
            }
            req_comment = urllib.request.Request(
                comment_url,
                data=json.dumps(comment_body).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                },
                method="POST",
            )
            urllib.request.urlopen(req_comment, timeout=10)

            # Close the PR
            close_url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}"
            close_body = {"state": "closed"}
            req_close = urllib.request.Request(
                close_url,
                data=json.dumps(close_body).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                },
                method="PATCH",
            )
            urllib.request.urlopen(req_close, timeout=10)

            print(f"  PR #{pr_number} force-closed: {pr['title']}")
            return

        print(f"  No matching PR found for {dep_name}@{dep_version}")
    except Exception as e:
        print(f"  Force-close failed: {e}")


def cleanup_lease(lease_id: str, dep_name: str, dep_version: str):
    """Remove lease and heartbeat files after completion."""
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=f"leases/{dep_name}@{dep_version}.json")
        s3.delete_object(Bucket=S3_BUCKET, Key=f"heartbeats/{lease_id}.json")
        print(f"  Lease {lease_id} cleaned up")
    except Exception:
        pass
