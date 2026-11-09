import os

with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update public_patient_qr_landing render_template
old_render_public = '''    return render_template(
        "patient/public_patient_info.html",
        patient=patient,
        health_id=health_id,
        qr_identifier=qr_identifier,
        calculated_age=age
    )'''

new_render_public = '''    return render_template(
        "patient/public_patient_info.html",
        patient=patient,
        health_id=health_id,
        qr_identifier=qr_identifier,
        calculated_age=age,
        msg91_widget_id=os.getenv("MSG91_WIDGET_ID", ""),
        msg91_token_auth=os.getenv("MSG91_INTEGRATION_TOKEN", ""),
        msg91_env=os.getenv("MSG91_ENVIRONMENT", "development")
    )'''

# Normalize newlines for replacement
if old_render_public.replace("\r\n", "\n") in code.replace("\r\n", "\n"):
    code = code.replace(old_render_public.replace("\n", "\r\n"), new_render_public.replace("\n", "\r\n"))
    print("1. public_patient_qr_landing updated successfully.")
else:
    print("Warning: old_render_public target not matched.")

# 2. Update external_consultation_verify_otp
old_ext_verify = '''@app.route("/qr/<qr_identifier>/verify-otp", methods=["POST"])
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
            return jsonify({"success": False, "error": msg}), 400'''

new_ext_verify = '''@app.route("/qr/<qr_identifier>/verify-otp", methods=["POST"])
def external_consultation_verify_otp(qr_identifier):
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        challenge_id = str(data.get("challenge_id") or "").strip()
        otp_code = str(data.get("otp_code") or "").strip()
        access_token = str(data.get("access_token") or data.get("access-token") or "").strip()

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

        # Verify either MSG91 widget access token or 4-digit OTP code
        if access_token:
            verified, msg, verified_meta = MSG91OTPService.verify_widget_access_token(
                access_token=access_token
            )
        elif challenge_id and otp_code:
            verified, msg, verified_meta = MSG91OTPService.verify_otp(
                challenge_id=challenge_id,
                patient_id=str(patient_id),
                entered_otp=otp_code
            )
        else:
            return jsonify({"success": False, "error": "Please enter the 4-digit OTP code or provide MSG91 access token."}), 400

        if not verified:
            return jsonify({"success": False, "error": msg}), 400'''

if old_ext_verify.replace("\r\n", "\n") in code.replace("\r\n", "\n"):
    code = code.replace(old_ext_verify.replace("\n", "\r\n"), new_ext_verify.replace("\n", "\r\n"))
    print("2. external_consultation_verify_otp updated successfully.")
else:
    print("Warning: old_ext_verify target not matched.")

# 3. Update doctor_patient_access render_template
old_render_doc = '''    return render_template(
        "doctor/patient_access.html",
        patient=patient,
        error=error,
        health_id=patient.get("health_id") if patient else identifier,
        identifier=identifier,
        masked_phone=masked_phone
    )'''

new_render_doc = '''    return render_template(
        "doctor/patient_access.html",
        patient=patient,
        error=error,
        health_id=patient.get("health_id") if patient else identifier,
        identifier=identifier,
        masked_phone=masked_phone,
        msg91_widget_id=os.getenv("MSG91_WIDGET_ID", ""),
        msg91_token_auth=os.getenv("MSG91_INTEGRATION_TOKEN", ""),
        msg91_env=os.getenv("MSG91_ENVIRONMENT", "development")
    )'''

if old_render_doc.replace("\r\n", "\n") in code.replace("\r\n", "\n"):
    code = code.replace(old_render_doc.replace("\n", "\r\n"), new_render_doc.replace("\n", "\r\n"))
    print("3. doctor_patient_access updated successfully.")
else:
    print("Warning: old_render_doc target not matched.")

# 4. Update doctor_patient_send_otp
old_doc_send = '''@app.route("/doctor/patient-access/<patient_id>/send-otp", methods=["POST"])
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
        return jsonify({"success": False, "error": "Failed to send OTP to patient."}), 500'''

