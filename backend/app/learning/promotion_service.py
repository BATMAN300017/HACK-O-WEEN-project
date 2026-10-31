"""
Model Promotion Service for SentinelFlow AI.

Supports dual promotion paradigms:
1. MANUAL APPROVAL (Default):
   Lifecycle: TRAINED -> EVALUATED -> AWAITING_APPROVAL -> APPROVED -> ACTIVE -> RETIRED.
   Requires explicit analyst/admin sign-off with recorded audit trail.

2. AUTOMATIC PROMOTION (Optional, Admin-Governed):
   Evaluates candidate model against independent evaluation benchmarks.
   Verifies precision, recall, PR-AUC, F1, and maximum false positive rate.
   Blocks promotion if any threshold is unmet or if validation is not independent.
   Can be disabled immediately by an administrator.
"""

import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import sqlite3
from app.utils.time import utc_now_iso
from app.utils.json_utils import safe_json_loads
from app.core.logging import logger

DEFAULT_PROMOTION_THRESHOLDS = {
    "min_precision": 0.70,
    "min_recall": 0.65,
    "min_pr_auc": 0.75,
    "max_fpr": 0.05,
    "min_f1": 0.70,
    "min_evaluation_samples": 20,
    "require_independent_validation": True
}

class ModelPromotionService:
    """Enterprise model governance and promotion subsystem."""

    @staticmethod
    def get_promotion_policy(conn: sqlite3.Connection) -> Dict[str, Any]:
        """Retrieves the active promotion policy from the database."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT mode, min_precision, min_recall, min_pr_auc, max_fpr, min_f1,
                   require_independent_validation, min_evaluation_samples, is_active, updated_by, updated_at
            FROM model_promotion_policy
            WHERE id = 'current_policy'
        """)
        row = cursor.fetchone()
        if not row:
            return {
                "mode": "MANUAL",
                **DEFAULT_PROMOTION_THRESHOLDS,
                "is_active": True,
                "updated_by": "System Default",
                "updated_at": utc_now_iso()
            }
        
        # Handle AdaptiveRow or sqlite3.Row
        d = dict(row) if hasattr(row, "keys") else {
            "mode": row[0], "min_precision": float(row[1]), "min_recall": float(row[2]),
            "min_pr_auc": float(row[3]), "max_fpr": float(row[4]), "min_f1": float(row[5]),
            "require_independent_validation": bool(row[6]), "min_evaluation_samples": int(row[7]),
            "is_active": bool(row[8]), "updated_by": row[9], "updated_at": str(row[10])
        }
        return d

    @staticmethod
    def update_promotion_policy(conn: sqlite3.Connection, policy_update: Dict[str, Any], actor_name: str) -> Dict[str, Any]:
        """Updates the promotion policy mode and evaluation thresholds."""
        cursor = conn.cursor()
        mode = policy_update.get("mode", "MANUAL").upper()
        if mode not in ("MANUAL", "AUTOMATIC"):
            raise ValueError(f"Invalid promotion mode: {mode}. Must be 'MANUAL' or 'AUTOMATIC'.")

        min_prec = float(policy_update.get("min_precision", 0.70))
        min_rec = float(policy_update.get("min_recall", 0.65))
        min_pr_auc = float(policy_update.get("min_pr_auc", 0.75))
        max_fpr = float(policy_update.get("max_fpr", 0.05))
        min_f1 = float(policy_update.get("min_f1", 0.70))
        req_indep = bool(policy_update.get("require_independent_validation", True))
        min_samples = int(policy_update.get("min_evaluation_samples", 20))
        is_active = bool(policy_update.get("is_active", True))
        now = utc_now_iso()

        cursor.execute("""
            UPDATE model_promotion_policy
            SET mode = ?, min_precision = ?, min_recall = ?, min_pr_auc = ?,
                max_fpr = ?, min_f1 = ?, require_independent_validation = ?,
                min_evaluation_samples = ?, is_active = ?, updated_by = ?, updated_at = ?
            WHERE id = 'current_policy'
        """, (mode, min_prec, min_rec, min_pr_auc, max_fpr, min_f1, req_indep, min_samples, is_active, actor_name, now))

        # Record policy change in audit log
        audit_id = f"AUD-POL-{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO model_promotion_audit (id, model_version, action, mode, actor_id, actor_name, metrics_evaluated_json, thresholds_checked_json, reason, created_at)
            VALUES (?, 'ALL_MODELS', 'UPDATE_POLICY', ?, NULL, ?, '{}', ?, ?, ?)
        """, (
            audit_id, mode, actor_name,
            json.dumps(policy_update),
            f"Promotion policy updated to {mode} by {actor_name}",
            now
        ))

        return ModelPromotionService.get_promotion_policy(conn)

    @staticmethod
    def evaluate_model_for_promotion(
        conn: sqlite3.Connection,
        model_version: str,
        evaluation_metrics: Dict[str, Any],
        is_independent_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Validates evaluation metrics against configured promotion thresholds.
        Checks precision, recall, PR-AUC, F1, FPR, and sample size.
        """
        policy = ModelPromotionService.get_promotion_policy(conn)
        checks = {}
        failures = []

        # 1. Independent validation requirement
        if policy.get("require_independent_validation") and not is_independent_validation:
            failures.append("Model evaluation was performed on training set rather than independent held-out validation vault.")

        # 2. Sample size
        samples = evaluation_metrics.get("training_samples", evaluation_metrics.get("samples_count", 0))
        min_samples = policy.get("min_evaluation_samples", 20)
        checks["samples_check"] = {"actual": samples, "required": min_samples, "passed": samples >= min_samples}
        if samples < min_samples:
            failures.append(f"Insufficient evaluation samples ({samples} < required {min_samples}).")

        # 3. Precision
        prec = float(evaluation_metrics.get("precision", 0.0))
        min_prec = float(policy.get("min_precision", 0.70))
        checks["precision_check"] = {"actual": prec, "required": min_prec, "passed": prec >= min_prec}
        if prec < min_prec:
            failures.append(f"Precision below threshold ({prec:.3f} < {min_prec:.3f}).")

        # 4. Recall
        rec = float(evaluation_metrics.get("recall", 0.0))
        min_rec = float(policy.get("min_recall", 0.65))
        checks["recall_check"] = {"actual": rec, "required": min_rec, "passed": rec >= min_rec}
        if rec < min_rec:
            failures.append(f"Recall below threshold ({rec:.3f} < {min_rec:.3f}).")

        # 5. F1-Score
        f1 = float(evaluation_metrics.get("f1", 0.0))
        min_f1 = float(policy.get("min_f1", 0.70))
        checks["f1_check"] = {"actual": f1, "required": min_f1, "passed": f1 >= min_f1}
        if f1 < min_f1:
            failures.append(f"F1-Score below threshold ({f1:.3f} < {min_f1:.3f}).")

        # 6. PR-AUC
        pr_auc = float(evaluation_metrics.get("pr_auc", 0.0))
        min_auc = float(policy.get("min_pr_auc", 0.75))
        checks["pr_auc_check"] = {"actual": pr_auc, "required": min_auc, "passed": pr_auc >= min_auc}
        if pr_auc < min_auc:
            failures.append(f"PR-AUC below threshold ({pr_auc:.3f} < {min_auc:.3f}).")

        # 7. False Positive Rate
        fpr = float(evaluation_metrics.get("false_positive_rate", evaluation_metrics.get("fpr", 0.0)))
        max_fpr = float(policy.get("max_fpr", 0.05))
        checks["fpr_check"] = {"actual": fpr, "maximum_allowed": max_fpr, "passed": fpr <= max_fpr}
        if fpr > max_fpr:
            failures.append(f"False Positive Rate exceeds limit ({fpr:.3f} > {max_fpr:.3f}).")

        passed = len(failures) == 0
        return {
            "model_version": model_version,
            "policy_mode": policy.get("mode", "MANUAL"),
            "passed": passed,
            "checks": checks,
            "failure_reasons": failures,
            "can_auto_promote": passed and policy.get("mode") == "AUTOMATIC",
            "evaluated_at": utc_now_iso()
        }

    @staticmethod
    def approve_model_manually(conn: sqlite3.Connection, model_version: str, approver_name: str, rationale: str) -> Dict[str, Any]:
        """Manually approves an evaluated model for production activation."""
        cursor = conn.cursor()
        now = utc_now_iso()

        # Update model version status in DB
        cursor.execute("""
            UPDATE model_versions
            SET approval_status = 'APPROVED', approved_by = ?, approved_at = ?, status = 'APPROVED', updated_at = ?
            WHERE version = ? OR id = ?
        """, (approver_name, now, now, model_version, model_version))

        # Log decision
        audit_id = f"AUD-APP-{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO model_promotion_audit (id, model_version, action, mode, actor_id, actor_name, metrics_evaluated_json, thresholds_checked_json, reason, created_at)
            VALUES (?, ?, 'APPROVED', 'MANUAL', NULL, ?, '{}', '{}', ?, ?)
        """, (audit_id, model_version, approver_name, rationale or "Manual approval granted by authorized analyst", now))

        return {
            "success": True,
            "model_version": model_version,
            "approval_status": "APPROVED",
            "approved_by": approver_name,
            "approved_at": now
        }

    @staticmethod
    def activate_model(conn: sqlite3.Connection, model_version: str, activator_name: str) -> Dict[str, Any]:
        """Activates an approved model to score operational production transactions."""
        cursor = conn.cursor()
        now = utc_now_iso()

        # Verify model exists and is approved
        cursor.execute("SELECT version, status, approval_status, evaluation_metrics_json FROM model_versions WHERE version = ? OR id = ?", (model_version, model_version))
        row = cursor.fetchone()
        if not row:
            return {"success": False, "message": f"Model {model_version} not found."}

        app_status = row[2] if len(row) > 2 else "APPROVED"
        if app_status != "APPROVED":
            return {
                "success": False,
                "message": f"Model {model_version} cannot be activated: approval status is '{app_status}' (must be 'APPROVED')."
            }

        # Deactivate previous active models
        cursor.execute("UPDATE model_versions SET is_active = 0, status = 'RETIRED', updated_at = ? WHERE is_active = 1", (now,))

        # Activate selected model
        cursor.execute("""
            UPDATE model_versions
            SET is_active = 1, status = 'ACTIVE', promoted_by = ?, promoted_at = ?, updated_at = ?
            WHERE version = ? OR id = ?
        """, (activator_name, now, now, model_version, model_version))

        # Log audit trail
        audit_id = f"AUD-ACT-{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO model_promotion_audit (id, model_version, action, mode, actor_id, actor_name, metrics_evaluated_json, thresholds_checked_json, reason, created_at)
            VALUES (?, ?, 'ACTIVATED', 'MANUAL', NULL, ?, '{}', '{}', ?, ?)
        """, (audit_id, model_version, activator_name, f"Model activated for operational scoring by {activator_name}", now))

        return {
            "success": True,
            "active_version": model_version,
            "status": "ACTIVE",
            "activated_by": activator_name,
            "activated_at": now
        }

    @staticmethod
    def retire_model(conn: sqlite3.Connection, model_version: str, actor_name: str, reason: str) -> Dict[str, Any]:
        """Retires a model from production scoring."""
        cursor = conn.cursor()
        now = utc_now_iso()

        cursor.execute("""
            UPDATE model_versions
            SET is_active = 0, status = 'RETIRED', updated_at = ?
            WHERE version = ? OR id = ?
        """, (now, model_version, model_version))

        audit_id = f"AUD-RET-{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO model_promotion_audit (id, model_version, action, mode, actor_id, actor_name, metrics_evaluated_json, thresholds_checked_json, reason, created_at)
            VALUES (?, ?, 'RETIRED', 'MANUAL', NULL, ?, '{}', '{}', ?, ?)
        """, (audit_id, model_version, actor_name, reason or "Model retired by administrator", now))

        return {
            "success": True,
            "model_version": model_version,
            "status": "RETIRED",
            "retired_by": actor_name,
            "retired_at": now
        }

    @staticmethod
    def get_promotion_audit_trail(conn: sqlite3.Connection, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the full audit history of model approvals, activations, and policy changes."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, model_version, action, mode, actor_name, metrics_evaluated_json, thresholds_checked_json, reason, created_at
            FROM model_promotion_audit
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        audits = []
        for r in rows:
            d = dict(r) if hasattr(r, "keys") else {
                "id": r[0], "model_version": r[1], "action": r[2], "mode": r[3],
                "actor_name": r[4], "metrics_evaluated": safe_json_loads(r[5], {}),
                "thresholds_checked": safe_json_loads(r[6], {}), "reason": r[7], "created_at": str(r[8])
            }
            audits.append(d)
        return audits
