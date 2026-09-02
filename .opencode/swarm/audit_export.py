"""
Audit Export Script
Exports Swarm Cascade hash chain as CSV/JSON for external verification.
Allows auditors to independently verify cryptographic integrity.
"""

import csv
import json
import sqlite3
import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


@dataclass
class AuditRecord:
    row_id: int
    query_hash: str
    evidence_tier: str
    execution_time: float
    report_json: str
    previous_hash: Optional[str]
    current_hash: str
    created_at: float
    persisted_at: float
    schema_version: int

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "query_hash": self.query_hash,
            "evidence_tier": self.evidence_tier,
            "execution_time": self.execution_time,
            "report_data": json.loads(self.report_json),
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash,
            "created_at": self.created_at,
            "persisted_at": self.persisted_at,
            "schema_version": self.schema_version,
        }


@dataclass
class AuditExport:
    export_timestamp: float
    total_records: int
    chain_valid: bool
    first_broken_row: Optional[int]
    records: List[AuditRecord]

    def to_dict(self) -> dict:
        return {
            "metadata": {
                "export_timestamp": self.export_timestamp,
                "total_records": self.total_records,
                "chain_valid": self.chain_valid,
                "first_broken_row": self.first_broken_row,
                "verification_instructions": self._get_verification_instructions(),
            },
            "records": [r.to_dict() for r in self.records],
        }

    def _get_verification_instructions(self) -> dict:
        return {
            "description": "To verify hash chain integrity, recompute SHA-256 hashes",
            "algorithm": "SHA-256",
            "formula": "current_hash = SHA256(report_json + previous_hash)",
            "genesis": "First record has previous_hash = null",
            "validation": "Each record's previous_hash must match the prior record's current_hash",
        }


class AuditExporter:
    """
    Exports Swarm Cascade data for external audit verification.
    """

    def __init__(self, db_path: str):
        self._db_path = db_path

    def export_full_chain(self) -> AuditExport:
        """Export complete hash chain with validation."""
        db = sqlite3.connect(self._db_path)
        cursor = db.cursor()

        cursor.execute("""
            SELECT id, query_hash, evidence_tier, execution_time,
                   report_json, previous_hash, current_hash,
                   created_at, persisted_at, schema_version
            FROM swarm_reports
            ORDER BY id
        """)

        records = []
        for row in cursor.fetchall():
            records.append(AuditRecord(
                row_id=row[0],
                query_hash=row[1],
                evidence_tier=row[2],
                execution_time=row[3],
                report_json=row[4],
                previous_hash=row[5],
                current_hash=row[6],
                created_at=row[7],
                persisted_at=row[8],
                schema_version=row[9],
            ))

        chain_valid, first_broken = self._validate_chain(records)

        db.close()

        return AuditExport(
            export_timestamp=time.time(),
            total_records=len(records),
            chain_valid=chain_valid,
            first_broken_row=first_broken,
            records=records,
        )

    def export_csv(self, output_path: str) -> str:
        """Export to CSV format."""
        export = self.export_full_chain()

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            writer.writerow([
                'row_id', 'query_hash', 'evidence_tier', 'execution_time',
                'previous_hash', 'current_hash', 'created_at', 'persisted_at',
                'schema_version', 'report_json_hash'
            ])

            for record in export.records:
                report_hash = hashlib.sha256(record.report_json.encode()).hexdigest()
                writer.writerow([
                    record.row_id,
                    record.query_hash,
                    record.evidence_tier,
                    record.execution_time,
                    record.previous_hash or '',
                    record.current_hash,
                    record.created_at,
                    record.persisted_at,
                    record.schema_version,
                    report_hash,
                ])

        return output_path

    def export_json(self, output_path: str) -> str:
        """Export to JSON format."""
        export = self.export_full_chain()

        with open(output_path, 'w') as f:
            json.dump(export.to_dict(), f, indent=2)

        return output_path

    def generate_verification_script(self, output_path: str) -> str:
        """Generate a standalone Python verification script."""
        script = '''#!/usr/bin/env python3
"""
Standalone Hash Chain Verification Script
Generated by Swarm Cascade Audit Exporter

Run: python verify_chain.py <export.json>
"""

import json
import hashlib
import sys


def compute_hash(report_json: str, previous_hash: str | None) -> str:
    data = report_json
    if previous_hash:
        data += previous_hash
    return hashlib.sha256(data.encode()).hexdigest()


def verify_chain(export_data: dict) -> bool:
    records = export_data.get("records", [])
    if not records:
        print("No records to verify")
        return True

    previous_hash = None
    valid = True

    for i, record in enumerate(records):
        report_json = json.dumps(record["report_data"], sort_keys=True)
        expected_hash = compute_hash(report_json, previous_hash)

        if record["current_hash"] != expected_hash:
            print(f"BREAK at row {record['row_id']}:")
            print(f"  Expected: {expected_hash}")
            print(f"  Found:    {record['current_hash']}")
            valid = False
            break

        if record["previous_hash"] != previous_hash:
            print(f"Chain link broken at row {record['row_id']}")
            valid = False
            break

        previous_hash = record["current_hash"]

    return valid


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify_chain.py <export.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    if verify_chain(data):
        print("VALID: Hash chain integrity verified")
        print(f"Total records: {len(data.get('records', []))}")
        sys.exit(0)
    else:
        print("INVALID: Hash chain compromised")
        sys.exit(1)
'''

        with open(output_path, 'w') as f:
            f.write(script)

        return output_path

    def _validate_chain(self, records: List[AuditRecord]) -> tuple[bool, Optional[int]]:
        """Validate hash chain integrity."""
        previous_hash = None

        for record in records:
            report_json = json.dumps(
                json.loads(record.report_json), sort_keys=True
            )
            expected_hash = compute_hash(report_json, previous_hash)

            if record.current_hash != expected_hash:
                return False, record.row_id

            if record.previous_hash != previous_hash:
                return False, record.row_id

            previous_hash = record.current_hash

        return True, None


def compute_hash(report_json: str, previous_hash: Optional[str]) -> str:
    data = report_json
    if previous_hash:
        data += previous_hash
    return hashlib.sha256(data.encode()).hexdigest()
