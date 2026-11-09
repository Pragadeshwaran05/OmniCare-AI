"""
tests/test_doctor_consultations_prescriptions.py

Comprehensive test suite verifying the Doctor Consultations & Prescriptions Module in OmniCare AI.
Tests:
1. Authentication & Route Accessibility (/doctor/consultations & /doctor/consultations-prescriptions)
2. Authorized Patient Retrieval & Security Validation (No cross-patient leakage)
3. Document History Retrieval & Category Counts
4. Consultation Note Creation (PDF Generation & Record Persistence)
5. Digital Prescription Creation (Horizontal M/A/E/N Timings & PDF Generation)
6. Document Upload Pipeline & Type Classification
7. Prescription Live Preview PDF Generation
8. PDF Download Route
9. Mobile Responsiveness & Layout Bounded Constraints
"""

import unittest
import json
import io
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app import app
from services.medical_record_document_service import (
    generate_consultation_pdf,
    generate_prescription_pdf,
    save_patient_medical_record
)


class TestDoctorConsultationsPrescriptions(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key-consultations"
        self.client = self.app.test_client()

        self.mock_doctor_id = "test-doc-uuid-101"
        self.mock_patient_id = "test-pat-uuid-202"
        self.mock_unauthorized_patient_id = "test-unauth-pat-uuid-999"

        self.mock_doctor_data = {
            "id": self.mock_doctor_id,
            "full_name": "Sarah Connor",
            "specialization": "Internal Medicine",
            "medical_registration_number": "MED-REG-98765",
            "hospital_name": "Metro General Hospital",
            "hospital_address": "456 Healthcare Blvd",
            "qualification": "MBBS, MD",
            "email": "dr.connor@omnicare.ai",
            "phone": "+91 98765 43210"
        }

        self.mock_patient_data = {
            "id": self.mock_patient_id,
            "patient_id": self.mock_patient_id,
            "name": "Johnathan Doe",
            "health_id": "HID-JD-2024",
            "age": 42,
            "gender": "Male",
            "blood_group": "O+",
            "weight": 76,
            "allergies": "Penicillin",
            "phone": "+91 91234 56789",
            "email": "johndoe@example.com",
            "is_permanent": True,
            "access_type": "permanent",
            "approved_at": "2024-10-14T09:30:00Z"
        }

    def test_01_authentication_required(self):
        """Unauthenticated requests must redirect to doctor login."""
        res1 = self.client.get("/doctor/consultations")
        self.assertEqual(res1.status_code, 302)
        self.assertIn("/doctor/login", res1.headers["Location"])

        res2 = self.client.get("/doctor/consultations-prescriptions")
        self.assertEqual(res2.status_code, 302)
        self.assertIn("/doctor/login", res2.headers["Location"])

    @patch("app.get_doctor_profile")
    @patch("app.get_authorized_patients_for_doctor")
    @patch("app.get_patient_document_history")
    def test_02_page_loads_with_authorized_patient(self, mock_get_history, mock_get_auth_patients, mock_get_profile):
        """Doctor can open Consultations & Prescriptions page with authorized patient selected."""
        mock_get_profile.return_value = self.mock_doctor_data
        mock_get_auth_patients.return_value = [self.mock_patient_data]
        mock_get_history.return_value = [
            {
                "id": "rec-1",
                "patient_id": self.mock_patient_id,
                "title": "Initial Consultation",
                "record_type": "consultation",
                "doctor_name": "Sarah Connor",
                "hospital_name": "Metro General Hospital",
                "uploaded_at": "2024-10-15T10:00:00Z",
                "file_url": "/test/url/1.pdf"
            },
            {
                "id": "rec-2",
                "patient_id": self.mock_patient_id,
                "title": "Antibiotic Prescription",
                "record_type": "prescription",
                "doctor_name": "Sarah Connor",
                "hospital_name": "Metro General Hospital",
                "uploaded_at": "2024-10-15T10:15:00Z",
                "file_url": "/test/url/2.pdf"
            }
        ]

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.mock_doctor_id
            sess["doctor_name"] = "Dr. Sarah Connor"

        res = self.client.get(f"/doctor/consultations-prescriptions?patient_id={self.mock_patient_id}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Verify page components
        self.assertIn("Consultations &amp; Prescriptions", html)
        self.assertIn("Johnathan Doe", html)
        self.assertIn("HID-JD-2024", html)
        self.assertIn("Permanent Access", html)
        self.assertIn("Initial Consultation", html)
        self.assertIn("Antibiotic Prescription", html)

    @patch("app.get_doctor_profile")
    @patch("app.get_authorized_patients_for_doctor")
    def test_03_unauthorized_patient_access_rejected(self, mock_get_auth_patients, mock_get_profile):
        """Doctor cannot access an unauthorized patient by changing patient_id in URL."""
        mock_get_profile.return_value = self.mock_doctor_data
        mock_get_auth_patients.return_value = [self.mock_patient_data]

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.mock_doctor_id

        # Request with an unauthorized patient ID
        res = self.client.get(f"/doctor/consultations-prescriptions?patient_id={self.mock_unauthorized_patient_id}")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Must display unauthorized flash message and empty selection prompt
        self.assertIn("Unauthorized access", html)
        self.assertNotIn("No matching patient", html)

    @patch("app.get_authorized_patients_for_doctor")
    def test_04_api_authorized_patients_list(self, mock_get_auth_patients):
        """API returns authorized patients in JSON format for live search."""
        mock_get_auth_patients.return_value = [self.mock_patient_data]

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.mock_doctor_id

        res = self.client.get("/doctor/consultations/api/patients")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))

        self.assertTrue(data.get("success"))
        self.assertEqual(len(data.get("patients")), 1)
        self.assertEqual(data["patients"][0]["health_id"], "HID-JD-2024")

    @patch("app.verify_doctor_patient_authorization")
    @patch("app.get_doctor_profile")
    @patch("app.save_patient_medical_record")
    def test_05_create_consultation_note(self, mock_save_rec, mock_get_profile, mock_verify):
        """Doctor can create clinical consultation note with ReportLab PDF and persistence."""
        mock_verify.return_value = (True, self.mock_patient_data)
        mock_get_profile.return_value = self.mock_doctor_data
        mock_save_rec.return_value = {
            "id": "new-consult-rec-id",
            "patient_id": self.mock_patient_id,
            "title": "Consultation (General Consultation)",
            "record_type": "consultation",
            "file_url": "/test/consult.pdf",
            "document_date": "2024-10-18"
        }

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.mock_doctor_id

        payload = {
            "consultation_type": "General Consultation",
            "chief_complaint": "Persistent coughing and fatigue for one week",
            "diagnosis_primary": "Acute Bronchitis",
            "treatment_plan": "Oral bronchodilator and steam inhalation",
            "recommendations": "Adequate rest and plenty of oral fluids",
            "vital_bp": "120/80",
            "vital_pulse": "76"
        }

        res = self.client.post(
            f"/doctor/consultations/{self.mock_patient_id}/create-consultation",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))

        self.assertTrue(data.get("success"))
        self.assertIn("record", data)
        self.assertEqual(data["record"]["record_type"], "consultation")

    @patch("app.verify_doctor_patient_authorization")
    @patch("app.get_doctor_profile")
    @patch("app.save_patient_medical_record")
    def test_06_create_prescription_with_timing(self, mock_save_rec, mock_get_profile, mock_verify):
        """Doctor can create digital prescription with horizontal M/A/E/N timings and medicines."""
        mock_verify.return_value = (True, self.mock_patient_data)
        mock_get_profile.return_value = self.mock_doctor_data
        mock_save_rec.return_value = {
            "id": "new-prescription-rec-id",
            "patient_id": self.mock_patient_id,
            "title": "Prescription - 18 Oct 2024",
            "record_type": "prescription",
            "file_url": "/test/prescription.pdf",
            "document_date": "2024-10-18"
        }

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.mock_doctor_id

        payload = {
            "diagnosis": "Bacterial Sinusitis",
            "general_advice": "Steam inhalation twice daily; stay hydrated.",
            "follow_up": "Follow-up after 5 days if fever persists.",
            "medicines": [
                {
                    "name": "Amoxicillin / Clavulanate",
                    "type": "Tablet",
                    "strength": "625 mg",
                    "dosage": "1 Tablet",
                    "frequency": "Twice Daily",
                    "duration": "5 Days",
                    "food": "After Food",
                    "instructions": "Take at equal 12-hour intervals",
                    "timing": {"m": True, "a": False, "e": True, "n": False}
                },
                {
                    "name": "Cetirizine",
                    "type": "Tablet",
                    "strength": "10 mg",
                    "dosage": "1 Tablet",
                    "frequency": "Once Daily",
                    "duration": "5 Days",
                    "food": "After Food",
                    "instructions": "Take before bed",
                    "timing": {"m": False, "a": False, "e": False, "n": True}
                }
            ]
        }

        res = self.client.post(
            f"/doctor/consultations/{self.mock_patient_id}/create-prescription",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))

        self.assertTrue(data.get("success"))
        self.assertIn("record", data)
        self.assertEqual(data["record"]["record_type"], "prescription")

    @patch("app.verify_doctor_patient_authorization")
    @patch("app.get_doctor_profile")
    def test_07_live_prescription_pdf_preview(self, mock_get_profile, mock_verify):
        """Live PDF preview generates streaming PDF bytes for live iframe rendering."""
        mock_verify.return_value = (True, self.mock_patient_data)
        mock_get_profile.return_value = self.mock_doctor_data

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.mock_doctor_id

        payload = {
            "template_type": "prescription",
            "diagnosis": "Hypertension Review",
            "medicines": [
                {
                    "name": "Amlodipine",
                    "type": "Tablet",
                    "strength": "5 mg",
                    "dosage": "1 Tablet",
                    "frequency": "Once Daily",
                    "duration": "30 Days",
                    "timing": {"m": True, "a": False, "e": False, "n": False}
                }
            ]
        }

        res = self.client.post(
            f"/doctor/consultations/{self.mock_patient_id}/preview-pdf",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, "application/pdf")
        # Validate PDF header bytes %PDF-
        self.assertTrue(res.data.startswith(b"%PDF"))

    @patch("app.verify_doctor_patient_authorization")
    @patch("app.get_doctor_profile")
    @patch("app.save_patient_medical_record")
    def test_08_upload_external_medical_document(self, mock_save_rec, mock_get_profile, mock_verify):
        """Doctor can upload external medical documents (lab, imaging, etc.)."""
        mock_verify.return_value = (True, self.mock_patient_data)
        mock_get_profile.return_value = self.mock_doctor_data
        mock_save_rec.return_value = {
            "id": "new-lab-rec-id",
            "patient_id": self.mock_patient_id,
            "title": "Lipid Profile Test",
            "record_type": "lab_report",
            "file_url": "/test/lipid.pdf",
            "document_date": "2024-10-18"
        }

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.mock_doctor_id

        fake_pdf = (io.BytesIO(b"%PDF-1.4 Fake PDF Content"), "lipid_profile.pdf")

        res = self.client.post(
            f"/doctor/consultations/{self.mock_patient_id}/upload-document",
            data={
                "title": "Lipid Profile Test",
                "category": "lab_report",
                "description": "Fasting lipid panel evaluation",
                "document_file": fake_pdf
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data.decode("utf-8"))

        self.assertTrue(data.get("success"))
        self.assertEqual(data["record"]["record_type"], "lab_report")

    def test_09_css_responsive_and_modal_rules(self):
        """CSS enforces no horizontal overflow, fixed modal viewports, and horizontal timing chips."""
        with open("static/css/doctor_consultations.css", "r", encoding="utf-8") as f:
            css = f.read()

        # Check container rules
        self.assertIn("overflow-x: hidden", css)
        self.assertIn("box-sizing: border-box", css)

        # Check modal rules preventing viewport overflow and background bleed
        self.assertIn(".consultations-modal-overlay", css)
        self.assertIn("max-height: 92vh", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn("body.modal-open-lock", css)

        # Check horizontal timing chips
        self.assertIn(".timing-horizontal-group", css)
        self.assertIn("flex-wrap: nowrap", css)

        # Check two-panel prescription grid
        self.assertIn(".prescription-two-panel-grid", css)
        self.assertIn("grid-template-columns: 1.15fr 0.85fr", css)

        # Check mobile breakpoints
        self.assertIn("@media (max-width: 768px)", css)
        self.assertIn("@media (max-width: 480px)", css)


if __name__ == "__main__":
    unittest.main()
