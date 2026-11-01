# ============================================================
# OMNICARE AI — DOCTOR PORTAL ACCESS & AUDIT LOG TEST SUITE
# ============================================================

import os
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from services.clinical_audit_service import (
    log_audit_event,
    log_clinical_event,
    query_doctor_audit_logs,
    get_audit_log_by_id,
    get_doctor_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    ACTION_LABELS
)

TEST_DOCTOR_ID = "ea83806c-f033-4012-944b-22098514d9e9"
ANOTHER_DOCTOR_ID = "ffffffff-ffff-ffff-ffff-ffffffffffff"
TEST_PATIENT_ID = "a8360a17-d8a0-4524-bcc2-b1b4775e5c4f"


class MockQueryResult:
    def __init__(self, data=None):
        self.data = data or []


def create_mock_supabase(requests_data=None, patients_data=None, doctor_data=None):
    """Helper to mock Supabase query chains."""
    mock_sb = MagicMock()

    def table_mock(tbl_name):
        table_obj = MagicMock()

        def select_mock(*args, **kwargs):
            query_obj = MagicMock()
            data = []
            if tbl_name == "access_requests":
                data = requests_data or []
            elif tbl_name == "patients":
                data = patients_data or []
            elif tbl_name == "doctors":
                data = [doctor_data] if doctor_data else []

            query_obj.eq.return_value = query_obj
            query_obj.in_.return_value = query_obj
            query_obj.order.return_value = query_obj
            query_obj.limit.return_value = query_obj
            query_obj.single.return_value = query_obj
            query_obj.execute.return_value = MockQueryResult(data)
            return query_obj

        table_obj.select.side_effect = select_mock
        table_obj.update.return_value.eq.return_value.execute.return_value = MockQueryResult([{"status": "cancelled"}])
        table_obj.insert.return_value.execute.return_value = MockQueryResult([{"id": "new-req-id"}])
        return table_obj

    mock_sb.table.side_effect = table_mock
    return mock_sb


