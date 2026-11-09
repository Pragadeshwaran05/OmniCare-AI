import os

# Restore fresh backup first
import shutil
shutil.copyfile('scratch/app.py.bak', 'app.py')

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ----------------------------------------------------------------------
# 1. IMPORTS
# ----------------------------------------------------------------------
imp_target = "from services.doctor_settings_service import ("
imp_repl = """from services.msg91_otp_service import MSG91OTPService, mask_phone_number, mask_email_address
from services.external_consultation_service import ExternalConsultationService
from services.doctor_settings_service import ("""

assert imp_target in content, "imp_target not found"
content = content.replace(imp_target, imp_repl, 1)

# ----------------------------------------------------------------------
# 2. HELPER FUNCTION: check_workspace_access
# ----------------------------------------------------------------------
helper_target = "@app.route(\"/patient/qr-health-id\", endpoint=\"patient_health_card\")"
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

# ----------------------------------------------------------------------
# 3. CANONICAL QR IN PATIENT HEALTH CARD
# ----------------------------------------------------------------------
qr_target = "qr_data = request.host_url.rstrip('/') + url_for(\"public_patient_info\", patient_id=patient_id)"
qr_replacement = """# Universal Canonical QR Token (Non-guessable, does not leak database UUID)
        qr_token = ExternalConsultationService.get_or_create_qr_token(patient_id, health_id=health_id)
        canonical_domain = (os.getenv("CANONICAL_DOMAIN") or request.host_url.rstrip('/')).rstrip('/')
        qr_data = f"{canonical_domain}/qr/{qr_token}\""""

assert qr_target in content, "qr_target not found"
content = content.replace(qr_target, qr_replacement, 1)

# Pass qr_token in patient_health_card render
render_target = "qr_code=qr_code\n        )"
render_replacement = "qr_code=qr_code,\n            qr_token=qr_token\n        )"
assert render_target in content, "render_target not found"
content = content.replace(render_target, render_replacement, 1)

# ----------------------------------------------------------------------
# 4. CANONICAL PUBLIC QR ROUTES & EXTERNAL CONSULTATION APIs
# ----------------------------------------------------------------------
public_info_block_target = """# =========================================================
# PUBLIC PATIENT INFO (QR SCAN PAGE)
# =========================================================
@app.route("/patient-info/<patient_id>", endpoint="public_patient_info")
def public_patient_info(patient_id):

    try:
        response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )

        patient = response.data

    except Exception as e:
        print("Public Patient Info Fetch Error:", e)
        patient = None

    if not patient:
        return render_template("patient/patient_not_found.html"), 404

    # Determine Health ID
    health_id = patient.get("health_id")
    if not health_id:
        health_id = f"OMC-P{str(patient_id)[-4:].upper()}"

    # Calculate age if DOB exists and age is missing
    age = patient.get("age")
    if not age and patient.get("date_of_birth"):
        try:
            from datetime import datetime, date
            dob_str = str(patient.get("date_of_birth"))
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            today = date.today()
            calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            age = f"{calculated_age} Years"
        except Exception:
            age = None
    elif age and str(age).isdigit():
        age = f"{age} Years"

    # Format Date of Birth if available
    formatted_dob = patient.get("date_of_birth")
    if formatted_dob:
        try:
            from datetime import datetime
            dt = datetime.strptime(str(formatted_dob), "%Y-%m-%d")
            formatted_dob = dt.strftime("%d/%m/%Y")
        except Exception:
            pass

    return render_template(
        "patient/public_patient_info.html",
        patient=patient,
        health_id=health_id,
        calculated_age=age,
        formatted_dob=formatted_dob
    )"""

