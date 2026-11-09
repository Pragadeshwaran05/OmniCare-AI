import re

app_path = "app.py"

with open(app_path, "r", encoding="utf-8") as f:
    app_code = f.read()

# 1. Update doctor_create_consultation_note
old_cons_block = """    diagnosis_primary = data.get("diagnosis_primary", "").strip()
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
    }"""

new_cons_block = """    diagnosis_primary = data.get("diagnosis_primary", "").strip()
    diagnosis_secondary = data.get("diagnosis_secondary", "").strip()
    treatment_plan = data.get("treatment_plan", "").strip()
    clinical_notes = data.get("clinical_notes", "").strip()
    consultation_time = data.get("consultation_time", "").strip() or data.get("time", "").strip()
    findings = data.get("findings", "").strip() or data.get("clinical_examination_notes", "").strip()
    recommendations = data.get("recommendations", "").strip() or data.get("advice_instructions", "").strip() or data.get("general_advice", "").strip()
    follow_up = data.get("follow_up", "").strip() or data.get("follow_up_date", "").strip()
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
        "consultation_date": document_date,
        "consultation_time": consultation_time,
        "time": consultation_time,
        "chief_complaint": chief_complaint,
        "hpi": hpi,
        "history_of_present_illness": hpi,
        "vitals": vitals,
        "diagnosis_primary": diagnosis_primary,
        "primary_diagnosis": diagnosis_primary,
        "diagnosis_secondary": diagnosis_secondary,
        "secondary_diagnosis": diagnosis_secondary,
        "findings": findings,
        "clinical_examination_notes": findings,
        "treatment_plan": treatment_plan,
        "recommendations": recommendations,
        "advice_instructions": recommendations,
        "follow_up": follow_up,
        "follow_up_date": follow_up,
        "clinical_notes": clinical_notes,
        "is_draft": is_draft
    }"""

app_code = app_code.replace(old_cons_block, new_cons_block)

# 2. Update doctor_create_prescription
old_rx_block = """    data = request.get_json(silent=True) or request.form.to_dict()
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
    }"""

new_rx_block = """    data = request.get_json(silent=True) or request.form.to_dict()
    diagnosis = data.get("diagnosis", "").strip()
    clinical_notes = data.get("clinical_notes", "").strip()
    general_advice = data.get("general_advice", "").strip()
    follow_up = data.get("follow_up", "").strip()
    prescription_time = data.get("prescription_time", "").strip() or data.get("time", "").strip()
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
        "prescription_date": document_date,
        "prescription_time": prescription_time,
        "time": prescription_time,
        "diagnosis": diagnosis,
        "clinical_notes": clinical_notes,
        "medicines": medicines,
        "general_advice": general_advice,
        "follow_up": follow_up,
        "is_draft": is_draft
    }"""

app_code = app_code.replace(old_rx_block, new_rx_block)

# 3. Update doctor_preview_document_pdf
old_preview_block = """        if template_type == "consultation":
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
            pdf_bytes = generate_prescription_pdf(doctor_data, patient_data, payload)"""

new_preview_block = """        if template_type == "consultation":
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
                "consultation_date": data.get("document_date") or datetime.now(timezone.utc).date().isoformat(),
                "consultation_time": data.get("consultation_time", "") or data.get("time", ""),
                "time": data.get("consultation_time", "") or data.get("time", ""),
                "chief_complaint": data.get("chief_complaint", ""),
                "hpi": data.get("hpi", ""),
                "history_of_present_illness": data.get("hpi", ""),
                "vitals": vitals,
                "diagnosis_primary": data.get("diagnosis_primary", ""),
                "primary_diagnosis": data.get("diagnosis_primary", ""),
                "diagnosis_secondary": data.get("diagnosis_secondary", ""),
                "secondary_diagnosis": data.get("diagnosis_secondary", ""),
                "findings": data.get("findings", "") or data.get("clinical_examination_notes", ""),
                "clinical_examination_notes": data.get("findings", "") or data.get("clinical_examination_notes", ""),
                "treatment_plan": data.get("treatment_plan", ""),
                "recommendations": data.get("recommendations", "") or data.get("advice_instructions", "") or data.get("general_advice", ""),
                "advice_instructions": data.get("recommendations", "") or data.get("advice_instructions", "") or data.get("general_advice", ""),
                "follow_up": data.get("follow_up", "") or data.get("follow_up_date", ""),
                "follow_up_date": data.get("follow_up", "") or data.get("follow_up_date", ""),
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
                "prescription_date": data.get("document_date") or datetime.now(timezone.utc).date().isoformat(),
                "prescription_time": data.get("prescription_time", "") or data.get("time", ""),
                "time": data.get("prescription_time", "") or data.get("time", ""),
                "diagnosis": data.get("diagnosis", ""),
                "clinical_notes": data.get("clinical_notes", ""),
                "medicines": medicines,
                "general_advice": data.get("general_advice", ""),
                "follow_up": data.get("follow_up", ""),
                "is_draft": False
            }
            pdf_bytes = generate_prescription_pdf(doctor_data, patient_data, payload)"""

app_code = app_code.replace(old_preview_block, new_preview_block)

with open(app_path, "w", encoding="utf-8") as f:
    f.write(app_code)

print("Successfully updated app.py")
