with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if '@app.route("/doctor/patient-access/<patient_id>/verify-otp", methods=["POST"])' in line:
        start_idx = i
    if start_idx is not None and i > start_idx:
        if '# DOCTOR - PATIENT WORKSPACE' in line or '# DOCTOR  PATIENT WORKSPACE' in line or ('# ==' in line and 'WORKSPACE' in lines[min(i+1, len(lines)-1)]):
            end_idx = i
            break

print(f"start_idx: {start_idx}, end_idx: {end_idx}")

new_code = '''@app.route("/doctor/patient-access/<patient_id>/verify-otp", methods=["POST"])
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
        return jsonify({"success": False, "error": f"Token verification error: {str(e)}"}), 500

'''

# Ensure CRLF line endings
new_lines = [l + "\r\n" for l in new_code.split("\n")]
lines[start_idx:end_idx] = new_lines

with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Replaced verify block and added verify-access-token route successfully.")