new_doc_send = '''@app.route("/doctor/patient-access/<patient_id>/send-otp", methods=["POST"])
def doctor_patient_send_otp(patient_id):
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Please login as a doctor."}), 401

    doctor_id = session["doctor_id"]

    try:
        # Get doctor name
        doc_res = supabase_admin.table("doctors").select("full_name, name").eq("id", doctor_id).maybe_single().execute()
        doctor_name = "Attending Doctor"
        if doc_res and doc_res.data:
            doctor_name = doc_res.data.get("full_name") or doc_res.data.get("name") or "Attending Doctor"

        # Resolve patient: support UUID, health_id, or QR token
        patient = None
        resolved_pid = patient_id
        token_rec = ExternalConsultationService.resolve_qr_token(patient_id)
        if token_rec and token_rec.get("patient_id"):
            resolved_pid = token_rec["patient_id"]

        try:
            pat_res = supabase_admin.table("patients").select("id, phone, email, full_name, name, health_id").eq("id", resolved_pid).maybe_single().execute()
            if pat_res and pat_res.data:
                patient = pat_res.data
        except Exception:
            pass

        if not patient:
            try:
                pat_res = supabase_admin.table("patients").select("id, phone, email, full_name, name, health_id").eq("health_id", patient_id).maybe_single().execute()
                if pat_res and pat_res.data:
                    patient = pat_res.data
            except Exception:
                pass

        if not patient:
            patient = ExternalConsultationService.get_cached_patient(resolved_pid)

        if not patient:
            return jsonify({"success": False, "error": f"Patient '{patient_id}' not found."}), 404

        real_patient_id = str(patient.get("id") or resolved_pid)
        phone = (patient.get("phone") or "").strip()
        email = (patient.get("email") or "").strip()

        # If contact is missing and in dev mode, use demo contact for developer testing
        if not phone and not email:
            if is_dev_mode():
                phone = "9876543210"
            else:
                return jsonify({"success": False, "error": "The patient does not have a verified phone number or email on file for OTP authorization."}), 400

        success, msg, challenge_meta = MSG91OTPService.request_otp(
            patient_id=real_patient_id,
            patient_phone=phone,
            patient_email=email,
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
            "expires_in_seconds": challenge_meta["expires_in_seconds"],
            "otp_length": challenge_meta.get("otp_length", 4)
        }), 200

    except Exception as e:
        print("Doctor Send OTP Error:", repr(e))
        return jsonify({"success": False, "error": f"Failed to send OTP to patient: {str(e)}"}), 500'''

if old_doc_send.replace("\r\n", "\n") in code.replace("\r\n", "\n"):
    code = code.replace(old_doc_send.replace("\n", "\r\n"), new_doc_send.replace("\n", "\r\n"))
    print("4. doctor_patient_send_otp updated successfully.")
else:
    print("Warning: old_doc_send target not matched.")

# 5. Update doctor_patient_verify_otp & Add direct verify access token endpoint
old_doc_verify = '''@app.route("/doctor/patient-access/<patient_id>/verify-otp", methods=["POST"])
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
        return jsonify({"success": False, "error": "Verification failed."}), 500'''

