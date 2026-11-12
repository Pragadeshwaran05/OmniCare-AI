with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Normalize newlines
c_norm = c.replace('\r\n', '\n')

old_block_start = c_norm.find('@app.route(\n    "/doctor/patient-workspace/<patient_id>/ai-assistant",')
old_block_end = c_norm.find('# ============================================================\n# DOCTOR - PATIENT WORKSPACE TREND DATA API')

assert old_block_start != -1, "start not found"
assert old_block_end != -1, "end not found"

new_block = '''@app.route(
    "/doctor/patient-workspace/<patient_id>/ai-assistant",
    methods=["POST"]
)
def doctor_patient_ai_assistant(patient_id):
    """
    Secure patient-specific medical history AI assistant.
    Strictly scoped to authorized patient records.
    """
    # 1. Check authorized clinical access
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return jsonify({
            "success": False,
            "message": err_msg or "You do not have active access to this patient's records."
        }), 403

    doctor_id = access_info.get("doctor_id", "EXTERNAL_CONSULTATION")

    try:
        data = request.get_json(silent=True) or {}
        question = data.get("question", "").strip()

        if not question:
            return jsonify({
                "success": False,
                "message": "Please enter a question."
            }), 400

        # 2. Retrieve patient profile
        patient = {}
        try:
            p_res = (
                supabase_admin.table("patients")
                .select("id, full_name, health_id, date_of_birth, gender, blood_group")
                .eq("id", patient_id)
                .single()
                .execute()
            )
            patient = p_res.data or {}
        except Exception as p_err:
            print("[DoctorAI Notice] Patient profile fetch notice:", repr(p_err))

        # 3. Retrieve patient clinical timeline events
        timeline_events = []
        try:
            tl_res = (
                supabase_admin.table("health_timeline_events")
                .select("*")
                .eq("patient_id", patient_id)
                .order("event_date", desc=True)
                .execute()
            )
            timeline_events = tl_res.data or []
        except Exception as tl_err:
            print("[DoctorAI Notice] Health timeline fetch notice:", repr(tl_err))

        # 4. Retrieve patient medical records (including unextracted/older documents)
        medical_records = []
        try:
            mr_res = (
                supabase_admin.table("medical_records")
                .select("id, patient_id, record_type, title, description, file_name, file_url, uploaded_at")
                .eq("patient_id", patient_id)
                .order("uploaded_at", desc=True)
                .execute()
            )
            medical_records = mr_res.data or []
        except Exception as mr_err:
            print("[DoctorAI Notice] Medical records fetch notice:", repr(mr_err))

        for rec in medical_records:
            if not rec.get("file_url") and rec.get("id"):
                try:
                    rec["file_url"] = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=rec["id"])
                except Exception:
                    pass

        # 5. Query Gemini AI with complete verified patient context
        answer = ask_doctor_ai(
            question=question,
            timeline_events=timeline_events,
            patient_data=patient,
            medical_records=medical_records
        )

        # 6. Build source records list
        sources = []
        seen_records = set()
        for event in timeline_events:
            rec_id = event.get("medical_record_id")
            if rec_id and rec_id not in seen_records:
                seen_records.add(rec_id)
                try:
                    v_url = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=rec_id)
                except Exception:
                    v_url = None
                sources.append({
                    "medical_record_id": rec_id,
                    "event_date": event.get("event_date"),
                    "event_type": event.get("event_type"),
                    "provider_name": event.get("provider_name"),
                    "hospital_name": event.get("hospital_name"),
                    "view_url": v_url
                })

        for rec in medical_records:
            rec_id = rec.get("id")
            if rec_id and rec_id not in seen_records:
                seen_records.add(rec_id)
                sources.append({
                    "medical_record_id": rec_id,
                    "event_date": rec.get("uploaded_at"),
                    "event_type": rec.get("record_type"),
                    "provider_name": rec.get("provider_name") or "OmniCare Healthcare",
                    "hospital_name": rec.get("hospital_name") or "Medical Center",
                    "view_url": rec.get("file_url")
                })

        # 7. Audit Logging
        try:
            log_audit_event(
                doctor_id=doctor_id,
                action="AI_ASSISTANT_QUERY",
                patient_ids=[patient_id],
                status="SUCCESS",
                metadata={"patient_id": patient_id, "question_len": len(question), "event_count": len(timeline_events)},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "answer": answer,
            "event_count": len(timeline_events),
            "record_count": len(medical_records),
            "sources": sources
        }), 200

    except Exception as e:
        print("=" * 70)
        print("DOCTOR AI ASSISTANT ERROR")
        print("Patient ID:", patient_id)
        print("Doctor ID :", doctor_id)
        print("Error     :", repr(e))
        print("=" * 70)
        return jsonify({
            "success": False,
            "message": "Unable to process the AI request right now. Please try again."
        }), 500


# ============================================================
# DOCTOR AI - SOURCE RECORDS
# ============================================================

@app.route(
    "/doctor/patient-workspace/<patient_id>/ai-sources",
    methods=["GET"]
)
def doctor_patient_ai_sources(patient_id):
    """
    Returns verified source documents for the patient's AI assistant responses.
    """
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return jsonify({
            "success": False,
            "message": err_msg or "You do not have active access to this patient."
        }), 403

    try:
        timeline_events = []
        try:
            tl_res = (
                supabase_admin.table("health_timeline_events")
                .select("id, medical_record_id, event_date, event_type, provider_name, hospital_name")
                .eq("patient_id", patient_id)
                .order("event_date", desc=True)
                .execute()
            )
            timeline_events = tl_res.data or []
        except Exception as tl_err:
            print("[DoctorAI Notice] Timeline sources fetch error:", repr(tl_err))

        sources = []
        seen_records = set()
        for event in timeline_events:
            rec_id = event.get("medical_record_id")
            if not rec_id or rec_id in seen_records:
                continue
            seen_records.add(rec_id)
            try:
                view_url = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=rec_id)
            except Exception:
                view_url = None

            sources.append({
                "medical_record_id": rec_id,
                "event_date": event.get("event_date"),
                "event_type": event.get("event_type"),
                "provider_name": event.get("provider_name"),
                "hospital_name": event.get("hospital_name"),
                "view_url": view_url
            })

        return jsonify({
            "success": True,
            "sources": sources
        }), 200

    except Exception as e:
        print("=" * 70)
        print("DOCTOR AI SOURCE ERROR")
        print("Patient ID:", patient_id)
        print("Error     :", repr(e))
        print("=" * 70)
        return jsonify({
            "success": False,
            "message": "Unable to load source records."
        }), 500

\n'''

c_updated = c_norm[:old_block_start] + new_block + c_norm[old_block_end:]

# Also update doctor_guest_ai_assistant to pass patient_data and medical_records
old_guest_call = '''        answer = ask_doctor_ai(
            question,
            timeline_events
        )'''

new_guest_call = '''        guest_records = []
        try:
            g_mr = (
                supabase_admin.table("guest_medical_records")
                .select("*")
                .eq("guest_patient_id", guest_patient_id)
                .order("created_at", desc=True)
                .execute()
            )
            guest_records = g_mr.data or []
        except Exception as g_mr_err:
            print("[DoctorAI Notice] Guest medical records fetch error:", repr(g_mr_err))

        answer = ask_doctor_ai(
            question=question,
            timeline_events=timeline_events,
            patient_data=guest,
            medical_records=guest_records
        )'''

assert old_guest_call in c_updated, "old_guest_call not found in c_updated"
c_updated = c_updated.replace(old_guest_call, new_guest_call)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c_updated)

print("SUCCESS: app.py updated cleanly.")