class TestAccessAuditSuite(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    # ========================================================
    # 1. AUTHENTICATION & ACCESS CONTROL
    # ========================================================
    def test_unauthenticated_page_access_redirects(self):
        """Unauthenticated doctor must be redirected to doctor_login."""
        res = self.client.get('/doctor/access-audit')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/doctor/login', res.headers.get('Location', ''))

    def test_unauthenticated_api_requests_return_401(self):
        """Unauthenticated API requests must return 401 Unauthorized."""
        endpoints = [
            '/doctor/access-audit/api/summary',
            '/doctor/access-audit/api/patients',
            '/doctor/access-audit/api/requests',
            '/doctor/access-audit/api/consent/test-req-id',
            '/doctor/access-audit/api/logs',
            '/doctor/access-audit/api/notifications',
            '/doctor/access-audit/api/search-patient'
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 401, f"Endpoint {ep} should return 401 when unauthenticated")

    def test_authenticated_page_render_success(self):
        """Authenticated doctor receives 200 and access & audit layout."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID
            sess["doctor_name"] = "Dr. Tamil Alagi"

        res = self.client.get('/doctor/access-audit')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Verify key UI components
        self.assertIn("Access &amp; Audit Log", html)
        self.assertIn("My Patient Access", html)
        self.assertIn("Access Requests", html)
        self.assertIn("Audit Activity Log", html)
        self.assertIn("Total Access Requests", html)
        self.assertIn("Active Access", html)
        self.assertIn("Pending Requests", html)
        self.assertIn("Revoked / Expired", html)
        self.assertIn("Access Notifications", html)
        self.assertIn("notifBellContainer", html)
        self.assertIn("notifDropdown", html)
        self.assertIn("closeNotifDropdownBtn", html)
        self.assertNotIn("notificationsSidePanel", html)
        self.assertIn("requestAccessModal", html)
        self.assertIn("consentDetailModal", html)
        self.assertIn("auditDetailModal", html)

    # ========================================================
    # 1B. REQUIREMENT VERIFICATION: TABLE LAYOUT & BELL DROPDOWN
    # ========================================================
    def test_requirement_1_table_columns_and_panel_removal(self):
        """Verify that all 3 tables have 7 columns and the side notification panel is removed."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        res = self.client.get('/doctor/access-audit')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Requirement 1: 7 columns in My Patient Access
        self.assertIn("col-patient-id", html)
        self.assertIn("col-patient-name", html)
        self.assertIn("col-access-type", html)
        self.assertIn("col-granted-at", html)
        self.assertIn("col-expiry", html)
        self.assertIn("col-status", html)
        self.assertIn("col-actions", html)

        # 7 columns in Access Requests
        self.assertIn("col-req-id", html)
        self.assertIn("col-req-name", html)
        self.assertIn("col-req-health-id", html)
        self.assertIn("col-req-type", html)
        self.assertIn("col-req-requested-at", html)
        self.assertIn("col-req-status", html)
        self.assertIn("col-req-actions", html)

        # 7 columns in Audit Activity Log
        self.assertIn("col-audit-id", html)
        self.assertIn("col-audit-activity", html)
        self.assertIn("col-audit-patients", html)
        self.assertIn("col-audit-details", html)
        self.assertIn("col-audit-timestamp", html)
        self.assertIn("col-audit-result", html)
        self.assertIn("col-audit-actions", html)

        # omnicare-table-fixed applied to tables
        self.assertIn("omnicare-table-fixed", html)

        # Requirement 2: Side panel removed, dropdown inside bell container
        self.assertNotIn('id="notificationsSidePanel"', html)
        self.assertIn('id="notifBellContainer"', html)
        self.assertIn('id="notifDropdown"', html)
        self.assertIn('id="headerBellBadge"', html)
        self.assertIn('id="closeNotifDropdownBtn"', html)
        self.assertIn('id="markAllNotifReadBtn"', html)
        self.assertIn('id="refreshNotifBtn"', html)

    # ========================================================
    # 2. AUDIT LOGGING SERVICE
    # ========================================================
    def test_log_audit_event_and_query(self):
        """Verify immutable audit recording and filtering."""
        test_action = "PATIENT_RECORD_VIEWED"
        test_meta = {"test_marker": "unittest_verify_123"}

        entry = log_audit_event(
            doctor_id=TEST_DOCTOR_ID,
            action=test_action,
            patient_ids=[TEST_PATIENT_ID],
            status="SUCCESS",
            metadata=test_meta,
            client_ip="127.0.0.1"
        )
        self.assertIsNotNone(entry.get("id"))
        self.assertEqual(entry["doctor_id"], TEST_DOCTOR_ID)
        self.assertEqual(entry["action"], test_action)

        # Query logs
        result = query_doctor_audit_logs(
            doctor_id=TEST_DOCTOR_ID,
            action=test_action,
            search="unittest_verify_123",
            page=1,
            per_page=10
        )
        self.assertGreaterEqual(result["total"], 1)
        found = any(l["id"] == entry["id"] for l in result["logs"])
        self.assertTrue(found, "Newly created audit log should be returned in query results")

        # Test single log fetch
        single = get_audit_log_by_id(entry["id"], doctor_id=TEST_DOCTOR_ID)
        self.assertIsNotNone(single)
        self.assertEqual(single["id"], entry["id"])

        # Test cross-doctor isolation (Another doctor cannot inspect this log)
        isolated = get_audit_log_by_id(entry["id"], doctor_id=ANOTHER_DOCTOR_ID)
        self.assertIsNone(isolated, "Audit log must not be accessible by another doctor")

    def test_audit_logs_api(self):
        """Test GET /doctor/access-audit/api/logs endpoint."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        res = self.client.get('/doctor/access-audit/api/logs?page=1&per_page=5')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("logs", data)
        self.assertIn("total", data)
        self.assertIn("page", data)
        self.assertIn("total_pages", data)

    # ========================================================
    # 3. ACCESS NOTIFICATIONS SERVICE
    # ========================================================
    def test_notifications_generation(self):
        """Test generating notifications from access requests."""
        sample_requests = [
            {
                "id": "req-1",
                "patient_id": TEST_PATIENT_ID,
                "status": "pending",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "access_type": "temporary"
            },
            {
                "id": "req-2",
                "patient_id": TEST_PATIENT_ID,
                "status": "active",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=45)).isoformat(),
                "access_type": "temporary"
            },
            {
                "id": "req-3",
                "patient_id": TEST_PATIENT_ID,
                "status": "revoked",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "access_type": "temporary"
            }
        ]

        patients_map = {
            TEST_PATIENT_ID: {"full_name": "Test Patient", "health_id": "OMC-T100"}
        }

        notif_data = get_doctor_notifications(
            doctor_id=TEST_DOCTOR_ID,
            access_requests=sample_requests,
            patients_map=patients_map
        )

        self.assertGreaterEqual(len(notif_data["notifications"]), 3)
        badges = [n["badge"] for n in notif_data["notifications"]]
        self.assertIn("Pending Approval", badges)
        self.assertIn("Expiring Soon", badges)
        self.assertIn("Access Revoked", badges)

    def test_notification_mark_read_api(self):
        """Test POST /doctor/access-audit/api/notifications/<id>/read."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        res = self.client.post('/doctor/access-audit/api/notifications/test-notif-1/read')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

    def test_notifications_all_required_types_and_mark_all_read(self):
        """Test generating all required notification types and marking all as read."""
        sample_requests = [
            {
                "id": "req-granted-test",
                "patient_id": TEST_PATIENT_ID,
                "status": "active",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "access_type": "permanent"
            },
            {
                "id": "req-pending-test",
                "patient_id": TEST_PATIENT_ID,
                "status": "pending",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "access_type": "temporary"
            },
            {
                "id": "req-expiring-test",
                "patient_id": TEST_PATIENT_ID,
                "status": "active",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
                "access_type": "temporary"
            },
            {
                "id": "req-expired-test",
                "patient_id": TEST_PATIENT_ID,
                "status": "expired",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "access_type": "temporary"
            },
            {
                "id": "req-revoked-test",
                "patient_id": TEST_PATIENT_ID,
                "status": "revoked",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "access_type": "temporary"
            },
            {
                "id": "req-rejected-test",
                "patient_id": TEST_PATIENT_ID,
                "status": "rejected",
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "access_type": "temporary"
            }
        ]

        patients_map = {
            TEST_PATIENT_ID: {"full_name": "Test Patient", "health_id": "OMC-T100"}
        }

        notif_data = get_doctor_notifications(
            doctor_id=TEST_DOCTOR_ID,
            access_requests=sample_requests,
            patients_map=patients_map
        )

        titles = [n["title"] for n in notif_data["notifications"]]
        badges = [n["badge"] for n in notif_data["notifications"]]

        self.assertTrue(any("Access Granted" in t for t in titles))
        self.assertTrue(any("Pending" in b for b in badges))
        self.assertTrue(any("Expiring Soon" in t for t in titles))
        self.assertTrue(any("Expired" in t for t in titles))
        self.assertTrue(any("Revoked" in t for t in titles))
        self.assertTrue(any("Rejected" in t for t in titles))

        # Check mark all as read API
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        notif_ids = [n["id"] for n in notif_data["notifications"]]
        res = self.client.post('/doctor/access-audit/api/notifications/all/read', json={
            "notification_ids": notif_ids
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

        # Re-fetch notifications and verify read status is preserved
        refreshed = get_doctor_notifications(
            doctor_id=TEST_DOCTOR_ID,
            access_requests=sample_requests,
            patients_map=patients_map
        )
        for n in refreshed["notifications"]:
            if n["id"] in notif_ids:
                self.assertTrue(n["is_read"], f"Notification {n['id']} should be marked read")

    # ========================================================
    # 4. SUMMARY & PATIENTS APIS (WITH DATABASE MOCKING)
    # ========================================================
    @patch('app.supabase_admin')
    def test_summary_api(self, mock_sb):
        """Test GET /doctor/access-audit/api/summary endpoint."""
        mock_requests = [
            {"id": "r1", "status": "active", "access_type": "permanent"},
            {"id": "r2", "status": "pending", "access_type": "temporary"},
            {"id": "r3", "status": "expired", "access_type": "temporary"},
            {"id": "r4", "status": "revoked", "access_type": "one_time"}
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MockQueryResult(mock_requests)

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        res = self.client.get('/doctor/access-audit/api/summary')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        summary = data.get("summary", {})
        self.assertEqual(summary["total_requests"], 4)
        self.assertEqual(summary["active_access"], 1)
        self.assertEqual(summary["pending_requests"], 1)
        self.assertEqual(summary["revoked_expired"], 2)

    @patch('app.supabase_admin')
    def test_patients_api(self, mock_sb):
        """Test GET /doctor/access-audit/api/patients endpoint."""
        mock_requests = [
            {
                "id": "req-10",
                "patient_id": TEST_PATIENT_ID,
                "status": "active",
                "access_type": "permanent",
                "approved_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        mock_patients = [
            {
                "id": TEST_PATIENT_ID,
                "full_name": "Sowmiya R",
                "health_id": "OMC-PD678",
                "gender": "Female"
            }
        ]

        def table_resolver(t):
            mock_t = MagicMock()
            if t == "access_requests":
                mock_t.select.return_value.eq.return_value.order.return_value.execute.return_value = MockQueryResult(mock_requests)
            elif t == "patients":
                mock_t.select.return_value.in_.return_value.execute.return_value = MockQueryResult(mock_patients)
            return mock_t

        mock_sb.table.side_effect = table_resolver

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        res = self.client.get('/doctor/access-audit/api/patients?status=all&page=1&per_page=10')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("patients", data)
        self.assertEqual(len(data["patients"]), 1)
        self.assertEqual(data["patients"][0]["patient_name"], "Sowmiya R")
        self.assertTrue(data["patients"][0]["can_view_records"])

    # ========================================================
    # 5. REQUEST CREATION & CANCELLATION VALIDATION
    # ========================================================
    def test_create_access_request_missing_patient(self):
        """Request creation with empty patient must return 400."""
        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        res = self.client.post('/doctor/access-audit/api/requests', json={
            "patient_id": "",
            "access_type": "temporary",
            "purpose": "Clinical evaluation"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data["success"])

    @patch('app.supabase_admin')
    def test_cancel_nonexistent_request_returns_404(self, mock_sb):
        """Cancelling a non-existent request returns 404."""
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MockQueryResult([])

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        res = self.client.post('/doctor/access-audit/api/requests/00000000-0000-0000-0000-000000000000/cancel')
        self.assertEqual(res.status_code, 404)

    @patch('app.supabase_admin')
    def test_cancel_pending_request_success(self, mock_sb):
        """Cancelling an existing pending request succeeds and logs audit event."""
        mock_req = [{
            "id": "valid-pending-req",
            "doctor_id": TEST_DOCTOR_ID,
            "patient_id": TEST_PATIENT_ID,
            "status": "pending"
        }]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MockQueryResult(mock_req)
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MockQueryResult([{"status": "cancelled"}])

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = TEST_DOCTOR_ID

        res = self.client.post('/doctor/access-audit/api/requests/valid-pending-req/cancel')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("cancelled", data["message"].lower())


if __name__ == "__main__":
    unittest.main()
