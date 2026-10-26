import sys
sys.path.insert(0, '.')
from app import app
from utils.supabase_client import supabase

client = app.test_client()

print("=" * 60)
print("RUNNING END-TO-END CLINICAL COPILOT BROWSER SIMULATION")
print("=" * 60)

# 1. Fetch real doctor credentials
from services.clinical_copilot_service import safe_db_call

doc_res = safe_db_call(lambda: supabase.table('doctors').select('*').limit(1))
assert doc_res and doc_res.data, "No doctor found in database"
doctor = doc_res.data[0]
doc_id = doctor["id"]
print(f"Doctor: {doctor['full_name']} (ID: {doc_id})")

# 2. Simulate login session
with client.session_transaction() as sess:
    sess["doctor_id"] = doc_id
    sess["doctor_name"] = doctor["full_name"]
    sess["doctor_email"] = doctor["email"]

# 3. GET /doctor/ai-assistant (HTML page)
res_page = client.get("/doctor/ai-assistant")
assert res_page.status_code == 200, f"Expected 200, got {res_page.status_code}"
html = res_page.data.decode("utf-8")
assert "loadCopilotBriefing" in html, "loadCopilotBriefing script missing in rendered page!"
assert 'id="priorityList"' in html, "priorityList element missing"
assert 'id="scopeCount"' in html, "scopeCount element missing"
assert 'id="abnormalCount"' in html, "abnormalCount element missing"
assert 'id="copilotTrendChart"' in html, "copilotTrendChart element missing"
assert 'id="copilotSafetyResults"' in html, "copilotSafetyResults element missing"
print("[PASS] Page renders cleanly with all required DOM elements and client-side scripts.")

# 4. GET /doctor/clinical-copilot/api/briefing
res_briefing = client.get("/doctor/clinical-copilot/api/briefing")
assert res_briefing.status_code == 200
briefing = res_briefing.get_json()
print("\n[BRIEFING DATA VERIFICATION]")
print("  Scope authorized patients:", briefing["scope"]["authorized_patient_count"])
print("  Expired consent count:", briefing["scope"]["expired_count"])
print("  Revoked consent count:", briefing["scope"]["revoked_count"])
print("  Abnormal reports count:", len(briefing["abnormal_reports"]))
print("  Overdue follow-ups count:", len(briefing["overdue_followups"]))
print("  Worsening trends count:", len(briefing["worsening_trends"]))
print("  Medication safety conflicts:", briefing["medication_safety"]["total_conflicts"])

assert briefing["scope"]["authorized_patient_count"] >= 1, "Expected authorized patients"
assert len(briefing["abnormal_reports"]) >= 1, "Expected real abnormal reports"
assert len(briefing["overdue_followups"]) >= 1, "Expected real overdue follow-ups"

# 5. POST /doctor/clinical-copilot/api/query
res_query = client.post(
    "/doctor/clinical-copilot/api/query",
    json={"question": "Show recent abnormal lab results"}
)
assert res_query.status_code == 200
q_data = res_query.get_json()
print("\n[QUERY DATA VERIFICATION]")
print("  Answer:", q_data.get("answer"))
print("  Results count:", len(q_data.get("results", [])))
print("  Sources count:", len(q_data.get("sources", [])))
assert len(q_data.get("results", [])) > 0, "Expected clinical results"
assert len(q_data.get("sources", [])) > 0, "Expected clinical sources"

# 6. POST /doctor/clinical-copilot/api/alert-review
sample_patient_id = briefing["abnormal_reports"][0]["patient_id"]
res_review = client.post(
    "/doctor/clinical-copilot/api/alert-review",
    json={
        "alert_id": "test-review-001",
        "alert_type": "abnormal_report",
        "patient_id": sample_patient_id,
        "notes": "Reviewed by clinician in test simulation."
    }
)
assert res_review.status_code == 200
rev_data = res_review.get_json()
assert rev_data.get("success") is True
print("\n[ALERT REVIEW VERIFICATION]")
print("  Alert review recorded successfully:", rev_data)

# 7. GET /doctor/access-audit
res_audit = client.get("/doctor/access-audit")
assert res_audit.status_code == 200
audit_html = res_audit.data.decode("utf-8")
assert "ALERT_REVIEWED" in audit_html, "Expected ALERT_REVIEWED in access-audit page"
assert "COPILOT_BRIEFING_VIEWED" in audit_html, "Expected COPILOT_BRIEFING_VIEWED in access-audit page"
print("[PASS] Access & Audit Log page displays live audit records.")

print("\n" + "=" * 60)
print("ALL END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY!")
print("=" * 60)
