import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Imports at top
import_target = """from services.doctor_settings_service import (
    get_doctor_settings,
    update_doctor_settings,
    check_connected_services_status,
    export_doctor_data,
    deactivate_doctor_account,
)"""

import_replacement = """from services.doctor_settings_service import (
    get_doctor_settings,
    update_doctor_settings,
    check_connected_services_status,
    export_doctor_data,
    deactivate_doctor_account,
)
from services.msg91_otp_service import MSG91OTPService, mask_phone_number, mask_email_address
from services.external_consultation_service import ExternalConsultationService"""

assert import_target in content, "import_target not found"
content = content.replace(import_target, import_replacement, 1)

# 2. Add check_workspace_access helper right before patient_health_card
helper_target = """@app.route("/patient/qr-health-id", endpoint="patient_health_card")"""

helper_code = """# =========================================================
# WORKSPACE & RECORD ACCESS VERIFICATION HELPER
# =========================================================
def check_workspace_access(patient_id):
    \"\"\"
    Validates if the caller is authorized to view this patient's records.
    Supports:
    1. Active External Consultation session (5-min OTP)
    2. Active Doctor OTP session (5-min OTP)
    3. Approved Doctor Access Request (active, non-expired)
    \"\"\"
    pid = str(patient_id).strip()

    # 1. Check External Consultation (Session-based, non-logged in visitor)
    ext_sess = session.get("external_consultation")
    if ext_sess and str(ext_sess.get("patient_id")) == pid:
        verified = ExternalConsultationService.get_session(ext_sess.get("session_id"))
        if verified and verified.get("status") == "active":
            now_ts = int(datetime.now(timezone.utc).timestamp())
            rem = max(0, verified.get("expires_at_timestamp", 0) - now_ts)
            return True, {
                "is_external": True,
                "read_only": True,
                "remaining_seconds": rem,
                "session": verified,
                "doctor_id": "EXTERNAL_CONSULTATION"
            }, ""
        else:
            session.pop("external_consultation", None)
            return False, {}, "External consultation session has expired or was revoked."

    # 2. Check Doctor Login
    doctor_id = session.get("doctor_id")
    if not doctor_id:
        return False, {}, "Please login as a doctor or authenticate via patient QR OTP."

    # 3. Check Active Doctor OTP Session
    doc_otp = session.get("active_otp_access")
    if doc_otp and str(doc_otp.get("patient_id")) == pid:
        verified = ExternalConsultationService.get_session(doc_otp.get("session_id"))
        if verified and verified.get("status") == "active":
            now_ts = int(datetime.now(timezone.utc).timestamp())
            rem = max(0, verified.get("expires_at_timestamp", 0) - now_ts)
            return True, {
                "is_external": False,
                "read_only": True,
                "remaining_seconds": rem,
                "session": verified,
                "doctor_id": str(doctor_id)
            }, ""

    # 4. Check standard access_requests in database
    try:
        access_res = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", pid)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )
        records = access_res.data or []
        if not records:
            return False, {}, "You do not have active access to this patient's medical records."

        acc = records[0]
        expires_at = acc.get("expires_at")
        if expires_at:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) >= exp_dt:
                try:
                    supabase_admin.table("access_requests").update({"status": "expired"}).eq("id", acc["id"]).execute()
                except Exception:
                    pass
                return False, {}, "This patient's temporary access has expired."

        return True, {
            "is_external": False,
            "read_only": False,
            "remaining_seconds": None,
            "access_record": acc,
            "doctor_id": str(doctor_id)
        }, ""
    except Exception as e:
        print("Database error checking access:", repr(e))
        return False, {}, "Failed to verify access permissions."


@app.route("/patient/qr-health-id", endpoint="patient_health_card")"""

assert helper_target in content, "helper_target not found"
content = content.replace(helper_target, helper_code, 1)

# 3. Update patient_health_card QR URL to canonical
qr_gen_target = """        # =================================================
        # GENERATE REAL QR CODE
        # =================================================
        #
        # IMPORTANT:
        # The QR does NOT contain medical records.
        #
        # It only contains a secure OmniCare identifier.
        #
        #

        qr_data = request.host_url.rstrip('/') + url_for("public_patient_info", patient_id=patient_id)"""

qr_gen_replacement = """        # =================================================
        # GENERATE REAL UNIVERSAL QR CODE
        # =================================================
        #
        # IMPORTANT:
        # The QR does NOT contain medical records or database UUIDs.
        # It uses a secure, non-guessable canonical public identifier.
        # Works via internal OmniCare AI doctor scanner and any external camera.
        #

        qr_token = ExternalConsultationService.get_or_create_qr_token(patient_id, health_id=health_id)
        canonical_domain = (os.getenv("CANONICAL_DOMAIN") or request.host_url.rstrip('/')).rstrip('/')
        qr_data = f"{canonical_domain}/qr/{qr_token}\""""

assert qr_gen_target in content, "qr_gen_target not found"
content = content.replace(qr_gen_target, qr_gen_replacement, 1)

# Pass qr_token to health card template
qr_render_target = """            # Real QR image
            qr_code=qr_code
        )"""
qr_render_replacement = """            # Real QR image
            qr_code=qr_code,
            qr_token=qr_token
        )"""

assert qr_render_target in content, "qr_render_target not found"
content = content.replace(qr_render_target, qr_render_replacement, 1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Part 1 of app.py patches applied successfully!")
