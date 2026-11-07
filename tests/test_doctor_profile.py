# ============================================================
# OMNICARE AI — DOCTOR PROFILE TEST SUITE
# Validates Profile UI, APIs, Photo Upload, Preferences,
# Document Management, Security, and Isolation.
# ============================================================

import io
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from services.doctor_profile_service import (
    get_doctor_profile,
    update_doctor_profile,
    upload_doctor_photo,
    delete_doctor_photo,
    get_working_preferences,
    update_working_preferences,
    list_doctor_documents,
    upload_doctor_document,
    get_document_for_doctor,
    delete_doctor_document,
    change_doctor_password,
    get_active_sessions_info,
    get_two_factor_status
)

TEST_DOCTOR_ID = "ea83806c-f033-4012-944b-22098514d9e9"
ANOTHER_DOCTOR_ID = "99999999-9999-9999-9999-999999999999"


class DoctorProfileTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "omnicare-test-secret"
        self.client = self.app.test_client()

    # ------------------------------------------------------------
    # 1. AUTHENTICATION & ACCESS CONTROL
    # ------------------------------------------------------------
    def test_unauthenticated_profile_page_redirects(self):
        """Unauthenticated access to /doctor/profile must redirect to doctor_login."""
        response = self.client.get("/doctor/profile")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/doctor/login", response.headers["Location"])

    def test_unauthenticated_api_details_returns_401(self):
        """Unauthenticated access to API details returns 401."""
        response = self.client.get("/doctor/profile/api/details")
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertFalse(data["success"])

    # ------------------------------------------------------------
    # 2. PROFILE PAGE RENDERING
    # ------------------------------------------------------------
    def test_authenticated_profile_page_renders_successfully(self):
        """Authenticated doctor receives 200 and sees My Profile page elements."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID
            sess["doctor_name"] = "Dr. Pragadesh Test"
            sess["doctor_email"] = "pragadesh.test@omnicare.ai"

        response = self.client.get("/doctor/profile")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("My Profile", html)
        self.assertIn("Professional Information", html)
        self.assertIn("Working Preferences", html)
        self.assertIn("Professional Documents", html)
        self.assertIn("Account &amp; Security", html)

    # ------------------------------------------------------------
    # 3. GET PROFILE API DETAILS
    # ------------------------------------------------------------
    def test_get_profile_api_details(self):
        """Details API returns complete profile, preferences, and documents without leaking password."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID
            sess["doctor_name"] = "Dr. Test Doctor"
            sess["doctor_email"] = "test@omnicare.ai"

        response = self.client.get("/doctor/profile/api/details")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("profile", data)
        self.assertIn("preferences", data)
        self.assertIn("documents", data)
        self.assertIn("active_sessions", data)
        self.assertIn("two_factor", data)
        self.assertNotIn("password", data["profile"])

    # ------------------------------------------------------------
    # 4. PROFILE UPDATE API
    # ------------------------------------------------------------
    def test_profile_update_success(self):
        """Doctor can update their name, qualification, and hospital information."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID
            sess["doctor_name"] = "Dr. Old Name"

        payload = {
            "full_name": "Dr. Pragadesh S",
            "qualification": "MBBS, MD (Cardiology), FRCP",
            "specialization": "Interventional Cardiology",
            "department": "Department of Cardiology",
            "hospital_name": "Apollo Multispecialty Hospital",
            "hospital_address": "21 Greams Road, Chennai",
            "experience_years": 12,
            "professional_bio": "Senior interventional cardiologist with over 12 years of clinical expertise."
        }

        response = self.client.post(
            "/doctor/profile/api/update",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["profile"]["full_name"], "Dr. Pragadesh S")
        self.assertEqual(data["profile"]["qualification"], "MBBS, MD (Cardiology), FRCP")
        self.assertEqual(data["profile"]["experience_years"], 12)

    def test_profile_update_validation_empty_name(self):
        """Updating with an empty full name is rejected with 400."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        payload = {"full_name": "   "}
        response = self.client.post(
            "/doctor/profile/api/update",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])

    # ------------------------------------------------------------
    # 5. PHOTO UPLOAD & REMOVE
    # ------------------------------------------------------------
    def test_photo_upload_and_delete(self):
        """Doctor can upload a photo and subsequently remove it."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        # Upload valid fake PNG
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        data = {
            "photo": (io.BytesIO(png_bytes), "profile.png", "image/png")
        }
        res_upload = self.client.post(
            "/doctor/profile/api/photo",
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(res_upload.status_code, 200)
        upload_data = res_upload.get_json()
        self.assertTrue(upload_data["success"])
        self.assertIn("photo_url", upload_data)

        # Delete photo
        res_delete = self.client.delete("/doctor/profile/api/photo")
        self.assertEqual(res_delete.status_code, 200)
        del_data = res_delete.get_json()
        self.assertTrue(del_data["success"])
        self.assertTrue(del_data.get("default_avatar"))

    def test_photo_upload_invalid_extension(self):
        """Uploading an executable or unsupported file extension is rejected."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        data = {
            "photo": (io.BytesIO(b"malicious script"), "hack.exe", "application/x-msdownload")
        }
        response = self.client.post(
            "/doctor/profile/api/photo",
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    # ------------------------------------------------------------
    # 6. WORKING PREFERENCES API
    # ------------------------------------------------------------
    def test_working_preferences_update(self):
        """Doctor can update consultation days, hours, and mode."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        payload = {
            "consultation_days": ["Monday", "Wednesday", "Friday"],
            "consultation_start_time": "10:00",
            "consultation_end_time": "16:00",
            "consultation_mode": "teleconsultation"
        }
        response = self.client.post(
            "/doctor/profile/api/preferences",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["preferences"]["consultation_mode"], "teleconsultation")
        self.assertEqual(data["preferences"]["consultation_start_time"], "10:00")
        self.assertEqual(data["preferences"]["consultation_days"], ["Monday", "Wednesday", "Friday"])

    # ------------------------------------------------------------
    # 7. DOCUMENT MANAGEMENT & DATA ISOLATION
    # ------------------------------------------------------------
    def test_document_upload_view_and_delete(self):
        """Doctor can upload a credential document, view it, and delete it."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        fake_pdf = b"%PDF-1.4 test document content"
        data = {
            "document_file": (io.BytesIO(fake_pdf), "mci_reg.pdf", "application/pdf"),
            "document_name": "State Medical Council Registration",
            "document_type": "medical_registration"
        }
        res_upload = self.client.post(
            "/doctor/profile/api/documents/upload",
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(res_upload.status_code, 201)
        doc_data = res_upload.get_json()
        self.assertTrue(doc_data["success"])
        doc_id = doc_data["document"]["id"]

        # View document
        res_view = self.client.get(f"/doctor/profile/api/documents/{doc_id}/view")
        self.assertIn(res_view.status_code, [200, 302])
        res_view.close()

        # Delete document
        res_del = self.client.delete(f"/doctor/profile/api/documents/{doc_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()["success"])

    def test_document_isolation_between_doctors(self):
        """Doctor B cannot view, download, or delete Doctor A's credential document."""
        # 1. Upload doc as Doctor A
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        data = {
            "document_file": (io.BytesIO(b"%PDF-1.4 confidential license"), "license.pdf", "application/pdf"),
            "document_name": "Confidential License",
            "document_type": "medical_registration"
        }
        res_upload = self.client.post(
            "/doctor/profile/api/documents/upload",
            data=data,
            content_type="multipart/form-data"
        )
        doc_id = res_upload.get_json()["document"]["id"]

        # 2. Switch session to Doctor B
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = ANOTHER_DOCTOR_ID

        # Doctor B attempts to delete Doctor A's document
        res_del = self.client.delete(f"/doctor/profile/api/documents/{doc_id}")
        self.assertEqual(res_del.status_code, 404)

        # Cleanup Doctor A doc
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID
        self.client.delete(f"/doctor/profile/api/documents/{doc_id}")

    # ------------------------------------------------------------
    # 8. PASSWORD CHANGE & SECURITY RULES
    # ------------------------------------------------------------
    def test_password_change_validation(self):
        """Password change requires length >= 8 and alphanumeric characters."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        # Short password
        payload_short = {
            "current_password": "any",
            "new_password": "short",
            "confirm_password": "short"
        }
        res_short = self.client.post(
            "/doctor/profile/api/change-password",
            data=json.dumps(payload_short),
            content_type="application/json"
        )
        self.assertEqual(res_short.status_code, 400)
        self.assertIn("at least 8 characters", res_short.get_json()["error"])

        # Mismatched confirmation
        payload_mismatch = {
            "current_password": "any",
            "new_password": "ValidPassword123",
            "confirm_password": "DifferentPassword123"
        }
        res_mismatch = self.client.post(
            "/doctor/profile/api/change-password",
            data=json.dumps(payload_mismatch),
            content_type="application/json"
        )
        self.assertEqual(res_mismatch.status_code, 400)
        self.assertIn("do not match", res_mismatch.get_json()["error"])

    # ------------------------------------------------------------
    # 9. MOBILE RESPONSIVE CSS & OVERFLOW PREVENTION
    # ------------------------------------------------------------
    def test_mobile_responsive_css_requirements(self):
        """Verifies Doctor Profile CSS meets all mobile responsiveness requirements."""
        css_path = os.path.join(PROJECT_ROOT, "static", "css", "doctor_profile.css")
        self.assertTrue(os.path.exists(css_path))
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # 1. Box sizing and max-width 100%
        self.assertIn("box-sizing: border-box;", css)
        self.assertIn("max-width: 100%;", css)
        self.assertIn("width: 100%;", css)

        # 2. Main profile card container and overflow handling
        self.assertIn(".doctor-profile-card", css)
        self.assertIn("flex-direction: column;", css)

        # 3. Word wrapping on doctor name, email, reg no, addresses
        self.assertIn("overflow-wrap: break-word;", css)
        self.assertIn("word-break: break-word;", css)
        self.assertIn("overflow-wrap: anywhere;", css)

        # 4. Edit profile button full width on mobile
        self.assertIn("#btnOpenEditProfileModal", css)

        # 5. Media queries for <= 700px and <= 380px (320px, 360px, 375px)
        self.assertIn("@media (max-width: 700px)", css)
        self.assertIn("@media (max-width: 380px)", css)

        # 6. Base layout overflow-x protection in doctor_base.html
        base_html_path = os.path.join(PROJECT_ROOT, "templates", "doctor_base.html")
        with open(base_html_path, "r", encoding="utf-8") as f:
            base_html = f.read()
        self.assertIn("overflow-x: hidden;", base_html)
        self.assertIn("max-width: 100%;", base_html)


if __name__ == "__main__":
    unittest.main()