public_info_block_replacement = """# =========================================================
# CANONICAL UNIVERSAL PATIENT QR LANDING PAGE
# =========================================================
@app.route("/qr/<qr_identifier>", endpoint="public_patient_qr_landing")
def public_patient_qr_landing(qr_identifier):
    patient = None
    health_id = None
    patient_id = None

    # 1. Resolve via ExternalConsultationService (token or health_id mapping)
    token_record = ExternalConsultationService.resolve_qr_token(qr_identifier)
    if token_record:
        patient_id = token_record.get("patient_id")

    if not patient_id:
        # Check direct lookup by health_id or id
        try:
            res = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("health_id", qr_identifier)
                .maybe_single()
                .execute()
            )
            if res.data:
                patient = res.data
                patient_id = patient.get("id")
        except Exception:
            pass

    if not patient and patient_id:
        try:
            res = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("id", patient_id)
                .single()
                .execute()
            )
            patient = res.data
        except Exception as e:
            print("QR Landing Patient Fetch Error:", repr(e))

    if not patient:
        # Final fallback: direct check if qr_identifier matches a database id
        try:
            res = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("id", qr_identifier)
                .maybe_single()
                .execute()
            )
            patient = res.data
        except Exception:
            pass

    if not patient:
        return render_template("patient/patient_not_found.html"), 404

    health_id = patient.get("health_id") or (f"OMC-P{str(patient['id'])[-4:].upper()}" if patient.get("id") else "OMC-PATIENT")

    # Calculate age safely
    age = patient.get("age")
    if not age and patient.get("date_of_birth"):
        try:
            from datetime import datetime, date
            dob_str = str(patient.get("date_of_birth"))
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            today = date.today()
            calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            age = f"{calculated_age} Years"
        except Exception:
            age = None
    elif age and str(age).isdigit():
        age = f"{age} Years"

    # Log external QR scan
    try:
        log_clinical_event(
            doctor_id="PUBLIC_VISITOR",
            action="INTERNAL_QR_SCAN" if "doctor_id" in session else "EXTERNAL_CONSULTATION_REQUESTED",
            patient_ids=[str(patient["id"])],
            status="SUCCESS",
            metadata={"qr_identifier": qr_identifier, "is_doctor_logged_in": "doctor_id" in session},
            client_ip=request.remote_addr
        )
    except Exception:
        pass

    return render_template(
        "patient/public_patient_info.html",
        patient=patient,
        health_id=health_id,
        qr_identifier=qr_identifier,
        calculated_age=age
    )


# Backward-compatible redirect for legacy URLs
@app.route("/patient-info/<patient_id>", endpoint="public_patient_info")
def public_patient_info(patient_id):
    qr_token = ExternalConsultationService.get_or_create_qr_token(patient_id)
    return public_patient_qr_landing(qr_identifier=qr_token)


# =========================================================
# EXTERNAL CONSULTATION — REQUEST PATIENT OTP
# =========================================================
@app.route("/qr/<qr_identifier>/request-consultation", methods=["POST"])
def external_consultation_request_otp(qr_identifier):
    try:
        data = request.get_json(silent=True) or request.form.to_dict()

        visitor_name = str(data.get("visitor_name") or "").strip()
        visitor_mobile = str(data.get("visitor_mobile") or "").strip()
        visitor_age = str(data.get("visitor_age") or "").strip()
        visitor_role = str(data.get("visitor_role") or "Doctor").strip()

        if not visitor_name:
            return jsonify({"success": False, "error": "Please enter your full name."}), 400

        digits_mobile = [c for c in visitor_mobile if c.isdigit()]
        if len(digits_mobile) < 10:
            return jsonify({"success": False, "error": "Please enter a valid 10-digit mobile number."}), 400

        if not visitor_age.isdigit() or int(visitor_age) < 18:
            return jsonify({"success": False, "error": "Please enter a valid adult age."}), 400

        # Resolve patient
        token_record = ExternalConsultationService.resolve_qr_token(qr_identifier)
        patient_id = token_record.get("patient_id") if token_record else None

        if not patient_id:
            try:
                res = supabase_admin.table("patients").select("id, phone, email, full_name").or_(f"health_id.eq.{qr_identifier},id.eq.{qr_identifier}").maybe_single().execute()
                if res.data:
                    patient = res.data
                    patient_id = patient.get("id")
                else:
                    return jsonify({"success": False, "error": "Patient not found for this QR identifier."}), 404
            except Exception:
                return jsonify({"success": False, "error": "Patient not found."}), 404
        else:
            try:
                res = supabase_admin.table("patients").select("id, phone, email, full_name").eq("id", patient_id).single().execute()
                patient = res.data or {}
            except Exception:
                patient = {"id": patient_id}

        # Request OTP strictly for the PATIENT (never the visitor)
        success, msg, challenge_meta = MSG91OTPService.request_otp(
            patient_id=str(patient_id),
            patient_phone=patient.get("phone"),
            patient_email=patient.get("email"),
            visitor_name=visitor_name,
            consultation_type="External Clinical Consultation"
        )

        if not success:
            return jsonify({"success": False, "error": msg}), 400

        # Cache visitor intake metadata in session for the verification step
        session[f"visitor_meta_{challenge_meta['challenge_id']}"] = {
            "full_name": visitor_name,
            "mobile": visitor_mobile,
            "age": visitor_age,
            "role": visitor_role,
            "hospital_name": data.get("hospital_name", ""),
            "location": data.get("location", ""),
            "email": data.get("visitor_email", ""),
            "qualification": data.get("qualification", ""),
            "medical_registration_number": data.get("medical_registration_number", "")
        }

        try:
            log_clinical_event(
                doctor_id=f"EXT_{digits_mobile[-4:]}",
                action="EXTERNAL_CONSULTATION_OTP_SENT",
                patient_ids=[str(patient_id)],
                status="SUCCESS",
                metadata={"visitor_name": visitor_name, "visitor_role": visitor_role, "masked_dest": challenge_meta["masked_destination"]},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": msg,
            "challenge_id": challenge_meta["challenge_id"],
            "masked_destination": challenge_meta["masked_destination"],
            "expires_in_seconds": challenge_meta["expires_in_seconds"]
        }), 200

    except Exception as e:
        print("External Consultation Request Error:", repr(e))
        return jsonify({"success": False, "error": "An unexpected error occurred while requesting consultation."}), 500


# =========================================================
# EXTERNAL CONSULTATION — VERIFY OTP & CREATE 5-MIN SESSION
# =========================================================
@app.route("/qr/<qr_identifier>/verify-otp", methods=["POST"])
def external_consultation_verify_otp(qr_identifier):
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        challenge_id = str(data.get("challenge_id") or "").strip()
        otp_code = str(data.get("otp_code") or "").strip()

        if not challenge_id or not otp_code:
            return jsonify({"success": False, "error": "Missing challenge ID or OTP code."}), 400

        # Resolve patient
        token_record = ExternalConsultationService.resolve_qr_token(qr_identifier)
        patient_id = token_record.get("patient_id") if token_record else None

        if not patient_id:
            try:
                res = supabase_admin.table("patients").select("id").or_(f"health_id.eq.{qr_identifier},id.eq.{qr_identifier}").maybe_single().execute()
                if res.data:
                    patient_id = res.data.get("id")
            except Exception:
                pass

        if not patient_id:
            return jsonify({"success": False, "error": "Patient identification failed."}), 404

        # Verify OTP
        verified, msg, verified_meta = MSG91OTPService.verify_otp(
            challenge_id=challenge_id,
            patient_id=str(patient_id),
            entered_otp=otp_code
        )

        if not verified:
            return jsonify({"success": False, "error": msg}), 400

        # Retrieve visitor details
        visitor_details = session.pop(f"visitor_meta_{challenge_id}", {}) or {
            "full_name": verified_meta.get("visitor_name") or "External Doctor",
            "role": "Doctor"
        }

        # Create 5-minute active session
        session_record = ExternalConsultationService.create_session(
            patient_id=str(patient_id),
            visitor_details=visitor_details,
            is_internal_doctor=False
        )

        # Store in visitor Flask session
        session["external_consultation"] = session_record

        try:
            log_clinical_event(
                doctor_id="EXTERNAL_CONSULTATION",
                action="EXTERNAL_CONSULTATION_SESSION_STARTED",
                patient_ids=[str(patient_id)],
                status="SUCCESS",
                metadata={"session_id": session_record["session_id"], "visitor_name": session_record["visitor_name"]},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "Patient authorization verified successfully.",
            "redirect_url": url_for("doctor_patient_workspace", patient_id=str(patient_id))
        }), 200

    except Exception as e:
        print("External Consultation Verify Error:", repr(e))
        return jsonify({"success": False, "error": "Verification failed due to an internal error."}), 500


# =========================================================
# PATIENT PORTAL — REVOKE CONSULTATION SESSION EARLY
# =========================================================
@app.route("/patient/revoke-consultation/<session_id>", methods=["POST"])
def patient_revoke_consultation(session_id):
    if "patient_id" not in session:
        flash("Please login to manage your consultations.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    success, msg = ExternalConsultationService.revoke_session(session_id, patient_id)

    if success:
        try:
            log_clinical_event(
                doctor_id="PATIENT",
                action="EXTERNAL_CONSULTATION_SESSION_REVOKED",
                patient_ids=[str(patient_id)],
                status="SUCCESS",
                metadata={"session_id": session_id},
                client_ip=request.remote_addr
            )
        except Exception:
            pass
        flash("Consultation access has been revoked immediately.", "success")
    else:
        flash(msg, "error")

    return redirect(url_for("patient_doctor_access"))"""

