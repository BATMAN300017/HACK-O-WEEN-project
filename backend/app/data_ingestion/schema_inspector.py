"""
Dataset Schema Inspector & Validation Subsystem.

Provides deep schema inspection, data type detection, missing value profiling,
and security verification of label isolation without loading entire datasets into memory.
"""

import os
from typing import Dict, Any, List, Optional
import pandas as pd

from app.data_ingestion.label_isolation import PROTECTED_LABEL_FIELDS

class SchemaInspector:
    """Inspects files and datasets for schema conformance and security isolation."""

    @staticmethod
    def inspect_file(file_path: str, sample_rows: int = 100) -> Dict[str, Any]:
        """Inspects CSV or Parquet file structure and verifies label isolation posture."""
        if not os.path.exists(file_path):
            return {
                "file_path": file_path,
                "status": "FILE_NOT_FOUND",
                "exists": False
            }

        file_size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".parquet":
            import pyarrow.parquet as pq
            pq_file = pq.ParquetFile(file_path)
            schema = pq_file.schema.names
            total_rows = pq_file.metadata.num_rows
            sample_df = next(pq_file.iter_batches(batch_size=sample_rows)).to_pandas()
        elif ext in (".csv", ".tsv", ".txt"):
            sample_df = pd.read_csv(file_path, nrows=sample_rows)
            schema = list(sample_df.columns)
            # Estimate total lines
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                total_rows = sum(1 for _ in f) - 1
        else:
            return {"file_path": file_path, "status": "UNSUPPORTED_FORMAT", "format": ext}

        # Analyze column data types and missing percentages
        columns_profile = []
        for col in schema:
            col_series = sample_df[col]
            missing_pct = round((col_series.isnull().sum() / len(sample_df)) * 100, 2)
            dtype_str = str(col_series.dtype)
            is_protected = col.lower() in PROTECTED_LABEL_FIELDS
            columns_profile.append({
                "column_name": col,
                "data_type": dtype_str,
                "missing_percentage": missing_pct,
                "is_protected_label": is_protected,
                "isolation_requirement": "STRIP_BEFORE_PIPELINE_A" if is_protected else "ALLOWED_IN_PIPELINE_A"
            })

        protected_detected = [c["column_name"] for c in columns_profile if c["is_protected_label"]]

        return {
            "file_path": file_path,
            "format": ext.replace(".", "").upper(),
            "file_size_mb": file_size_mb,
            "estimated_total_rows": total_rows,
            "sample_rows_analyzed": len(sample_df),
            "columns_count": len(schema),
            "columns": columns_profile,
            "protected_labels_detected": protected_detected,
            "isolation_status": "REQUIRES_ISOLATION_STRIPPING" if protected_detected else "LABEL_FREE"
        }
