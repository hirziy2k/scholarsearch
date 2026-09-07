"""
Sovereign Live Schema Validator — Vector-Isolated Toxicity Matrices
===================================================================
Injects ISOLATED pathological vectors into core endpoints.
Each vector targets a single library subsystem for precise regression localization.
NO FALLBACK — if any vector fails, pipeline fatal-arrests.

Exit codes:
    0 — all vectors captured and intersected successfully
    1 — vector failure — pipeline must arrest with localized diagnosis
"""

import ast
import hashlib
import hmac
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import httpx

SCAN_PATHS = {
    "scholarsearch": [
        Path("services/scholarsearch/apps/server/src"),
    ],
    "pdf-engine": [
        Path("services/pdf-engine"),
    ],
}

# ── Vector-Isolated PDF Pathology Matrix ─────────────────────
# Each vector targets ONE subsystem. If Vector A crashes but B/C/D pass,
# regression is localized to the font-rendering module.

VECTOR_FONT_CORRUPTED = (
    b"%PDF-1.7\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R\n"
    b"/Resources<</Font<</F1 4 0 R>>>>\n"
    b"/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/AAAAAA\n"
    b"/Encoding<</Type/Encoding/Differences[200/space/300/A/301/B]>>>>>>endobj\n"
    b"5 0 obj<</Length 128>>stream\n"
    b"BT /F1 999 Tf 72 720 Td (Font crash test) Tj ET\n"
    b"endstream\nendobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000296 00000 n \n"
    b"0000000549 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n679\n%%EOF"
)

VECTOR_ENCRYPTION_MALFORMED = (
    b"%PDF-1.7\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R\n"
    b"/Resources<</Font<</F1 4 0 R>>>>\n"
    b"/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 64>>stream\n"
    b"BT /F1 12 Tf 72 720 Td (Encryption crash test) Tj ET\n"
    b"endstream\nendobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000296 00000 n \n"
    b"0000000549 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R/Encrypt<</Filter/Standard\n"
    b"/V 99/R 99/Length 0/P -1\n"
    b"/O <000102030405060708090A0B0C0D0E0F>\n"
    b"/U <000102030405060708090A0B0C0D0E0F>>>>\n"
    b"startxref\n629\n%%EOF"
)

VECTOR_NULL_BYTE_INJECTION = (
    b"%PDF-1.7\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R\n"
    b"/Resources<</Font<</F1 4 0 R>>>>\n"
    b"/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 80>>stream\n"
    b"BT /F1 12 Tf 72 720 Td "
    b"(\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0aNull bytes) Tj ET\n"
    b"endstream\nendobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000296 00000 n \n"
    b"0000000549 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n639\n%%EOF"
)

VECTOR_STRUCTURAL_CORRUPTION = (
    b"%PDF-1.7\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R\n"
    b"/Resources<</Font<</F1 4 0 R>>>>\n"
    b"/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 64>>stream\n"
    b"BT /F1 12 Tf 72 720 Td (Struct crash test) Tj ET\n"
    b"endstream\nendobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000296 00000 n \n"
    b"0000000549 00000 n \n"
    b"trailer<</Size 999/Root 1 0 R>>\n"
    b"startxref\n999999\n%%EOF"
)

VECTOR_UNICODE_TEXT_RENDERING = (
    b"%PDF-1.7\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R\n"
    b"/Resources<</Font<</F1 4 0 R>>>>\n"
    b"/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 256>>stream\n"
    b"BT /F1 12 Tf 72 720 Td "
    b"(\xc3\x89ncrypt\xc3\xa9d \xc3\xa9l\xc3\xa8ves) Tj\n"
    b"0 -20 Td "
    b"(\xe6\xb5\x8b\xe8\xaf\x95\xe6\x96\x87\xe6\x9c\xac) Tj\n"
    b"0 -20 Td "
    b"(\xd0\x9f\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82) Tj\n"
    b"0 -20 Td "
    b"(\xf0\x9f\x98\x80\xf0\x9f\x92\xa9\xf0\x9f\x92\x80) Tj\n"
    b"0 -20 Td "
    b"(\xe2\x80\x8b\xe2\x80\x8c\xe2\x80\x8d\xef\xbb\xbf ZeroWidth) Tj\n"
    b"ET\nendstream\nendobj\n"
    b"xref\n0 6\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000296 00000 n \n"
    b"0000000549 00000 n \n"
    b"trailer<</Size 6/Root 1 0 R>>\n"
    b"startxref\n849\n%%EOF"
)

# Search vectors: isolated query pathologies
SEARCH_VECTOR_EXTREME_UNICODE = (
    "\u0644\u0627 \u064a\u064f\u0639\u0650\u0631\u064e\u0627\u0628\u0650 "
    "\u05d0\u05b8\u05dc\u05b4\u05d4\u05b9 "
    "\u3042\u3044\u3046\u3048\u304a "
    "\U0001f600\U0001f4a9\U00026201 "
    "\u200b\u200c\u200d\ufeff"
)

