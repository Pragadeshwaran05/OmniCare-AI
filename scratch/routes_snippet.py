import json
import secrets
from datetime import datetime, timezone
from flask import request, jsonify, Response, url_for

# ============================================================
# DOCTOR - PATIENT WORKSPACE MEDICAL RECORD ROUTES
# ============================================================

def register_medical_record_workspace_routes(app, supabase_admin, check_workspace_access, log_audit_event, get_doctor_profile, process_medical_document, save_patient_medical_record, generate_consultation_pdf, generate_prescription_pdf, generate_other_document_pdf):

    @app.route("/doctor/patient-workspace/<patient_id>/upload-medical-record", methods=["POST"])
    def doctor_upload_patient_medical_record(patient_id):
        is_auth, access_info, err_msg = check_workspace_access(patient_id)
        if not is_auth:
            return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

        if access_info.get("read_only", False) or access_info.get("is_external", False):
            return jsonify({
                "success": False,
                "error": "Access is read-only. Medical record upload is prohibited during read-only sessions."
            }), 403

        doctor_id = access_info.get("doctor_id") or "DOCTOR"
        doctor_data = {}
        if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
            try:
                doctor_data = get_doctor_profile(doctor_id, supabase_admin, {}) or {}
            except Exception:
                doctor_data = {}

        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file uploaded."}), 400

        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"success": False, "error": "Selected file is invalid."}), 400

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        allowed = {"pdf", "jpg", "jpeg", "png", "webp"}
        if ext not in allowed:
            return jsonify({"success": False, "error": f"Unsupported format. Allowed: {', '.join(allowed)}"}), 400

        file_bytes = file.read()
        if len(file_bytes) > 15 * 1024 * 1024:
            return jsonify({"success": False, "error": "File size exceeds 15MB limit."}), 400

        content_type = file.content_type or ("application/pdf" if ext == "pdf" else f"image/{ext}")
        record_type = request.form.get("record_type", "other").strip()
        title = request.form.get("title", "").strip() or f"{record_type.replace('_', ' ').title()} - {datetime.now().strftime('%d %b %Y')}"
        description = request.form.get("description", "").strip()
        document_date = request.form.get("document_date", "").strip() or datetime.now(timezone.utc).date().isoformat()
        hospital_name = request.form.get("hospital_name", "").strip() or doctor_data.get("hospital_name") or ""
        doctor_name = request.form.get("doctor_name", "").strip() or doctor_data.get("full_name") or ""
        trigger_ai = request.form.get("trigger_ai", "true").lower() in ("true", "1", "yes")

        try:
            saved_rec = save_patient_medical_record(
                supabase_client=supabase_admin,
                patient_id=patient_id,
                doctor_id=doctor_id,
                record_type=record_type,
                title=title,
                description=description,
                file_bytes=file_bytes,
                filename=file.filename,
                content_type=content_type,
                document_date=document_date
            )

            # Link view_url if missing
            if not saved_rec.get("file_url") and saved_rec.get("id"):
                try:
                    saved_rec["file_url"] = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=saved_rec["id"])
                except Exception:
                    pass

            # Gemini AI extraction or fallback timeline event
            ai_processed = False
            if trigger_ai:
                try:
                    extracted_data = process_medical_document(
                        file_bytes=file_bytes,
                        filename=file.filename,
                        content_type=content_type
                    )
                    if extracted_data:
                        timeline_payload = {
                            "patient_id": patient_id,
                            "medical_record_id": saved_rec.get("id"),
                            "event_date": extracted_data.get("event_date") or document_date,
                            "event_type": extracted_data.get("event_type") or record_type,
                            "provider_name": doctor_name or extracted_data.get("provider_name") or doctor_data.get("full_name"),
                            "hospital_name": hospital_name or extracted_data.get("hospital_name") or doctor_data.get("hospital_name"),
                            "diagnosis": extracted_data.get("diagnosis"),
                            "clinical_findings": extracted_data.get("clinical_findings"),
                            "investigations": extracted_data.get("investigations") or [],
                            "medications": extracted_data.get("medications") or [],
                            "follow_up": extracted_data.get("follow_up"),
                            "clinical_summary": extracted_data.get("clinical_summary") or description,
                            "ai_processed": True
                        }
                        supabase_admin.table("health_timeline_events").insert(timeline_payload).execute()
                        ai_processed = True
                except Exception as ai_err:
                    print("Notice: AI extraction skipped/failed:", repr(ai_err))

            if not ai_processed:
                try:
                    supabase_admin.table("health_timeline_events").insert({
                        "patient_id": patient_id,
                        "medical_record_id": saved_rec.get("id"),
                        "event_date": document_date,
                        "event_type": record_type,
                        "provider_name": doctor_name or doctor_data.get("full_name") or "Doctor",
                        "hospital_name": hospital_name or doctor_data.get("hospital_name") or "Hospital",
                        "clinical_summary": description or title,
                        "ai_processed": False
                    }).execute()
                except Exception as tl_err:
                    print("Notice: Timeline fallback insert notice:", repr(tl_err))

            try:
                log_audit_event(
                    doctor_id=doctor_id,
                    action="MEDICAL_RECORD_UPLOADED",
                    patient_ids=[patient_id],
                    status="SUCCESS",
                    metadata={"record_id": saved_rec.get("id"), "type": record_type, "title": title},
                    client_ip=request.remote_addr
                )
            except Exception:
                pass

            return jsonify({
                "success": True,
                "message": "Medical record uploaded successfully.",
                "record": saved_rec
            })

        except Exception as e:
            print("Error uploading patient medical record:", repr(e))
            return jsonify({"success": False, "error": f"Failed to upload record: {str(e)}"}), 500

    @app.route("/doctor/patient-workspace/<patient_id>/create-consultation", methods=["POST"])
    def doctor_create_consultation_note(patient_id):
        is_auth, access_info, err_msg = check_workspace_access(patient_id)
        if not is_auth:
            return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

        if access_info.get("read_only", False) or access_info.get("is_external", False):
            return jsonify({"success": False, "error": "Access is read-only. Record creation is prohibited."}), 403

        doctor_id = access_info.get("doctor_id") or "DOCTOR"
        doctor_data = {}
        if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
            try:
                doctor_data = get_doctor_profile(doctor_id, supabase_admin, {}) or {}
            except Exception:
                doctor_data = {}

        patient_res = supabase_admin.table("patients").select("*").eq("id", patient_id).single().execute()
        patient_data = patient_res.data or {}

        data = request.get_json(silent=True) or request.form.to_dict()
        consultation_type = data.get("consultation_type", "General Consultation").strip()
        chief_complaint = data.get("chief_complaint", "").strip()
        hpi = data.get("hpi", "").strip()
        vitals = data.get("vitals") if isinstance(data.get("vitals"), dict) else {}
        if not vitals:
            # parse from form fields
            vitals = {
                "bp": data.get("vitals_bp", "").strip(),
                "pulse": data.get("vitals_pulse", "").strip(),
                "temperature": data.get("vitals_temperature", "").strip(),
                "respiratory_rate": data.get("vitals_rr", "").strip(),
                "oxygen_saturation": data.get("vitals_spo2", "").strip(),
                "weight": data.get("vitals_weight", "").strip(),
                "height": data.get("vitals_height", "").strip(),
                "bmi": data.get("vitals_bmi", "").strip()
            }
        diagnosis_primary = data.get("diagnosis_primary", "").strip()
        diagnosis_secondary = data.get("diagnosis_secondary", "").strip()
        treatment_plan = data.get("treatment_plan", "").strip()
        clinical_notes = data.get("clinical_notes", "").strip()
        document_date = data.get("document_date", "").strip() or datetime.now(timezone.utc).date().isoformat()
        hospital_name = data.get("hospital_name", "").strip() or doctor_data.get("hospital_name") or "Medical Center"
        doctor_name = data.get("doctor_name", "").strip() or doctor_data.get("full_name") or "Doctor"
        is_draft = str(data.get("is_draft", "")).lower() in ("true", "1")

        if hospital_name:
            doctor_data["hospital_name"] = hospital_name
        if doctor_name:
            doctor_data["full_name"] = doctor_name

        consultation_payload = {
            "consultation_type": consultation_type,
            "date": document_date,
            "chief_complaint": chief_complaint,
            "hpi": hpi,
            "vitals": vitals,
            "diagnosis_primary": diagnosis_primary,
            "diagnosis_secondary": diagnosis_secondary,
            "treatment_plan": treatment_plan,
            "clinical_notes": clinical_notes,
            "is_draft": is_draft
        }

        try:
            pdf_bytes = generate_consultation_pdf(doctor_data, patient_data, consultation_payload)
            filename = f"consultation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            title = data.get("title", "").strip() or f"Consultation Note - {consultation_type}"
            description = f"Chief complaint: {chief_complaint}. Diagnosis: {diagnosis_primary}" if diagnosis_primary else (chief_complaint or "Consultation Note")

            saved_rec = save_patient_medical_record(
                supabase_client=supabase_admin,
                patient_id=patient_id,
                doctor_id=doctor_id,
                record_type="consultation",
                title=title,
                description=description,
                file_bytes=pdf_bytes,
                filename=filename,
                content_type="application/pdf",
                document_date=document_date,
                structured_data=consultation_payload,
                is_draft=is_draft
            )

            if not saved_rec.get("file_url") and saved_rec.get("id"):
                try:
                    saved_rec["file_url"] = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=saved_rec["id"])
                except Exception:
                    pass

            # Timeline event
            try:
                vitals_summary = ", ".join([f"{k.upper()}: {v}" for k, v in vitals.items() if v])
                supabase_admin.table("health_timeline_events").insert({
                    "patient_id": patient_id,
                    "medical_record_id": saved_rec.get("id"),
                    "event_date": document_date,
                    "event_type": "consultation",
                    "provider_name": doctor_name or doctor_data.get("full_name") or "Doctor",
                    "hospital_name": hospital_name or doctor_data.get("hospital_name") or "Hospital",
                    "diagnosis": f"{diagnosis_primary} {f'({diagnosis_secondary})' if diagnosis_secondary else ''}".strip(),
                    "clinical_findings": f"Chief Complaint: {chief_complaint}\n\nVitals: {vitals_summary}",
                    "clinical_summary": f"Treatment: {treatment_plan}\n\nNotes: {clinical_notes}".strip(),
                    "ai_processed": False
                }).execute()
            except Exception as tl_err:
                print("Notice: Timeline consultation insert fallback:", repr(tl_err))

            return jsonify({
                "success": True,
                "message": "Consultation note created successfully.",
                "record": saved_rec
            })

        except Exception as e:
            print("Error creating consultation note:", repr(e))
            return jsonify({"success": False, "error": f"Failed to create consultation note: {str(e)}"}), 500

    @app.route("/doctor/patient-workspace/<patient_id>/create-prescription", methods=["POST"])
    def doctor_create_prescription(patient_id):
        is_auth, access_info, err_msg = check_workspace_access(patient_id)
        if not is_auth:
            return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

        if access_info.get("read_only", False) or access_info.get("is_external", False):
            return jsonify({"success": False, "error": "Access is read-only. Prescription creation is prohibited."}), 403

        doctor_id = access_info.get("doctor_id") or "DOCTOR"
        doctor_data = {}
        if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
            try:
                doctor_data = get_doctor_profile(doctor_id, supabase_admin, {}) or {}
            except Exception:
                doctor_data = {}

        patient_res = supabase_admin.table("patients").select("*").eq("id", patient_id).single().execute()
        patient_data = patient_res.data or {}

        data = request.get_json(silent=True) or request.form.to_dict()
        diagnosis = data.get("diagnosis", "").strip()
        clinical_notes = data.get("clinical_notes", "").strip()
        general_advice = data.get("general_advice", "").strip()
        follow_up = data.get("follow_up", "").strip()
        document_date = data.get("document_date", "").strip() or datetime.now(timezone.utc).date().isoformat()
        hospital_name = data.get("hospital_name", "").strip() or doctor_data.get("hospital_name") or "Medical Center"
        doctor_name = data.get("doctor_name", "").strip() or doctor_data.get("full_name") or "Doctor"
        is_draft = str(data.get("is_draft", "")).lower() in ("true", "1")

        if hospital_name:
            doctor_data["hospital_name"] = hospital_name
        if doctor_name:
            doctor_data["full_name"] = doctor_name

        medicines_raw = data.get("medicines", [])
        if isinstance(medicines_raw, str):
            try:
                medicines = json.loads(medicines_raw)
            except Exception:
                medicines = []
        elif isinstance(medicines_raw, list):
            medicines = medicines_raw
        else:
            medicines = []

        prescription_payload = {
            "date": document_date,
            "diagnosis": diagnosis,
            "clinical_notes": clinical_notes,
            "medicines": medicines,
            "general_advice": general_advice,
            "follow_up": follow_up,
            "is_draft": is_draft
        }

        try:
            pdf_bytes = generate_prescription_pdf(doctor_data, patient_data, prescription_payload)
            filename = f"prescription_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            title = data.get("title", "").strip() or f"Prescription - {datetime.now().strftime('%d %b %Y')}"
            med_count = len(medicines)
            description = f"Prescribed {med_count} medication(s). Diagnosis: {diagnosis}" if diagnosis else f"Prescribed {med_count} medication(s)."

            saved_rec = save_patient_medical_record(
                supabase_client=supabase_admin,
                patient_id=patient_id,
                doctor_id=doctor_id,
                record_type="prescription",
                title=title,
                description=description,
                file_bytes=pdf_bytes,
                filename=filename,
                content_type="application/pdf",
                document_date=document_date,
                structured_data=prescription_payload,
                is_draft=is_draft
            )

            if not saved_rec.get("file_url") and saved_rec.get("id"):
                try:
                    saved_rec["file_url"] = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=saved_rec["id"])
                except Exception:
                    pass

            # Timeline event
            try:
                supabase_admin.table("health_timeline_events").insert({
                    "patient_id": patient_id,
                    "medical_record_id": saved_rec.get("id"),
                    "event_date": document_date,
                    "event_type": "prescription",
                    "provider_name": doctor_name or doctor_data.get("full_name") or "Doctor",
                    "hospital_name": hospital_name or doctor_data.get("hospital_name") or "Hospital",
                    "diagnosis": diagnosis,
                    "medications": medicines,
                    "clinical_summary": f"{general_advice}\n{clinical_notes}".strip(),
                    "follow_up": follow_up,
                    "ai_processed": False
                }).execute()
            except Exception as tl_err:
                print("Notice: Timeline prescription insert fallback:", repr(tl_err))

            return jsonify({
                "success": True,
                "message": "Prescription created successfully.",
                "record": saved_rec
            })

        except Exception as e:
            print("Error creating prescription:", repr(e))
            return jsonify({"success": False, "error": f"Failed to create prescription: {str(e)}"}), 500

    @app.route("/doctor/patient-workspace/<patient_id>/create-other-document", methods=["POST"])
    def doctor_create_other_document(patient_id):
        is_auth, access_info, err_msg = check_workspace_access(patient_id)
        if not is_auth:
            return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

        if access_info.get("read_only", False) or access_info.get("is_external", False):
            return jsonify({"success": False, "error": "Access is read-only. Document creation is prohibited."}), 403

        doctor_id = access_info.get("doctor_id") or "DOCTOR"
        doctor_data = {}
        if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
            try:
                doctor_data = get_doctor_profile(doctor_id, supabase_admin, {}) or {}
            except Exception:
                doctor_data = {}

        patient_res = supabase_admin.table("patients").select("*").eq("id", patient_id).single().execute()
        patient_data = patient_res.data or {}

        data = request.get_json(silent=True) or request.form.to_dict()
        doc_type = data.get("doc_type", "other").strip()
        title = data.get("title", "").strip() or f"{doc_type.replace('_', ' ').title()}"
        clinical_summary = data.get("clinical_summary", "").strip()
        findings = data.get("findings", "").strip()
        recommendations = data.get("recommendations", "").strip()
        recipient = data.get("recipient", "").strip()
        certificate_reason = data.get("certificate_reason", "").strip()
        valid_from = data.get("valid_from", "").strip()
        valid_to = data.get("valid_to", "").strip()
        document_date = data.get("document_date", "").strip() or datetime.now(timezone.utc).date().isoformat()
        hospital_name = data.get("hospital_name", "").strip() or doctor_data.get("hospital_name") or "Medical Center"
        doctor_name = data.get("doctor_name", "").strip() or doctor_data.get("full_name") or "Doctor"
        is_draft = str(data.get("is_draft", "")).lower() in ("true", "1")

        if hospital_name:
            doctor_data["hospital_name"] = hospital_name
        if doctor_name:
            doctor_data["full_name"] = doctor_name

        document_payload = {
            "doc_type": doc_type,
            "title": title,
            "date": document_date,
            "clinical_summary": clinical_summary,
            "findings": findings,
            "recommendations": recommendations,
            "recipient": recipient,
            "certificate_reason": certificate_reason,
            "valid_from": valid_from,
            "valid_to": valid_to,
            "is_draft": is_draft
        }

        try:
            pdf_bytes = generate_other_document_pdf(doctor_data, patient_data, document_payload)
            filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            description = clinical_summary or findings or title

            saved_rec = save_patient_medical_record(
                supabase_client=supabase_admin,
                patient_id=patient_id,
                doctor_id=doctor_id,
                record_type=doc_type,
                title=title,
                description=description,
                file_bytes=pdf_bytes,
                filename=filename,
                content_type="application/pdf",
                document_date=document_date,
                structured_data=document_payload,
                is_draft=is_draft
            )

            if not saved_rec.get("file_url") and saved_rec.get("id"):
                try:
                    saved_rec["file_url"] = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=saved_rec["id"])
                except Exception:
                    pass

            # Timeline event
            try:
                supabase_admin.table("health_timeline_events").insert({
                    "patient_id": patient_id,
                    "medical_record_id": saved_rec.get("id"),
                    "event_date": document_date,
                    "event_type": doc_type,
                    "provider_name": doctor_name or doctor_data.get("full_name") or "Doctor",
                    "hospital_name": hospital_name or doctor_data.get("hospital_name") or "Hospital",
                    "clinical_findings": findings,
                    "clinical_summary": clinical_summary or recommendations,
                    "ai_processed": False
                }).execute()
            except Exception as tl_err:
                print("Notice: Timeline other doc insert fallback:", repr(tl_err))

            return jsonify({
                "success": True,
                "message": f"{title} created successfully.",
                "record": saved_rec
            })

        except Exception as e:
            print("Error creating other document:", repr(e))
            return jsonify({"success": False, "error": f"Failed to create document: {str(e)}"}), 500

    @app.route("/doctor/patient-workspace/<patient_id>/preview-document-pdf", methods=["POST"])
    def doctor_preview_document_pdf(patient_id):
        is_auth, access_info, err_msg = check_workspace_access(patient_id)
        if not is_auth:
            return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

        if access_info.get("read_only", False) or access_info.get("is_external", False):
            return jsonify({"success": False, "error": "Access is read-only."}), 403

        doctor_id = access_info.get("doctor_id") or "DOCTOR"
        doctor_data = {}
        if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
            try:
                doctor_data = get_doctor_profile(doctor_id, supabase_admin, {}) or {}
            except Exception:
                doctor_data = {}

        patient_res = supabase_admin.table("patients").select("*").eq("id", patient_id).single().execute()
        patient_data = patient_res.data or {}

        data = request.get_json(silent=True) or request.form.to_dict()
        template_type = data.get("template_type", "consultation").strip().lower()

        hospital_name = data.get("hospital_name", "").strip() or doctor_data.get("hospital_name") or "Medical Center"
        doctor_name = data.get("doctor_name", "").strip() or doctor_data.get("full_name") or "Doctor"
        doctor_data["hospital_name"] = hospital_name
        doctor_data["full_name"] = doctor_name

        try:
            if template_type == "consultation":
                vitals = data.get("vitals") if isinstance(data.get("vitals"), dict) else {}
                if not vitals:
                    vitals = {
                        "bp": data.get("vitals_bp", "").strip(),
                        "pulse": data.get("vitals_pulse", "").strip(),
                        "temperature": data.get("vitals_temperature", "").strip(),
                        "respiratory_rate": data.get("vitals_rr", "").strip(),
                        "oxygen_saturation": data.get("vitals_spo2", "").strip(),
                        "weight": data.get("vitals_weight", "").strip(),
                        "height": data.get("vitals_height", "").strip(),
                        "bmi": data.get("vitals_bmi", "").strip()
                    }
                payload = {
                    "consultation_type": data.get("consultation_type", "General Consultation"),
                    "date": data.get("document_date") or datetime.now(timezone.utc).date().isoformat(),
                    "chief_complaint": data.get("chief_complaint", ""),
                    "hpi": data.get("hpi", ""),
                    "vitals": vitals,
                    "diagnosis_primary": data.get("diagnosis_primary", ""),
                    "diagnosis_secondary": data.get("diagnosis_secondary", ""),
                    "treatment_plan": data.get("treatment_plan", ""),
                    "clinical_notes": data.get("clinical_notes", ""),
                    "is_draft": False
                }
                pdf_bytes = generate_consultation_pdf(doctor_data, patient_data, payload)

            elif template_type == "prescription":
                medicines_raw = data.get("medicines", [])
                if isinstance(medicines_raw, str):
                    try:
                        medicines = json.loads(medicines_raw)
                    except Exception:
                        medicines = []
                elif isinstance(medicines_raw, list):
                    medicines = medicines_raw
                else:
                    medicines = []

                payload = {
                    "date": data.get("document_date") or datetime.now(timezone.utc).date().isoformat(),
                    "diagnosis": data.get("diagnosis", ""),
                    "clinical_notes": data.get("clinical_notes", ""),
                    "medicines": medicines,
                    "general_advice": data.get("general_advice", ""),
                    "follow_up": data.get("follow_up", ""),
                    "is_draft": False
                }
                pdf_bytes = generate_prescription_pdf(doctor_data, patient_data, payload)

            else:
                payload = {
                    "doc_type": data.get("doc_type", "other"),
                    "title": data.get("title") or "Medical Document",
                    "date": data.get("document_date") or datetime.now(timezone.utc).date().isoformat(),
                    "clinical_summary": data.get("clinical_summary", ""),
                    "findings": data.get("findings", ""),
                    "recommendations": data.get("recommendations", ""),
                    "recipient": data.get("recipient", ""),
                    "certificate_reason": data.get("certificate_reason", ""),
                    "valid_from": data.get("valid_from", ""),
                    "valid_to": data.get("valid_to", ""),
                    "is_draft": False
                }
                pdf_bytes = generate_other_document_pdf(doctor_data, patient_data, payload)

            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename={template_type}_preview.pdf",
                    "Cache-Control": "no-cache, no-store, must-revalidate"
                }
            )

        except Exception as e:
            print("Error generating PDF preview:", repr(e))
            return jsonify({"success": False, "error": f"Preview generation failed: {str(e)}"}), 500

    @app.route("/doctor/patient-workspace/<patient_id>/api/records", methods=["GET"])
    def doctor_get_patient_records_api(patient_id):
        is_auth, access_info, err_msg = check_workspace_access(patient_id)
        if not is_auth:
            return jsonify({"success": False, "error": err_msg or "Unauthorized"}), 403

        try:
            records_response = (
                supabase_admin
                .table("medical_records")
                .select("*")
                .eq("patient_id", patient_id)
                .order("uploaded_at", desc=True)
                .execute()
            )
            records = records_response.data or []
        except Exception:
            try:
                records_response = (
                    supabase_admin
                    .table("medical_records")
                    .select("*")
                    .eq("patient_id", patient_id)
                    .execute()
                )
                records = records_response.data or []
            except Exception as e2:
                return jsonify({"success": False, "error": str(e2)}), 500

        for rec in records:
            if not rec.get("file_url") and rec.get("id"):
                try:
                    rec["file_url"] = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=rec["id"])
                except Exception:
                    pass

        return jsonify({
            "success": True,
            "records": records,
            "count": len(records)
        })
