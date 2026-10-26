# ============================================================
# OMNICARE AI — CLINICAL COPILOT TEST SUITE
# ============================================================

import sys
import os
import unittest
from datetime import datetime, timezone

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from services.medical_record_normalizer import (
    parse_strict_date,
    format_iso_date,
    extract_followup_date,
    normalize_numeric_value,
    parse_blood_pressure,
)
from services.clinical_rules_engine import (
    evaluate_investigation,
    check_followup_overdue,
)
from services.clinical_query_service import (
    generate_evidence_answer,
    retrieve_query_evidence,
)
from services.clinical_audit_service import (
    log_clinical_event,
    get_doctor_audit_logs,
)
from utils.supabase_client import supabase


REAL_DOCTOR_ID = "ea83806c-f033-4012-944b-22098514d9e9"
REAL_PATIENT_ID = "a8360a17-d8a0-4524-bcc2-b1b4775e5c4f"
FAKE_DOCTOR_ID = "00000000-0000-0000-0000-000000000000"
UNAUTHORIZED_PATIENT_ID = "f623d596-3515-409c-840d-6505012ef07d"


class TestClinicalCopilot(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    # --------------------------------------------------------
    # 1. AUTHENTICATION & ACCESS CONTROL
    # --------------------------------------------------------

    def test_01_unauthenticated_page_access_redirects(self):
        """Unauthenticated requests to clinical copilot page redirect to login."""
        res1 = self.client.get("/doctor/clinical-copilot")
        self.assertEqual(res1.status_code, 302)
        self.assertIn("/doctor/login", res1.headers.get("Location", ""))

        res2 = self.client.get("/doctor/ai-assistant")
        self.assertEqual(res2.status_code, 302)
        self.assertIn("/doctor/login", res2.headers.get("Location", ""))

    def test_02_unauthenticated_api_endpoints_return_401(self):
        """Unauthenticated requests to all copilot APIs return 401 Unauthorized."""
        endpoints = [
            ("GET", "/doctor/clinical-copilot/api/briefing"),
            ("POST", "/doctor/clinical-copilot/api/query"),
            ("GET", "/doctor/clinical-copilot/api/trends"),
            ("GET", "/doctor/clinical-copilot/api/medication-safety"),
            ("POST", "/doctor/clinical-copilot/api/alert-review"),
        ]
        for method, endpoint in endpoints:
            if method == "GET":
                res = self.client.get(endpoint)
            else:
                res = self.client.post(endpoint, json={"question": "test"})
            self.assertEqual(
                res.status_code, 401,
                f"Endpoint {endpoint} returned {res.status_code} instead of 401"
            )
            data = res.get_json()
            self.assertFalse(data.get("success", True))

    def test_03_authorized_doctor_loads_copilot_page(self):
        """Authorized doctor session renders Clinical Copilot template cleanly."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = REAL_DOCTOR_ID

        res = self.client.get("/doctor/clinical-copilot")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("Clinical Copilot", html)
        self.assertIn("Practice-Level AI Assistant", html)
        self.assertIn("Priority Patients", html)
        self.assertIn("Cross-Patient Trends", html)

    # --------------------------------------------------------
    # 2. BRIEFING & SCOPE AUTHORIZATION
    # --------------------------------------------------------

    def test_04_briefing_api_authorized_returns_real_metrics(self):
        """Authorized doctor briefing returns real database metrics."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = REAL_DOCTOR_ID

        res = self.client.get("/doctor/clinical-copilot/api/briefing")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Check required fields
        self.assertIn("scope", data)
        self.assertIn("abnormal_reports", data)
        self.assertIn("overdue_followups", data)
        self.assertIn("worsening_trends", data)
        self.assertIn("medication_safety", data)

        # Check scope numbers reflect real active consent
        self.assertGreaterEqual(data["scope"]["authorized_patient_count"], 1)
        self.assertIn("expired_count", data["scope"])
        self.assertIn("revoked_count", data["scope"])

    def test_05_unauthorized_doctor_gets_empty_zero_scope(self):
        """Unauthorized doctor gets 0 authorized patients and empty alert list."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = FAKE_DOCTOR_ID

        res = self.client.get("/doctor/clinical-copilot/api/briefing")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["scope"]["authorized_patient_count"], 0)
        self.assertEqual(len(data["abnormal_reports"]), 0)
        self.assertEqual(len(data["overdue_followups"]), 0)

    # --------------------------------------------------------
    # 3. CROSS-PATIENT CLINICAL QUERY & GROUNDING
    # --------------------------------------------------------

    def test_06_query_api_authorized_execution(self):
        """Authorized query executes, returns grounded answer and structured sources."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = REAL_DOCTOR_ID

        res = self.client.post(
            "/doctor/clinical-copilot/api/query",
            json={"question": "Show overdue follow-ups"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("answer", data)
        self.assertTrue(len(data["answer"]) > 10)
        self.assertIn("results", data)
        self.assertIn("sources", data)
        self.assertTrue(data.get("requires_clinician_review", False))

        # Check source structure
        if data["sources"]:
            src = data["sources"][0]
            self.assertIn("patient_id", src)
            self.assertIn("record_id", src)
            self.assertIn("event_date", src)

    def test_07_query_api_unauthorized_doctor_denied(self):
        """Doctor with no authorized patients gets clear consent denial."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = FAKE_DOCTOR_ID

        res = self.client.post(
            "/doctor/clinical-copilot/api/query",
            json={"question": "Show recent abnormal lab results"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("consent", data["answer"].lower())
        self.assertEqual(len(data["results"]), 0)

    def test_08_alert_review_endpoint_and_authorization(self):
        """Alert review is authorized and recorded in audit log."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = REAL_DOCTOR_ID

        # Valid alert review for authorized patient
        res = self.client.post(
            "/doctor/clinical-copilot/api/alert-review",
            json={
                "alert_id": "test-alert-123",
                "alert_type": "abnormal_report",
                "patient_id": REAL_PATIENT_ID,
                "notes": "Reviewed by clinician"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

        # Unauthorized alert review for restricted patient
        res_unauth = self.client.post(
            "/doctor/clinical-copilot/api/alert-review",
            json={
                "alert_id": "test-alert-456",
                "alert_type": "abnormal_report",
                "patient_id": UNAUTHORIZED_PATIENT_ID,
                "notes": "Attempting unauthorized review"
            }
        )
        self.assertEqual(res_unauth.status_code, 403)

    # --------------------------------------------------------
    # 4. MEDICAL RECORD NORMALIZER TESTS
    # --------------------------------------------------------

    def test_09_normalizer_strict_dates(self):
        """Dates are normalized strictly; ambiguous/invalid dates are rejected."""
        self.assertEqual(format_iso_date("15-10-2026"), "2026-10-15")
        self.assertEqual(format_iso_date("09 Oct 2026"), "2026-10-09")
        self.assertEqual(format_iso_date("2026-10-02"), "2026-10-02")
        self.assertEqual(format_iso_date("October 09, 2026"), "2026-10-09")

        # Invalid calendar dates must return None
        self.assertIsNone(format_iso_date("31-02-2026"))
        self.assertIsNone(format_iso_date("99-99-9999"))
        self.assertIsNone(format_iso_date("not-a-date"))
        self.assertIsNone(format_iso_date(None))

    def test_10_followup_date_extraction(self):
        """Follow-up dates are extracted accurately from text."""
        f_dt = extract_followup_date("09 Oct 2026 (After 7 days) or SOS if breathlessness occurs.")
        self.assertEqual(f_dt, datetime(2026, 10, 9))

        f_dt2 = extract_followup_date("Review on 2026-11-15")
        self.assertEqual(f_dt2, datetime(2026, 11, 15))

        # Relative without calendar date returns None
        self.assertIsNone(extract_followup_date("Review after 2 weeks"))

    def test_11_measurement_normalization(self):
        """Numeric values and BP are parsed safely."""
        self.assertEqual(normalize_numeric_value("142"), 142.0)
        self.assertEqual(normalize_numeric_value(" < 140 mg/dL"), 140.0)
        self.assertIsNone(normalize_numeric_value("Within normal limits"))

        sys, dia = parse_blood_pressure("130/85 mmHg")
        self.assertEqual((sys, dia), (130.0, 85.0))

    # --------------------------------------------------------
    # 5. CLINICAL RULES ENGINE TESTS
    # --------------------------------------------------------

    def test_12_clinical_rules_investigation_evaluation(self):
        """Deterministic evaluation flags abnormal investigations with transparent rules."""
        # Fasting glucose 142 -> diabetes threshold (>= 126)
        fbs_eval = evaluate_investigation("Fasting Blood Glucose", 142, "mg/dL")
        self.assertTrue(fbs_eval["is_abnormal"])
        self.assertEqual(fbs_eval["status"], "high")
        self.assertIn("RULE_FBS_DIABETIC", fbs_eval["rule_id"])

        # HbA1c 8.2% -> poor control (>= 8.0)
        hba1c_eval = evaluate_investigation("HbA1c", 8.2, "%")
        self.assertTrue(hba1c_eval["is_abnormal"])
        self.assertEqual(hba1c_eval["status"], "high")

        # Normal glucose 85 -> normal
        normal_eval = evaluate_investigation("Fasting Blood Glucose", 85, "mg/dL")
        self.assertFalse(normal_eval["is_abnormal"])
        self.assertEqual(normal_eval["status"], "normal")

        # Stage 2 hypertension 145/95 -> high
        bp_eval = evaluate_investigation("Blood Pressure", "145/95", "mmHg")
        self.assertTrue(bp_eval["is_abnormal"])
        self.assertEqual(bp_eval["status"], "high")

    def test_13_overdue_followup_rule(self):
        """Overdue follow-up rule computes days overdue and severity."""
        check = check_followup_overdue("2026-10-09", datetime(2026, 10, 24))
        self.assertIsNotNone(check)
        self.assertTrue(check["is_overdue"])
        self.assertEqual(check["days_overdue"], 15)
        self.assertEqual(check["severity"], "high")

        # Future date is not overdue
        future_check = check_followup_overdue("2026-11-01", datetime(2026, 10, 24))
        self.assertIsNone(future_check)

    # --------------------------------------------------------
    # 6. RELIABILITY & GEMINI FALLBACK
    # --------------------------------------------------------

    def test_14_gemini_fallback_deterministic_summary(self):
        """When Gemini is unavailable, deterministic answer is produced without crashing."""
        import services.clinical_query_service as cqs
        orig_client = cqs.gemini_client
        try:
            cqs.gemini_client = None  # Simulate Gemini offline / quota failure
            sample_results = [{
                "patient_name": "Test Patient",
                "test_name": "Fasting Blood Glucose",
                "parameter": "FBS",
                "value": 142,
                "unit": "mg/dL",
                "date": "2026-10-02",
                "source": "Record 1b21c402"
            }]
            ans = generate_evidence_answer(
                question="Show abnormal results",
                results=sample_results,
                sources=[],
                intent="abnormal_labs",
                limitations=[]
            )
            self.assertIn("Test Patient", ans)
            self.assertIn("authorized medical records", ans.lower())
        finally:
            cqs.gemini_client = orig_client

    # --------------------------------------------------------
    # 7. AUDIT TRAIL PERSISTENCE
    # --------------------------------------------------------

    def test_15_audit_trail_logging_and_retrieval(self):
        """Audit events are logged and retrievable for doctor access-audit view."""
        log_entry = log_clinical_event(
            doctor_id=REAL_DOCTOR_ID,
            action="TEST_COPILOT_ACTION",
            patient_ids=[REAL_PATIENT_ID],
            status="SUCCESS",
            metadata={"test_key": "test_val"}
        )
        self.assertIn("id", log_entry)

        logs = get_doctor_audit_logs(REAL_DOCTOR_ID, limit=10)
        self.assertTrue(len(logs) > 0)
        actions = [l["action"] for l in logs]
        self.assertIn("TEST_COPILOT_ACTION", actions)

    # --------------------------------------------------------
    # 8. REGRESSION VERIFICATION OF EXISTING ROUTES
    # --------------------------------------------------------

    def test_16_regression_existing_app_routes(self):
        """Preserve existing app endpoints without breaking changes."""
        # Home
        res_home = self.client.get("/")
        self.assertEqual(res_home.status_code, 200)

        # Doctor login page
        res_doc_login = self.client.get("/doctor/login")
        self.assertEqual(res_doc_login.status_code, 200)

        # Patient login page
        res_pat_login = self.client.get("/patient/login")
        self.assertEqual(res_pat_login.status_code, 200)

        # Access audit page for authenticated doctor
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = REAL_DOCTOR_ID
        res_audit = self.client.get("/doctor/access-audit")
        self.assertEqual(res_audit.status_code, 200)
        self.assertIn("Access &amp; Audit Log", res_audit.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
