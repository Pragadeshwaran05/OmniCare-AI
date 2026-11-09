import sys, os
sys.path.insert(0, os.path.abspath("."))

from unittest.mock import MagicMock, patch
from app import app
from services.external_consultation_service import ExternalConsultationService

app.config["TESTING"] = True
client = app.test_client()

patient_id = "test-patient-uuid-999"
patient_health_id = "OMC-P8888"

patient_data = {
    "id": patient_id,
    "full_name": "John Doe",
    "health_id": patient_health_id
}

qr_token = ExternalConsultationService.get_or_create_qr_token(patient_id, health_id=patient_health_id)
print("qr_token created:", qr_token)
resolved = ExternalConsultationService.resolve_qr_token(patient_health_id)
print("resolved for health_id:", resolved)

with client.session_transaction() as sess:
    sess["doctor_id"] = "doc-111"

with patch("app.supabase_admin") as mock_sup:
    mock_sup.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = patient_data
    mock_sup.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = patient_data
    
    res = client.get(f"/doctor/patient-access?identifier={patient_health_id}")
    print("Status:", res.status_code)
    html = res.data.decode("utf-8")
    print("Has btnStartDoctorOtp:", 'id="btnStartDoctorOtp"' in html)
    print("Has error:", "No patient found" in html or "Patient search failed" in html)
    if "No patient found" in html:
        print("Error was: No patient found")
    if "Patient search failed" in html:
        print("Error was: Patient search failed")
