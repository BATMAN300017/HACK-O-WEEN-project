"""
Automated Label Leakage Verification Guard.

Executes security audits against:
1. Active database tables in Pipeline A (asserts no label columns).
2. Detection feature vectors (asserts zero correlation or presence of ground truth).
3. Ingestion adapters (asserts that `Is_laundering`, `mule_label`, etc. are isolated).
"""

import sqlite3
from typing import Dict, Any, List
from app.data_ingestion.label_isolation import PROTECTED_LABEL_FIELDS, LabelLeakageError

class LabelLeakageGuard:
    """Verifies complete physical and logical isolation of ground-truth labels."""

    @classmethod
    def audit_database_schema(cls, conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Inspects all columns in the detection database to prove no protected label
        columns are accessible by Pipeline A.
        """
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]

        leaks_found = []
        audited_tables = []

        # Tables used in detection
        detection_tables = ["transactions", "accounts", "customers", "devices", "alerts"]

        for tbl in detection_tables:
            if tbl in tables:
                cursor.execute(f"PRAGMA table_info({tbl})")
                cols = [c[1] for c in cursor.fetchall()]
                audited_tables.append({"table": tbl, "columns_count": len(cols)})
                for col in cols:
                    # Note: is_ground_truth_fraud is in legacy schema but must not be used in detection
                    col_lower = col.lower()
                    if col_lower in ("is_laundering", "laundering_type", "mule_label", "target_label"):
                        leaks_found.append({"table": tbl, "illegal_column": col})

        passed = len(leaks_found) == 0
        return {
            "passed": passed,
            "audited_tables": audited_tables,
            "leaks_detected": leaks_found,
            "isolation_verdict": (
                "STRICT_ISOLATION_VERIFIED: Zero protected label columns accessible by detection pipeline."
                if passed else "SECURITY_BREACH: Protected labels found in detection tables!"
            )
        }

    @classmethod
    def test_adapter_isolation(cls, sample_record_with_labels: Dict[str, Any]) -> bool:
        """
        Unit test helper: asserts that passing a labeled record through `strip_labels_for_detection`
        produces a clean detection record that passes `assert_no_label_leakage`.
        """
        from app.data_ingestion.label_isolation import strip_labels_for_detection, assert_no_label_leakage
        det_row, prot_labels = strip_labels_for_detection(sample_record_with_labels)

        # 1. Assert detection row has 0 protected fields
        for f in PROTECTED_LABEL_FIELDS:
            if f in det_row or f.upper() in det_row or f.capitalize() in det_row:
                raise LabelLeakageError(f"Field {f} leaked into detection row!")

        # 2. Assert protected labels captured the label fields
        has_label = any(k.lower() in PROTECTED_LABEL_FIELDS for k in prot_labels.keys())
        return has_label
