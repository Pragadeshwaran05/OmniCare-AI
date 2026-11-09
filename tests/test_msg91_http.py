# ============================================================
# MSG91 HTTP API & WIDGET VERIFICATION TEST
# ============================================================

import os
import unittest
from unittest.mock import patch, MagicMock
from services.msg91_otp_service import MSG91OTPService


class TestMSG91HTTP(unittest.TestCase):
    def setUp(self):
        os.environ["MSG91_AUTH_KEY"] = "test_auth_key_123"
        os.environ["MSG91_WIDGET_ID"] = "test_widget_id_456"
        os.environ["MSG91_INTEGRATION_TOKEN"] = "test_token_789"
        os.environ["MSG91_ENVIRONMENT"] = "production"  # switch to production to test HTTP calls

    def tearDown(self):
        os.environ["MSG91_ENVIRONMENT"] = "development"

    @patch("services.msg91_otp_service.httpx.Client")
    def test_verify_widget_access_token_real_api(self, mock_client_cls):
        """Test verify_widget_access_token sends exact official headers and payload."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "type": "success",
            "message": "919876543210"
        }
        mock_client.post.return_value = mock_response

        valid, msg, meta = MSG91OTPService.verify_widget_access_token(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_token"
        )

        self.assertTrue(valid)
        self.assertEqual(meta["verified_identifier"], "919876543210")

        # Verify exact URL, headers, and payload
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        self.assertEqual(args[0], "https://control.msg91.com/api/v5/widget/verifyAccessToken")
        self.assertEqual(kwargs["headers"]["authkey"], "test_auth_key_123")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["json"]["access-token"], "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_token")

    @patch("services.msg91_otp_service.httpx.Client")
    def test_send_msg91_otp_real_api(self, mock_client_cls):
        """Test _send_msg91_otp formats 4-digit payload, 15-minute expiry, and E.164 mobile."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"type": "success", "message": "OTP sent successfully."}'
        mock_response.json.return_value = {
            "type": "success",
            "message": "OTP sent successfully."
        }
        mock_client.post.return_value = mock_response

        success, msg = MSG91OTPService._send_msg91_otp(
            phone="9876543210",
            otp="1234",
            visitor_name="Dr. Smith"
        )

        self.assertTrue(success)

        # Verify exact payload
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        self.assertEqual(args[0], "https://control.msg91.com/api/v5/otp")
        self.assertEqual(kwargs["headers"]["authkey"], "test_auth_key_123")
        self.assertEqual(kwargs["json"]["mobile"], "919876543210")
        self.assertEqual(kwargs["json"]["otp"], "1234")
        self.assertEqual(kwargs["json"]["otp_length"], 4)
        self.assertEqual(kwargs["json"]["otp_expiry"], 15)


if __name__ == "__main__":
    unittest.main()
