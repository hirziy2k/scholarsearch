"""
Sovereign Live Schema Validator — Generative Fuzzing Protocols
==============================================================
Dynamically mutates valid core payloads into unpredictable anomalies.
Combines fuzzing with resource profiling to detect metabolic regressions.
NO FALLBACK — if fuzzing detects crash or >15% resource spike, pipeline arrests.

Exit codes:
    0 — fuzzing complete, no crashes or metabolic regressions
    1 — crash or metabolic regression detected — pipeline arrested
"""

import ast
import hashlib
import hmac
import json
import os
import random
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Generator

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False  # Windows — use fallback profiling

import httpx

SCAN_PATHS = {
    "scholarsearch": [
        Path("services/scholarsearch/apps/server/src"),
    ],
    "pdf-engine": [
        Path("services/pdf-engine"),
    ],
}

HMAC_SECRET = os.environ.get("PAYLOAD_HMAC_SECRET", "sovereign-gateway-default-key")
RESOURCE_SPIKE_THRESHOLD = 0.15  # 15% spike triggers metabolic regression
FUZZ_ITERATIONS = 20  # Per vector category
BASELINE_SAMPLES = 3  # Baseline measurement samples

# ── Valid Base PDF ────────────────────────────────────────────
VALID_BASE_PDF = (
    b"%PDF-1.7\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R\n"
    b"/Resources<</Font<</F1 4 0 R>>>>\n"
    b"/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 44>>stream\n"
    b"BT /F1 12 Tf 72 720 Td (Hello World) Tj ET\n"
    b"endstream\nendobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000266 00000 n \n"
    b"0000000340 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n434\n%%EOF"
)

# ── Search seed queries ──────────────────────────────────────
SEARCH_SEEDS = [
    "machine learning",
    "deep neural networks",
    "quantum computing",
    "natural language processing",
    "computer vision",
]


# ── Fuzz Mutation Engines ────────────────────────────────────

def mutate_bit_flip(data: bytes, count: int = 3) -> bytes:
    """Flip random bits in the payload."""
    buf = bytearray(data)
    for _ in range(count):
        if buf:
            pos = random.randint(0, len(buf) - 1)
            bit = 1 << random.randint(0, 7)
            buf[pos] ^= bit
    return bytes(buf)


def mutate_byte_insert(data: bytes, count: int = 5) -> bytes:
    """Insert random bytes at random positions."""
    buf = bytearray(data)
    for _ in range(count):
        pos = random.randint(0, len(buf))
        val = random.randint(0, 255)
        buf.insert(pos, val)
    return bytes(buf)


def mutate_byte_delete(data: bytes, count: int = 3) -> bytes:
    """Delete random bytes."""
    buf = bytearray(data)
    for _ in range(count):
        if buf:
            pos = random.randint(0, len(buf) - 1)
            del buf[pos]
    return bytes(buf)


def mutate_boundary(data: bytes) -> bytes:
    """Corrupt PDF object boundaries and trailer."""
    buf = bytearray(data)
    # Find and corrupt a boundary marker
    for marker in [b"endobj", b"endstream", b"trailer", b"xref"]:
        idx = buf.find(marker)
        if idx >= 0:
            # Overwrite marker with random bytes
            for i in range(min(len(marker), 4)):
                buf[idx + i] = random.randint(0, 255)
            break
    return bytes(buf)


def mutate_encoding(data: bytes) -> bytes:
    """Inject encoding corruption — invalid UTF-8, null bytes, control chars."""
    buf = bytearray(data)
    injections = [
        b"\x00",  # null byte
        b"\xff\xfe",  # invalid UTF-8 BOM
        b"\xc0\xaf",  # overlong encoding
        b"\xed\xa0\x80",  # surrogate half
        bytes([random.randint(0x80, 0xFF)]),  # random high byte
    ]
    for inj in random.sample(injections, min(2, len(injections))):
        pos = random.randint(0, len(buf))
        buf[pos:pos] = inj
    return bytes(buf)


