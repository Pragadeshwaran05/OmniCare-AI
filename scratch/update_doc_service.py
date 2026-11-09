import re

doc_service_path = "services/medical_record_document_service.py"

with open(doc_service_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update doc_date and c_time in generate_consultation_pdf
code = code.replace(
    'doc_date = consultation_data.get("consultation_date") or datetime.now().strftime("%Y-%m-%d")',
    'doc_date = consultation_data.get("consultation_date") or consultation_data.get("date") or datetime.now().strftime("%Y-%m-%d")'
)
code = code.replace(
    'c_time = consultation_data.get("consultation_time") or ""',
    'c_time = consultation_data.get("consultation_time") or consultation_data.get("time") or ""'
)
code = code.replace(
    'hpi = consultation_data.get("history_of_present_illness") or ""',
    'hpi = consultation_data.get("history_of_present_illness") or consultation_data.get("hpi") or ""'
)

# 2. Update vitals extraction in generate_consultation_pdf
old_vitals_block = """    # Section 2: Clinical Examination & Vitals
    vitals = []
    if consultation_data.get("blood_pressure"):
        vitals.append(["Blood Pressure", f"{consultation_data['blood_pressure']} mmHg"])
    if consultation_data.get("pulse_rate"):
        vitals.append(["Pulse Rate", f"{consultation_data['pulse_rate']} bpm"])
    if consultation_data.get("temperature"):
        vitals.append(["Temperature", f"{consultation_data['temperature']} °F"])
    if consultation_data.get("respiratory_rate"):
        vitals.append(["Resp. Rate", f"{consultation_data['respiratory_rate']} /min"])
    if consultation_data.get("oxygen_saturation"):
        vitals.append(["SpO2", f"{consultation_data['oxygen_saturation']} %"])
    if consultation_data.get("weight"):
        vitals.append(["Weight", f"{consultation_data['weight']} kg"])
    if consultation_data.get("height"):
        vitals.append(["Height", f"{consultation_data['height']} cm"])

    exam_notes = consultation_data.get("clinical_examination_notes") or "" """

new_vitals_block = """    # Section 2: Clinical Examination & Vitals
    v_dict = consultation_data.get("vitals") if isinstance(consultation_data.get("vitals"), dict) else {}
    vitals = []
    bp = consultation_data.get("blood_pressure") or v_dict.get("bp")
    if bp:
        vitals.append(["Blood Pressure", f"{bp} mmHg"])
    pulse = consultation_data.get("pulse_rate") or v_dict.get("pulse")
    if pulse:
        vitals.append(["Pulse Rate", f"{pulse} bpm"])
    temp = consultation_data.get("temperature") or v_dict.get("temperature") or v_dict.get("temp")
    if temp:
        vitals.append(["Temperature", f"{temp} °F"])
    rr = consultation_data.get("respiratory_rate") or v_dict.get("respiratory_rate") or v_dict.get("rr")
    if rr:
        vitals.append(["Resp. Rate", f"{rr} /min"])
    spo2 = consultation_data.get("oxygen_saturation") or v_dict.get("oxygen_saturation") or v_dict.get("spo2")
    if spo2:
        vitals.append(["SpO2", f"{spo2} %"])
    weight = consultation_data.get("weight") or v_dict.get("weight")
    if weight:
        vitals.append(["Weight", f"{weight} kg"])
    height = consultation_data.get("height") or v_dict.get("height")
    if height:
        vitals.append(["Height", f"{height} cm"])

    exam_notes = consultation_data.get("clinical_examination_notes") or consultation_data.get("findings") or "" """

code = code.replace(old_vitals_block.strip(), new_vitals_block.strip())

# 3. Update diagnosis & treatment plan fallbacks in generate_consultation_pdf
code = code.replace(
    'primary_dx = consultation_data.get("primary_diagnosis") or "Clinical evaluation completed"',
    'primary_dx = consultation_data.get("primary_diagnosis") or consultation_data.get("diagnosis_primary") or "Clinical evaluation completed"'
)
code = code.replace(
    'secondary_dx = consultation_data.get("secondary_diagnosis") or ""',
    'secondary_dx = consultation_data.get("secondary_diagnosis") or consultation_data.get("diagnosis_secondary") or ""'
)
code = code.replace(
    'advice = consultation_data.get("advice_instructions") or ""',
    'advice = consultation_data.get("advice_instructions") or consultation_data.get("recommendations") or consultation_data.get("advice") or ""'
)
code = code.replace(
    'follow_up = consultation_data.get("follow_up_date") or ""',
    'follow_up = consultation_data.get("follow_up_date") or consultation_data.get("follow_up") or ""'
)

# 4. In generate_prescription_pdf, ensure date fallback
code = code.replace(
    'rx_date = prescription_data.get("prescription_date") or datetime.now().strftime("%Y-%m-%d")',
    'rx_date = prescription_data.get("prescription_date") or prescription_data.get("date") or datetime.now().strftime("%Y-%m-%d")'
)
code = code.replace(
    'rx_time = prescription_data.get("prescription_time") or ""',
    'rx_time = prescription_data.get("prescription_time") or prescription_data.get("time") or ""'
)

with open(doc_service_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Successfully updated services/medical_record_document_service.py")
