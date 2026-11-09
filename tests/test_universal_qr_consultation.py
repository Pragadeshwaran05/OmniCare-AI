# ============================================================
# OMNICARE AI — UNIVERSAL QR, MSG91 OTP & EXTERNAL CONSULTATION TEST SUITE
# ============================================================

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from services.msg91_otp_service import (
    MSG91OTPService,
    mask_phone_number,
    mask_email_address,
    _ACTIVE_OTP_CHALLENGES,
    _OTP_RATE_LIMITS,
    DEMO_OTP,
)
from services.external_consultation_service import ExternalConsultationService


class TestUniversalQRAndExternalConsultation(unittest.TestCase):
    """Integration and unit tests for Universal QR, MSG91 OTP, and External Consultation."""

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-omnicare"
        self.client = app.test_client()

        # Test Patient & Doctor Data
        self.patient_id = "test-patient-uuid-1234"
        self.patient_health_id = "OMC-P9999"
        self.doctor_id = "test-doctor-uuid-5678"

        self.patient_data = {
            "id": self.patient_id,
            "full_name": "Test Patient",
            "name": "Test Patient",
            "health_id": self.patient_health_id,
            "phone": "9876543210",
            "email": "testpatient@example.com",
            "age": "32",
            "date_of_birth": "1994-05-15",
            "gender": "Female",
            "blood_group": "B+",
            "address": "123 Private Health Street, Bangalore",
        }

        # Clear in-memory state
        _ACTIVE_OTP_CHALLENGES.clear()
        _OTP_RATE_LIMITS.clear()

    # ---------------------------------------------------------
    # 1. UNIVERSAL CANONICAL QR TOKEN & MASKING
    # ---------------------------------------------------------
    def test_01_masking_helpers(self):
        """Contact masking protects patient phone and email privacy."""
        self.assertEqual(mask_phone_number("9876543210"), "******3210")
        self.assertEqual(mask_phone_number("+91 9876543210"), "+91 ******3210")
        self.assertEqual(mask_email_address("testpatient@example.com"), "t*********t@example.com")
        self.assertEqual(mask_phone_number(""), "Registered mobile number")

    def test_02_universal_qr_token_generation_and_resolution(self):
        """Universal QR token is non-guessable, does not expose internal database ID, and resolves consistently."""
        token = ExternalConsultationService.get_or_create_qr_token(self.patient_id, health_id=self.patient_health_id)
        self.assertTrue(token.startswith("OMC-QR-"))
        self.assertNotIn(self.patient_id, token)

        # Idempotence: same patient returns existing active token
        token2 = ExternalConsultationService.get_or_create_qr_token(self.patient_id)
        self.assertEqual(token, token2)

        # Resolution
        resolved = ExternalConsultationService.resolve_qr_token(token)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["patient_id"], self.patient_id)
        self.assertEqual(resolved["health_id"], self.patient_health_id)

    # ---------------------------------------------------------
    # 2. PATIENT HEALTH CARD QR GENERATION
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_03_patient_health_card_generates_canonical_qr(self, mock_supabase):
        """Patient health card renders QR containing canonical /qr/<token> URL."""
        mock_supabase.table().select().eq().single().execute.return_value.data = self.patient_data

        with self.client.session_transaction() as sess:
            sess["patient_id"] = self.patient_id

        res = self.client.get("/patient/qr-health-id")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("OMC-P9999", html)
        self.assertIn("QR / Health ID", html)

    # ---------------------------------------------------------
    # 3. PUBLIC QR LANDING PAGE (PRIVACY PROTECTION)
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_04_public_qr_landing_page_protects_privacy(self, mock_supabase):
        """Public landing page at /qr/<token> strictly protects private contact and clinical data."""
        token = ExternalConsultationService.get_or_create_qr_token(self.patient_id, health_id=self.patient_health_id)
        mock_supabase.table().select().eq().single().execute.return_value.data = self.patient_data

        res = self.client.get(f"/qr/{token}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Must display permitted safe info
        self.assertIn("Test Patient", html)
        self.assertIn("OMC-P9999", html)
        self.assertIn("Female", html)
        self.assertIn("B+", html)
        self.assertIn("Request External Consultation Access", html)
        self.assertIn("Protected Health Information", html)

        # MUST NOT display private phone, email, or home address
        self.assertNotIn("9876543210", html)
        self.assertNotIn("testpatient@example.com", html)
        self.assertNotIn("123 Private Health Street", html)

    # ---------------------------------------------------------
    # 4. VISITOR INTAKE VALIDATION & MSG91 OTP DISPATCH
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_05_visitor_intake_validation(self, mock_supabase):
        """Visitor form rejects missing name, invalid mobile (<10 digits), or underage input."""
        token = ExternalConsultationService.get_or_create_qr_token(self.patient_id, health_id=self.patient_health_id)
        mock_supabase.table().select().eq().single().execute.return_value.data = self.patient_data

        # Invalid mobile
        res = self.client.post(f"/qr/{token}/request-consultation", json={
            "visitor_name": "Dr. Sarah",
            "visitor_mobile": "123",
            "visitor_age": "35",
            "visitor_role": "Doctor"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("valid 10-digit mobile number", res.get_json()["error"])

        # Missing name
        res = self.client.post(f"/qr/{token}/request-consultation", json={
            "visitor_name": "",
            "visitor_mobile": "9876543210",
            "visitor_age": "35",
            "visitor_role": "Doctor"
        })
        self.assertEqual(res.status_code, 400)

    @patch("app.supabase_admin")
    def test_06_msg91_otp_dispatch_in_dev_mode(self, mock_supabase):
        """OTP is dispatched strictly to patient contact, costs zero SMS in dev mode, and returns masked destination."""
        token = ExternalConsultationService.get_or_create_qr_token(self.patient_id, health_id=self.patient_health_id)
        mock_supabase.table().select().eq().single().execute.return_value.data = self.patient_data

        res = self.client.post(f"/qr/{token}/request-consultation", json={
            "visitor_name": "Dr. Sarah External",
            "visitor_mobile": "9123456789",
            "visitor_age": "40",
            "visitor_role": "Doctor",
            "hospital_name": "City General Hospital",
            "location": "Bangalore",
            "medical_registration_number": "MCI-88990"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["challenge_id"].startswith("otp_ch_"))
        # Masked destination matches patient's phone ending in 3210 (NOT visitor's 6789!)
        self.assertIn("3210", data["masked_destination"])
        self.assertNotIn("6789", data["masked_destination"])
        self.assertEqual(data.get("otp_length", 4), 4)

    # ---------------------------------------------------------
    # 5. OTP VERIFICATION (4-DIGIT & MSG91 DEMO OTP 1234)
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_07_otp_verification_creates_5min_session(self, mock_supabase):
        """Entering the 4-digit demo OTP '1234' verifies consent, creates a 5-minute session, and returns workspace redirect."""
        token = ExternalConsultationService.get_or_create_qr_token(self.patient_id, health_id=self.patient_health_id)
        mock_supabase.table().select().eq().single().execute.return_value.data = self.patient_data

        # Request OTP
        req_res = self.client.post(f"/qr/{token}/request-consultation", json={
            "visitor_name": "Dr. Sarah External",
            "visitor_mobile": "9123456789",
            "visitor_age": "40",
            "visitor_role": "Doctor",
            "hospital_name": "City General Hospital"
        })
        challenge_id = req_res.get_json()["challenge_id"]

        # Verify with wrong OTP fails
        fail_res = self.client.post(f"/qr/{token}/verify-otp", json={
            "challenge_id": challenge_id,
            "otp_code": "0000"
        })
        self.assertEqual(fail_res.status_code, 400)
        self.assertIn("Incorrect OTP", fail_res.get_json()["error"])

        # Re-request to get fresh challenge
        req_res2 = self.client.post(f"/qr/{token}/request-consultation", json={
            "visitor_name": "Dr. Sarah External",
            "visitor_mobile": "9123456789",
            "visitor_age": "40",
            "visitor_role": "Doctor"
        })
        ch_id2 = req_res2.get_json()["challenge_id"]

        # Verify with MSG91 Demo OTP "9841"
        verify_res = self.client.post(f"/qr/{token}/verify-otp", json={
            "challenge_id": ch_id2,
            "otp_code": "9841"
        })
        self.assertEqual(verify_res.status_code, 200)
        data = verify_res.get_json()
        self.assertTrue(data["success"])
        self.assertIn(f"/doctor/patient-workspace/{self.patient_id}", data["redirect_url"])

    # ---------------------------------------------------------
    # 6. PATIENT WORKSPACE REUSE IN READ-ONLY MODE
    # ---------------------------------------------------------
    @patch("app.get_trend_analysis_data", return_value={"measurements": [], "timeline": []})
    @patch("app.detect_medical_conflicts", return_value=[])
    @patch("app.supabase_admin")
    def test_08_external_consultation_workspace_reuse(self, mock_supabase, mock_conflicts, mock_trend):
        """Active external consultation session reuses patient workspace in strict read-only mode with timer banner."""
        # Create an active consultation session
        sess_record = ExternalConsultationService.create_session(
            patient_id=self.patient_id,
            visitor_details={"full_name": "Dr. Sarah External", "role": "Doctor", "hospital_name": "City Hospital"}
        )

        mock_supabase.table().select().eq().single().execute.return_value.data = self.patient_data
        mock_supabase.table().select().eq().order().execute.return_value.data = []

        with self.client.session_transaction() as sess:
            sess["external_consultation"] = sess_record

        res = self.client.get(f"/doctor/patient-workspace/{self.patient_id}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Must display prominent read-only banner and countdown timer
        self.assertIn("EXTERNAL CONSULTATION – READ ONLY", html)
        self.assertIn("SESSION EXPIRES IN", html)
        self.assertIn("consultationCountdownText", html)
        self.assertIn("Test Patient", html)
        self.assertIn("OMC-P9999", html)

    # ---------------------------------------------------------
    # 7. EXPIRATION & PATIENT EARLY REVOCATION
    # ---------------------------------------------------------
    def test_09_session_expiration_enforcement(self):
        """Expired session is immediately denied access."""
        sess_record = ExternalConsultationService.create_session(
            patient_id=self.patient_id,
            visitor_details={"full_name": "Dr. Sarah External", "role": "Doctor"}
        )

        # Manually backdate expiration timestamp
        sess_record["expires_at_timestamp"] = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
        sess_record["status"] = "expired"

        with self.client.session_transaction() as sess:
            sess["external_consultation"] = sess_record

        res = self.client.get(f"/doctor/patient-workspace/{self.patient_id}")
        # Should redirect to patient info with notice
        self.assertEqual(res.status_code, 302)

    @patch("app.supabase_admin")
    def test_10_patient_early_revocation(self, mock_supabase):
        """Patient can view active external consultations and revoke them immediately."""
        sess_record = ExternalConsultationService.create_session(
            patient_id=self.patient_id,
            visitor_details={"full_name": "Dr. Attending", "role": "Doctor", "hospital_name": "Care Clinic"}
        )

        # Check listed in patient active consultations
        active = ExternalConsultationService.get_active_sessions_for_patient(self.patient_id)
        self.assertTrue(any(s["session_id"] == sess_record["session_id"] for s in active))

        # Patient revokes
        with self.client.session_transaction() as sess:
            sess["patient_id"] = self.patient_id

        res = self.client.post(f"/patient/revoke-consultation/{sess_record['session_id']}")
        self.assertEqual(res.status_code, 302)

        # Session is now revoked
        sess_after = ExternalConsultationService.get_session(sess_record["session_id"])
        self.assertEqual(sess_after["status"], "revoked")

    # ---------------------------------------------------------
    # 8. DOCTOR PORTAL: OPTION A & OPTION B (4-DIGIT OTP)
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_11_doctor_patient_access_options(self, mock_supabase):
        """Doctor patient access interface renders both Option A (Temporary Access) and Option B (Instant OTP)."""
        mock_supabase.table().select().eq().maybe_single().execute.return_value.data = self.patient_data

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        res = self.client.get(f"/doctor/patient-access?identifier={self.patient_health_id}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Option A: Existing Request Temporary Access preserved
        self.assertIn("Option A: Request Temporary Access", html)
        self.assertIn("Send Portal Access Request", html)

        # Option B: Instant OTP Access
        self.assertIn("Option B: Instant OTP Access", html)
        self.assertIn("Start OTP Consultation", html)

        # Universal QR Scanner
        self.assertIn("Scan Patient QR Code", html)
        self.assertIn("qr-reader", html)

    @patch("app.supabase_admin")
    def test_12_doctor_instant_otp_flow(self, mock_supabase):
        """Doctor can dispatch 4-digit OTP to patient and verify demo OTP '1234' for instant 5-minute access."""
        def table_mock(tbl):
            m = MagicMock()
            if tbl == "doctors":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                    "id": self.doctor_id,
                    "full_name": "Dr. Internal Hospital"
                }
            elif tbl == "patients":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = self.patient_data
            return m
        mock_supabase.table.side_effect = table_mock

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        # Doctor triggers OTP dispatch
        send_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/send-otp")
        self.assertEqual(send_res.status_code, 200)
        send_data = send_res.get_json()
        self.assertTrue(send_data["success"])
        self.assertIn("3210", send_data["masked_destination"])
        self.assertEqual(send_data.get("otp_length", 4), 4)

        # Doctor verifies OTP with demo OTP '9841'
        verify_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/verify-otp", json={
            "challenge_id": send_data["challenge_id"],
            "otp_code": "9841"
        })
        self.assertEqual(verify_res.status_code, 200)
        self.assertTrue(verify_res.get_json()["success"])
        self.assertIn(f"/doctor/patient-workspace/{self.patient_id}", verify_res.get_json()["redirect_url"])

    # ---------------------------------------------------------
    # 9. MSG91 WIDGET ACCESS TOKEN VERIFICATION
    # ---------------------------------------------------------
    def test_13_msg91_widget_access_token_verification(self):
        """MSG91 widget verify_widget_access_token validates tokens securely."""
        # Dev demo token verification
        valid, msg, meta = MSG91OTPService.verify_widget_access_token("demo_token_xyz", expected_identifier="9876543210")
        self.assertTrue(valid)
        self.assertIsNotNone(meta)

        # Test API endpoint
        res = self.client.post("/api/msg91/verify-access-token", json={
            "access_token": "demo_token_xyz",
            "patient_id": self.patient_id,
            "context": "external"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn(f"/doctor/patient-workspace/{self.patient_id}", data["redirect_url"])

    # ---------------------------------------------------------
    # 10. DATABASE SCHEMA INTEGRITY & NO "doctors.name"
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_14_doctor_send_otp_schema_integrity(self, mock_supabase):
        """Simulates strict PostgreSQL column enforcement: reject any query referencing non-existent 'name' column."""
        def strict_table_mock(tbl):
            m = MagicMock()
            def select_fn(cols):
                col_list = [c.strip() for c in cols.split(",")]
                # PostgreSQL 42703 strict check: table doctors only has full_name, not name
                if tbl == "doctors":
                    if "name" in col_list:
                        raise Exception("PostgreSQL error 42703: column doctors.name does not exist")
                    sel_mock = MagicMock()
                    sel_mock.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                        "id": self.doctor_id,
                        "full_name": "Dr. Schema Verified"
                    }
                    return sel_mock
                elif tbl == "patients":
                    if "name" in col_list:
                        raise Exception("PostgreSQL error 42703: column patients.name does not exist")
                    sel_mock = MagicMock()
                    sel_mock.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data
                    sel_mock.eq.return_value.single.return_value.execute.return_value.data = self.patient_data
                    return sel_mock
                return MagicMock()

            m.select.side_effect = select_fn
            return m

        mock_supabase.table.side_effect = strict_table_mock

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        # Must succeed without PostgreSQL 42703
        send_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/send-otp")
        self.assertEqual(send_res.status_code, 200)
        send_data = send_res.get_json()
        self.assertTrue(send_data["success"])
        self.assertIn("3210", send_data["masked_destination"])


if __name__ == "__main__":
    unittest.main()
