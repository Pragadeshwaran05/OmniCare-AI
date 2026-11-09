with open('services/clinical_audit_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '"DOCTOR_ACCOUNT_DEACTIVATED": "Doctor Account Deactivated"'
replacement = '''"DOCTOR_ACCOUNT_DEACTIVATED": "Doctor Account Deactivated",
    "EXTERNAL_CONSULTATION_REQUESTED": "External Consultation Requested",
    "EXTERNAL_CONSULTATION_OTP_SENT": "Patient OTP Dispatched",
    "EXTERNAL_CONSULTATION_OTP_VERIFIED": "Patient OTP Verified",
    "EXTERNAL_CONSULTATION_SESSION_STARTED": "External Consultation Session Started",
    "EXTERNAL_CONSULTATION_RECORD_VIEWED": "External Consultation Record Viewed",
    "EXTERNAL_CONSULTATION_SESSION_REVOKED": "External Consultation Session Revoked",
    "EXTERNAL_CONSULTATION_SESSION_EXPIRED": "External Consultation Session Expired",
    "INTERNAL_QR_SCAN": "Internal QR Code Scanned",
    "INTERNAL_OTP_ACCESS_GRANTED": "Doctor OTP Access Granted"'''

assert target in text, "target not found in clinical_audit_service.py"
new_text = text.replace(target, replacement, 1)

with open('services/clinical_audit_service.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Updated clinical_audit_service.py successfully!")