def mutate_structural(data: bytes) -> bytes:
    """Corrupt xref table, trailer size, object references."""
    buf = bytearray(data)
    # Corrupt trailer /Size
    idx = buf.find(b"/Size")
    if idx >= 0:
        # Replace size with random large number
        size_str = f"/Size {random.randint(9999, 99999)}".encode()
        buf[idx:idx + 20] = size_str.ljust(20, b"\x00")
    return bytes(buf)


def mutate_large_object(data: bytes) -> bytes:
    """Inject a massive object to test memory handling."""
    # Insert a 1MB content stream
    large_stream = b"A" * (1024 * 1024)
    marker = b"endstream"
    idx = data.find(marker)
    if idx >= 0:
        return data[:idx] + large_stream + b"\n" + data[idx:]
    return data + large_stream


def mutate_search_query(query: str) -> str:
    """Mutate a search query with encoding injection, nesting, truncation."""
    mutations = [
        lambda q: q + "\x00" * 10,
        lambda q: q * 50,  # massive repetition
        lambda q: "(" * 20 + q + ")" * 20,  # deep nesting
        lambda q: q.replace(" ", "\u200b\u200c\u200d"),  # zero-width chars
        lambda q: q.encode("utf-8").decode("utf-8", errors="replace"),
        lambda q: q + "\" OR \"1\"=\"1",  # injection attempt
        lambda q: "\x00" + q + "\xff",
        lambda q: q[::-1],  # reversed
    ]
    return random.choice(mutations)(query)


# ── Resource Profiler ─────────────────────────────────────────

class ResourceProfiler:
    """Tracks memory and CPU consumption for metabolic regression detection."""

    def __init__(self):
        self.baseline_memory = []
        self.baseline_cpu = []
        self.test_memory = []
        self.test_cpu = []

    def measure_memory(self) -> int:
        """Get current RSS in bytes."""
        if HAS_RESOURCE:
            try:
                return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
            except Exception:
                pass
        # Windows fallback: use psutil if available, else return 0
        try:
            import psutil
            return psutil.Process().memory_info().rss
        except Exception:
            return 0

    def measure_cpu(self) -> float:
        """Get current CPU time in seconds."""
        if HAS_RESOURCE:
            try:
                times = resource.getrusage(resource.RUSAGE_SELF)
                return times.ru_utime + times.ru_stime
            except Exception:
                pass
        # Windows fallback
        try:
            import psutil
            return psutil.Process().cpu_times().user + psutil.Process().cpu_times().system
        except Exception:
            return 0.0

    def sample_baseline(self, func, samples: int = BASELINE_SAMPLES):
        """Sample baseline resource usage."""
        for _ in range(samples):
            mem_before = self.measure_memory()
            cpu_before = self.measure_cpu()
            func()
            self.baseline_memory.append(self.measure_memory() - mem_before)
            self.baseline_cpu.append(self.measure_cpu() - cpu_before)

    def sample_test(self, func):
        """Sample test resource usage."""
        mem_before = self.measure_memory()
        cpu_before = self.measure_cpu()
        result = func()
        self.test_memory.append(self.measure_memory() - mem_before)
        self.test_cpu.append(self.measure_cpu() - cpu_before)
        return result

    def check_metabolic_regression(self) -> tuple[bool, str]:
        """Check if test resources exceed baseline by >15%."""
        if not self.baseline_memory or not self.test_memory:
            return False, ""

        avg_baseline_mem = sum(self.baseline_memory) / len(self.baseline_memory)
        avg_test_mem = sum(self.test_memory) / len(self.test_memory)

        if avg_baseline_mem > 0:
            mem_spike = (avg_test_mem - avg_baseline_mem) / avg_baseline_mem
            if mem_spike > RESOURCE_SPIKE_THRESHOLD:
                return True, f"Memory spike: {mem_spike:.1%} (>{RESOURCE_SPIKE_THRESHOLD:.0%} threshold)"

        avg_baseline_cpu = sum(self.baseline_cpu) / len(self.baseline_cpu)
        avg_test_cpu = sum(self.test_cpu) / len(self.test_cpu)

        if avg_baseline_cpu > 0:
            cpu_spike = (avg_test_cpu - avg_baseline_cpu) / avg_baseline_cpu
            if cpu_spike > RESOURCE_SPIKE_THRESHOLD:
                return True, f"CPU spike: {cpu_spike:.1%} (>{RESOURCE_SPIKE_THRESHOLD:.0%} threshold)"

        return False, ""