assert public_info_block_target in content, "public_info_block_target not found"
content = content.replace(public_info_block_target, public_info_block_replacement, 1)

# ----------------------------------------------------------------------
# 5. UPDATE DOCTOR PATIENT ACCESS & ADD DOCTOR OTP ROUTES
# ----------------------------------------------------------------------
patient_access_target = """@app.route("/doctor/patient-access", methods=["GET"])
def doctor_patient_access():

    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    health_id = request.args.get("health_id", "").strip()

    patient = None
    error = None

    if health_id:

        try:
            response = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("health_id", health_id)
                .maybe_single()
                .execute()
            )

            patient = response.data

            if not patient:
                error = "No patient found with this Health ID."

        except Exception as e:
            print("PATIENT ACCESS SEARCH ERROR:", repr(e))
            error = "Patient search failed. Please try again."

    return render_template(
        "doctor/patient_access.html",
        patient=patient,
        error=error,
        health_id=health_id
    )"""

patient_access_replacement = """@app.route("/doctor/patient-access", methods=["GET"])
def doctor_patient_access():

    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    identifier = request.args.get("identifier") or request.args.get("health_id", "").strip()

    patient = None
    error = None
    masked_phone = None

    if identifier:
        try:
            # 1. Try resolving via ExternalConsultationService (token / health_id)
            token_rec = ExternalConsultationService.resolve_qr_token(identifier)
            if token_rec and token_rec.get("patient_id"):
                res = supabase_admin.table("patients").select("*").eq("id", token_rec["patient_id"]).maybe_single().execute()
                patient = res.data

            # 2. Try health_id match
            if not patient:
                res = supabase_admin.table("patients").select("*").eq("health_id", identifier).maybe_single().execute()
                patient = res.data

            # 3. Try database ID match
            if not patient:
                res = supabase_admin.table("patients").select("*").eq("id", identifier).maybe_single().execute()
                patient = res.data

            if not patient:
                error = "No patient found with this Health ID or QR code."
            else:
                masked_phone = mask_phone_number(patient.get("phone"))

        except Exception as e:
            print("PATIENT ACCESS SEARCH ERROR:", repr(e))
            error = "Patient search failed. Please try again."

    return render_template(
        "doctor/patient_access.html",
        patient=patient,
        error=error,
        health_id=patient.get("health_id") if patient else identifier,
        identifier=identifier,
        masked_phone=masked_phone
    )


# =========================================================
# DOCTOR INTERNAL OTP ACCESS — SEND OTP
# =========================================================
@app.route("/doctor/patient-access/<patient_id>/send-otp", methods=["POST"])
def doctor_patient_send_otp(patient_id):
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Please login as a doctor."}), 401

    doctor_id = session["doctor_id"]

    try:
        # Get doctor name
        doc_res = supabase_admin.table("doctors").select("full_name, name").eq("id", doctor_id).maybe_single().execute()
        doctor_name = "Attending Doctor"
        if doc_res.data:
            doctor_name = doc_res.data.get("full_name") or doc_res.data.get("name") or "Attending Doctor"

        # Get patient
        pat_res = supabase_admin.table("patients").select("id, phone, email, full_name").eq("id", patient_id).single().execute()
        patient = pat_res.data
        if not patient:
            return jsonify({"success": False, "error": "Patient not found."}), 404

        success, msg, challenge_meta = MSG91OTPService.request_otp(
            patient_id=str(patient_id),
            patient_phone=patient.get("phone"),
            patient_email=patient.get("email"),
            visitor_name=doctor_name,
            consultation_type="Doctor Instant OTP Consultation"
        )

        if not success:
            return jsonify({"success": False, "error": msg}), 400

        return jsonify({
            "success": True,
            "message": msg,
            "challenge_id": challenge_meta["challenge_id"],
            "masked_destination": challenge_meta["masked_destination"],
            "expires_in_seconds": challenge_meta["expires_in_seconds"]
        }), 200

    except Exception as e:
        print("Doctor Send OTP Error:", repr(e))
        return jsonify({"success": False, "error": "Failed to send OTP to patient."}), 500


# =========================================================
# DOCTOR INTERNAL OTP ACCESS — VERIFY OTP
# =========================================================
@app.route("/doctor/patient-access/<patient_id>/verify-otp", methods=["POST"])
def doctor_patient_verify_otp(patient_id):
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Please login as a doctor."}), 401

    doctor_id = session["doctor_id"]

    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        challenge_id = str(data.get("challenge_id") or "").strip()
        otp_code = str(data.get("otp_code") or "").strip()

        verified, msg, verified_meta = MSG91OTPService.verify_otp(
            challenge_id=challenge_id,
            patient_id=str(patient_id),
            entered_otp=otp_code
        )

        if not verified:
            return jsonify({"success": False, "error": msg}), 400

        # Create active 5-minute session in ExternalConsultationService
        session_rec = ExternalConsultationService.create_session(
            patient_id=str(patient_id),
            visitor_details={"full_name": "Attending Doctor", "role": "Doctor"},
            is_internal_doctor=True,
            doctor_id=str(doctor_id)
        )

        # Set session flag
        session["active_otp_access"] = session_rec

        # Also create active record in access_requests table for full audit/portal visibility
        now_dt = datetime.now(timezone.utc)
        exp_dt = now_dt + timedelta(minutes=5)
        try:
            supabase_admin.table("access_requests").insert({
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "status": "active",
                "access_type": "temporary",
                "access_method": "otp",
                "requested_at": now_dt.isoformat(),
                "approved_at": now_dt.isoformat(),
                "expires_at": exp_dt.isoformat()
            }).execute()
        except Exception as ins_err:
            print("Notice: Could not insert OTP access_request row in Supabase:", repr(ins_err))

        try:
            log_clinical_event(
                doctor_id=str(doctor_id),
                action="INTERNAL_OTP_ACCESS_GRANTED",
                patient_ids=[str(patient_id)],
                status="SUCCESS",
                metadata={"session_id": session_rec["session_id"], "duration_minutes": 5},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "OTP verified successfully.",
            "redirect_url": url_for("doctor_patient_workspace", patient_id=str(patient_id))
        }), 200

    except Exception as e:
        print("Doctor Verify OTP Error:", repr(e))
        return jsonify({"success": False, "error": "Verification failed."}), 500"""

