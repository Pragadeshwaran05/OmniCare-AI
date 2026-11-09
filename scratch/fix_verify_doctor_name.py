import os

def main():
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        code = f.read()

    target = '''        # Create active 5-minute session in ExternalConsultationService

        session_rec = ExternalConsultationService.create_session(

            patient_id=str(resolved_pid),

            visitor_details={"full_name": "Attending Doctor", "role": "Doctor"},

            is_internal_doctor=True,

            doctor_id=str(doctor_id)

        )'''

    replacement = '''        # Resolve doctor name for session audit
        doctor_name = "Attending Doctor"
        try:
            doc_res = supabase_admin.table("doctors").select("full_name").eq("id", doctor_id).maybe_single().execute()
            if doc_res and doc_res.data and doc_res.data.get("full_name"):
                doctor_name = doc_res.data.get("full_name").strip()
        except Exception:
            pass

        # Create active 5-minute session in ExternalConsultationService
        session_rec = ExternalConsultationService.create_session(
            patient_id=str(resolved_pid),
            visitor_details={"full_name": doctor_name, "role": "Doctor"},
            is_internal_doctor=True,
            doctor_id=str(doctor_id)
        )'''

    code_norm = code.replace("\r\n", "\n")
    target_norm = target.replace("\r\n", "\n")
    replacement_norm = replacement.replace("\r\n", "\n")

    if target_norm in code_norm:
        new_code = code_norm.replace(target_norm, replacement_norm, 1)
        with open(app_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_code)
        print("SUCCESS: Target replaced in doctor_patient_verify_otp")
    else:
        print("FAILURE: Target not found in doctor_patient_verify_otp")

if __name__ == "__main__":
    main()