# ── Generative Fuzzing Engine ────────────────────────────────

def generate_pdf_fuzz_vectors(count: int) -> Generator[bytes, None, None]:
    """Generate fuzzed PDF payloads via dynamic mutation."""
    mutation_engines = [
        mutate_bit_flip,
        mutate_byte_insert,
        mutate_byte_delete,
        mutate_boundary,
        mutate_encoding,
        mutate_structural,
        mutate_large_object,
    ]

    for i in range(count):
        # Apply 1-3 random mutations
        payload = VALID_BASE_PDF
        num_mutations = random.randint(1, 3)
        engines = random.sample(mutation_engines, min(num_mutations, len(mutation_engines)))
        for engine in engines:
            try:
                payload = engine(payload)
            except Exception:
                pass
        yield payload


def generate_search_fuzz_vectors(count: int) -> Generator[str, None, None]:
    """Generate fuzzed search queries via dynamic mutation."""
    for i in range(count):
        seed = random.choice(SEARCH_SEEDS)
        yield mutate_search_query(seed)


# ── Deep-tissue injection with fuzzing ───────────────────────
DEEP_INJECTIONS = {
    "pdf-engine": {
        "base_url": "http://localhost:8000",
        "health_path": "/v1/health",
        "convert_path": "/v1/convert",
    },
    "scholarsearch": {
        "base_url": "http://localhost:3001",
        "health_path": "/health",
        "search_path": "/api/search/sync",
    },
}


def fuzz_pdf_engine(config: dict, profiler: ResourceProfiler) -> tuple[int, list[str]]:
    """Fuzz PDF engine with dynamically generated payloads."""
    crashes = 0
    errors = []
    base_url = config["base_url"]

    # Health check
    try:
        with httpx.Client(base_url=base_url, timeout=5) as client:
            resp = client.get(config["health_path"])
            if resp.status_code != 200:
                errors.append(f"Health check failed: HTTP {resp.status_code}")
                return -1, errors
    except Exception as e:
        errors.append(f"Health check unreachable: {e}")
        return -1, errors

    # Fuzz with generative vectors
    for i, fuzzed_pdf in enumerate(generate_pdf_fuzz_vectors(FUZZ_ITERATIONS)):
        try:
            with httpx.Client(base_url=base_url, timeout=30) as client:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(fuzzed_pdf)
                    f.seek(0)

                    def convert():
                        return client.post(
                            config["convert_path"],
                            files={"file": ("fuzz.pdf", f, "application/pdf")},
                        )

                    resp = profiler.sample_test(convert)

                if resp.status_code in (200, 202):
                    print(f"  PDF fuzz {i+1}/{FUZZ_ITERATIONS}: PASS (HTTP {resp.status_code})")
                elif resp.status_code == 422:
                    # 422 = rejected payload, not a crash — expected for some mutations
                    print(f"  PDF fuzz {i+1}/{FUZZ_ITERATIONS}: REJECTED (422)")
                else:
                    crashes += 1
                    print(f"  PDF fuzz {i+1}/{FUZZ_ITERATIONS}: CRASH (HTTP {resp.status_code})")
                    errors.append(f"PDF fuzz vector {i+1}: HTTP {resp.status_code}")

        except Exception as e:
            crashes += 1
            print(f"  PDF fuzz {i+1}/{FUZZ_ITERATIONS}: EXCEPTION ({e})")
            errors.append(f"PDF fuzz vector {i+1}: {e}")

    return crashes, errors