assert patient_access_target in content, "patient_access_target not found"
content = content.replace(patient_access_target, patient_access_replacement, 1)

# ----------------------------------------------------------------------
# 6. UPDATE DOCTOR PATIENT WORKSPACE ACCESS CHECK
# ----------------------------------------------------------------------
workspace_access_check_target = """@app.route("/doctor/patient-workspace/<patient_id>")
def doctor_patient_workspace(patient_id):

    # -----------------------------------------------------
    # CHECK DOCTOR LOGIN
    # -----------------------------------------------------

    if "doctor_id" not in session:
        flash(
            "Please login as a doctor.",
            "error"
        )

        return redirect(
            url_for("doctor_login")
        )

    doctor_id = session["doctor_id"]

    try:

        # -------------------------------------------------
        # 1. CHECK ACTIVE ACCESS
        # -------------------------------------------------

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )

        access_requests = access_response.data or []

        if not access_requests:

            try:
                log_audit_event(
                    doctor_id=doctor_id,
                    action="UNAUTHORIZED_ACCESS_ATTEMPT",
                    patient_ids=[patient_id],
                    status="DENIED",
                    metadata={"target": "patient_workspace", "reason": "No active consent"},
                    client_ip=request.remote_addr
                )
            except Exception:
                pass

            flash(
                "You do not have active access to this patient's medical records.",
                "error"
            )

            return redirect(
                url_for("doctor_my_patients")
            )

        access = access_requests[0]

        # -------------------------------------------------
        # 2. CHECK EXPIRATION
        # -------------------------------------------------

        expires_at = access.get("expires_at")

        if expires_at:

            expiry_time = datetime.fromisoformat(
                expires_at.replace("Z", "+00:00")
            )

            current_time = datetime.now(timezone.utc)

            if current_time >= expiry_time:

                # Mark access as expired
                (
                    supabase_admin
                    .table("access_requests")
                    .update({
                        "status": "expired"
                    })
                    .eq("id", access["id"])
                    .execute()
                )

                flash(
                    "This patient's temporary access has expired.",
                    "error"
                )

                return redirect(
                    url_for("doctor_my_patients")
                )"""

