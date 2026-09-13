#!/usr/bin/env python3
"""
Interactive Trade-off Simulator
- Evaluates FHE, SMPC, OTP under varying conditions
- Simulates network latency and compute limits
- Shows degradation curves
- Helps select optimal primitive for given constraints

Key Insight:
As network latency and compute limits increase,
both SMPC and FHE degrade rapidly,
leaving OTP as the only viable primitive
in highly resource-constrained, hostile environments.
"""

import time
import random
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class EnvironmentConstraints:
    """Constraints of the deployment environment."""
    network_latency_ms: float = 10.0
    compute_power_mhz: float = 3000.0  # MHz
    memory_mb: float = 8192.0
    bandwidth_mbps: float = 100.0
    num_nodes: int = 5
    availability_percent: float = 99.9
    hostile_host: bool = True


@dataclass
class PrimitivePerformance:
    """Performance metrics for a cryptographic primitive."""
    name: str
    latency_ms: float
    throughput_kbps: float
    memory_mb: float
    availability: float
    security_score: float
    operational_complexity: float


class TradeoffSimulator:
    """
    Interactive simulator for cryptographic primitive trade-offs.
    """
    
    def __init__(self):
        self.results = []
    
    def simulate_fhe(self, constraints: EnvironmentConstraints) -> PrimitivePerformance:
        """
        Simulate FHE performance.
        
        FHE is compute-bound and has high latency.
        """
        # FHE is 10-100x slower than plaintext
        base_latency_ms = 100.0  # Base FHE operation time
        
        # Adjust for compute power
        compute_factor = 3000.0 / constraints.compute_power_mhz
        latency = base_latency_ms * compute_factor
        
        # Adjust for network (minimal - FHE is local)
        latency += constraints.network_latency_ms * 0.1
        
        # Throughput (FHE is slow)
        throughput_kbps = 10.0 / compute_factor
        
        # Memory (FHE needs more)
        memory_mb = 256.0
        
        # Availability (depends on compute)
        availability = constraints.availability_percent * 0.95
        
        # Security (high - mathematical guarantee)
        security_score = 95.0
        
        # Operational complexity (high)
        operational_complexity = 85.0
        
        return PrimitivePerformance(
            name="FHE",
            latency_ms=latency,
            throughput_kbps=throughput_kbps,
            memory_mb=memory_mb,
            availability=availability,
            security_score=security_score,
            operational_complexity=operational_complexity
        )
    
    def simulate_smpc(self, constraints: EnvironmentConstraints) -> PrimitivePerformance:
        """
        Simulate SMPC performance.
        
        SMPC is network-bound and has high latency.
        """
        # SMPC requires communication between nodes
        base_latency_ms = 50.0  # Base SMPC operation time
        
        # Adjust for network latency (critical factor)
        latency = base_latency_ms + (constraints.network_latency_ms * 2)
        
        # Adjust for compute
        compute_factor = 3000.0 / constraints.compute_power_mhz
        latency *= compute_factor
        
        # Throughput (SMPC is network-bound)
        throughput_kbps = min(1000.0, constraints.bandwidth_mbps * 10) / compute_factor
        
        # Memory (distributed)
        memory_mb = 128.0
        
        # Availability (depends on node availability)
        node_availability = (constraints.availability_percent / 100.0) ** constraints.num_nodes
        availability = node_availability * 100
        
        # Security (high - distributed trust)
        security_score = 90.0
        
        # Operational complexity (medium)
        operational_complexity = 70.0
        
        return PrimitivePerformance(
            name="SMPC",
            latency_ms=latency,
            throughput_kbps=throughput_kbps,
            memory_mb=memory_mb,
            availability=availability,
            security_score=security_score,
            operational_complexity=operational_complexity
        )
    
    def simulate_otp(self, constraints: EnvironmentConstraints) -> PrimitivePerformance:
        """
        Simulate OTP performance.
        
        OTP is minimal - just XOR operation.
        """
        # OTP is just XOR - extremely fast
        base_latency_ms = 0.001  # 1 microsecond
        
        # Adjust for network (minimal - pad is pre-distributed)
        latency = base_latency_ms + (constraints.network_latency_ms * 0.01)
        
        # Throughput (OTP is fast)
        throughput_kbps = 10000.0  # 10 MB/s
        
        # Memory (minimal)
        memory_mb = 16.0
        
        # Availability (high - simple operation)
        availability = constraints.availability_percent
        
        # Security (perfect - information-theoretic)
        security_score = 100.0
        
        # Operational complexity (low)
        operational_complexity = 30.0
        
        return PrimitivePerformance(
            name="OTP",
            latency_ms=latency,
            throughput_kbps=throughput_kbps,
            memory_mb=memory_mb,
            availability=availability,
            security_score=security_score,
            operational_complexity=operational_complexity
        )
    
    def simulate_all(self, constraints: EnvironmentConstraints) -> Dict[str, PrimitivePerformance]:
        """Simulate all primitives under given constraints."""
        return {
            "FHE": self.simulate_fhe(constraints),
            "SMPC": self.simulate_smpc(constraints),
            "OTP": self.simulate_otp(constraints)
        }
    
    def find_optimal(self, constraints: EnvironmentConstraints) -> str:
        """
        Find optimal primitive for given constraints.
        
        Scoring:
        - Latency: lower is better
        - Throughput: higher is better
        - Availability: higher is better
        - Security: higher is better
        - Complexity: lower is better
        """
        results = self.simulate_all(constraints)
        
        best_score = -1
        best_primitive = None
        
        for name, perf in results.items():
            # Normalize scores (0-100)
            latency_score = max(0, 100 - (perf.latency_ms / 10))
            throughput_score = min(100, perf.throughput_kbps / 100)
            availability_score = perf.availability
            security_score = perf.security_score
            complexity_score = 100 - perf.operational_complexity
            
            # Weighted score
            total_score = (
                latency_score * 0.2 +
                throughput_score * 0.2 +
                availability_score * 0.2 +
                security_score * 0.3 +
                complexity_score * 0.1
            )
            
            if total_score > best_score:
                best_score = total_score
                best_primitive = name
        
        return best_primitive
    
    def print_comparison(self, constraints: EnvironmentConstraints):
        """Print comparison table."""
        results = self.simulate_all(constraints)
        
        print("\n" + "=" * 80)
        print("CRYPTOGRAPHIC PRIMITIVE COMPARISON")
        print("=" * 80)
        
        print(f"\nEnvironment Constraints:")
        print(f"  Network Latency: {constraints.network_latency_ms:.1f} ms")
        print(f"  Compute Power: {constraints.compute_power_mhz:.0f} MHz")
        print(f"  Memory: {constraints.memory_mb:.0f} MB")
        print(f"  Bandwidth: {constraints.bandwidth_mbps:.0f} Mbps")
        print(f"  Number of Nodes: {constraints.num_nodes}")
        print(f"  Availability: {constraints.availability_percent:.2f}%")
        print(f"  Hostile Host: {constraints.hostile_host}")
        
        print(f"\n{'Primitive':<10} {'Latency':<12} {'Throughput':<15} {'Memory':<10} {'Avail':<10} {'Security':<10} {'Complexity':<12}")
        print("-" * 80)
        
        for name, perf in results.items():
            print(f"{name:<10} {perf.latency_ms:<12.2f} {perf.throughput_kbps:<15.2f} {perf.memory_mb:<10.1f} {perf.availability:<10.2f} {perf.security_score:<10.1f} {perf.operational_complexity:<12.1f}")
        
        optimal = self.find_optimal(constraints)
        print(f"\nOptimal Primitive: {optimal}")
        print("=" * 80)
    
    def run_interactive(self):
        """Run interactive simulation."""
        print("\n" + "=" * 80)
        print("INTERACTIVE TRADE-OFF SIMULATOR")
        print("=" * 80)
        
        # Preset scenarios
        scenarios = {
            "1": ("Low Latency, High Compute", EnvironmentConstraints(
                network_latency_ms=1.0,
                compute_power_mhz=4000.0,
                memory_mb=16384.0,
                bandwidth_mbps=1000.0,
                num_nodes=5,
                availability_percent=99.99,
                hostile_host=True
            )),
            "2": ("High Latency, Low Compute", EnvironmentConstraints(
                network_latency_ms=500.0,
                compute_power_mhz=1000.0,
                memory_mb=2048.0,
                bandwidth_mbps=10.0,
                num_nodes=3,
                availability_percent=95.0,
                hostile_host=True
            )),
            "3": ("Constrained Environment", EnvironmentConstraints(
                network_latency_ms=1000.0,
                compute_power_mhz=500.0,
                memory_mb=512.0,
                bandwidth_mbps=1.0,
                num_nodes=2,
                availability_percent=90.0,
                hostile_host=True
            )),
            "4": ("Ideal Conditions", EnvironmentConstraints(
                network_latency_ms=0.1,
                compute_power_mhz=5000.0,
                memory_mb=32768.0,
                bandwidth_mbps=10000.0,
                num_nodes=10,
                availability_percent=99.999,
                hostile_host=False
            ))
        }
        
        print("\nSelect a scenario:")
        for key, (name, _) in scenarios.items():
            print(f"  {key}. {name}")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice in scenarios:
            name, constraints = scenarios[choice]
            print(f"\nRunning simulation: {name}")
            self.print_comparison(constraints)
        else:
            print("Invalid choice")
    
    def run_degradation_analysis(self):
        """Run degradation analysis across varying conditions."""
        print("\n" + "=" * 80)
        print("DEGRADATION ANALYSIS")
        print("=" * 80)
        
        # Test across network latency spectrum
        latencies = [1, 10, 50, 100, 500, 1000]
        
        print(f"\n{'Latency (ms)':<15} {'FHE Latency':<15} {'SMPC Latency':<15} {'OTP Latency':<15} {'Optimal':<10}")
        print("-" * 80)
        
        for latency in latencies:
            constraints = EnvironmentConstraints(
                network_latency_ms=latency,
                compute_power_mhz=3000.0,
                memory_mb=8192.0,
                bandwidth_mbps=100.0,
                num_nodes=5,
                availability_percent=99.9,
                hostile_host=True
            )
            
            results = self.simulate_all(constraints)
            optimal = self.find_optimal(constraints)
            
            print(f"{latency:<15} {results['FHE'].latency_ms:<15.2f} {results['SMPC'].latency_ms:<15.2f} {results['OTP'].latency_ms:<15.2f} {optimal:<10}")
        
        print("\n" + "=" * 80)
        print("KEY INSIGHT:")
        print("As network latency increases, SMPC degrades rapidly.")
        print("FHE remains compute-bound but unaffected by network.")
        print("OTP is virtually unaffected by any constraint.")
        print("In high-latency, resource-constrained environments,")
        print("OTP is the only viable primitive.")
        print("=" * 80)


if __name__ == "__main__":
    simulator = TradeoffSimulator()
    
    # Run interactive mode
    simulator.run_interactive()
    
    # Run degradation analysis
    simulator.run_degradation_analysis()
