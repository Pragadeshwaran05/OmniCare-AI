with open("app.py", "r", encoding="utf-8") as f:
    text = f.read()

target_send_block = """@app.route("/doctor/patient-access/<patient_id>/send-otp", methods=["POST"])
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
        return jsonify({"success": False, "error": "Failed to send OTP to patient."}), 500"""

replacement_send_block = """@app.route("/doctor/patient-access/<patient_id>/send-otp", methods=["POST"])
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
        return jsonify({"success": False, "error": f"Failed to send OTP to patient: {str(e)}"}), 500"""

if target_send_block in text:
    text = text.replace(target_send_block, replacement_send_block, 1)
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Successfully replaced doctor_patient_send_otp with hardened version!")
else:
    print("Error: target_send_block not matched in app.py!")
