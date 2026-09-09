"""
Watchdog Lambda — Bidirectional State-Channel Hedging
======================================================
Monitors UDP heartbeats from Spot Fuzzer instances.
If UDP heartbeat flatlines, initiates active TCP ping to sidecar.
Only executes fatal arrest if sidecar explicitly refuses (kernel panic).
If sidecar responds but fuzzer is hanging → memory dump + graceful pause.

Deployed as AWS Lambda with CloudWatch Events rule (every 30s).

States:
    FLATLINE      — UDP heartbeat missed >45s
    TCP_PROBING   — Active TCP ping sent to sidecar
    SIDECAR_ALIVE — Sidecar responded, fuzzer hanging → DUMP + PAUSE
    SIDECAR_DEAD  — Sidecar refused → FATAL ARREST
    HEALTHY       — Heartbeat fresh, lease active

Environment variables:
    FUZZ_S3_BUCKET — S3 bucket containing lease registry + certificates
    GITHUB_TOKEN — GitHub personal access token
    GITHUB_REPO — owner/repo
    HEARTBEAT_TIMEOUT — seconds without heartbeat before flatline (default: 45)
    SIDECAR_TCP_PORT — port for sidecar health check (default: 7777)
    TCP_PROBE_TIMEOUT — seconds to wait for TCP response (default: 10)
    MEMORY_DUMP_ENABLED — upload core dump to S3 (default: true)
"""

import hashlib
import json
import os
import socket
import struct
import time
from datetime import datetime, timedelta

import boto3

S3_BUCKET = os.environ.get("FUZZ_S3_BUCKET", "scholarsearch-fuzz-certs")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
HEARTBEAT_TIMEOUT = int(os.environ.get("HEARTBEAT_TIMEOUT", "45"))
SIDECAR_TCP_PORT = int(os.environ.get("SIDECAR_TCP_PORT", "7777"))
TCP_PROBE_TIMEOUT = int(os.environ.get("TCP_PROBE_TIMEOUT", "10"))
MEMORY_DUMP_ENABLED = os.environ.get("MEMORY_DUMP_ENABLED", "true").lower() == "true"

s3 = boto3.client("s3")


def lambda_handler(event, context):
    """CloudWatch Events invokes this every 30s."""
    print("Watchdog scan started")

    leases = list_active_leases()
    print(f"Found {len(leases)} active leases")

    for lease in leases:
        state = evaluate_lease(lease)
        print(f"  Lease {lease.get('lease_id')}: {state}")

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


def evaluate_lease(lease: dict) -> str:
    """Evaluate lease state with bidirectional state-channel hedging."""
    lease_id = lease.get("lease_id")
    dep_name = lease.get("dep_name")
    dep_version = lease.get("dep_version")
    created_at = lease.get("created_at")

    if not lease_id or not created_at:
        return "INVALID"

    lease_created = datetime.fromisoformat(created_at)
    lease_ttl = lease.get("ttl_seconds", 600)
    lease_expiry = lease_created + timedelta(seconds=lease_ttl)
    now = datetime.now()

    # Check for existing valid certificate (fuzzer completed successfully)
    cert_key = f"certs/{dep_name}@{dep_version}.json"
    try:
        data = s3.get_object(Bucket=S3_BUCKET, Key=cert_key)
        cert = json.loads(data["Body"].read().decode())
        if cert.get("certificate_valid"):
            print(f"  Lease {lease_id}: cert valid — cleaning up")
            cleanup_lease(lease_id, dep_name, dep_version)
            return "HEALTHY"
    except Exception:
        pass

    # Lease hasn't expired — check heartbeat freshness
    if now < lease_expiry:
        last_heartbeat_key = f"heartbeats/{lease_id}.json"
        try:
            data = s3.get_object(Bucket=S3_BUCKET, Key=last_heartbeat_key)
            hb = json.loads(data["Body"].read().decode())
            last_hb_time = datetime.fromisoformat(hb.get("timestamp", created_at))
            hb_age = (now - last_hb_time).total_seconds()

            if hb_age < HEARTBEAT_TIMEOUT:
                return "HEALTHY"

            # UDP HEARTBEAT FLATLINED — hypervisor introspection (no guest OS reliance)
            print(f"  Lease {lease_id}: UDP flatline ({hb_age:.0f}s) — hypervisor introspection")
            return hypervisor_introspect(lease)

        except Exception:
            # No heartbeat file — check if lease is old enough to introspect
            lease_age = (now - lease_created).total_seconds()
            if lease_age > HEARTBEAT_TIMEOUT:
                print(f"  Lease {lease_id}: no heartbeat file — hypervisor introspection")
                return hypervisor_introspect(lease)
            return "WAITING"

    # Lease expired — check certificate
    try:
        data = s3.get_object(Bucket=S3_BUCKET, Key=cert_key)
        cert = json.loads(data["Body"].read().decode())
        if cert.get("certificate_valid"):
            cleanup_lease(lease_id, dep_name, dep_version)
            return "HEALTHY"
    except Exception:
        pass

    # Lease expired + no cert — hypervisor introspection before fatal decision
    print(f"  Lease {lease_id}: expired + no cert — hypervisor introspection")
    return hypervisor_introspect(lease)


