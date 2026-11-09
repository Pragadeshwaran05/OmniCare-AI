import unittest
from unittest.mock import patch, MagicMock
import io
import json
import os

from app import app
from services.medical_record_document_service import (
    generate_consultation_pdf,
    generate_prescription_pdf
)


class TestPrescriptionConsultationModalAndRecordsResponsive(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key-ui-responsive"
        self.client = self.app.test_client()
        self.patient_id = "test-pt-uuid-ui-999"
        self.doctor_id = "test-doc-uuid-ui-888"

    def test_01_consultation_pdf_generation_with_findings_and_vitals(self):
        """ReportLab PDF generation succeeds with consultation time, findings, recommendations, and vitals."""
        doctor_data = {
            "full_name": "Dr. Sarah Mitchell",
            "specialization": "Consultant Pulmonologist",
            "registration_number": "MCI-48291",
            "hospital_name": "Metro Speciality Health Clinic",
            "hospital_address": "452 Healthcare Boulevard, Bangalore"
        }
        patient_data = {
            "name": "Alex Johnson",
            "age": 42,
            "gender": "Male",
            "blood_group": "O+",
            "id": self.patient_id
        }
        consultation_payload = {
            "consultation_type": "Specialist Consultation",
            "consultation_date": "2026-11-09",
            "consultation_time": "14:30",
            "chief_complaint": "Persistent dry cough, mild wheezing on exertion",
            "hpi": "Symptoms ongoing for 2 weeks following seasonal allergy flare-up.",
            "vitals": {
                "bp": "124/82",
                "pulse": "76",
                "temperature": "98.6",
                "respiratory_rate": "18",
                "oxygen_saturation": "98",
                "weight": "74",
                "height": "175",
                "bmi": "24.2"
            },
            "diagnosis_primary": "Allergic Bronchitis with Reactive Airways",
            "diagnosis_secondary": "Mild Rhinosinusitis",
            "findings": "Bilateral mild expiratory wheeze in lower zones. No crepitations. Normal heart sounds S1/S2.",
            "treatment_plan": "Inhaled corticosteroid/long-acting beta-agonist inhaler BID, oral antihistamine at bedtime.",
            "recommendations": "Avoid exposure to dust and cold environments. Steam inhalation daily. Hydration 2.5L/day.",
            "follow_up": "Clinical review in 7 days or sooner if breathing difficulty increases.",
            "clinical_notes": "Patient informed about correct inhaler spacer technique."
        }

        pdf_bytes = generate_consultation_pdf(doctor_data, patient_data, consultation_payload)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_02_prescription_pdf_generation_with_type_strength_timing(self):
        """ReportLab PDF generation succeeds with prescription time, medicine type, strength, and M/A/E/N timing."""
        doctor_data = {
            "full_name": "Dr. Sarah Mitchell",
            "specialization": "Consultant Pulmonologist",
            "registration_number": "MCI-48291",
            "hospital_name": "Metro Speciality Health Clinic",
            "hospital_address": "452 Healthcare Boulevard, Bangalore"
        }
        patient_data = {
            "name": "Alex Johnson",
            "age": 42,
            "gender": "Male",
            "id": self.patient_id
        }
        prescription_payload = {
            "prescription_date": "2026-11-09",
            "prescription_time": "14:35",
            "diagnosis": "Allergic Bronchitis & Rhinitis",
            "medicines": [
                {
                    "name": "Amoxicillin and Potassium Clavulanate",
                    "type": "Tablet",
                    "strength": "625 mg",
                    "dosage": "1 Tab",
                    "timing": {"morning": True, "afternoon": False, "evening": True, "night": False},
                    "frequency": "Twice daily (BD)",
                    "food_relation": "After Food (PC)",
                    "duration": "5 days",
                    "instructions": "Swallow whole with plenty of water. Finish full course."
                },
                {
                    "name": "Budesonide & Formoterol Inhaler",
                    "type": "Inhaler",
                    "strength": "200/6 mcg",
                    "dosage": "2 Puffs",
                    "timing": {"morning": True, "afternoon": False, "evening": False, "night": True},
                    "frequency": "Twice daily",
                    "food_relation": "After Food",
                    "duration": "14 days",
                    "instructions": "Rinse mouth thoroughly with water after inhalation."
                },
                {
                    "name": "Montelukast & Levocetirizine",
                    "type": "Tablet",
                    "strength": "10 mg / 5 mg",
                    "dosage": "1 Tab",
                    "timing": {"morning": False, "afternoon": False, "evening": False, "night": True},
                    "frequency": "At bedtime (HS)",
                    "food_relation": "At Bedtime",
                    "duration": "10 days",
                    "instructions": "Take at night before sleeping."
                }
            ],
            "general_advice": "Drink lukewarm water, avoid cold beverages and active smoking zones.",
            "follow_up": "Review after 7 days.",
            "clinical_notes": "Monitor peak expiratory flow if possible."
        }

        pdf_bytes = generate_prescription_pdf(doctor_data, patient_data, prescription_payload)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_03_css_modal_layout_structure(self):
        """Verify CSS modal overlay, modal card, form, header, body, and footer layout constraints."""
        css_path = os.path.join("static", "css", "doctor_patient_workspace.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # Modal overlay: fixed, high z-index, overflow hidden
        self.assertIn(".workspace-modal-overlay {", css)
        self.assertIn("overflow: hidden", css)

        # Modal card: flex column, max-height 92vh, overflow hidden
        self.assertIn("max-height: 92vh", css)
        self.assertIn(".workspace-modal-card > form", css)
        self.assertIn(".modal-card-form {", css)

        # Header: flex-shrink: 0
        self.assertIn("flex-shrink: 0", css)

        # Body: overflow-y: auto, flex: 1 1 auto, min-height: 0
        self.assertIn("overflow-y: auto", css)
        self.assertIn("min-height: 0", css)

        # Footer: flex-shrink: 0, position: relative
        self.assertIn(".modal-card-footer {", css)
        self.assertIn("position: relative", css)

    def test_04_css_medical_record_card_mobile_grid_and_word_wrap(self):
        """Verify 2-column mobile CSS grid and overflow-wrap prevention of 1-char vertical wrapping."""
        css_path = os.path.join("static", "css", "doctor_patient_workspace.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # 2-column grid layout for mobile card
        self.assertIn("grid-template-columns: 42px minmax(0, 1fr)", css)
        self.assertIn("grid-column: 1", css)
        self.assertIn("grid-column: 2", css)

        # Word wrap rules: white-space: normal, word-break: normal, overflow-wrap: anywhere
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn("word-break: normal", css)

        # Bottom nav clearance padding (95px)
        self.assertIn("padding-bottom: calc(95px + env(safe-area-inset-bottom, 0px)) !important;", css)

    def test_05_template_has_all_required_modal_fields(self):
        """Verify HTML template includes all required consultation & prescription fields and classes."""
        tmpl_path = os.path.join("templates", "doctor", "patient_workspace.html")
        with open(tmpl_path, "r", encoding="utf-8") as f:
            tmpl = f.read()

        # Modal forms have modal-card-form class
        self.assertIn('form id="formOptionB" class="modal-card-form"', tmpl)
        self.assertIn('form id="formOptionC" class="modal-card-form"', tmpl)

        # Consultation fields
        self.assertIn('id="consTime"', tmpl)
        self.assertIn('id="consFindings"', tmpl)
        self.assertIn('id="consRecommendations"', tmpl)
        self.assertIn('id="consFollowUp"', tmpl)
        self.assertIn('id="consChiefComplaint"', tmpl)
        self.assertIn('id="consHpi"', tmpl)
        self.assertIn('id="consPrimaryDiag"', tmpl)

        # Prescription fields
        self.assertIn('id="rxTime"', tmpl)
        self.assertIn('id="rxDiagnosis"', tmpl)
        self.assertIn('id="rxAdvice"', tmpl)
        self.assertIn('id="rxFollowUp"', tmpl)
        self.assertIn('id="rxClinicalNotes"', tmpl)

        # Medicine builder items
        self.assertIn('med-input-type', tmpl)
        self.assertIn('med-input-strength', tmpl)
        self.assertIn('med-input-dosage', tmpl)
        self.assertIn('timing-m', tmpl)
        self.assertIn('timing-a', tmpl)
        self.assertIn('timing-e', tmpl)
        self.assertIn('timing-n', tmpl)

    @patch("app.check_workspace_access")
    @patch("app.save_patient_medical_record")
    @patch("app.supabase_admin")
    def test_06_api_create_consultation_saves_structured_findings(self, mock_supabase, mock_save_rec, mock_access):
        """API creates consultation note saving findings, recommendations, and time in structured data."""
        mock_access.return_value = (
            True,
            {"doctor_id": self.doctor_id, "read_only": False, "is_external": False, "remaining_seconds": 3600},
            None
        )
        mock_pt_query = MagicMock()
        mock_pt_query.execute.return_value = MagicMock(data={
            "id": self.patient_id,
            "full_name": "Alex Johnson",
            "age": 42,
            "gender": "Male"
        })
        def table_router(table_name):
            mock_tbl = MagicMock()
            if table_name == "patients":
                mock_tbl.select.return_value.eq.return_value.single.return_value = mock_pt_query
            elif table_name == "health_timeline_events":
                mock_ins = MagicMock()
                mock_ins.execute.return_value = MagicMock(data=[{"id": "evt_c1"}])
                mock_tbl.insert.return_value = mock_ins
            return mock_tbl

        mock_supabase.table.side_effect = table_router
        mock_save_rec.return_value = {
            "id": "rec_cons_verified",
            "patient_id": self.patient_id,
            "title": "Consultation Note - Specialist Consultation",
            "record_type": "consultation",
            "file_url": "https://example.com/cons.pdf"
        }

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id
            sess["doctor_name"] = "Dr. Sarah Mitchell"

        payload = {
            "consultation_type": "Specialist Consultation",
            "document_date": "2026-11-09",
            "consultation_time": "14:30",
            "chief_complaint": "Persistent dry cough",
            "hpi": "Symptoms for 2 weeks",
            "vitals": {"bp": "120/80", "pulse": "74"},
            "diagnosis_primary": "Allergic Bronchitis",
            "findings": "Mild expiratory wheezing",
            "treatment_plan": "Inhaler BID",
            "recommendations": "Hydration and avoidance of cold air",
            "follow_up": "Review in 7 days",
            "clinical_notes": "Technique demonstrated"
        }

        res = self.client.post(
            f"/doctor/patient-workspace/{self.patient_id}/create-consultation",
            json=payload
        )

        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertTrue(res_json["success"])
        mock_save_rec.assert_called_once()
        call_kwargs = mock_save_rec.call_args[1]
        structured_data = call_kwargs.get("structured_data", {})
        self.assertEqual(structured_data.get("consultation_time"), "14:30")
        self.assertEqual(structured_data.get("findings"), "Mild expiratory wheezing")
        self.assertEqual(structured_data.get("recommendations"), "Hydration and avoidance of cold air")
        self.assertEqual(structured_data.get("follow_up"), "Review in 7 days")

    @patch("app.check_workspace_access")
    @patch("app.save_patient_medical_record")
    @patch("app.supabase_admin")
    def test_07_api_create_prescription_saves_type_and_strength(self, mock_supabase, mock_save_rec, mock_access):
        """API creates prescription saving medicine type, strength, and timing in structured data."""
        mock_access.return_value = (
            True,
            {"doctor_id": self.doctor_id, "read_only": False, "is_external": False, "remaining_seconds": 3600},
            None
        )
        mock_pt_query = MagicMock()
        mock_pt_query.execute.return_value = MagicMock(data={
            "id": self.patient_id,
            "full_name": "Alex Johnson",
            "age": 42,
            "gender": "Male"
        })
        def table_router(table_name):
            mock_tbl = MagicMock()
            if table_name == "patients":
                mock_tbl.select.return_value.eq.return_value.single.return_value = mock_pt_query
            elif table_name == "health_timeline_events":
                mock_ins = MagicMock()
                mock_ins.execute.return_value = MagicMock(data=[{"id": "evt_rx_v"}])
                mock_tbl.insert.return_value = mock_ins
            return mock_tbl

        mock_supabase.table.side_effect = table_router
        mock_save_rec.return_value = {
            "id": "rec_rx_verified",
            "patient_id": self.patient_id,
            "title": "Prescription - 09 Nov 2026",
            "record_type": "prescription",
            "file_url": "https://example.com/rx.pdf"
        }

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id
            sess["doctor_name"] = "Dr. Sarah Mitchell"

        payload = {
            "diagnosis": "Allergic Bronchitis",
            "document_date": "2026-11-09",
            "prescription_time": "14:35",
            "medicines": [
                {
                    "name": "Amoxicillin-Clavulanate",
                    "type": "Tablet",
                    "strength": "625 mg",
                    "dosage": "1 Tab",
                    "timing": {"morning": True, "afternoon": False, "evening": True, "night": False},
                    "frequency": "Twice daily",
                    "food_relation": "After Food",
                    "duration": "5 days",
                    "instructions": "Take after meals."
                }
            ],
            "general_advice": "Hydrate well.",
            "follow_up": "Review in 5 days."
        }

        res = self.client.post(
            f"/doctor/patient-workspace/{self.patient_id}/create-prescription",
            json=payload
        )

        self.assertEqual(res.status_code, 200)
        res_json = res.get_json()
        self.assertTrue(res_json["success"])
        mock_save_rec.assert_called_once()
        call_kwargs = mock_save_rec.call_args[1]
        structured_data = call_kwargs.get("structured_data", {})
        self.assertEqual(structured_data.get("prescription_time"), "14:35")
        meds = structured_data.get("medicines", [])
        self.assertEqual(len(meds), 1)
        self.assertEqual(meds[0].get("type"), "Tablet")
        self.assertEqual(meds[0].get("strength"), "625 mg")


if __name__ == "__main__":
    unittest.main()
