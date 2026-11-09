# ============================================================
# OMNICARE AI — FIXED DEMO OTP TEST SUITE
# ============================================================
"""
Tests development-only fixed demo OTP (9841) behavior:
1. Correct OTP: 9841 succeeds, returns workspace redirect.
2. Incorrect OTP: rejected with remaining attempts count.
3. Expired OTP: rejected after 5 minutes (300 seconds).
4. Reused OTP: single-use enforcement rejects reused challenge.
5. More than five failed attempts: locks/invalidates the challenge.
6. Five-minute consultation expiry: workspace access terminates after 5 minutes.
7. Production rejection of demo OTP: in production mode, 9841 is strictly rejected.
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from services.msg91_otp_service import (
    MSG91OTPService,
    is_demo_otp_active,
    is_production,
    get_demo_otp_code,
    _ACTIVE_OTP_CHALLENGES,
    _OTP_RATE_LIMITS,
)
from services.external_consultation_service import ExternalConsultationService


class TestFixedDemoOTP(unittest.TestCase):
    """Test suite verifying all 7 criteria of the development-only Fixed Demo OTP."""

    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-fixed-demo-otp"
        self.client = app.test_client()

        self.patient_id = "test-patient-uuid-demo-9841"
        self.patient_health_id = "OMC-P9841"
        self.doctor_id = "test-doctor-uuid-demo-doc"

        self.patient_data = {
            "id": self.patient_id,
            "full_name": "Demo Patient",
            "name": "Demo Patient",
            "health_id": self.patient_health_id,
            "phone": "9876543210",
            "email": "demopatient@example.com",
            "gender": "Male",
            "date_of_birth": "1990-01-01",
            "blood_group": "O+",
            "address": "456 Healthcare Blvd",
        }

        # Clear in-memory active OTP challenges & rate limits
        _ACTIVE_OTP_CHALLENGES.clear()
        _OTP_RATE_LIMITS.clear()

        # Ensure environment defaults to development fixed demo OTP
        self._orig_env = dict(os.environ)
        os.environ["DEMO_OTP_ENABLED"] = "true"
        os.environ["DEMO_OTP_CODE"] = "9841"
        os.environ["MSG91_ENVIRONMENT"] = "development"
        os.environ.pop("FLASK_ENV", None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)
        _ACTIVE_OTP_CHALLENGES.clear()
        _OTP_RATE_LIMITS.clear()

    # ---------------------------------------------------------
    # TEST 1: CORRECT OTP 9841
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_01_correct_demo_otp_9841(self, mock_sup):
        """When doctor requests OTP, fixed demo code 9841 is used, displays demo notice, and verifies successfully."""
        def table_mock(tbl):
            m = MagicMock()
            if tbl == "doctors":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                    "id": self.doctor_id,
                    "full_name": "Dr. Attending Physician"
                }
            elif tbl == "patients":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = self.patient_data
            return m
        mock_sup.table.side_effect = table_mock

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        # 1. Trigger Send OTP
        send_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/send-otp")
        self.assertEqual(send_res.status_code, 200)
        send_data = send_res.get_json()
        self.assertTrue(send_data["success"])
        self.assertEqual(send_data["message"], "Demo OTP: 9841 (Development Mode)")
        self.assertTrue(send_data.get("is_demo_mode"))
        self.assertEqual(send_data.get("demo_otp_notice"), "Demo OTP: 9841 (Development Mode)")
        self.assertEqual(send_data["expires_in_seconds"], 300)
        self.assertEqual(send_data["otp_length"], 4)
        challenge_id = send_data["challenge_id"]

        # 2. Verify with correct fixed OTP 9841
        verify_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/verify-otp", json={
            "challenge_id": challenge_id,
            "otp_code": "9841"
        })
        self.assertEqual(verify_res.status_code, 200)
        verify_data = verify_res.get_json()
        self.assertTrue(verify_data["success"])
        self.assertIn(f"/doctor/patient-workspace/{self.patient_id}", verify_data["redirect_url"])

    # ---------------------------------------------------------
    # TEST 2: INCORRECT OTP
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_02_incorrect_otp(self, mock_sup):
        """Entering incorrect OTP is rejected with remaining attempts count."""
        def table_mock(tbl):
            m = MagicMock()
            if tbl == "doctors":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                    "id": self.doctor_id,
                    "full_name": "Dr. Attending Physician"
                }
            elif tbl == "patients":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data
            return m
        mock_sup.table.side_effect = table_mock

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        send_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/send-otp")
        ch_id = send_res.get_json()["challenge_id"]

        # Incorrect OTP (e.g. 0000)
        fail_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/verify-otp", json={
            "challenge_id": ch_id,
            "otp_code": "0000"
        })
        self.assertEqual(fail_res.status_code, 400)
        err = fail_res.get_json()["error"]
        self.assertIn("Incorrect OTP", err)
        self.assertIn("4 attempt(s) remaining", err)

    # ---------------------------------------------------------
    # TEST 3: EXPIRED OTP (5 MINUTES)
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_03_expired_otp(self, mock_sup):
        """OTP expires after 5 minutes (300 seconds); verification is rejected."""
        def table_mock(tbl):
            m = MagicMock()
            if tbl == "doctors":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                    "id": self.doctor_id,
                    "full_name": "Dr. Attending Physician"
                }
            elif tbl == "patients":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data
            return m
        mock_sup.table.side_effect = table_mock

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        send_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/send-otp")
        ch_id = send_res.get_json()["challenge_id"]

        # Manually backdate the challenge expiry timestamp by 301 seconds
        _ACTIVE_OTP_CHALLENGES[ch_id]["expires_at"] = time.time() - 10

        verify_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/verify-otp", json={
            "challenge_id": ch_id,
            "otp_code": "9841"
        })
        self.assertEqual(verify_res.status_code, 400)
        self.assertIn("The OTP has expired", verify_res.get_json()["error"])

    # ---------------------------------------------------------
    # TEST 4: REUSED OTP (SINGLE-USE ENFORCEMENT)
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_04_reused_otp(self, mock_sup):
        """Single-use enforcement: verified OTP challenge cannot be reused."""
        def table_mock(tbl):
            m = MagicMock()
            if tbl == "doctors":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                    "id": self.doctor_id,
                    "full_name": "Dr. Attending Physician"
                }
            elif tbl == "patients":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data
            return m
        mock_sup.table.side_effect = table_mock

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        send_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/send-otp")
        ch_id = send_res.get_json()["challenge_id"]

        # First verification succeeds
        v1 = self.client.post(f"/doctor/patient-access/{self.patient_id}/verify-otp", json={
            "challenge_id": ch_id,
            "otp_code": "9841"
        })
        self.assertEqual(v1.status_code, 200)

        # Second verification with identical challenge_id is rejected
        v2 = self.client.post(f"/doctor/patient-access/{self.patient_id}/verify-otp", json={
            "challenge_id": ch_id,
            "otp_code": "9841"
        })
        self.assertEqual(v2.status_code, 400)
        self.assertIn("OTP session has expired or is invalid", v2.get_json()["error"])

    # ---------------------------------------------------------
    # TEST 5: MORE THAN FIVE FAILED ATTEMPTS
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_05_max_five_attempts_exceeded(self, mock_sup):
        """After 5 failed attempts, the challenge is invalidated and locked out."""
        def table_mock(tbl):
            m = MagicMock()
            if tbl == "doctors":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                    "id": self.doctor_id,
                    "full_name": "Dr. Attending Physician"
                }
            elif tbl == "patients":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data
            return m
        mock_sup.table.side_effect = table_mock

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        send_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/send-otp")
        ch_id = send_res.get_json()["challenge_id"]

        # Fail 5 times
        for i in range(1, 6):
            res = self.client.post(f"/doctor/patient-access/{self.patient_id}/verify-otp", json={
                "challenge_id": ch_id,
                "otp_code": "1111"
            })
            self.assertEqual(res.status_code, 400)
            if i < 5:
                self.assertIn(f"{5 - i} attempt(s) remaining", res.get_json()["error"])
            else:
                self.assertIn("0 attempt(s) remaining", res.get_json()["error"])

        # 6th attempt: locked out
        lock_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/verify-otp", json={
            "challenge_id": ch_id,
            "otp_code": "9841"
        })
        self.assertEqual(lock_res.status_code, 400)
        self.assertIn("Maximum verification attempts exceeded", lock_res.get_json()["error"])

    # ---------------------------------------------------------
    # TEST 6: FIVE-MINUTE CONSULTATION EXPIRY ON WORKSPACE
    # ---------------------------------------------------------
    def test_06_five_minute_consultation_expiry(self):
        """Consultation workspace access strictly terminates after 5 minutes."""
        # Create an active session
        sess_rec = ExternalConsultationService.create_session(
            patient_id=self.patient_id,
            visitor_details={"full_name": "Dr. Attending Physician", "role": "Doctor"},
            is_internal_doctor=True,
            doctor_id=self.doctor_id
        )

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id
            sess["active_otp_access"] = sess_rec

        # Fast-forward session expiration past 300 seconds
        sess_rec["expires_at_timestamp"] = int((datetime.now(timezone.utc) - timedelta(seconds=10)).timestamp())
        sess_rec["status"] = "expired"

        # Attempt to access workspace -> should redirect because session expired
        res = self.client.get(f"/doctor/patient-workspace/{self.patient_id}")
        self.assertEqual(res.status_code, 302)

    # ---------------------------------------------------------
    # TEST 7: PRODUCTION REJECTION OF DEMO OTP
    # ---------------------------------------------------------
    def test_07_production_rejection_of_demo_otp(self):
        """In production mode, demo OTP verification is strictly rejected regardless of env variables."""
        # Force production environment
        os.environ["MSG91_ENVIRONMENT"] = "production"
        os.environ["FLASK_ENV"] = "production"
        os.environ["DEMO_OTP_ENABLED"] = "true"
        os.environ["DEMO_OTP_CODE"] = "9841"

        self.assertTrue(is_production())
        self.assertFalse(is_demo_otp_active())

        # Create challenge directly
        now = time.time()
        ch_id = "otp_ch_prod_test"
        _ACTIVE_OTP_CHALLENGES[ch_id] = {
            "challenge_id": ch_id,
            "patient_id": self.patient_id,
            "otp_code": "7294",  # Real random SMS code in production
            "otp_hash": "dummy_hash",
            "expires_at": now + 300,
            "attempts": 0,
            "is_demo": False
        }

        # Submitting 9841 in production must fail
        verified, err, meta = MSG91OTPService.verify_otp(
            challenge_id=ch_id,
            patient_id=self.patient_id,
            entered_otp="9841"
        )
        self.assertFalse(verified)
        self.assertIn("Incorrect OTP", err)

        # Even if a challenge was marked is_demo, in production it is rejected immediately
        ch_id_demo = "otp_ch_prod_demo_attempt"
        _ACTIVE_OTP_CHALLENGES[ch_id_demo] = {
            "challenge_id": ch_id_demo,
            "patient_id": self.patient_id,
            "otp_code": "9841",
            "otp_hash": "dummy_hash",
            "expires_at": now + 300,
            "attempts": 0,
            "is_demo": True
        }
        verified2, err2, meta2 = MSG91OTPService.verify_otp(
            challenge_id=ch_id_demo,
            patient_id=self.patient_id,
            entered_otp="9841"
        )
        self.assertFalse(verified2)
        self.assertIn("Demo OTP verification is not permitted in production", err2)


if __name__ == "__main__":
    unittest.main()