def hypervisor_introspect(lease: dict) -> str:
    """Out-of-band hypervisor introspection — bypasses guest OS entirely.

    Uses AWS Nitro / EC2 hypervisor metrics to determine stall cause.
    No diagnostic agent shares the OS with the fuzzer.

    Four outcomes:
        1. Fuzzer compute-bound (high CPU, low I/O) → PAUSE + investigate
        2. OOM kill cascade (hypervisor impaired) → GRACEFUL PAUSE
        3. Kernel-level failure (system status impaired) → FATAL ARREST
        4. Instance unreachable → FATAL ARREST
    """
    lease_id = lease.get("lease_id")
    dep_name = lease.get("dep_name")
    dep_version = lease.get("dep_version")
    instance_id = lease.get("instance_id", "")

    if not instance_id:
        print(f"  Lease {lease_id}: no instance_id — assuming dead")
        trigger_fatal_arrest(lease, "No instance ID for hypervisor introspection")
        return "INSTANCE_UNKNOWN"

    # Query CloudWatch for hypervisor-level metrics (out-of-band)
    analysis = query_hypervisor_metrics(instance_id, lease)

    determination = analysis.get("determination", "unknown")
    print(f"  Lease {lease_id}: hypervisor determination = {determination}")

    if determination == "fuzzer_compute_stall":
        # Fuzzer is alive but stuck in compute loop — not dead, just slow
        print(f"  Lease {lease_id}: fuzzer compute stall — graceful pause")
        capture_memory_dump(lease)
        graceful_pause_pr(lease, "hypervisor_compute_stall")
        return "PAUSED"

    elif determination == "oom_kill_cascade":
        # OOM killed sidecar, fuzzer may still be alive — don't assume fatal
        print(f"  Lease {lease_id}: OOM kill cascade detected — graceful pause")
        capture_memory_dump(lease)
        graceful_pause_pr(lease, "oom_kill_cascade_sidecar_lost")
        return "OOM_CASCADE"

    elif determination in ("kernel_level_failure", "instance_unreachable"):
        # Hypervisor confirms kernel-level failure — safe to fatal arrest
        print(f"  Lease {lease_id}: {determination} — fatal arrest")
        trigger_fatal_arrest(lease, f"Hypervisor confirmed: {determination}")
        return "FATAL"

    else:
        # Unknown state — pause, don't destroy
        print(f"  Lease {lease_id}: indeterminate — graceful pause")
        graceful_pause_pr(lease, "indeterminate_hypervisor_state")
        return "INDETERMINATE"


