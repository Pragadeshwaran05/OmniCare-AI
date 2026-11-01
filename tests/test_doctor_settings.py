# ============================================================
# OMNICARE AI — DOCTOR SETTINGS TEST SUITE
# Validates Settings UI, APIs, Preferences, Appearance,
# Connected Services, Data Export, and Account Deactivation.
# ============================================================

import os
import sys
import json
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from services.doctor_settings_service import (
    get_doctor_settings,
    update_doctor_settings,
    check_connected_services_status,
    export_doctor_data,
    deactivate_doctor_account
)
from services.clinical_audit_service import get_doctor_notifications

TEST_DOCTOR_ID = "ea83806c-f033-4012-944b-22098514d9e9"
ANOTHER_DOCTOR_ID = "11111111-2222-3333-4444-555555555555"


class DoctorSettingsTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "omnicare-settings-test-secret"
        self.client = self.app.test_client()

    # ------------------------------------------------------------
    # 1. AUTHENTICATION & ACCESS CONTROL
    # ------------------------------------------------------------
    def test_unauthenticated_settings_page_redirects(self):
        """Unauthenticated doctor accessing /doctor/settings is redirected to doctor_login."""
        response = self.client.get("/doctor/settings")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/doctor/login", response.headers["Location"])

    def test_unauthenticated_api_preferences_returns_401(self):
        """Unauthenticated API call returns 401."""
        response = self.client.get("/doctor/settings/api/preferences")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.get_json()["success"])

    # ------------------------------------------------------------
    # 2. SETTINGS PAGE RENDERING & CARDS
    # ------------------------------------------------------------
    def test_authenticated_settings_page_renders_all_cards(self):
        """Authenticated doctor receives 200 with all 6 required settings cards."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID
            sess["doctor_name"] = "Dr. Pragadesh Test"
            sess["doctor_email"] = "pragadesh@omnicare.ai"

        response = self.client.get("/doctor/settings")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        # Check title & subtitle
        self.assertIn("Settings", html)
        self.assertIn("Manage your account, security, preferences, and application settings", html)

        # Check all 6 cards
        self.assertIn("Account Settings", html)
        self.assertIn("Security &amp; Login", html)
        self.assertIn("Notifications", html)
        self.assertIn("Appearance", html)
        self.assertIn("Data &amp; Privacy", html)
        self.assertIn("Connected Services", html)

        # Check settings items
        self.assertIn("Edit Profile", html)
        self.assertIn("Professional Details", html)
        self.assertIn("Working Preferences", html)
        self.assertIn("Change Password", html)
        self.assertIn("Two-Factor Authentication", html)
        self.assertIn("Patient Access Requests", html)
        self.assertIn("Access Expiry &amp; Revocation", html)
        self.assertIn("Download My Data", html)
        self.assertIn("Delete Account", html)
        self.assertIn("Supabase", html)
        self.assertIn("Gemini AI", html)

    # ------------------------------------------------------------
    # 3. NOTIFICATION PREFERENCES & LIVE FILTERING
    # ------------------------------------------------------------
    def test_notification_preferences_persistence_and_filtering(self):
        """Toggling notification preferences updates database/cache and filters actual notifications."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        # 1. Disable access request notifications
        res_post = self.client.post(
            "/doctor/settings/api/preferences",
            data=json.dumps({"notify_access_requests": False}),
            content_type="application/json"
        )
        self.assertEqual(res_post.status_code, 200)
        data = res_post.get_json()
        self.assertTrue(data["success"])
        self.assertFalse(data["settings"]["notify_access_requests"])

        # 2. Check get_doctor_notifications respects the preference
        mock_requests = [
            {
                "id": "req-101",
                "patient_id": "pat-1",
                "status": "pending",
                "requested_at": "2026-11-01T10:00:00Z"
            }
        ]
        notifs = get_doctor_notifications(TEST_DOCTOR_ID, mock_requests)
        # Pending request notification should be suppressed when notify_access_requests is False
        pending_notifs = [n for n in notifs["notifications"] if "pending" in n["id"]]
        self.assertEqual(len(pending_notifs), 0)

        # 3. Re-enable access requests
        self.client.post(
            "/doctor/settings/api/preferences",
            data=json.dumps({"notify_access_requests": True}),
            content_type="application/json"
        )
        notifs_enabled = get_doctor_notifications(TEST_DOCTOR_ID, mock_requests)
        self.assertGreaterEqual(len(notifs_enabled["notifications"]), 1)

    # ------------------------------------------------------------
    # 4. APPEARANCE PREFERENCES (THEME & SIDEBAR)
    # ------------------------------------------------------------
    def test_theme_and_sidebar_preferences(self):
        """Updating theme and sidebar mode validates and saves successfully."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        # Dark theme
        res_theme = self.client.post(
            "/doctor/settings/api/preferences",
            data=json.dumps({"theme": "dark"}),
            content_type="application/json"
        )
        self.assertEqual(res_theme.status_code, 200)
        self.assertEqual(res_theme.get_json()["settings"]["theme"], "dark")

        # Compact sidebar
        res_sb = self.client.post(
            "/doctor/settings/api/preferences",
            data=json.dumps({"sidebar_mode": "compact"}),
            content_type="application/json"
        )
        self.assertEqual(res_sb.status_code, 200)
        self.assertEqual(res_sb.get_json()["settings"]["sidebar_mode"], "compact")

        # Invalid values are safely ignored / unchanged
        res_invalid = self.client.post(
            "/doctor/settings/api/preferences",
            data=json.dumps({"theme": "neon-purple", "sidebar_mode": "floating"}),
            content_type="application/json"
        )
        self.assertEqual(res_invalid.status_code, 200)
        self.assertEqual(res_invalid.get_json()["settings"]["theme"], "dark")
        self.assertEqual(res_invalid.get_json()["settings"]["sidebar_mode"], "compact")

    # ------------------------------------------------------------
    # 5. PASSWORD CHANGE VIA SETTINGS
    # ------------------------------------------------------------
    def test_settings_password_change_validation(self):
        """Password update validates length and complexity."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        # Short password
        res = self.client.post(
            "/doctor/settings/api/change-password",
            data=json.dumps({
                "current_password": "any",
                "new_password": "short",
                "confirm_password": "short"
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("at least 8 characters", res.get_json()["error"])

    # ------------------------------------------------------------
    # 6. CONNECTED SERVICES HEALTH CHECK
    # ------------------------------------------------------------
    def test_connected_services_status_api(self):
        """Connected services endpoint returns accurate status without leaking secrets."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        response = self.client.get("/doctor/settings/api/services/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("services", data)
        self.assertIn("supabase", data["services"])
        self.assertIn("gemini", data["services"])

        # Ensure no sensitive credentials leaked
        text = json.dumps(data)
        self.assertNotIn("SUPABASE_KEY", text)
        self.assertNotIn("service_role", text)
        self.assertNotIn("eyJh", text)

    # ------------------------------------------------------------
    # 7. DATA EXPORT (JSON DOWNLOAD)
    # ------------------------------------------------------------
    def test_data_export_security_and_content(self):
        """Export endpoint downloads doctor profile, settings, and metadata in JSON."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID
            sess["doctor_name"] = "Dr. Pragadesh S"

        response = self.client.get("/doctor/settings/api/export")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers.get("Content-Disposition", ""))

        export_data = response.get_json()
        self.assertIn("export_metadata", export_data)
        self.assertIn("doctor_profile", export_data)
        self.assertIn("application_settings", export_data)
        self.assertIn("credential_documents", export_data)
        self.assertIn("compliance_notice", export_data["export_metadata"])

        # Ensure password hash is NOT present in exported doctor profile
        self.assertNotIn("password", export_data["doctor_profile"])

    # ------------------------------------------------------------
    # 8. ACCOUNT DEACTIVATION WORKFLOW
    # ------------------------------------------------------------
    def test_account_deactivation_requires_password(self):
        """Account deactivation requires password confirmation."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        # Empty password
        res = self.client.post(
            "/doctor/settings/api/delete-account",
            data=json.dumps({"password_confirm": ""}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("password", res.get_json()["error"].lower())

    # ------------------------------------------------------------
    # 9. CROSS-DOCTOR ISOLATION
    # ------------------------------------------------------------
    def test_cross_doctor_settings_isolation(self):
        """Doctor A's settings modifications do not affect Doctor B."""
        # Update Doctor A settings
        update_doctor_settings(TEST_DOCTOR_ID, {"theme": "dark", "notify_system_updates": False})

        # Doctor B settings remain default
        doc_b_settings = get_doctor_settings(ANOTHER_DOCTOR_ID)
        self.assertEqual(doc_b_settings["theme"], "light")
        self.assertTrue(doc_b_settings["notify_system_updates"])


if __name__ == "__main__":
    unittest.main()