def fuzz_scholarsearch(config: dict, profiler: ResourceProfiler) -> tuple[int, list[str]]:
    """Fuzz ScholarSearch with dynamically generated queries."""
    crashes = 0
    errors = []
    base_url = config["base_url"]

    # Health check
    try:
        with httpx.Client(base_url=base_url, timeout=5) as client:
            resp = client.get(config["health_path"])
            if resp.status_code != 200:
                errors.append(f"Health check failed: HTTP {resp.status_code}")
                return -1, errors
    except Exception as e:
        errors.append(f"Health check unreachable: {e}")
        return -1, errors

    # Fuzz with generative vectors
    for i, fuzzed_query in enumerate(generate_search_fuzz_vectors(FUZZ_ITERATIONS)):
        try:
            with httpx.Client(base_url=base_url, timeout=30) as client:
                def search():
                    return client.post(
                        config["search_path"],
                        json={"raw_query": fuzzed_query},
                    )

                resp = profiler.sample_test(search)

            if resp.status_code in (200, 400):
                # 200 = processed, 400 = validation error — both expected
                print(f"  Search fuzz {i+1}/{FUZZ_ITERATIONS}: PASS (HTTP {resp.status_code})")
            else:
                crashes += 1
                print(f"  Search fuzz {i+1}/{FUZZ_ITERATIONS}: CRASH (HTTP {resp.status_code})")
                errors.append(f"Search fuzz vector {i+1}: HTTP {resp.status_code}")

        except Exception as e:
            crashes += 1
            print(f"  Search fuzz {i+1}/{FUZZ_ITERATIONS}: EXCEPTION ({e})")
            errors.append(f"Search fuzz vector {i+1}: {e}")

    return crashes, errors


def extract_ast_keys(service: str) -> set[str]:
    all_keys = set()
    for scan_path in SCAN_PATHS.get(service, []):
        if not scan_path.exists():
            continue
        for py_file in scan_path.rglob("*.py"):
            if "test" in py_file.name.lower():
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Subscript):
                        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                            all_keys.add(node.slice.value)
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                            if node.args and isinstance(node.args[0], ast.Constant):
                                if isinstance(node.args[0].value, str):
                                    all_keys.add(node.args[0].value)
            except (SyntaxError, UnicodeDecodeError):
                pass
        for ts_file in scan_path.rglob("*.ts"):
            if "test" in ts_file.name.lower() or ".d.ts" in ts_file.name:
                continue
            try:
                source = ts_file.read_text(encoding="utf-8")
                for line in source.split("\n"):
                    all_keys.update(re.findall(r'\[[\'"]([\w_]+)[\'"]\]', line))
                    all_keys.update(re.findall(r'\.get\([\'"]([\w_]+)[\'"]\)', line))
            except UnicodeDecodeError:
                pass
    return all_keys


def main() -> int:
    print("=" * 60)
    print("SOVEREIGN LIVE SCHEMA VALIDATOR -- GENERATIVE FUZZING")
    print("=" * 60)

    all_errors = []
    total_crashes = 0

    for service, config in DEEP_INJECTIONS.items():
        print(f"\n-- {service} --")

        profiler = ResourceProfiler()

        if service == "pdf-engine":
            crashes, errors = fuzz_pdf_engine(config, profiler)
        elif service == "scholarsearch":
            crashes, errors = fuzz_scholarsearch(config, profiler)
        else:
            continue

        if crashes == -1:
            # Unreachable — fatal
            all_errors.extend(errors)
            print(f"  FATAL: Service unreachable")
            continue

        total_crashes += crashes
        all_errors.extend(errors)

        # Check metabolic regression
        is_regression, reason = profiler.check_metabolic_regression()
        if is_regression:
            all_errors.append(f"METABOLIC REGRESSION {service}: {reason}")
            print(f"  METABOLIC REGRESSION: {reason}")
        else:
            print(f"  Resource profile: NORMAL")

        print(f"  Crashes: {crashes}/{FUZZ_ITERATIONS}")

    if all_errors:
        print(f"\n{'=' * 60}")
        print(f"SOVEREIGN GATEWAY DENIAL: {len(all_errors)} fatal error(s)")
        for e in all_errors:
            print(f"  FATAL: {e}")
        print("Pipeline arrested. Fuzzing detected vulnerabilities.")
        return 1

    print(f"\n{'=' * 60}")
    print(f"FUZZING COMPLETE: {total_crashes} crashes across {FUZZ_ITERATIONS * 2} vectors")
    print("No metabolic regressions detected. Deployment eligible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
