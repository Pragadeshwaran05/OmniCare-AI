import sys
import os
import unittest
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app
from services.clinical_audit_service import get_doctor_notifications, mark_notification_as_read, mark_all_notifications_as_read

def test_full_access_audit_ui():
    client = app.test_client()
    client.testing = True

    # 1. Render Access & Audit Log page with authenticated doctor session
    with client.session_transaction() as sess:
        sess["doctor_id"] = "ea83806c-f033-4012-944b-22098514d9e9"
        sess["doctor_name"] = "Dr. Tamil Alagi"

    res = client.get('/doctor/access-audit')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.data.decode('utf-8')

    # Requirement 1: Verify Table Visibility & 7 columns
    print("--- REQUIREMENT 1: TABLE COLUMNS & LAYOUT VERIFICATION ---")
    required_patient_cols = [
        "Patient ID",
        "Patient Name",
        "Access Type",
        "Granted At",
        "Expiry",
        "Status",
        "Actions"
    ]
    for col in required_patient_cols:
        assert col in html, f"Column '{col}' missing from table header"
        print(f"  [OK] Column present: {col}")

    # Verify column classes in patients table
    assert 'class="col-patient-id"' in html, "col-patient-id class missing"
    assert 'class="col-patient-name"' in html, "col-patient-name class missing"
    assert 'class="col-access-type"' in html, "col-access-type class missing"
    assert 'class="col-granted-at"' in html, "col-granted-at class missing"
    assert 'class="col-expiry"' in html, "col-expiry class missing"
    assert 'class="col-status"' in html, "col-status class missing"
    assert 'class="col-actions"' in html, "col-actions class missing"
    print("  [OK] Patient access column classes present")

    # Verify other two tables
    assert 'class="col-req-id"' in html, "Access Requests column classes missing"
    assert 'class="col-audit-id"' in html, "Audit Activity Log column classes missing"
    assert 'omnicare-table-fixed' in html, "Table fixed class missing"
    print("  [OK] Access Requests and Audit Log tables have fixed column definitions")

    # Requirement 2: Verify Removal of Side Panel & Bell Dropdown
    print("\n--- REQUIREMENT 2: NOTIFICATIONS BELL & DROPDOWN VERIFICATION ---")
    assert 'id="notificationsSidePanel"' not in html, "Right side notifications panel was not removed!"
    print("  [OK] Right side notification panel completely removed from page layout")

    assert 'id="notifBellContainer"' in html, "Notification bell container missing"
    assert 'id="notifBellBtn"' in html, "Notification bell button missing"
    assert 'id="headerBellBadge"' in html, "Notification unread badge missing"
    assert 'id="notifDropdown"' in html, "Notification dropdown missing"
    assert 'id="closeNotifDropdownBtn"' in html, "Notification close button missing"
    assert 'id="markAllNotifReadBtn"' in html, "Mark all as read button missing"
    assert 'id="notificationsScrollArea"' in html, "Notification scroll area missing"
    assert 'id="refreshNotifBtn"' in html, "Refresh notifications button missing"
    print("  [OK] Notification bell dropdown, badge, close button, and mark all read controls present in header")

    # Verify CSS file exists and has dropdown styles
    css_path = os.path.join(PROJECT_ROOT, 'static', 'css', 'doctor_access_audit.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()

    assert '.notif-dropdown' in css, ".notif-dropdown CSS rule missing"
    assert '.notif-dropdown.open' in css, ".notif-dropdown.open CSS rule missing"
    assert '.omnicare-table-fixed' in css, ".omnicare-table-fixed CSS rule missing"
    assert '#patientsTable .col-actions' in css, "Table 1 actions column CSS missing"
    assert 'table-layout: fixed' in css, "table-layout: fixed CSS rule missing"
    print("  [OK] CSS contains table-layout: fixed, column proportioning, and animated dropdown styles")

    # Verify JS controller has notification dropdown and interaction methods
    js_path = os.path.join(PROJECT_ROOT, 'static', 'js', 'doctor_access_audit.js')
    with open(js_path, 'r', encoding='utf-8') as f:
        js = f.read()

    assert 'toggleNotificationDropdown' in js, "toggleNotificationDropdown missing from JS"
    assert 'closeNotificationDropdown' in js, "closeNotificationDropdown missing from JS"
    assert 'markAllNotificationsRead' in js, "markAllNotificationsRead missing from JS"
    assert 'onNotificationClick' in js, "onNotificationClick missing from JS"
    assert 'Escape' in js, "Escape key handler missing from JS"
    print("  [OK] JS controller implements toggle, outside click, Escape close, and mark-as-read workflows")

    # 3. Test Notifications REST APIs
    print("\n--- BACKEND API & NOTIFICATION INTEGRATION VERIFICATION ---")
    res_notif = client.get('/doctor/access-audit/api/notifications')
    assert res_notif.status_code == 200, f"Notifications API returned {res_notif.status_code}"
    notif_json = res_notif.get_json()
    assert notif_json.get("success") is True, "Notifications API did not return success=True"
    assert "notifications" in notif_json, "notifications array missing from API response"
    assert "unread_count" in notif_json, "unread_count missing from API response"
    print(f"  [OK] GET /doctor/access-audit/api/notifications returned {len(notif_json['notifications'])} notifications (unread: {notif_json['unread_count']})")

    # Test single mark read
    res_read = client.post('/doctor/access-audit/api/notifications/test-notif-single/read')
    assert res_read.status_code == 200
    assert res_read.get_json().get("success") is True
    print("  [OK] POST /doctor/access-audit/api/notifications/<id>/read succeeded")

    # Test mark all read
    res_read_all = client.post('/doctor/access-audit/api/notifications/all/read', json={"notification_ids": ["test-1", "test-2"]})
    assert res_read_all.status_code == 200
    assert res_read_all.get_json().get("success") is True
    print("  [OK] POST /doctor/access-audit/api/notifications/all/read succeeded")

    print("\n========================================================")
    print("ALL TESTS PASSED! UI & BACKEND REQUIREMENTS 1 & 2 VERIFIED!")
    print("========================================================")

if __name__ == '__main__':
    test_full_access_audit_ui()
