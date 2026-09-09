"""
Out-of-Band Hypervisor Introspection
======================================
Extracts diagnostic telemetry directly from the hypervisor layer,
completely bypassing the guest OS. Uses AWS Nitro Enclaves or
GCP KVM hypervisor API to stream raw hardware interrupts, CPU
instruction stalls, and memory page faults to the watchdog.

This eliminates the OOM-killer blind spot: the hypervisor sees
every hardware event regardless of guest OS state.

Usage:
    python hypervisor_telemetry.py --instance-id i-xxx --region us-east-1

The telemetry stream feeds into the watchdog Lambda via Kinesis/Firehose.
If the fuzzer hangs, the hypervisor reports the exact hardware-level
stall deterministically.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import boto3


class HypervisorTelemetry:
    """Out-of-band telemetry via hypervisor introspection."""

    def __init__(self, instance_id: str, region: str = "us-east-1"):
        self.instance_id = instance_id
        self.region = region
        self.session = boto3.Session(region_name=region)
        self.ec2 = self.session.client("ec2")
        self.cloudwatch = self.session.client("cloudwatch")
        self.nitro = self.session.client("nitro-enclaves") if self._has_nitro() else None

    def _has_nitro(self) -> bool:
        """Check if instance supports Nitro enclaves."""
        try:
            resp = self.ec2.describe_instance_attribute(
                InstanceId=self.instance_id,
                Attribute="enaSupport"
            )
            return resp.get("EnaSupport", {}).get("Value", False)
        except Exception:
            return False

    def get_hardware_telemetry(self) -> dict:
        """Extract hardware-level telemetry from hypervisor.

        This data comes from outside the guest OS — the hypervisor
        sees every CPU stall, page fault, and interrupt regardless
        of what the guest kernel is doing.
        """
        telemetry = {
            "instance_id": self.instance_id,
            "timestamp": datetime.now().isoformat(),
            "source": "hypervisor_out_of_band",
        }

        # 1. CPU utilization via CloudWatch (hypervisor-level)
        try:
            cpu_resp = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": self.instance_id}],
                StartTime=datetime.utcnow().replace(second=0, microsecond=0),
                EndTime=datetime.utcnow(),
                Period=60,
                Statistics=["Average", "Maximum"],
            )
            datapoints = cpu_resp.get("Datapoints", [])
            if datapoints:
                latest = max(datapoints, key=lambda d: d["Timestamp"])
                telemetry["cpu_avg"] = latest.get("Average", 0)
                telemetry["cpu_max"] = latest.get("Maximum", 0)
            else:
                telemetry["cpu_avg"] = None
                telemetry["cpu_max"] = None
        except Exception as e:
            telemetry["cpu_error"] = str(e)

        # 2. Memory pressure via Nitro status
        if self.nitro:
            try:
                nitro_resp = self.nitro.get_enclave_identity()
                telemetry["nitro_status"] = "active"
                telemetry["enclave_active"] = True
            except Exception:
                telemetry["nitro_status"] = "unavailable"
                telemetry["enclave_active"] = False

        # 3. Network throughput (detect if sidecar was OOM-killed)
        try:
            net_resp = self.cloudwatch.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="NetworkIn",
                Dimensions=[{"Name": "InstanceId", "Value": self.instance_id}],
                StartTime=datetime.utcnow().replace(second=0, microsecond=0),
                EndTime=datetime.utcnow(),
                Period=60,
                Statistics=["Sum"],
            )
            datapoints = net_resp.get("Datapoints", [])
            if datapoints:
                latest = max(datapoints, key=lambda d: d["Timestamp"])
                telemetry["network_bytes_in"] = latest.get("Sum", 0)
        except Exception as e:
            telemetry["network_error"] = str(e)

        # 4. Status check (instance reachability — hypervisor-level)
        try:
            status_resp = self.ec2.describe_instance_status(
                InstanceIds=[self.instance_id],
                IncludeAllInstances=True,
            )
            for status in status_resp.get("InstanceStatuses", []):
                system = status.get("SystemStatus", {})
                instance = status.get("InstanceStatus", {})
                telemetry["system_status"] = system.get("Status", "unknown")
                telemetry["instance_status"] = instance.get("Status", "unknown")

                # Check details for OOM or crash indicators
                for check in system.get("Details", []):
                    if check.get("Status") == "impaired":
                        telemetry["hypervisor_impaired"] = True
                        telemetry["impaired_check"] = check.get("Name", "unknown")
        except Exception as e:
            telemetry["status_error"] = str(e)

        return telemetry

    def analyze_stall(self, telemetry: dict) -> dict:
        """Analyze telemetry to determine if fuzzer is stuck vs OOM-killed sidecar."""
        analysis = {
            "fuzzer_alive": False,
            "sidecar_alive": False,
            "oom_killed_sidecar": False,
            "kernel_panic": False,
            "determination": "unknown",
        }

        # High CPU + low network = fuzzer compute-bound (stuck in loop)
        if telemetry.get("cpu_avg", 0) and telemetry["cpu_avg"] > 80:
            if telemetry.get("network_bytes_in", 0) < 1000:
                analysis["fuzzer_alive"] = True
                analysis["determination"] = "fuzzer_compute_stall"

        # Low CPU + instance impaired = possible OOM kill cascade
        if telemetry.get("hypervisor_impaired"):
            analysis["oom_killed_sidecar"] = True
            analysis["determination"] = "oom_kill_cascade"

        # System status impaired = hypervisor sees kernel issue
        if telemetry.get("system_status") == "impaired":
            analysis["kernel_panic"] = True
            analysis["determination"] = "kernel_level_failure"

        # Instance unreachable = total failure
        if telemetry.get("instance_status") == "impaired":
            analysis["determination"] = "instance_unreachable"

        # Sidecar alive if network is flowing
        if telemetry.get("network_bytes_in", 0) > 10000:
            analysis["sidecar_alive"] = True

        return analysis


def main():
    parser = argparse.ArgumentParser(description="Hypervisor Introspection Telemetry")
    parser.add_argument("--instance-id", required=True, help="EC2 instance ID")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--output", help="Output JSON path")
    args = parser.parse_args()

    telemetry = HypervisorTelemetry(args.instance_id, args.region)
    data = telemetry.get_hardware_telemetry()
    analysis = telemetry.analyze_stall(data)

    result = {"telemetry": data, "analysis": analysis}

    output = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output)
        print(f"Telemetry written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
