with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update doctor_view_medical_record access check
doc_view_target = """    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------

    if "doctor_id" not in session:

        print("❌ Doctor is not logged in")

        flash(
            "Please login as a doctor.",
            "error"
        )

        return redirect(
            url_for("doctor_login")
        )

    doctor_id = session["doctor_id"]

    print("Doctor ID :", doctor_id)
    print("Patient ID:", patient_id)
    print("Record ID :", record_id)


    try:

        # ----------------------------------------------------
        # 2. CHECK ACTIVE ACCESS
        # ----------------------------------------------------

        print("\\n[1] Checking doctor access...")

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

        print(
            "Active access records:",
            len(access_requests)
        )

        if not access_requests:

            print("❌ NO ACTIVE ACCESS")

            flash(
                "You do not have active access to this patient's medical records.",
                "error"
            )

            return redirect(
                url_for("doctor_my_patients")
            )

        access = access_requests[0]"""

doc_view_replacement = """    # --------------------------------------------------------
    # 1. CHECK AUTHORIZED WORKSPACE / RECORD ACCESS
    # --------------------------------------------------------
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        flash(err_msg or "You do not have active access to this patient's medical records.", "error")
        if "external_consultation" in session:
            return redirect(url_for("public_patient_info", patient_id=patient_id))
        return redirect(url_for("doctor_my_patients"))

    doctor_id = access_info.get("doctor_id", "EXTERNAL_CONSULTATION")
    access = access_info.get("access_record") or {"status": "active"}

    try:"""

assert doc_view_target in content, "doc_view_target not found"
content = content.replace(doc_view_target, doc_view_replacement, 1)

# 2. Update doctor_patient_trend_data
trend_target = """    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------
    if "doctor_id" not in session:
        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    doctor_id = session["doctor_id"]

    # Validate UUID format
    import uuid
    try:
        uuid.UUID(str(patient_id))
        uuid.UUID(str(doctor_id))
    except (ValueError, AttributeError):
        return {
            "success": False,
            "message": "Invalid patient or doctor identifier."
        }, 403

    try:
        # ----------------------------------------------------
        # 2. CHECK ACTIVE PATIENT ACCESS
        # ----------------------------------------------------
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
            return {
                "success": False,
                "message": "You do not have active access to this patient's records."
            }, 403"""

trend_replacement = """    # --------------------------------------------------------
    # 1. CHECK AUTHORIZED ACCESS (DOCTOR OR EXTERNAL CONSULTATION)
    # --------------------------------------------------------
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return {
            "success": False,
            "message": err_msg or "You do not have active access to this patient's records."
        }, 403

    doctor_id = access_info.get("doctor_id", "EXTERNAL_CONSULTATION")

    try:"""

assert trend_target in content, "trend_target not found"
content = content.replace(trend_target, trend_replacement, 1)

# 3. Update doctor_patient_ai_assistant
ai_asst_target = """    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------

    if "doctor_id" not in session:

        return {
            "success": False,
            "message": "Doctor login required."
        }, 401


    doctor_id = session["doctor_id"]


    try:

        # ----------------------------------------------------
        # 2. CHECK ACTIVE PATIENT ACCESS
        # ----------------------------------------------------

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )

        access_requests = (
            access_response.data or []
        )


        if not access_requests:

            return {
                "success": False,
                "message":
                    "You do not have active access "
                    "to this patient's records."
            }, 403"""

ai_asst_replacement = """    # --------------------------------------------------------
    # 1. CHECK AUTHORIZED ACCESS (DOCTOR OR EXTERNAL CONSULTATION)
    # --------------------------------------------------------
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return {
            "success": False,
            "message": err_msg or "You do not have active access to this patient's records."
        }, 403

    doctor_id = access_info.get("doctor_id", "EXTERNAL_CONSULTATION")

    try:"""

assert ai_asst_target in content, "ai_asst_target not found"
content = content.replace(ai_asst_target, ai_asst_replacement, 1)

# 4. Update doctor_patient_ai_sources
ai_src_target = """    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------

    if "doctor_id" not in session:

        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    doctor_id = session["doctor_id"]

    try:

        # ----------------------------------------------------
        # 2. VERIFY ACTIVE ACCESS
        # ----------------------------------------------------

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )

        access_requests = (
            access_response.data or []
        )

        if not access_requests:

            return {
                "success": False,
                "message": (
                    "You do not have active "
                    "access to this patient."
                )
            }, 403"""

ai_src_replacement = """    # --------------------------------------------------------
    # 1. CHECK AUTHORIZED ACCESS (DOCTOR OR EXTERNAL CONSULTATION)
    # --------------------------------------------------------
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return {
            "success": False,
            "message": err_msg or "You do not have active access to this patient."
        }, 403

    doctor_id = access_info.get("doctor_id", "EXTERNAL_CONSULTATION")

    try:"""

assert ai_src_target in content, "ai_src_target not found"
content = content.replace(ai_src_target, ai_src_replacement, 1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("All 4 workspace endpoints patched successfully!")