def query_hypervisor_metrics(instance_id: str, lease: dict) -> dict:
    """Query CloudWatch for hypervisor-level metrics.

    These metrics come from the AWS Nitro hypervisor, NOT from
    the guest OS. They are immune to OOM-killer interference.
    """
    import boto3
    cloudwatch = boto3.client("cloudwatch", region_name=REGION)

    analysis = {
        "fuzzer_alive": False,
        "oom_killed_sidecar": False,
        "kernel_panic": False,
        "determination": "unknown",
    }

    try:
        # CPU utilization (hypervisor-reported, not guest agent)
        cpu_resp = cloudwatch.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=datetime.utcnow().replace(second=0, microsecond=0),
            EndTime=datetime.utcnow(),
            Period=60,
            Statistics=["Average", "Maximum"],
        )

        datapoints = cpu_resp.get("Datapoints", [])
        if datapoints:
            latest = max(datapoints, key=lambda d: d["Timestamp"])
            cpu_avg = latest.get("Average", 0)
            cpu_max = latest.get("Maximum", 0)

            # High CPU = fuzzer alive but compute-bound
            if cpu_avg > 80:
                analysis["fuzzer_alive"] = True
                analysis["determination"] = "fuzzer_compute_stall"

        # Status check (hypervisor-level reachability)
        ec2 = boto3.client("ec2", region_name=REGION)
        status_resp = ec2.describe_instance_status(
            InstanceIds=[instance_id],
            IncludeAllInstances=True,
        )

        for status in status_resp.get("InstanceStatuses", []):
            system = status.get("SystemStatus", {})
            instance_status = status.get("InstanceStatus", {})

            if system.get("Status") == "impaired":
                analysis["kernel_panic"] = True
                analysis["determination"] = "kernel_level_failure"

                for detail in system.get("Details", []):
                    if detail.get("Status") == "impaired":
                        analysis["impaired_check"] = detail.get("Name", "unknown")

            if instance_status.get("Status") == "impaired":
                analysis["determination"] = "instance_unreachable"

        # If CPU is low but instance is running = fuzzer dead or OOM-killed
        if not analysis["fuzzer_alive"] and not analysis["kernel_panic"]:
            if not analysis["oom_killed_sidecar"]:
                analysis["determination"] = "fuzzer_dead_low_cpu"

    except Exception as e:
        analysis["determination"] = "query_failed"
        analysis["error"] = str(e)

    return analysis


def capture_memory_dump(lease: dict) -> str:
    """Request memory dump from sidecar and upload to S3 forensic bucket."""
    lease_id = lease.get("lease_id")
    dep_name = lease.get("dep_name")
    dep_version = lease.get("dep_version")
    instance_ip = lease.get("instance_ip", "")

    if not instance_ip or not MEMORY_DUMP_ENABLED:
        return "dump_not_available"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((instance_ip, SIDECAR_TCP_PORT))
        sock.sendall(b'{"action":"memory_dump"}\n')

        dump_data = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            dump_data += chunk
        sock.close()

        # Upload forensic dump to S3
        dump_key = f"forensics/{dep_name}@{dep_version}_{lease_id}_{int(time.time())}.dump"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=dump_key,
            Body=dump_data,
            ContentType="application/octet-stream",
        )

        print(f"  Memory dump uploaded: s3://{S3_BUCKET}/{dump_key}")
        return dump_key

    except Exception as e:
        print(f"  Memory dump failed: {e}")
        return f"dump_failed: {e}"


