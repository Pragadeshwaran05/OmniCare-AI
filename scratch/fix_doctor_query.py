import os
import sys

def main():
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Target snippet to find
    target = '''        # Get doctor name
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
                pass'''

    replacement = '''        # Get doctor name
        doctor_name = "Attending Doctor"
        try:
            doc_res = supabase_admin.table("doctors").select("full_name").eq("id", doctor_id).maybe_single().execute()
            if doc_res and doc_res.data and doc_res.data.get("full_name"):
                doctor_name = doc_res.data.get("full_name").strip()
        except Exception as e:
            print("Notice: Error fetching doctor full_name:", repr(e))

        # Resolve patient: support UUID, health_id, or QR token
        patient = None
        resolved_pid = patient_id
        token_rec = ExternalConsultationService.resolve_qr_token(patient_id)
        if token_rec and token_rec.get("patient_id"):
            resolved_pid = token_rec["patient_id"]

        try:
            pat_res = supabase_admin.table("patients").select("id, phone, email, full_name, health_id").eq("id", resolved_pid).maybe_single().execute()
            if pat_res and pat_res.data:
                patient = pat_res.data
        except Exception:
            pass

        if not patient:
            try:
                pat_res = supabase_admin.table("patients").select("id, phone, email, full_name, health_id").eq("health_id", patient_id).maybe_single().execute()
                if pat_res and pat_res.data:
                    patient = pat_res.data
            except Exception:
                pass'''

    code_norm = code.replace("\r\n", "\n")
    target_norm = target.replace("\r\n", "\n")
    replacement_norm = replacement.replace("\r\n", "\n")

    if target_norm in code_norm:
        new_code = code_norm.replace(target_norm, replacement_norm, 1)
        with open(app_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_code)
        print("SUCCESS: Target replaced in app.py")
    else:
        print("FAILURE: Target not found in code_norm")

if __name__ == "__main__":
    main()
