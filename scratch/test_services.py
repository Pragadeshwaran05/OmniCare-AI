import sys, os
sys.path.insert(0, os.path.abspath('.'))

from services.msg91_otp_service import MSG91OTPService, mask_phone_number, mask_email_address
from services.external_consultation_service import ExternalConsultationService

print("Testing MSG91OTPService and ExternalConsultationService...")

# 1. Test masking
assert mask_phone_number("9876543210") == "******3210"
assert mask_phone_number("+91 9876543210") == "+91 ******3210"
assert mask_email_address("testpatient@omnicare.ai") == "t*********t@omnicare.ai"

# 2. Test QR token generation
token1 = ExternalConsultationService.get_or_create_qr_token("p_test_123", health_id="OMC-P9999")
assert token1.startswith("OMC-QR-")
token2 = ExternalConsultationService.get_or_create_qr_token("p_test_123")
assert token1 == token2, "Token should be idempotent per patient"

# 3. Test token resolution
resolved = ExternalConsultationService.resolve_qr_token(token1)
assert resolved is not None
assert resolved["patient_id"] == "p_test_123"

# 4. Test OTP dispatch in dev mode
success, msg, meta = MSG91OTPService.request_otp(
    patient_id="p_test_123",
    patient_phone="9876543210",
    patient_email="test@example.com",
    visitor_name="Dr. External Smith",
    consultation_type="Test Consultation"
)
assert success, f"Failed OTP dispatch: {msg}"
challenge_id = meta["challenge_id"]

# 5. Check active challenge in service
from services.msg91_otp_service import _ACTIVE_OTP_CHALLENGES
challenge = _ACTIVE_OTP_CHALLENGES[challenge_id]
# Verify wrong otp
wrong_verified, wrong_msg, _ = MSG91OTPService.verify_otp(challenge_id, "p_test_123", "000000")
assert not wrong_verified
assert "Incorrect OTP" in wrong_msg

# 6. Test session creation and expiration
sess = ExternalConsultationService.create_session(
    patient_id="p_test_123",
    visitor_details={"full_name": "Dr. External Smith", "role": "Doctor", "hospital_name": "Apollo"}
)
assert sess["status"] == "active"
assert sess["read_only"] is True

# Test revoke
revoked, r_msg = ExternalConsultationService.revoke_session(sess["session_id"], "p_test_123")
assert revoked
sess_after = ExternalConsultationService.get_session(sess["session_id"])
assert sess_after["status"] == "revoked"

print("All Services tests passed successfully!")
