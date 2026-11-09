import sys, os
sys.path.insert(0, os.path.abspath("."))

from app import app
from unittest.mock import patch

app.config["TESTING"] = True
client = app.test_client()

patient_data = {
    "id": "11111111-2222-3333-4444-555555555555",
    "full_name": "Test Patient",
    "name": "Test Patient",
    "health_id": "OMC-P1000",
    "phone": "9876543210",
    "email": "test@example.com",
    "age": 30,
    "gender": "Male",
    "blood_group": "O+"
}

# 1. Test public_patient_info rendering
with patch("app.supabase_admin") as mock_sup:
    mock_sup.table().select().eq().single().execute.return_value.data = patient_data
    mock_sup.table().select().eq().maybe_single().execute.return_value.data = patient_data
    res = client.get("/patient-info/11111111-2222-3333-4444-555555555555")
    print("public_patient_info status:", res.status_code)
    html_public = res.data.decode("utf-8")
    with open("scratch/rendered_public.html", "w", encoding="utf-8") as f:
        f.write(html_public)

# 2. Test doctor patient_access rendering
with client.session_transaction() as sess:
    sess["doctor_id"] = "doc-1234"

with patch("app.supabase_admin") as mock_sup:
    mock_sup.table().select().eq().single().execute.return_value.data = patient_data
    mock_sup.table().select().eq().maybe_single().execute.return_value.data = patient_data
    res = client.get("/doctor/patient-access?identifier=OMC-P1000")
    print("doctor patient_access status:", res.status_code)
    html_doc = res.data.decode("utf-8")
    with open("scratch/rendered_doc_access.html", "w", encoding="utf-8") as f:
        f.write(html_doc)

print("Rendered files saved to scratch/.")