SEARCH_VECTOR_BOOLEAN_NESTING = (
    "(learning OR (AI AND (deep OR (neural AND (network OR "
    "(backprop OR (gradient AND descent))))))) "
    "NOT (cat OR dog) AND NOT (bird OR fish)"
)

SEARCH_VECTOR_SYNTAX_INJECTION = (
    "\"exact phrase with \\\"escaped\\\" quotes\" "
    "site:arxiv.org filetype:pdf intitle:\"\\\"nested\\\"\" "
    "before:2025-01-01 after:2024-01-01"
)

# ── HMAC Signature for Reconciliation ────────────────────────
HMAC_SECRET = os.environ.get("PAYLOAD_HMAC_SECRET", "sovereign-gateway-default-key")


def compute_hmac(payload_bytes: bytes) -> str:
    return hmac.new(HMAC_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()


# ── Deep-tissue injection with vector isolation ──────────────
DEEP_INJECTIONS = {
    "pdf-engine": {
        "base_url": "http://localhost:8000",
        "captures": [
            {"name": "health", "method": "GET", "path": "/v1/health", "body": None, "required": True},
            {"name": "vec_font_corrupted", "method": "POST", "path": "/v1/convert", "body": None,
             "pdf_vector": VECTOR_FONT_CORRUPTED, "vector_name": "V1_FONT_CORRUPTED", "required": True},
            {"name": "vec_encryption_malformed", "method": "POST", "path": "/v1/convert", "body": None,
             "pdf_vector": VECTOR_ENCRYPTION_MALFORMED, "vector_name": "V2_ENCRYPTION_MALFORMED", "required": True},
            {"name": "vec_null_byte", "method": "POST", "path": "/v1/convert", "body": None,
             "pdf_vector": VECTOR_NULL_BYTE_INJECTION, "vector_name": "V3_NULL_BYTE_INJECTION", "required": True},
            {"name": "vec_structural", "method": "POST", "path": "/v1/convert", "body": None,
             "pdf_vector": VECTOR_STRUCTURAL_CORRUPTION, "vector_name": "V4_STRUCTURAL_CORRUPTION", "required": True},
            {"name": "vec_unicode_text", "method": "POST", "path": "/v1/convert", "body": None,
             "pdf_vector": VECTOR_UNICODE_TEXT_RENDERING, "vector_name": "V5_UNICODE_TEXT_RENDERING", "required": True},
        ],
    },
    "scholarsearch": {
        "base_url": "http://localhost:3001",
        "captures": [
            {"name": "health", "method": "GET", "path": "/health", "body": None, "required": True},
            {"name": "vec_extreme_unicode", "method": "POST", "path": "/api/search/sync",
             "body": {"raw_query": SEARCH_VECTOR_EXTREME_UNICODE},
             "vector_name": "V6_EXTREME_UNICODE", "required": True},
            {"name": "vec_boolean_nesting", "method": "POST", "path": "/api/search/sync",
             "body": {"raw_query": SEARCH_VECTOR_BOOLEAN_NESTING},
             "vector_name": "V7_BOOLEAN_NESTING", "required": True},
            {"name": "vec_syntax_injection", "method": "POST", "path": "/api/search/sync",
             "body": {"raw_query": SEARCH_VECTOR_SYNTAX_INJECTION},
             "vector_name": "V8_SYNTAX_INJECTION", "required": True},
        ],
    },
}

NOISE_KEYS = {
    "self", "cls", "args", "kwargs", "return", "value", "name", "path",
    "type", "id", "key", "item", "data", "result", "error", "message",
    "status", "code", "url", "method", "host", "port", "scheme",
    "timeout", "headers", "cookies", "params", "json", "text",
    "content", "encoding", "stream", "hooks", "auth", "verify",
    "cert", "proxies", "allow_redirects", "follow_redirects",
}


def extract_dict_keys_from_file(filepath: Path) -> set[str]:
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    keys = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                keys.add(node.slice.value)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                if node.args and isinstance(node.args[0], ast.Constant):
                    if isinstance(node.args[0].value, str):
                        keys.add(node.args[0].value)
    return keys


def extract_typescript_keys_from_file(filepath: Path) -> set[str]:
    try:
        source = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()
    keys = set()
    for line in source.split("\n"):
        keys.update(re.findall(r'\[[\'"]([\w_]+)[\'"]\]', line))
        keys.update(re.findall(r'\.get\([\'"]([\w_]+)[\'"]\)', line))
    return keys


def extract_ast_keys(service: str) -> set[str]:
    all_keys = set()
    for scan_path in SCAN_PATHS.get(service, []):
        if not scan_path.exists():
            continue
        for py_file in scan_path.rglob("*.py"):
            if "test" in py_file.name.lower():
                continue
            all_keys.update(extract_dict_keys_from_file(py_file))
        for ts_file in scan_path.rglob("*.ts"):
            if "test" in ts_file.name.lower() or ".d.ts" in ts_file.name:
                continue
            all_keys.update(extract_typescript_keys_from_file(ts_file))
    return all_keys


def _extract_nested_keys(data: dict, keys: set, prefix: str) -> None:
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        keys.add(full_key)
        if isinstance(v, dict):
            _extract_nested_keys(v, keys, full_key)
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            _extract_nested_keys(v[0], keys, f"{full_key}[]")


def capture_deep_live_keys(service: str) -> tuple[set[str], list[str], list[str]]:
    """
    Inject vector-isolated pathological payloads into core endpoints.
    Returns (keys, errors, vector_names). If errors is non-empty, pipeline MUST arrest.
    """
    config = DEEP_INJECTIONS.get(service)
    if not config:
        return set(), [f"No injection config for {service}"], []

    all_keys = set()
    errors = []
    vector_names = []
    base_url = config["base_url"]

    for capture in config["captures"]:
        required = capture.get("required", False)
        vec_name = capture.get("vector_name")
        if vec_name:
            vector_names.append(vec_name)

        try:
            with httpx.Client(base_url=base_url, timeout=10) as client:
                if capture["method"] == "GET":
                    resp = client.get(capture["path"])
                elif capture.get("pdf_vector"):
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                        f.write(capture["pdf_vector"])
                        f.seek(0)
                        resp = client.post(
                            capture["path"],
                            files={"file": ("test.pdf", f, "application/pdf")},
                        )
                else:
                    resp = client.post(capture["path"], json=capture.get("body"))

                if resp.status_code in (200, 202):
                    data = resp.json()
                    if isinstance(data, dict):
                        all_keys.update(data.keys())
                        _extract_nested_keys(data, all_keys, prefix="")
                    print(f"  CAPTURED {capture['name']}: {len(data.keys()) if isinstance(data, dict) else 0} keys")
                else:
                    msg = f"HTTP {resp.status_code} from {capture['name']}"
                    if required:
                        errors.append(msg)
                        print(f"  FATAL: {msg}")
                    else:
                        print(f"  PARTIAL: {msg}")
        except Exception as e:
            msg = f"{capture['name']}: {e}"
            if required:
                errors.append(msg)
                print(f"  FATAL: {msg}")
            else:
                print(f"  SKIP: {msg}")

    return all_keys, errors, vector_names


def intersect_with_live(ast_keys: set[str], live_keys: set[str]) -> set[str]:
    direct_match = set()
    for ast_key in ast_keys:
        if ast_key in live_keys:
            direct_match.add(ast_key)
        for live_key in live_keys:
            if "." in live_key:
                top_level = live_key.split(".")[0]
                if ast_key == top_level:
                    direct_match.add(ast_key)
            if live_key.endswith(f".{ast_key}"):
                direct_match.add(ast_key)
    return {k for k in direct_match if k not in NOISE_KEYS and len(k) >= 2}


def generate_schema_contracts(intersected: dict) -> dict:
    contracts = {}
    for service, keys in intersected.items():
        contracts[service] = {
            "ingested_top_level": sorted([k for k in keys if "." not in k]),
            "ingested_nested": sorted([k for k in keys if "." in k]),
        }
    return contracts


def main() -> int:
    all_errors = []

    result = {
        "extracted_at": __import__("datetime").datetime.now().isoformat(),
        "method": "vector_isolated_toxicity_matrices",
        "ast_keys": {},
        "live_keys": {},
        "intersected_keys": {},
        "schema_contracts": {},
        "vector_matrix": {},
    }

    for service in SCAN_PATHS:
        ast_keys = extract_ast_keys(service)
        live_keys, errors, vector_names = capture_deep_live_keys(service)

        all_errors.extend(errors)

        if not live_keys:
            all_errors.append(f"{service}: Live injection returned zero keys")

        intersected = intersect_with_live(ast_keys, live_keys)

        result["ast_keys"][service] = sorted(ast_keys)
        result["live_keys"][service] = sorted(live_keys)
        result["intersected_keys"][service] = sorted(intersected)
        result["vector_matrix"][service] = {
            "vectors_tested": vector_names,
            "total_vectors": len(vector_names),
            "failures": [e for e in errors if service in e],
        }

        print(f"{service}:")
        print(f"  AST keys: {len(ast_keys)}")
        print(f"  Live keys: {len(live_keys)}")
        print(f"  Intersected: {len(intersected)}")
        print(f"  Vectors: {len(vector_names)} tested")

    if all_errors:
        print(f"\nSOVEREIGN GATEWAY DENIAL: {len(all_errors)} fatal error(s):")
        for e in all_errors:
            print(f"  FATAL: {e}")
        print("Pipeline arrested. Blind deployment blocked.")
        return 1

    result["schema_contracts"] = generate_schema_contracts(result["intersected_keys"])

    output_path = Path("tests/ingested_fields.json")
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWritten to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
