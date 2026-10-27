import unittest
import sqlite3
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BACKEND_DIR)

from app.core.database import SCHEMA_SQL
from app.repositories.investigation_repository import create_investigation, get_investigation_by_id
from app.services.investigation_service import add_investigation_note, complete_investigation_task, submit_case_disposition
from app.repositories.evidence_repository import create_evidence, list_evidence_for_case

class TestInvestigationWorkflow(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO users (id, username, email, full_name, role, hashed_password, created_at) VALUES ('USR-1', 'sarah', 'sarah@bank.com', 'Sarah Lin', 'investigator', 'hash', '2026-01-01')")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_full_investigation_lifecycle(self):
        # 1. Open investigation
        inv = create_investigation(self.conn, {
            "title": "Suspicious Account Takeover Test",
            "summary": "Rapid outbound transfers to foreign beneficiary",
            "priority": "HIGH",
            "assigned_investigator_id": "USR-1"
        })
        inv_id = inv["id"]
        
        # 2. Add Evidence
        ev = create_evidence(self.conn, {
            "investigation_id": inv_id,
            "evidence_type": "TRANSACTION",
            "description": "Observed $9,500 outgoing wire transfer",
            "observed_facts": {"amount": 9500.0},
            "collector": "Sarah Lin"
        })
        self.assertIsNotNone(ev["integrity_hash"])
        
        evidence_list = list_evidence_for_case(self.conn, inv_id)
        self.assertEqual(len(evidence_list), 1)
        
        # 3. Add Note
        note = add_investigation_note(self.conn, inv_id, "USR-1", "Contacted customer to verify wire authorization.")
        self.assertEqual(note["investigation_id"], inv_id)
        
        # 4. Submit Case Disposition
        disp_res = submit_case_disposition(
            self.conn, inv_id, "USR-1", "Sarah Lin",
            "CONFIRMED_FRAUD", "Customer confirmed credentials were compromised via phishing.",
            requires_peer_review=False
        )
        self.assertEqual(disp_res["status"], "RESOLVED")
        self.assertTrue(disp_res["training_label_eligible"])
        
        # 5. Check Case state
        updated_inv = get_investigation_by_id(self.conn, inv_id)
        self.assertEqual(updated_inv["status"], "RESOLVED")
        self.assertEqual(updated_inv["disposition"], "CONFIRMED_FRAUD")
        
        # 6. Check feedback record created
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM analyst_feedback WHERE investigation_id = ?", (inv_id,))
        fb = cursor.fetchone()
        self.assertIsNotNone(fb)
        self.assertEqual(fb["training_label"], 1)

if __name__ == "__main__":
    unittest.main()