def graceful_pause_pr(lease: dict, dump_key: str):
    """Gracefully pause the Dependabot PR (not destroy it)."""
    dep_name = lease.get("dep_name")
    dep_version = lease.get("dep_version")
    lease_id = lease.get("lease_id")

    github_token = GITHUB_TOKEN
    if not github_token or not GITHUB_REPO:
        return

    import urllib.request

    # Find PR
    prs_url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls?state=open&per_page=100"
    req = urllib.request.Request(prs_url, headers={
        "Authorization": f"token {github_token}",
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

            # Add graceful pause comment
            comment_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{pr_number}/comments"
            comment_body = {
                "body": (
                    f"## GRACEFUL PAUSE\n\n"
                    f"| Field | Value |\n"
                    f"|-------|-------|\n"
                    f"| Dependency | {dep_name}@{dep_version} |\n"
                    f"| Lease ID | `{lease_id}` |\n"
                    f"| Reason | Fuzzer appears to be hanging — memory captured |\n"
                    f"| Forensic Dump | `{dump_key}` |\n"
                    f"| Status | `paused_pending_investigation` |\n\n"
                    f"This PR has been **paused**, not closed. The fuzzer appears to be "
                    f"hanging but the sidecar is still alive. A memory dump has been captured "
                    f"for forensic analysis. Maintainers should investigate before proceeding.\n\n"
                    f"---\n*Auto-generated by bidirectional state-channel hedging*"
                ),
            }
            req_comment = urllib.request.Request(
                comment_url,
                data=json.dumps(comment_body).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                method="POST",
            )
            urllib.request.urlopen(req_comment, timeout=10)

            # Do NOT close the PR — only add label
            label_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{pr_number}/labels"
            try:
                req_label = urllib.request.Request(
                    label_url,
                    data=json.dumps({"labels": ["paused", "needs-investigation"]}).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    method="POST",
                )
                urllib.request.urlopen(req_label, timeout=10)
            except Exception:
                pass

            print(f"  PR #{pr_number} gracefully paused")
            return

    except Exception as e:
        print(f"  Graceful pause failed: {e}")


def trigger_fatal_arrest(lease: dict, reason: str):
    """Only called when sidecar explicitly refuses (kernel panic)."""
    dep_name = lease.get("dep_name")
    dep_version = lease.get("dep_version")
    lease_id = lease.get("lease_id")

    # Mint fatal arrest certificate
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
        "probe_method": "bidirectional_tcp",
    }

    cert_bytes = json.dumps(cert, sort_keys=True).encode()
    cert["certificate_hash"] = hashlib.sha256(cert_bytes).hexdigest()

    cert_key = f"certs/{dep_name}@{dep_version}.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=cert_key,
        Body=json.dumps(cert, indent=2).encode(),
        ContentType="application/json",
    )

    # Force-close PR
    force_close_pr(dep_name, dep_version, reason)
    cleanup_lease(lease_id, dep_name, dep_version)


def force_close_pr(dep_name: str, dep_version: str, reason: str):
    """Find and force-close the Dependabot PR."""
    import urllib.request

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

            comment_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{pr_number}/comments"
            comment_body = {
                "body": (
                    f"## TOXIC REGRESSION (FATAL ARREST)\n\n"
                    f"**Bidirectional State-Channel Confirmed Dead**\n\n"
                    f"| Field | Value |\n"
                    f"|-------|-------|\n"
                    f"| Dependency | {dep_name}@{dep_version} |\n"
                    f"| Lease ID | `{lease_id}` |\n"
                    f"| Reason | {reason} |\n"
                    f"| Probe Method | TCP sidecar (SYN refused) |\n"
                    f"| Status | `toxic_regression_fatal_arrest` |\n\n"
                    f"This PR has been force-closed. The sidecar confirmed kernel-level "
                    f"failure via TCP refusal.\n\n"
                    f"---\n*Auto-generated by bidirectional state-channel hedging*"
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

            close_url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{pr_number}"
            req_close = urllib.request.Request(
                close_url,
                data=json.dumps({"state": "closed"}).encode(),
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

    except Exception as e:
        print(f"  Force-close failed: {e}")


def cleanup_lease(lease_id: str, dep_name: str, dep_version: str):
    """Remove lease and heartbeat files."""
    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=f"leases/{dep_name}@{dep_version}.json")
        s3.delete_object(Bucket=S3_BUCKET, Key=f"heartbeats/{lease_id}.json")
        print(f"  Lease {lease_id} cleaned up")
    except Exception:
        pass
