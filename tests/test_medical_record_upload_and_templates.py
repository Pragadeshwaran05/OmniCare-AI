import unittest
from unittest.mock import patch, MagicMock
import io
import json
import os

from app import app


class TestMedicalRecordUploadAndTemplates(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key-medical-records"
        self.client = self.app.test_client()
        self.patient_id = "test-patient-uuid-101"
        self.doctor_id = "test-doctor-uuid-202"

    @patch("app.check_workspace_access")
    @patch("app.save_patient_medical_record")
    @patch("app.process_medical_document")
    @patch("app.supabase_admin")
    def test_01_upload_existing_document_success(self, mock_supabase, mock_ai_proc, mock_save_rec, mock_access):
        """Option A: Uploading an existing PDF/image document saves record and triggers AI extraction."""
        mock_access.return_value = (
            True,
            {"doctor_id": self.doctor_id, "read_only": False, "is_external": False, "remaining_seconds": 3600},
            None
        )
        mock_save_rec.return_value = {
            "id": "rec_uuid_999",
            "patient_id": self.patient_id,
            "title": "Lab CBC Report",
            "record_type": "lab_report",
            "file_url": "https://example.com/storage/lab.pdf"
        }
        mock_ai_proc.return_value = {
            "event_date": "2026-11-09",
            "event_type": "lab_report",
            "diagnosis": "Normal Complete Blood Count",
            "clinical_findings": "WBC: 6.5, Hemoglobin: 14.2 g/dL",
            "investigations": [{"test_name": "CBC", "result": "Normal"}],
            "medications": [],
            "clinical_summary": "All hematologic parameters within normal reference ranges."
        }
        mock_insert = MagicMock()
        mock_insert.execute.return_value = MagicMock(data=[{"id": "timeline_1"}])
        mock_supabase.table.return_value.insert.return_value = mock_insert

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id
            sess["doctor_name"] = "Dr. Test Clinician"

        dummy_pdf = io.BytesIO(b"%PDF-1.4 test dummy content")
        data = {
            "file": (dummy_pdf, "cbc_report.pdf"),
            "record_type": "lab_report",
            "title": "Lab CBC Report",
            "document_date": "2026-11-09",
            "description": "Routine annual health screening CBC",
            "hospital_name": "OmniCare Labs",
            "doctor_name": "Dr. Test Clinician",
            "trigger_ai": "true"
        }

        res = self.client.post(
            f"/doctor/patient-workspace/{self.patient_id}/upload-medical-record",
            data=data,
            content_type="multipart/form-data"
        )

        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["record"]["id"], "rec_uuid_999")
        mock_save_rec.assert_called_once()
        mock_ai_proc.assert_called_once()

    @patch("app.check_workspace_access")
    @patch("app.save_patient_medical_record")
    @patch("app.supabase_admin")
    def test_02_create_consultation_note_success(self, mock_supabase, mock_save_rec, mock_access):
        """Option B: Create consultation note with vitals and generate hospital-grade PDF."""
        mock_access.return_value = (
            True,
            {"doctor_id": self.doctor_id, "read_only": False, "is_external": False, "remaining_seconds": 3600},
            None
        )
        # Mock patient lookup
        mock_pt_query = MagicMock()
        mock_pt_query.execute.return_value = MagicMock(data={
            "id": self.patient_id,
            "full_name": "Jane Doe",
            "age": 34,
            "gender": "Female",
            "blood_group": "A+"
        })
        # Mock table returns
        def table_router(table_name):
            mock_tbl = MagicMock()
            if table_name == "patients":
                mock_tbl.select.return_value.eq.return_value.single.return_value = mock_pt_query
            elif table_name == "health_timeline_events":
                mock_ins = MagicMock()
                mock_ins.execute.return_value = MagicMock(data=[{"id": "evt_1"}])
                mock_tbl.insert.return_value = mock_ins
            return mock_tbl

        mock_supabase.table.side_effect = table_router

        mock_save_rec.return_value = {
            "id": "rec_cons_123",
            "patient_id": self.patient_id,
            "title": "Consultation Note - General Consultation",
            "record_type": "consultation",
            "file_url": "https://example.com/storage/consultation.pdf"
        }

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id
            sess["doctor_name"] = "Dr. Test Clinician"

        payload = {
            "consultation_type": "General Consultation",
            "document_date": "2026-11-09",
            "chief_complaint": "Persistent dry cough for 5 days with mild chest tightness",
            "hpi": "Symptoms began after viral exposure. No hemoptysis. Mildly worse at night.",
            "vitals": {
                "bp": "118/76",
                "pulse": "74",
                "temperature": "98.4",
                "respiratory_rate": "16",
                "oxygen_saturation": "99",
                "weight": "62",
                "height": "168",
                "bmi": "22.0"
            },
            "diagnosis_primary": "Post-viral bronchial hyperreactivity",
            "diagnosis_secondary": "Mild seasonal allergic rhinitis",
            "treatment_plan": "Inhaled bronchodilator as needed, oral antihistamine, steam inhalation",
            "clinical_notes": "Avoid cold air and known allergens. Review in 10 days if symptoms persist."
        }

        res = self.client.post(
            f"/doctor/patient-workspace/{self.patient_id}/create-consultation",
            json=payload
        )

        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["record"]["record_type"], "consultation")
        mock_save_rec.assert_called_once()

    @patch("app.check_workspace_access")
    @patch("app.save_patient_medical_record")
    @patch("app.supabase_admin")
    def test_03_create_prescription_with_timing_chips_success(self, mock_supabase, mock_save_rec, mock_access):
        """Option C: Create prescription with horizontal M/A/E/N timing chips."""
        mock_access.return_value = (
            True,
            {"doctor_id": self.doctor_id, "read_only": False, "is_external": False, "remaining_seconds": 3600},
            None
        )
        mock_pt_query = MagicMock()
        mock_pt_query.execute.return_value = MagicMock(data={
            "id": self.patient_id,
            "full_name": "Jane Doe",
            "age": 34,
            "gender": "Female"
        })
        def table_router(table_name):
            mock_tbl = MagicMock()
            if table_name == "patients":
                mock_tbl.select.return_value.eq.return_value.single.return_value = mock_pt_query
            elif table_name == "health_timeline_events":
                mock_ins = MagicMock()
                mock_ins.execute.return_value = MagicMock(data=[{"id": "evt_rx_1"}])
                mock_tbl.insert.return_value = mock_ins
            return mock_tbl

        mock_supabase.table.side_effect = table_router

        mock_save_rec.return_value = {
            "id": "rec_rx_555",
            "patient_id": self.patient_id,
            "title": "Prescription - 09 Nov 2026",
            "record_type": "prescription",
            "file_url": "https://example.com/storage/prescription.pdf"
        }

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id
            sess["doctor_name"] = "Dr. Test Clinician"

        payload = {
            "diagnosis": "Acute Bronchitis",
            "document_date": "2026-11-09",
            "medicines": [
                {
                    "name": "Amoxicillin-Clavulanate (Augmentin)",
                    "dosage": "625 mg",
                    "timing": {"morning": True, "afternoon": False, "evening": True, "night": False},
                    "frequency": "Twice daily",
                    "food_relation": "After Food",
                    "duration": "5 days",
                    "instructions": "Take with full glass of water. Complete 5-day course."
                },
                {
                    "name": "Levocetirizine",
                    "dosage": "5 mg",
                    "timing": {"morning": False, "afternoon": False, "evening": False, "night": True},
                    "frequency": "Once daily",
                    "food_relation": "At Bedtime",
                    "duration": "7 days",
                    "instructions": "May cause mild drowsiness."
                }
            ],
            "general_advice": "Adequate hydration (2-3 L/day), warm saline gargles, voice rest.",
            "follow_up": "Review after 5 days if fever persists or cough worsens."
        }

        res = self.client.post(
            f"/doctor/patient-workspace/{self.patient_id}/create-prescription",
            json=payload
        )

        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["record"]["record_type"], "prescription")
        mock_save_rec.assert_called_once()

    @patch("app.check_workspace_access")
    @patch("app.save_patient_medical_record")
    @patch("app.supabase_admin")
    def test_04_create_other_document_medical_certificate(self, mock_supabase, mock_save_rec, mock_access):
        """Option D: Create medical certificate with from/to period and diagnosis."""
        mock_access.return_value = (
            True,
            {"doctor_id": self.doctor_id, "read_only": False, "is_external": False, "remaining_seconds": 3600},
            None
        )
        mock_pt_query = MagicMock()
        mock_pt_query.execute.return_value = MagicMock(data={
            "id": self.patient_id,
            "full_name": "Jane Doe",
            "age": 34,
            "gender": "Female"
        })
        def table_router(table_name):
            mock_tbl = MagicMock()
            if table_name == "patients":
                mock_tbl.select.return_value.eq.return_value.single.return_value = mock_pt_query
            elif table_name == "health_timeline_events":
                mock_ins = MagicMock()
                mock_ins.execute.return_value = MagicMock(data=[{"id": "evt_cert_1"}])
                mock_tbl.insert.return_value = mock_ins
            return mock_tbl

        mock_supabase.table.side_effect = table_router

        mock_save_rec.return_value = {
            "id": "rec_cert_777",
            "patient_id": self.patient_id,
            "title": "Medical Fitness Certificate",
            "record_type": "medical_certificate",
            "file_url": "https://example.com/storage/cert.pdf"
        }

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id
            sess["doctor_name"] = "Dr. Test Clinician"

        payload = {
            "doc_type": "medical_certificate",
            "title": "Medical Fitness Certificate",
            "document_date": "2026-11-09",
            "certificate_reason": "Acute Viral Gastroenteritis with moderate dehydration",
            "valid_from": "2026-11-09",
            "valid_to": "2026-11-12",
            "clinical_summary": "Patient was examined and found unfit for duty. Complete bed rest advised.",
            "findings": "Afebrile, soft abdomen, mild epigastric tenderness.",
            "recommendations": "Oral rehydration, light diet, rest until 12 Nov 2026."
        }

        res = self.client.post(
            f"/doctor/patient-workspace/{self.patient_id}/create-other-document",
            json=payload
        )

        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["record"]["record_type"], "medical_certificate")

    @patch("app.check_workspace_access")
    @patch("app.supabase_admin")
    def test_05_preview_document_pdf_stream(self, mock_supabase, mock_access):
        """Preview endpoint returns in-memory PDF stream with application/pdf MIME type."""
        mock_access.return_value = (
            True,
            {"doctor_id": self.doctor_id, "read_only": False, "is_external": False, "remaining_seconds": 3600},
            None
        )
        mock_pt_query = MagicMock()
        mock_pt_query.execute.return_value = MagicMock(data={
            "id": self.patient_id,
            "full_name": "Jane Doe",
            "age": 34,
            "gender": "Female"
        })
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value = mock_pt_query

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id
            sess["doctor_name"] = "Dr. Test Clinician"

        payload = {
            "template_type": "prescription",
            "document_date": "2026-11-09",
            "diagnosis": "Mild Hypertension",
            "medicines": [
                {
                    "name": "Telmisartan",
                    "dosage": "40 mg",
                    "timing": {"morning": True, "afternoon": False, "evening": False, "night": False},
                    "frequency": "Once daily",
                    "food_relation": "Before Food",
                    "duration": "30 days"
                }
            ],
            "general_advice": "Low salt diet, regular morning walking.",
            "follow_up": "Check BP weekly."
        }

        res = self.client.post(
            f"/doctor/patient-workspace/{self.patient_id}/preview-document-pdf",
            json=payload
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "application/pdf")
        self.assertTrue(res.data.startswith(b"%PDF"))

    @patch("app.check_workspace_access")
    def test_06_read_only_access_strictly_blocks_creation_and_upload(self, mock_access):
        """Read-only and external consultation sessions must be strictly blocked with HTTP 403."""
        # 1. Read-only session
        mock_access.return_value = (
            True,
            {"doctor_id": "EXTERNAL_CONSULTATION", "read_only": True, "is_external": True, "remaining_seconds": 300},
            None
        )

        endpoints = [
            (f"/doctor/patient-workspace/{self.patient_id}/upload-medical-record", "multipart/form-data", {"file": (io.BytesIO(b"abc"), "test.pdf")}),
            (f"/doctor/patient-workspace/{self.patient_id}/create-consultation", "application/json", {"chief_complaint": "test"}),
            (f"/doctor/patient-workspace/{self.patient_id}/create-prescription", "application/json", {"diagnosis": "test"}),
            (f"/doctor/patient-workspace/{self.patient_id}/create-other-document", "application/json", {"title": "test"}),
            (f"/doctor/patient-workspace/{self.patient_id}/preview-document-pdf", "application/json", {"template_type": "consultation"})
        ]

        for url, ctype, data in endpoints:
            if ctype == "application/json":
                res = self.client.post(url, json=data)
            else:
                res = self.client.post(url, data=data, content_type=ctype)

            self.assertEqual(
                res.status_code,
                403,
                f"Endpoint {url} did not return 403 in read-only mode!"
            )
            res_json = res.get_json()
            self.assertFalse(res_json.get("success", True))
            self.assertIn("read-only", res_json.get("error", "").lower())

    @patch("app.check_workspace_access")
    @patch("app.supabase_admin")
    def test_07_api_records_endpoint_returns_json_list(self, mock_supabase, mock_access):
        """API records endpoint returns list of records with count."""
        mock_access.return_value = (
            True,
            {"doctor_id": self.doctor_id, "read_only": False, "is_external": False, "remaining_seconds": 3600},
            None
        )
        mock_records_query = MagicMock()
        mock_records_query.execute.return_value = MagicMock(data=[
            {"id": "r1", "title": "Record 1", "record_type": "prescription", "file_url": "https://example.com/r1.pdf"},
            {"id": "r2", "title": "Record 2", "record_type": "lab_report", "file_url": "https://example.com/r2.pdf"}
        ])
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value = mock_records_query

        res = self.client.get(f"/doctor/patient-workspace/{self.patient_id}/api/records")
        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["count"], 2)
        self.assertEqual(len(res_json["records"]), 2)

    @patch("app.check_workspace_access")
    def test_08_invalid_file_extension_rejected(self, mock_access):
        """Uploading non-medical format (.exe, .bat, etc.) is rejected with 400 Bad Request."""
        mock_access.return_value = (
            True,
            {"doctor_id": self.doctor_id, "read_only": False, "is_external": False, "remaining_seconds": 3600},
            None
        )
        dummy_file = io.BytesIO(b"binary executable")
        data = {
            "file": (dummy_file, "malicious.exe"),
            "record_type": "other"
        }
        res = self.client.post(
            f"/doctor/patient-workspace/{self.patient_id}/upload-medical-record",
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 400)
        res_json = res.get_json()
        self.assertFalse(res_json["success"])
        self.assertIn("unsupported format", res_json["error"].lower())


if __name__ == "__main__":
    unittest.main()