new_doc_verify = '''@app.route("/doctor/patient-access/<patient_id>/verify-otp", methods=["POST"])
def doctor_patient_verify_otp(patient_id):
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Please login as a doctor."}), 401

    doctor_id = session["doctor_id"]

    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        challenge_id = str(data.get("challenge_id") or "").strip()
        otp_code = str(data.get("otp_code") or "").strip()
        access_token = str(data.get("access_token") or data.get("access-token") or "").strip()

        # Resolve patient: support UUID, health_id, or QR token
        resolved_pid = patient_id
        token_rec = ExternalConsultationService.resolve_qr_token(patient_id)
        if token_rec and token_rec.get("patient_id"):
            resolved_pid = token_rec["patient_id"]

        # Support either MSG91 widget access token or 4-digit OTP code
        if access_token:
            verified, msg, verified_meta = MSG91OTPService.verify_widget_access_token(
                access_token=access_token
            )
        elif challenge_id and otp_code:
            verified, msg, verified_meta = MSG91OTPService.verify_otp(
                challenge_id=challenge_id,
                patient_id=str(resolved_pid),
                entered_otp=otp_code
            )
        else:
            return jsonify({"success": False, "error": "Please enter the 4-digit OTP code or provide MSG91 access token."}), 400

        if not verified:
            return jsonify({"success": False, "error": msg}), 400

        # Create active 5-minute session in ExternalConsultationService
        session_rec = ExternalConsultationService.create_session(
            patient_id=str(resolved_pid),
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
                "patient_id": resolved_pid,
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
                patient_ids=[str(resolved_pid)],
                status="SUCCESS",
                metadata={"session_id": session_rec["session_id"], "duration_minutes": 5},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "OTP verified successfully.",
            "redirect_url": url_for("doctor_patient_workspace", patient_id=str(resolved_pid))
        }), 200

    except Exception as e:
        print("Doctor Verify OTP Error:", repr(e))
        return jsonify({"success": False, "error": f"Verification failed: {str(e)}"}), 500


# =========================================================
# MSG91 WIDGET DIRECT ACCESS TOKEN VERIFICATION API
# =========================================================
@app.route("/api/msg91/verify-access-token", methods=["POST"])
def msg91_verify_access_token_api():
    """
    Validates MSG91 OTP Widget JWT access-token against control.msg91.com/api/v5/widget/verifyAccessToken.
    Creates authorized 5-minute session and returns redirect URL to patient workspace.
    """
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        access_token = str(data.get("access_token") or data.get("access-token") or "").strip()
        patient_id = str(data.get("patient_id") or data.get("qr_identifier") or "").strip()
        context = str(data.get("context") or "external").strip()

        if not access_token:
            return jsonify({"success": False, "error": "Missing access-token."}), 400

        # Resolve patient
        token_rec = ExternalConsultationService.resolve_qr_token(patient_id)
        resolved_pid = token_rec.get("patient_id") if token_rec else patient_id

        verified, msg, verified_meta = MSG91OTPService.verify_widget_access_token(
            access_token=access_token
        )

        if not verified:
            return jsonify({"success": False, "error": msg}), 400

        is_doctor = (context == "doctor" and "doctor_id" in session)
        visitor_details = data.get("visitor_details") or {
            "full_name": (verified_meta or {}).get("visitor_name") or ("Attending Doctor" if is_doctor else "External Clinician"),
            "role": "Doctor"
        }

        session_rec = ExternalConsultationService.create_session(
            patient_id=str(resolved_pid),
            visitor_details=visitor_details,
            is_internal_doctor=is_doctor,
            doctor_id=str(session.get("doctor_id")) if is_doctor else None
        )

        if is_doctor:
            session["active_otp_access"] = session_rec
        else:
            session["external_consultation"] = session_rec

        try:
            log_clinical_event(
                doctor_id=str(session.get("doctor_id") or "EXTERNAL_WIDGET"),
                action="EXTERNAL_CONSULTATION_OTP_VERIFIED" if not is_doctor else "INTERNAL_OTP_ACCESS_GRANTED",
                patient_ids=[str(resolved_pid)],
                status="SUCCESS",
                metadata={"session_id": session_rec["session_id"], "auth_method": "msg91_widget"},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "MSG91 access token verified successfully.",
            "redirect_url": url_for("doctor_patient_workspace", patient_id=str(resolved_pid))
        }), 200

    except Exception as e:
        print("MSG91 Verify Access Token Route Error:", repr(e))
        return jsonify({"success": False, "error": f"Token verification error: {str(e)}"}), 500'''

if old_doc_verify.replace("\r\n", "\n") in code.replace("\r\n", "\n"):
    code = code.replace(old_doc_verify.replace("\n", "\r\n"), new_doc_verify.replace("\n", "\r\n"))
    print("5. doctor_patient_verify_otp updated successfully.")
else:
    print("Warning: old_doc_verify target not matched.")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Finished applying updates to app.py.")