workspace_access_check_replacement = """@app.route("/doctor/patient-workspace/<patient_id>")
def doctor_patient_workspace(patient_id):

    # Unified Access Verification (supports External Consultation, Doctor OTP, & Portal Consent)
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        flash(err_msg or "You do not have active access to this patient's medical records.", "error")
        if "external_consultation" in session:
            return redirect(url_for("public_patient_info", patient_id=patient_id))
        return redirect(url_for("doctor_my_patients"))

    is_external_consultation = access_info.get("is_external", False)
    read_only = access_info.get("read_only", False)
    remaining_seconds = access_info.get("remaining_seconds") or 300
    doctor_id = access_info.get("doctor_id", "EXTERNAL_CONSULTATION")
    access = access_info.get("access_record") or {
        "access_type": "temporary",
        "access_method": "otp" if is_external_consultation or read_only else "approval",
        "status": "active"
    }

    try:"""

assert workspace_access_check_target in content, "workspace_access_check_target not found"
content = content.replace(workspace_access_check_target, workspace_access_check_replacement, 1)

# Pass is_external_consultation and read_only in workspace render_template
workspace_render_target = """            access=access,

            trend_data=trend_data
        )"""

workspace_render_replacement = """            access=access,

            trend_data=trend_data,

            is_external_consultation=is_external_consultation,
            read_only=read_only,
            remaining_seconds=remaining_seconds
        )"""

assert workspace_render_target in content, "workspace_render_target not found"
content = content.replace(workspace_render_target, workspace_render_replacement, 1)

# ----------------------------------------------------------------------
# 7. UPDATE PATIENT PORTAL ACCESS REQUESTS TO INCLUDE ACTIVE CONSULTATIONS
# ----------------------------------------------------------------------
patient_req_render_target = """        return render_template(
            "patient/access_requests.html",
            access_requests=access_requests
        )"""

patient_req_render_replacement = """        active_consultations = ExternalConsultationService.get_active_sessions_for_patient(patient_id)
        return render_template(
            "patient/access_requests.html",
            access_requests=access_requests,
            active_consultations=active_consultations
        )"""

assert patient_req_render_target in content, "patient_req_render_target not found"
content = content.replace(patient_req_render_target, patient_req_render_replacement, 1)

# In patient_doctor_access render
doc_access_render_target = """        return render_template(
            "patient/access_requests.html",
            access_requests=access_requests
        )"""
# (Note: already replaced first instance in patient_access_requests; let's replace second instance in patient_doctor_access)
if doc_access_render_target in content:
    content = content.replace(doc_access_render_target, patient_req_render_replacement, 1)

# Save patched app.py
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("All app.py patches applied cleanly!")
