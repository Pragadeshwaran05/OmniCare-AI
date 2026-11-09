import sys, os
sys.path.insert(0, os.path.abspath("."))

import unittest
from unittest.mock import patch, MagicMock
from app import app
from services.external_consultation_service import ExternalConsultationService
from services.msg91_otp_service import _ACTIVE_OTP_CHALLENGES, _OTP_RATE_LIMITS

class TestButtonClicksAndModals(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret"
        self.client = app.test_client()
        _ACTIVE_OTP_CHALLENGES.clear()
        _OTP_RATE_LIMITS.clear()

        self.patient_id = "test-patient-uuid-999"
        self.patient_health_id = "OMC-P8888"
        self.doctor_id = "doc-uuid-111"

        self.patient_data = {
            "id": self.patient_id,
            "full_name": "John Doe",
            "name": "John Doe",
            "health_id": self.patient_health_id,
            "phone": "9876543210",
            "email": "john@example.com",
            "age": 40,
            "gender": "Male",
            "blood_group": "A+"
        }

        # Register patient in ExternalConsultationService
        self.qr_token = ExternalConsultationService.get_or_create_qr_token(
            self.patient_id,
            health_id=self.patient_health_id
        )

    @patch("app.supabase_admin")
    def test_button_1_request_external_consultation_end_to_end(self, mock_sup):
        """Test Button 1: Request External Consultation Access -> modal opens -> submit -> verify -> workspace."""
        mock_sup.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = self.patient_data
        mock_sup.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data

        # 1. Page renders button and modal
        res = self.client.get(f"/qr/{self.qr_token}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertIn('id="btnRequestConsultation"', html)
        self.assertIn('Request External Consultation Access', html)
        self.assertIn('id="consultationModal"', html)
        self.assertIn('openConsultationModal()', html)

        # 2. Submit visitor details (handles button click and modal submission)
        post_res = self.client.post(f"/qr/{self.qr_token}/request-consultation", json={
            "visitor_name": "Dr. Specialist",
            "visitor_mobile": "9988776655",
            "visitor_age": "45",
            "visitor_role": "Doctor",
            "hospital_name": "Apollo Clinic",
            "location": "Chennai",
            "medical_registration_number": "REG-12345"
        })
        self.assertEqual(post_res.status_code, 200)
        post_data = post_res.get_json()
        self.assertTrue(post_data["success"])
        self.assertIn("3210", post_data["masked_destination"])
        challenge_id = post_data["challenge_id"]

        # 3. Submit 4-digit demo OTP 9841
        verify_res = self.client.post(f"/qr/{self.qr_token}/verify-otp", json={
            "challenge_id": challenge_id,
            "otp_code": "9841"
        })
        self.assertEqual(verify_res.status_code, 200)
        verify_data = verify_res.get_json()
        self.assertTrue(verify_data["success"])
        self.assertIn(f"/doctor/patient-workspace/{self.patient_id}", verify_data["redirect_url"])

    @patch("app.supabase_admin")
    def test_button_2_start_otp_consultation_end_to_end(self, mock_sup):
        """Test Button 2: Start OTP Consultation -> modal opens -> send OTP -> verify -> workspace."""
        mock_sup.table().select().eq().maybe_single().execute.return_value.data = self.patient_data
        mock_sup.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = self.patient_data
        mock_sup.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        # 1. Doctor Patient Access page renders button and modal
        res = self.client.get(f"/doctor/patient-access?identifier={self.patient_health_id}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertIn('id="btnStartDoctorOtp"', html)
        self.assertIn('Start OTP Consultation', html)
        self.assertIn('id="doctorOtpModal"', html)
        self.assertIn('openDoctorOtpModal', html)

        # 2. Trigger send-otp
        send_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/send-otp")
        self.assertEqual(send_res.status_code, 200)
        send_data = send_res.get_json()
        self.assertTrue(send_data["success"])
        self.assertIn("3210", send_data["masked_destination"])
        self.assertEqual(send_data.get("otp_length"), 4)
        ch_id = send_data["challenge_id"]

        # 3. Verify with 4-digit demo OTP 9841
        verify_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/verify-otp", json={
            "challenge_id": ch_id,
            "otp_code": "9841"
        })
        self.assertEqual(verify_res.status_code, 200)
        verify_data = verify_res.get_json()
        self.assertTrue(verify_data["success"])
        self.assertIn(f"/doctor/patient-workspace/{self.patient_id}", verify_data["redirect_url"])

if __name__ == "__main__":
    unittest.main()
