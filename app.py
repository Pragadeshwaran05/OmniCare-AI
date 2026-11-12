import utils.network_config  # Prioritize IPv4 on Windows
from services.doctor_ai_assistant import ask_doctor_ai
from services.medical_document_processor import process_medical_document
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, Response
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
from dotenv import load_dotenv
from utils.supabase_client import supabase
from services.medical_record_document_service import (
    save_patient_medical_record,
    generate_consultation_pdf,
    generate_prescription_pdf,
    generate_other_document_pdf
)
from services.medical_conflict_detector import detect_medical_conflicts
from services.health_trend_analyzer import get_trend_analysis_data
from services.clinical_copilot_service import (
    get_clinical_briefing,
    get_authorized_patient_scope,
    record_alert_review,
)
from services.clinical_query_service import execute_clinical_query
from services.clinical_audit_service import (
    get_doctor_audit_logs,
    log_clinical_event,
    log_audit_event,
    query_doctor_audit_logs,
    get_audit_log_by_id,
    get_doctor_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    ACTION_LABELS,
)
from services.doctor_profile_service import (
    get_doctor_profile,
    update_doctor_profile,
    upload_doctor_photo,
    delete_doctor_photo,
    get_working_preferences,
    update_working_preferences,
    list_doctor_documents,
    upload_doctor_document,
    get_document_for_doctor,
    delete_doctor_document,
    change_doctor_password,
    get_active_sessions_info,
    get_two_factor_status,
)
from services.msg91_otp_service import MSG91OTPService, mask_phone_number, mask_email_address, is_dev_mode
from services.external_consultation_service import ExternalConsultationService
from services.doctor_settings_service import (
    get_doctor_settings,
    update_doctor_settings,
    check_connected_services_status,
    export_doctor_data,
    deactivate_doctor_account,
)
import os
import httpx
import qrcode
import io
import base64

import uuid

# ---------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------
# FLASK APP
# ---------------------------------------------------------

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "temporary-development-secret"
)

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
print("URL loaded:", bool(SUPABASE_URL))
print("KEY loaded:", bool(SUPABASE_KEY))
# Normal Supabase client
supabase_admin: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# Use HTTP/1.1 transport to prevent HTTP/2 Windows socket EOF drops
if hasattr(supabase_admin, "postgrest") and hasattr(supabase_admin.postgrest, "base_url"):
    supabase_admin.postgrest.session = httpx.Client(
        base_url=str(supabase_admin.postgrest.base_url),
        headers=supabase_admin.postgrest.headers,
        timeout=supabase_admin.postgrest.timeout,
        follow_redirects=True,
        http2=False
    )

# Admin / service-role client

# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------------------------
# PATIENT REGISTER
# ---------------------------------------------------------

@app.route("/patient/register", methods=["GET", "POST"])
def patient_register():

    if request.method == "POST":

        # Get form data
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        date_of_birth = request.form.get("date_of_birth", "")
        blood_group = request.form.get("blood_group", "")
        gender = request.form.get("gender", "")
        address = request.form.get("address", "").strip()

        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not all([
            full_name,
            email,
            phone,
            date_of_birth,
            blood_group,
            gender,
            address,
            password,
            confirm_password
        ]):
            flash(
                "Please fill in all required fields.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        # Check password
        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        # Minimum password length
        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        # -------------------------------------------------
        # CHECK WHETHER EMAIL ALREADY EXISTS
        # -------------------------------------------------

        try:

            existing_patient = (
                supabase
                .table("patients")
                .select("id")
                .eq("email", email)
                .execute()
            )


            if existing_patient.data:

                flash(
                    "An account with this email already exists.",
                    "error"
                )

                return render_template(
                    "auth/patient_register.html"
                )


        except Exception as e:

            print("Email check error:", e)

            flash(
                "Unable to check your account. Please try again.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        # -------------------------------------------------
        # HASH PASSWORD
        # -------------------------------------------------

        password_hash = generate_password_hash(password)


        # -------------------------------------------------
        # INSERT PATIENT
        # -------------------------------------------------

        patient_data = {

            "full_name": full_name,

            "email": email,

            "phone": phone,

            "date_of_birth": date_of_birth,

            "blood_group": blood_group,

            "gender": gender,

            "address": address,

            "password_hash": password_hash
        }


        try:

            response = (
                supabase
                .table("patients")
                .insert(patient_data)
                .execute()
            )


            if response.data:

                flash(
                    "Registration successful! Please login.",
                    "success"
                )

                return redirect(
                    url_for("patient_login")
                )


            flash(
                "Registration failed. Please try again.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


        except Exception as e:

            print("Registration error:", e)

            flash(
                "Something went wrong while creating your account.",
                "error"
            )

            return render_template(
                "auth/patient_register.html"
            )


    # GET request
    return render_template(
        "auth/patient_register.html"
    )


# ---------------------------------------------------------
# PATIENT LOGIN
# ---------------------------------------------------------

@app.route("/patient/login", methods=["GET", "POST"])
def patient_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "error"
            )

            return render_template(
                "auth/patient_login.html"
            )


        # -------------------------------------------------
        # FIND PATIENT
        # -------------------------------------------------

        try:

            response = (
                supabase
                .table("patients")
                .select("*")
                .eq("email", email)
                .limit(1)
                .execute()
            )


            if not response.data:

                flash(
                    "Invalid email or password.",
                    "error"
                )

                return render_template(
                    "auth/patient_login.html"
                )


            patient = response.data[0]


        except Exception as e:

            print("Login database error:", e)

            flash(
                "Unable to login right now. Please try again.",
                "error"
            )

            return render_template(
                "auth/patient_login.html"
            )


        # -------------------------------------------------
        # CHECK PASSWORD
        # -------------------------------------------------

        if not check_password_hash(
            patient["password_hash"],
            password
        ):

            flash(
                "Invalid email or password.",
                "error"
            )

            return render_template(
                "auth/patient_login.html"
            )


        # -------------------------------------------------
        # CREATE SESSION
        # -------------------------------------------------

        session["patient_id"] = patient["id"]

        session["patient_name"] = patient["full_name"]

        session["patient_email"] = patient["email"]


        flash(
            "Login successful!",
            "success"
        )


        return redirect(
            url_for("patient_dashboard")
        )


    # GET request
    return render_template(
        "auth/patient_login.html"
    )


# ---------------------------------------------------------
# PATIENT DASHBOARD
# ---------------------------------------------------------

@app.route("/patient/dashboard")
def patient_dashboard():

    # Check login
    if "patient_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("patient_login")
        )


    # Get current patient
    try:

        response = (
            supabase
            .table("patients")
            .select(
                "id, full_name, email, phone, "
                "date_of_birth, blood_group, "
                "gender, address, created_at"
            )
            .eq("id", session["patient_id"])
            .limit(1)
            .execute()
        )


        if not response.data:

            session.clear()

            flash(
                "Patient account not found.",
                "error"
            )

            return redirect(
                url_for("patient_login")
            )


        patient = response.data[0]


    except Exception as e:

        print("Dashboard error:", e)

        flash(
            "Unable to load your profile.",
            "error"
        )

        return redirect(
            url_for("patient_login")
        )


    return render_template(
        "patient/dashboard.html",
        patient=patient
    )


# ---------------------------------------------------------
# PATIENT LOGOUT
# ---------------------------------------------------------

@app.route("/patient/logout")
def patient_logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )

# ==========================================
# PATIENT PAGES
# ==========================================



@app.route("/patient/access-requests")
def patient_access_requests():

    if "patient_id" not in session:
        flash("Please login to access your account.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # =====================================================
        # 1. GET ACCESS REQUESTS FOR THIS PATIENT
        # =====================================================

        response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .order("requested_at", desc=True)
            .execute()
        )

        access_requests = response.data or []

        # =====================================================
        # 2. GET ALL DOCTOR IDs
        # =====================================================

        doctor_ids = list({
            access.get("doctor_id")
            for access in access_requests
            if access.get("doctor_id")
        })

        doctors_map = {}

        # =====================================================
        # 3. GET DOCTOR DETAILS
        # =====================================================

        if doctor_ids:

            doctor_response = (
                supabase_admin
                .table("doctors")
                .select("*")
                .in_("id", doctor_ids)
                .execute()
            )

            for doctor in doctor_response.data or []:
                doctors_map[str(doctor["id"])] = doctor

        # =====================================================
        # 4. ADD DOCTOR / HOSPITAL INFORMATION
        # =====================================================

        for access in access_requests:

            doctor = doctors_map.get(
                str(access.get("doctor_id"))
            )

            if doctor:

                # Doctor name
                access["doctor_name"] = (
                    doctor.get("full_name")
                    or doctor.get("name")
                    or doctor.get("doctor_name")
                    or "Doctor"
                )

                # Hospital name
                access["hospital_name"] = (
                    doctor.get("hospital_name")
                    or doctor.get("hospital")
                    or doctor.get("clinic_name")
                    or "Not provided"
                )

                # Hospital address
                access["hospital_address"] = (
                    doctor.get("hospital_address")
                    or doctor.get("address")
                    or doctor.get("clinic_address")
                    or "Not provided"
                )

            else:

                access["doctor_name"] = "Doctor"
                access["hospital_name"] = "Not provided"
                access["hospital_address"] = "Not provided"

            # =================================================
            # 5. FORMAT REQUESTED DATE
            # =================================================

            requested_at = access.get("requested_at")

            if requested_at:

                try:

                    from datetime import datetime

                    dt = datetime.fromisoformat(
                        requested_at.replace("Z", "+00:00")
                    )

                    access["requested_at_display"] = dt.strftime(
                        "%d %b %Y, %I:%M %p"
                    )

                except Exception:

                    access["requested_at_display"] = requested_at

            else:

                access["requested_at_display"] = "Not available"

            # =================================================
            # 6. FORMAT APPROVED DATE
            # =================================================

            approved_at = access.get("approved_at")

            if approved_at:

                try:

                    from datetime import datetime

                    dt = datetime.fromisoformat(
                        approved_at.replace("Z", "+00:00")
                    )

                    access["approved_at_display"] = dt.strftime(
                        "%d %b %Y, %I:%M %p"
                    )

                except Exception:

                    access["approved_at_display"] = approved_at

            else:

                access["approved_at_display"] = None

            # =================================================
            # 7. FORMAT EXPIRY DATE
            # =================================================

            expires_at = access.get("expires_at")

            if expires_at:

                try:

                    from datetime import datetime

                    dt = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )

                    access["expires_at_display"] = dt.strftime(
                        "%d %b %Y, %I:%M %p"
                    )

                except Exception:

                    access["expires_at_display"] = expires_at

            else:

                access["expires_at_display"] = None

        # =====================================================
        # DEBUG
        # =====================================================

        print("=" * 70)
        print("PATIENT ACCESS REQUESTS")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Total Requests:", len(access_requests))

        for access in access_requests:

            print(
                "Doctor:",
                access.get("doctor_name")
            )

            print(
                "Hospital:",
                access.get("hospital_name")
            )

            print(
                "Address:",
                access.get("hospital_address")
            )

            print(
                "Status:",
                access.get("status")
            )

            print(
                "Access Type:",
                access.get("access_type")
            )

            print("-" * 70)

        # =====================================================
        # 8. SEND DATA TO TEMPLATE
        # =====================================================

        active_consultations = ExternalConsultationService.get_active_sessions_for_patient(patient_id)
        return render_template(
            "patient/access_requests.html",
            access_requests=access_requests,
            active_consultations=active_consultations
        )

    except Exception as e:

        print("=" * 70)
        print("PATIENT ACCESS REQUESTS ERROR")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 70)

        return render_template(
            "patient/access_requests.html",
            access_requests=[],
            error="Unable to load access requests."
        )
@app.route("/patient/approve-access/<request_id>", methods=["POST"])
def patient_approve_access(request_id):

    if "patient_id" not in session:
        flash("Please login to continue.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    # Get selected access type
    access_type = request.form.get("access_type", "temporary").strip().lower()

    # Allow only these values
    allowed_types = {
        "one_time",
        "temporary",
        "permanent"
    }

    if access_type not in allowed_types:
        flash("Invalid access type selected.", "error")
        return redirect(url_for("patient_access_requests"))

    try:

        # -----------------------------------------------------
        # 1. CHECK REQUEST BELONGS TO THIS PATIENT
        # -----------------------------------------------------

        existing = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .eq("status", "pending")
            .execute()
        )

        if not existing.data:
            flash(
                "Access request not found.",
                "error"
            )
            return redirect(
                url_for("patient_access_requests")
            )

        # -----------------------------------------------------
        # 2. CURRENT TIME
        # -----------------------------------------------------

        now = datetime.now(timezone.utc)

        # -----------------------------------------------------
        # 3. SET EXPIRATION
        # -----------------------------------------------------

        expires_at = None

        if access_type == "temporary":

            # Temporary access = 4 hours
            expires_at = (
                now + timedelta(hours=4)
            ).isoformat()

        elif access_type == "one_time":

            # One-time access
            # No fixed time expiration.
            # It will be revoked after the consultation/action
            # is completed.
            expires_at = None

        elif access_type == "permanent":

            # Permanent access
            # No expiration unless patient revokes it.
            expires_at = None

        # -----------------------------------------------------
        # 4. UPDATE ACCESS REQUEST
        # -----------------------------------------------------

        update_data = {
            "status": "active",
            "access_type": access_type,
            "approved_at": now.isoformat(),
            "expires_at": expires_at
        }

        response = (
            supabase_admin
            .table("access_requests")
            .update(update_data)
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .execute()
        )

        try:
            req_doc_id = existing.data[0].get("doctor_id")
            if req_doc_id:
                log_audit_event(
                    doctor_id=req_doc_id,
                    action="PATIENT_ACCESS_GRANTED",
                    patient_ids=[patient_id],
                    status="SUCCESS",
                    metadata={"request_id": request_id, "access_type": access_type},
                    client_ip=request.remote_addr
                )
        except Exception as audit_err:
            print("Audit log error on approve access:", repr(audit_err))

        # -----------------------------------------------------
        # 5. SUCCESS MESSAGE
        # -----------------------------------------------------

        if access_type == "temporary":

            flash(
                "Access granted for 4 hours.",
                "success"
            )

        elif access_type == "one_time":

            flash(
                "One-time access granted to the doctor.",
                "success"
            )

        elif access_type == "permanent":

            flash(
                "Permanent access granted to the doctor.",
                "success"
            )

    except Exception as e:

        print("=" * 70)
        print("APPROVE ACCESS ERROR")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Request ID:", request_id)
        print("Access Type:", access_type)
        print("Error:", repr(e))
        print("=" * 70)

        flash(
            "Unable to approve the access request.",
            "error"
        )

    return redirect(
        url_for("patient_access_requests")
    )
@app.route("/patient/reject-access/<request_id>", methods=["POST"])
def patient_reject_access(request_id):

    if "patient_id" not in session:
        flash("Please login to continue.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:
        # Make sure this request belongs to the logged-in patient
        existing = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .eq("status", "pending")
            .execute()
        )

        if not existing.data:
            flash("Access request not found.", "error")
            return redirect(url_for("patient_access_requests"))

        # Reject the request
        response = (
            supabase_admin
            .table("access_requests")
            .update({
                "status": "rejected"
            })
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .execute()
        )

        flash(
            "Access request rejected.",
            "success"
        )

    except Exception as e:
        print("REJECT ACCESS ERROR:", repr(e))

        flash(
            "Unable to reject the access request.",
            "error"
        )

    return redirect(url_for("patient_access_requests"))

@app.route("/patient/revoke-access/<request_id>", methods=["POST"])
def patient_revoke_access(request_id):

    if "patient_id" not in session:
        flash("Please login to continue.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # ---------------------------------------------------------
        # Verify that this access request belongs to this patient
        # and is currently active
        # ---------------------------------------------------------

        existing = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .eq("status", "active")
            .execute()
        )

        if not existing.data:

            flash(
                "Active access request not found.",
                "error"
            )

            return redirect(
                url_for("patient_doctor_access")
            )


        # ---------------------------------------------------------
        # Revoke access
        # ---------------------------------------------------------

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        (
            supabase_admin
            .table("access_requests")
            .update({
                "status": "revoked",
                "revoked_at": now.isoformat()
            })
            .eq("id", request_id)
            .eq("patient_id", patient_id)
            .execute()
        )

        try:
            req_doc_id = existing.data[0].get("doctor_id")
            if req_doc_id:
                log_audit_event(
                    doctor_id=req_doc_id,
                    action="PATIENT_ACCESS_REVOKED",
                    patient_ids=[patient_id],
                    status="SUCCESS",
                    metadata={"request_id": request_id},
                    client_ip=request.remote_addr
                )
        except Exception as audit_err:
            print("Audit log error on revoke access:", repr(audit_err))


        flash(
            "Doctor access has been revoked successfully.",
            "success"
        )


    except Exception as e:

        print("=" * 60)
        print("REVOKE ACCESS ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Request ID:", request_id)
        print("Error:", repr(e))
        print("=" * 60)

        flash(
            "Unable to revoke doctor access.",
            "error"
        )


    return redirect(
        url_for("patient_doctor_access")
    )
# ==========================================
# PATIENT - HEALTH TIMELINE
# ==========================================

@app.route("/patient/health-timeline")
def health_timeline():

    # Require patient login
    if "patient_id" not in session:
        flash("Please login to view your health timeline.", "error")
        return redirect(url_for("patient_login"))

    # Always use the logged-in patient's ID
    patient_id = session["patient_id"]

    try:
        response = (
            supabase_admin
            .table("health_timeline_events")
            .select(
                "id, patient_id, medical_record_id, event_date, "
                "event_type, provider_name, hospital_name, "
                "diagnosis, clinical_findings, investigations, "
                "medications, follow_up, clinical_summary, "
                "ai_processed"
            )
            .eq("patient_id", patient_id)
            .order("event_date", desc=True)
            .execute()
        )

        timeline_events = response.data or []

        return render_template(
            "patient/patient_health_timeline.html",
            timeline_events=timeline_events
        )

    except Exception as e:
        print("PATIENT HEALTH TIMELINE ERROR:", str(e))

        flash(
            "Unable to load your health timeline. Please try again.",
            "error"
        )

        return render_template(
            "patient/patient_health_timeline.html",
            timeline_events=[],
            timeline_error=True
        )

@app.route("/patient/doctor-access")
def patient_doctor_access():

    if "patient_id" not in session:
        flash("Please login to continue.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # =====================================================
        # 1. GET ACCESS REQUESTS
        # =====================================================

        response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .order("requested_at", desc=True)
            .execute()
        )

        access_requests = response.data or []

        print("\n" + "=" * 70)
        print("PATIENT ACCESS REQUESTS")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Access Requests:")
        print(access_requests)


        # =====================================================
        # 2. GET DOCTOR IDS
        # =====================================================

        doctor_ids = []

        for access in access_requests:

            doctor_id = access.get("doctor_id")

            if doctor_id:
                doctor_ids.append(str(doctor_id))

        doctor_ids = list(set(doctor_ids))

        print("Doctor IDs:", doctor_ids)


        # =====================================================
        # 3. GET DOCTORS
        # =====================================================

        doctors_map = {}

        if doctor_ids:

            # First try normal "id" column
            doctor_response = (
                supabase_admin
                .table("doctors")
                .select("*")
                .in_("id", doctor_ids)
                .execute()
            )

            doctors = doctor_response.data or []

            print("Doctors found using id:", doctors)

            for doctor in doctors:

                doctor_id = doctor.get("id")

                if doctor_id:
                    doctors_map[str(doctor_id)] = doctor


        # =====================================================
        # 4. ADD DISPLAY INFORMATION
        # =====================================================

        for access in access_requests:

            doctor_id = access.get("doctor_id")

            doctor = doctors_map.get(
                str(doctor_id)
            )


            # -------------------------------------------------
            # DEFAULT VALUES
            # -------------------------------------------------

            access["doctor_name"] = "Doctor"
            access["hospital_name"] = "Not provided"
            access["hospital_address"] = "Not provided"


            # -------------------------------------------------
            # DOCTOR FOUND
            # -------------------------------------------------

            if doctor:

                access["doctor_name"] = (
                    doctor.get("full_name")
                    or doctor.get("doctor_name")
                    or doctor.get("name")
                    or "Doctor"
                )

                access["hospital_name"] = (
                    doctor.get("hospital_name")
                    or doctor.get("hospital")
                    or doctor.get("clinic_name")
                    or "Not provided"
                )

                access["hospital_address"] = (
                    doctor.get("hospital_address")
                    or doctor.get("address")
                    or doctor.get("clinic_address")
                    or "Not provided"
                )


            # =================================================
            # 5. REQUESTED DATE
            # =================================================

            requested_at = access.get("requested_at")

            print("Requested At:", requested_at)

            if requested_at:

                try:

                    dt = datetime.fromisoformat(
                        str(requested_at).replace(
                            "Z",
                            "+00:00"
                        )
                    )

                    access["requested_at_display"] = dt.strftime(
                        "%d %b %Y, %I:%M %p"
                    )

                except Exception as date_error:

                    print(
                        "DATE FORMAT ERROR:",
                        repr(date_error)
                    )

                    access["requested_at_display"] = str(
                        requested_at
                    )

            else:

                access["requested_at_display"] = "Not available"


            # =================================================
            # 6. DEBUG
            # =================================================

            print("----------------------------------------")
            print("Request ID:", access.get("id"))
            print("Doctor ID:", access.get("doctor_id"))
            print("Doctor Name:", access.get("doctor_name"))
            print("Hospital:", access.get("hospital_name"))
            print(
                "Hospital Address:",
                access.get("hospital_address")
            )
            print(
                "Requested:",
                access.get("requested_at_display")
            )
            print("Status:", access.get("status"))
            print(
                "Access Type:",
                access.get("access_type")
            )


        print("=" * 70)


        # =====================================================
        # 7. RENDER
        # =====================================================

        active_consultations = ExternalConsultationService.get_active_sessions_for_patient(patient_id)
        return render_template(
            "patient/access_requests.html",
            access_requests=access_requests,
            active_consultations=active_consultations
        )


    except Exception as e:

        print("\n" + "=" * 70)
        print("PATIENT DOCTOR ACCESS ERROR")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 70)

        return render_template(
            "patient/access_requests.html",
            access_requests=[],
            error="Unable to load access requests."
        )


from datetime import date

from datetime import date


@app.route("/patient/profile", methods=["GET", "POST"])
def patient_profile():

    # 1. Require patient login
    if "patient_id" not in session:
        flash("Please login to access your profile.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:
        # 2. Load this patient's existing personal information
        patient_response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .limit(1)
            .execute()
        )

        if not patient_response.data:
            flash("Patient account not found.", "error")
            return redirect(url_for("patient_login"))

        patient = patient_response.data[0]

        # 3. Load this patient's emergency profile
        emergency_response = (
            supabase_admin
            .table("patient_emergency_profiles")
            .select("*")
            .eq("patient_id", patient_id)
            .limit(1)
            .execute()
        )

        emergency_profile = (
            emergency_response.data[0]
            if emergency_response.data
            else {}
        )

        if request.method == "POST":

            # 4. Validate personal details
            full_name = request.form.get("name", "").strip()
            dob = request.form.get("date_of_birth", "").strip()
            gender = request.form.get("gender", "").strip()
            blood_group = request.form.get("blood_group", "").strip()
            phone = request.form.get("phone", "").strip()
            email = request.form.get("email", "").strip().lower()
            address = request.form.get("address", "").strip()

            if not full_name:
                flash("Full name is required.", "error")
                return redirect(url_for("patient_profile"))

            if dob:
                try:
                    parsed_dob = date.fromisoformat(dob)
                    if parsed_dob > date.today():
                        raise ValueError
                except ValueError:
                    flash("Enter a valid date of birth.", "error")
                    return redirect(url_for("patient_profile"))

            # 5. Update existing patients table
            personal_data = {
                "full_name": full_name,
                "date_of_birth": dob or None,
                "gender": gender or None,
                "blood_group": blood_group or None,
                "phone": phone or None,
                "email": email or None,
                "address": address or None
            }

            # 6. Collect emergency and medical information
            def form_text(field_name):
                return request.form.get(field_name, "").strip() or None

            height_text = form_text("height_cm")
            weight_text = form_text("weight_kg")

            try:
                height_cm = float(height_text) if height_text else None
                weight_kg = float(weight_text) if weight_text else None

                if height_cm is not None and not 1 <= height_cm <= 300:
                    raise ValueError("Height must be between 1 and 300 cm.")

                if weight_kg is not None and not 1 <= weight_kg <= 700:
                    raise ValueError("Weight must be between 1 and 700 kg.")

            except ValueError:
                flash("Enter valid height and weight values.", "error")
                return redirect(url_for("patient_profile"))

            emergency_data = {
                "patient_id": patient_id,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "allergies": form_text("allergies"),
                "chronic_conditions": form_text("chronic_conditions"),
                "current_medications": form_text("current_medications"),
                "emergency_contact_name": form_text("emergency_contact_name"),
                "emergency_relationship": form_text("emergency_relationship"),
                "emergency_contact_phone": form_text("emergency_contact_phone"),
                "alternate_contact_phone": form_text("alternate_contact_phone"),
                "emergency_address": form_text("emergency_address"),
                "emergency_notes": form_text("emergency_notes"),
                "updated_at": date.today().isoformat()
            }

            try:
                # Update only the logged-in patient's row.
                (
                    supabase_admin
                    .table("patients")
                    .update(personal_data)
                    .eq("id", patient_id)
                    .execute()
                )

                # Insert or update this patient's emergency profile.
                (
                    supabase_admin
                    .table("patient_emergency_profiles")
                    .upsert(
                        emergency_data,
                        on_conflict="patient_id"
                    )
                    .execute()
                )

                flash("Profile and emergency information saved.", "success")
                return redirect(url_for("patient_profile"))

            except Exception as save_error:
                print("PATIENT PROFILE SAVE ERROR:", repr(save_error))
                flash("Unable to save profile. Please try again.", "error")
                return redirect(url_for("patient_profile"))

        # 7. Combine the two records for the template.
        # Keep both name keys for compatibility with existing HTML.
        patient["name"] = patient.get("full_name", "")
        patient.update(emergency_profile)

        # Use the ISO date format expected by <input type="date">.
        if patient.get("date_of_birth"):
            patient["date_of_birth"] = str(
                patient["date_of_birth"]
            )[:10]

        return render_template(
            "patient/patient_profile.html",
            patient=patient,
            today=date.today().isoformat()
        )

    except Exception as error:
        print("PATIENT PROFILE ERROR:", repr(error))
        flash("Unable to load your profile information.", "error")
        return redirect(url_for("patient_dashboard"))







# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("patient_login"))


# =========================================================
# PATIENT - UPLOAD MEDICAL RECORD
# =========================================================
@app.route("/patient/upload-records", methods=["GET", "POST"])
def patient_upload_records():

    if "patient_id" not in session:
        flash("Please login to access your health records.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    # =========================
    # GET → SHOW UPLOAD PAGE
    # =========================
    if request.method == "GET":
        return render_template(
            "patient/patient_upload_records.html"
        )

    # =========================
    # POST → PROCESS UPLOAD
    # =========================

    record_type = request.form.get("record_type", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    uploaded_file = request.files.get("medical_file")

    # =========================
    # VALIDATION
    # =========================

    if not record_type:
        flash("Please select the record type.", "error")
        return redirect(url_for("patient_upload_records"))

    if not title:
        flash("Please enter a record title.", "error")
        return redirect(url_for("patient_upload_records"))

    if not uploaded_file or uploaded_file.filename == "":
        flash("Please select a medical file.", "error")
        return redirect(url_for("patient_upload_records"))

    # =========================
    # ALLOWED EXTENSIONS
    # =========================

    allowed_extensions = {
        "pdf", "png", "jpg", "jpeg", "webp"
    }

    original_filename = uploaded_file.filename

    extension = (
        original_filename.rsplit(".", 1)[-1].lower()
    )

    if extension not in allowed_extensions:
        flash(
            "Only PDF, PNG, JPG, JPEG and WEBP files are allowed.",
            "error"
        )
        return redirect(url_for("patient_upload_records"))

    # =========================
    # PATIENT-SPECIFIC PATH
    # =========================

    unique_name = secrets.token_hex(16) + "." + extension

    storage_path = f"{patient_id}/{unique_name}"

    try:

        # =====================================================
        # 1. READ ORIGINAL FILE
        # =====================================================

        file_bytes = uploaded_file.read()

        if not file_bytes:
            flash("The uploaded file is empty.", "error")
            return redirect(
                url_for("patient_upload_records")
            )

        content_type = (
            uploaded_file.content_type
            or "application/octet-stream"
        )

        # =====================================================
        # 2. UPLOAD ORIGINAL FILE TO SUPABASE STORAGE
        # =====================================================

        storage_response = (
            supabase_admin
            .storage
            .from_("medical-records")
            .upload(
                storage_path,
                file_bytes,
                {
                    "content-type": content_type
                }
            )
        )

        print("Storage upload:", storage_response)

        # =====================================================
        # 3. SAVE ORIGINAL RECORD TO DATABASE
        # =====================================================

        record_data = {
            "patient_id": patient_id,
            "record_type": record_type,
            "title": title,
            "description": description,
            "file_name": original_filename,
            "file_path": storage_path,
            "file_url": None
        }

        db_response = (
            supabase_admin
            .table("medical_records")
            .insert(record_data)
            .execute()
        )

        # =====================================================
        # 4. CHECK DATABASE SAVE
        # =====================================================

        if not db_response.data:

            try:
                (
                    supabase_admin
                    .storage
                    .from_("medical-records")
                    .remove([storage_path])
                )
            except Exception:
                pass

            flash(
                "Record could not be saved.",
                "error"
            )

            return redirect(
                url_for("patient_upload_records")
            )

        # =====================================================
        # 5. GET MEDICAL RECORD ID
        # =====================================================

        medical_record = db_response.data[0]

        medical_record_id = medical_record.get("id")

        if not medical_record_id:

            print("WARNING: Medical record ID was not returned.")

            flash(
                "Record was uploaded, but its ID could not be determined.",
                "error"
            )

            return redirect(
                url_for("patient_health_records")
            )

        print("=" * 70)
        print("MEDICAL RECORD SAVED")
        print("=" * 70)
        print("Patient ID:", patient_id)
        print("Medical Record ID:", medical_record_id)
        print("File:", original_filename)
        print("=" * 70)

        # =====================================================
        # 6. AI MEDICAL DOCUMENT PROCESSING
        # =====================================================

        try:

            print("=" * 70)
            print("STARTING AI MEDICAL DOCUMENT PROCESSING")
            print("=" * 70)

            extracted_data = process_medical_document(
                file_bytes=file_bytes,
                filename=original_filename,
                content_type=content_type
            )

            print("AI EXTRACTION RESULT:")
            print(extracted_data)

            # =================================================
            # 7. SAVE AI RESULT TO HEALTH TIMELINE
            # =================================================

            timeline_data = {
                "patient_id": patient_id,
                "medical_record_id": medical_record_id,

                "event_date": extracted_data.get(
                    "event_date"
                ),

                "event_type": extracted_data.get(
                    "event_type",
                    "other"
                ),

                "provider_name": extracted_data.get(
                    "provider_name"
                ),

                "hospital_name": extracted_data.get(
                    "hospital_name"
                ),

                "diagnosis": extracted_data.get(
                    "diagnosis"
                ),

                "clinical_findings": extracted_data.get(
                    "clinical_findings"
                ),

                "investigations": extracted_data.get(
                    "investigations",
                    []
                ),

                "medications": extracted_data.get(
                    "medications",
                    []
                ),

                "follow_up": extracted_data.get(
                    "follow_up"
                ),

                "clinical_summary": extracted_data.get(
                    "clinical_summary"
                ),

                "ai_processed": True
            }

            timeline_response = (
                supabase_admin
                .table("health_timeline_events")
                .insert(timeline_data)
                .execute()
            )

            if timeline_response.data:

                print("=" * 70)
                print("AI TIMELINE EVENT CREATED")
                print("=" * 70)
                print(
                    "Timeline Event ID:",
                    timeline_response.data[0].get("id")
                )
                print("Patient ID:", patient_id)
                print(
                    "Medical Record ID:",
                    medical_record_id
                )
                print("=" * 70)

            else:

                print(
                    "WARNING: AI extraction succeeded, "
                    "but timeline event was not saved."
                )

        except Exception as ai_error:

            # =================================================
            # AI FAILURE SHOULD NOT DELETE ORIGINAL RECORD
            # =================================================

            print("=" * 70)
            print("AI MEDICAL PROCESSING ERROR")
            print("=" * 70)
            print("Patient ID:", patient_id)
            print(
                "Medical Record ID:",
                medical_record_id
            )
            print(
                "File:",
                original_filename
            )
            print(
                "AI Error:",
                repr(ai_error)
            )
            print("=" * 70)

            # Original medical record is still safely stored.
            # AI can be processed again later.

        # =====================================================
        # 8. SUCCESS
        # =====================================================

        flash(
            "Medical record uploaded successfully!",
            "success"
        )

        return redirect(
            url_for("patient_health_records")
        )

    except Exception as e:

        print("=" * 60)
        print("UPLOAD RECORD ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 60)

        flash(
            f"Upload failed: {str(e)}",
            "error"
        )

        return redirect(
            url_for("patient_upload_records")
        )


# =========================================================
# PATIENT - MY HEALTH RECORDS
# =========================================================

@app.route("/patient/records")
def patient_records():

    # Make sure patient is logged in
    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:
        # Fetch ONLY this patient's records
        response = (
            supabase
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("created_at", desc=True)
            .execute()
        )

        records = response.data or []

        return render_template(
            "patient/patient_records.html",
            records=records
        )

    except Exception as e:

        print("Error loading patient records:", e)

        flash(
            "Unable to load your health records.",
            "error"
        )

        return render_template(
            "patient/patient_records.html",
            records=[]
        )

@app.route("/patient/health-records")
def patient_health_records():

    # -----------------------------------------------------
    # CHECK PATIENT LOGIN
    # -----------------------------------------------------

    if "patient_id" not in session:
        flash("Please login to access your health records.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # -------------------------------------------------
        # FETCH ONLY THIS PATIENT'S RECORDS
        # -------------------------------------------------

        response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("id", desc=True)
            .execute()
        )

        records = response.data or []

        # -------------------------------------------------
        # CREATE SIGNED URL FOR EACH FILE
        # -------------------------------------------------

        for record in records:

            file_path = record.get("file_path")

            if file_path:

                try:

                    signed_response = (
                        supabase_admin
                        .storage
                        .from_("medical-records")
                        .create_signed_url(
                            file_path,
                            3600
                        )
                    )

                    # Supabase response
                    if signed_response:

                        record["file_url"] = (
                            signed_response.get("signedURL")
                            or signed_response.get("signedUrl")
                        )

                except Exception as url_error:

                    print(
                        "Signed URL error:",
                        repr(url_error)
                    )

                    record["file_url"] = None

        # -------------------------------------------------
        # DISPLAY RECORDS
        # -------------------------------------------------

        return render_template(
            "patient/patient_health_records.html",
            records=records
        )

    except Exception as e:

        print("=" * 60)
        print("HEALTH RECORDS ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 60)

        return render_template(
            "patient/patient_health_records.html",
            records=[],
            error="Unable to load your health records."
        )

@app.route("/doctor/register", methods=["GET", "POST"])
def doctor_register():

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        medical_registration_number = request.form.get("medical_registration_number", "").strip()
        specialization = request.form.get("specialization", "").strip()
        hospital_name = request.form.get("hospital_name", "").strip()
        hospital_address = request.form.get("hospital_address", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        terms = request.form.get("terms")

        # -------------------------------------------------
        # SERVER-SIDE DEBUGGING & LOGGING
        # -------------------------------------------------
        print("=" * 60)
        print("DEBUG - DOCTOR REGISTRATION FORM DATA:")
        print(f"  full_name:                   '{full_name}'")
        print(f"  medical_registration_number: '{medical_registration_number}'")
        print(f"  specialization:              '{specialization}'")
        print(f"  hospital_name:               '{hospital_name}'")
        print(f"  hospital_address:            '{hospital_address}'")
        print(f"  email:                       '{email}'")
        print(f"  phone:                       '{phone}'")
        print(f"  terms:                       '{terms}'")
        print("=" * 60)

        # -------------------------------------------------
        # SERVER-SIDE VALIDATION
        # -------------------------------------------------
        if not medical_registration_number:
            flash("Medical registration number is required.", "error")
            return render_template("auth/doctor_register.html")

        if not all([
            full_name,
            medical_registration_number,
            specialization,
            hospital_name,
            hospital_address,
            email,
            phone,
            password,
            confirm_password
        ]):
            flash("Please fill in all required fields.", "error")
            return render_template("auth/doctor_register.html")

        if not terms:
            flash("Please confirm that you are a registered medical professional.", "error")
            return render_template("auth/doctor_register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/doctor_register.html")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("auth/doctor_register.html")

        # -------------------------------------------------
        # CHECK IF EMAIL OR REGISTRATION NUMBER ALREADY EXISTS
        # -------------------------------------------------
        try:
            existing_email = (
                supabase_admin
                .table("doctors")
                .select("id")
                .eq("email", email)
                .limit(1)
                .execute()
            )
            if existing_email.data:
                flash("An account with this email already exists.", "error")
                return render_template("auth/doctor_register.html")

            existing_reg = (
                supabase_admin
                .table("doctors")
                .select("id")
                .eq("medical_registration_number", medical_registration_number)
                .limit(1)
                .execute()
            )
            if existing_reg.data:
                flash("A doctor with this medical registration number already exists.", "error")
                return render_template("auth/doctor_register.html")
        except Exception as e:
            print("Doctor duplicate check error:", e)

        # -------------------------------------------------
        # INSERT DOCTOR INTO SUPABASE
        # -------------------------------------------------
        doctor_data = {
            "full_name": full_name,
            "medical_registration_number": medical_registration_number,
            "specialization": specialization,
            "hospital_name": hospital_name,
            "hospital_address": hospital_address,
            "email": email,
            "phone": phone,
            "password": password
        }

        try:
            response = (
                supabase_admin
                .table("doctors")
                .insert(doctor_data)
                .execute()
            )

            if response.data:
                flash("Doctor registration successful! Please login.", "success")
                return redirect(url_for("doctor_login"))

            flash("Registration failed. Please try again.", "error")
            return render_template("auth/doctor_register.html")

        except Exception as e:
            print("Doctor registration insert error:", e)
            flash("Unable to create doctor account right now. Please try again.", "error")
            return render_template("auth/doctor_register.html")

    return render_template("auth/doctor_register.html")


@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter your email and password.", "error")
            return render_template("auth/doctor_login.html")

        try:
            result = (
                supabase_admin
                .table("doctors")
                .select("*")
                .eq("email", email)
                .eq("password", password)
                .limit(1)
                .execute()
            )

            if result.data:
                doctor = result.data[0]

                session["doctor_id"] = doctor["id"]
                session["doctor_name"] = doctor["full_name"]
                session["doctor_email"] = doctor["email"]

                try:
                    log_audit_event(
                        doctor_id=doctor["id"],
                        action="DOCTOR_LOGIN",
                        status="SUCCESS",
                        client_ip=request.remote_addr
                    )
                except Exception as log_err:
                    print("Audit log error on doctor login:", repr(log_err))

                flash("Login successful!", "success")
                return redirect(url_for("doctor_dashboard"))

            flash("Invalid email or password.", "error")

        except Exception as e:
            print("Doctor login error:", e)
            flash("Unable to login right now. Please try again.", "error")

    return render_template("auth/doctor_login.html")




# ============================================================
# DOCTOR DASHBOARD & PORTAL ROUTES
# ============================================================

@app.route("/doctor/dashboard")
def doctor_dashboard():

    # Check doctor login
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")

    try:
        doctor_response = (
            supabase_admin
            .table("doctors")
            .select("*")
            .eq("id", doctor_id)
            .single()
            .execute()
        )
        doctor = doctor_response.data
    except Exception as e:
        print("Error fetching doctor details:", e)
        doctor = {
            "full_name": session.get("doctor_name", "Doctor"),
            "specialization": "Medical Specialist",
            "medical_registration_number": "Registered"
        }

    if not doctor:
        session.clear()
        return redirect(url_for("doctor_login"))

    return render_template(
        "doctor/doctor_dashboard.html",
        doctor=doctor
    )


@app.route("/doctor/access")
def doctor_access():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return render_template("doctor/guest_patient.html")



@app.route("/doctor/guest-patient")
def doctor_guest_patient():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()

    try:
        print("GUEST LIST: doctor_id =", repr(doctor_id))

        response = (
            supabase_admin
            .table("guest_patients")
            .select("*")
            .eq("created_by_doctor_id", doctor_id)
            .order("created_at", desc=True)
            .execute()
        )

        guests = response.data or []

        print("GUEST LIST: returned rows =", len(guests))

        return render_template(
            "doctor/guest_patient.html",
            guests=guests
        )

    except Exception as e:
        import traceback

        print("GUEST LIST DATABASE ERROR:", repr(e))
        traceback.print_exc()

        flash(
            "Unable to load guest patients. Check the Flask terminal for details.",
            "error"
        )

        return render_template(
            "doctor/guest_patient.html",
            guests=[]
        )


@app.route("/doctor/medical-records")
def doctor_medical_records():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return render_template("doctor/medical_records.html")


# ============================================================
# CLINICAL COPILOT (PRACTICE-LEVEL AI ASSISTANT)
# ============================================================

@app.route("/doctor/clinical-copilot", endpoint="doctor_clinical_copilot")
@app.route("/doctor/ai-assistant", endpoint="doctor_ai_assistant")
def doctor_ai_assistant():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))
    return render_template("doctor/doctor_ai_assistant.html")


@app.route("/doctor/clinical-copilot/api/briefing", methods=["GET"])
def doctor_clinical_copilot_briefing():
    if "doctor_id" not in session:
        return jsonify({
            "success": False,
            "error": "Doctor authentication required."
        }), 401

    doctor_id = session["doctor_id"]
    try:
        briefing_data = get_clinical_briefing(doctor_id, supabase_admin)
        return jsonify(briefing_data), 200
    except Exception as e:
        print("Clinical Copilot Briefing error:", repr(e))
        return jsonify({
            "success": False,
            "error": "Failed to generate clinical briefing."
        }), 500


@app.route("/doctor/clinical-copilot/api/query", methods=["POST"])
def doctor_clinical_copilot_query():
    if "doctor_id" not in session:
        return jsonify({
            "success": False,
            "error": "Doctor authentication required."
        }), 401

    doctor_id = session["doctor_id"]
    body = request.get_json(silent=True) or {}
    question = str(body.get("question") or "").strip()

    if not question:
        return jsonify({
            "success": False,
            "error": "A question is required."
        }), 400

    if len(question) > 1000:
        return jsonify({
            "success": False,
            "error": "Question exceeds maximum allowed length of 1000 characters."
        }), 400

    try:
        response_data = execute_clinical_query(doctor_id, question, supabase_admin)
        return jsonify(response_data), 200
    except Exception as e:
        print("Clinical Copilot Query error:", repr(e))
        return jsonify({
            "success": False,
            "error": "Failed to process clinical query."
        }), 500


@app.route("/doctor/clinical-copilot/api/trends", methods=["GET"])
def doctor_clinical_copilot_trends():
    if "doctor_id" not in session:
        return jsonify({
            "success": False,
            "error": "Doctor authentication required."
        }), 401

    doctor_id = session["doctor_id"]
    try:
        briefing_data = get_clinical_briefing(doctor_id, supabase_admin)
        return jsonify({
            "success": True,
            "worsening_trends": briefing_data.get("worsening_trends", []),
            "trend_summary": briefing_data.get("trend_summary", {}),
            "refreshed_at": briefing_data.get("refreshed_at")
        }), 200
    except Exception as e:
        print("Clinical Copilot Trends error:", repr(e))
        return jsonify({
            "success": False,
            "error": "Failed to retrieve trend analytics."
        }), 500


@app.route("/doctor/clinical-copilot/api/medication-safety", methods=["GET"])
def doctor_clinical_copilot_medication_safety():
    if "doctor_id" not in session:
        return jsonify({
            "success": False,
            "error": "Doctor authentication required."
        }), 401

    doctor_id = session["doctor_id"]
    try:
        briefing_data = get_clinical_briefing(doctor_id, supabase_admin)
        return jsonify({
            "success": True,
            "medication_safety": briefing_data.get("medication_safety", {}),
            "refreshed_at": briefing_data.get("refreshed_at")
        }), 200
    except Exception as e:
        print("Clinical Copilot Safety error:", repr(e))
        return jsonify({
            "success": False,
            "error": "Failed to retrieve medication safety sweep."
        }), 500


@app.route("/doctor/clinical-copilot/api/alert-review", methods=["POST"])
def doctor_clinical_copilot_alert_review():
    if "doctor_id" not in session:
        return jsonify({
            "success": False,
            "error": "Doctor authentication required."
        }), 401

    doctor_id = session["doctor_id"]
    body = request.get_json(silent=True) or {}
    alert_id = str(body.get("alert_id") or "").strip()
    alert_type = str(body.get("alert_type") or "alert").strip()
    patient_id = str(body.get("patient_id") or "").strip()
    notes = str(body.get("notes") or "").strip()

    if not alert_id:
        return jsonify({
            "success": False,
            "error": "alert_id is required."
        }), 400

    # Verify authorization for patient_id if provided
    if patient_id:
        scope = get_authorized_patient_scope(doctor_id, supabase_admin)
        if patient_id not in scope["authorized_patient_ids"]:
            return jsonify({
                "success": False,
                "error": "You do not have active consent for this patient."
            }), 403

    try:
        record = record_alert_review(doctor_id, alert_id, alert_type, patient_id, notes)
        return jsonify({
            "success": True,
            "message": "Alert marked as reviewed.",
            "review": record
        }), 200
    except Exception as e:
        print("Alert review error:", repr(e))
        return jsonify({
            "success": False,
            "error": "Failed to record alert review."
        }), 500


# ============================================================
# DOCTOR CONSULTATIONS & PRESCRIPTIONS MODULE
# ============================================================

def get_authorized_patients_for_doctor(doctor_id):
    """Retrieve list of all patients for whom the doctor has active, non-expired access."""
    if not doctor_id:
        return []

    try:
        access_res = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )
        access_records = access_res.data or []
    except Exception as e:
        print("[DoctorConsultations] access_requests fetch error:", repr(e))
        access_records = []

    authorized_patients = []
    seen_patient_ids = set()
    now_utc = datetime.now(timezone.utc)

    for acc in access_records:
        pid = acc.get("patient_id")
        if not pid or pid in seen_patient_ids:
            continue

        # Check expiration
        expires_at = acc.get("expires_at")
        access_type = acc.get("access_type") or "temporary"
        if expires_at and access_type != "permanent":
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if now_utc >= exp_dt:
                    try:
                        supabase_admin.table("access_requests").update({"status": "expired"}).eq("id", acc["id"]).execute()
                    except Exception:
                        pass
                    continue
            except Exception:
                pass

        # Fetch patient profile
        try:
            p_res = supabase_admin.table("patients").select("*").eq("id", pid).limit(1).execute()
            p_data = p_res.data or []
            if p_data:
                patient = dict(p_data[0])
                patient["patient_id"] = patient.get("id")
                patient["access_id"] = acc.get("id")
                patient["access_type"] = access_type
                patient["access_status"] = "active"
                patient["approved_at"] = acc.get("approved_at") or acc.get("created_at")
                patient["expires_at"] = expires_at
                patient["is_permanent"] = (access_type == "permanent") or not expires_at
                authorized_patients.append(patient)
                seen_patient_ids.add(pid)
        except Exception as p_err:
            print("[DoctorConsultations] patient fetch error:", repr(p_err))

    return authorized_patients


def verify_doctor_patient_authorization(doctor_id, patient_id):
    """Strict backend verification that doctor_id has active access to patient_id."""
    if not doctor_id or not patient_id:
        return False, None
    patients = get_authorized_patients_for_doctor(doctor_id)
    for p in patients:
        if str(p.get("id")) == str(patient_id) or str(p.get("patient_id")) == str(patient_id):
            return True, p
    return False, None


def get_patient_document_history(patient_id):
    """
    Retrieve all medical documents belonging to patient_id.
    Includes:
    1. Patient-uploaded records
    2. Doctor-uploaded records
    3. Doctor-created consultation notes
    4. Doctor-generated prescriptions
    """
    if not patient_id:
        return []

    try:
        res = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("uploaded_at", desc=True)
            .execute()
        )
        records = res.data or []
    except Exception:
        try:
            res = (
                supabase_admin
                .table("medical_records")
                .select("*")
                .eq("patient_id", patient_id)
                .execute()
            )
            records = res.data or []
        except Exception as e:
            print("[DoctorConsultations] Error fetching records:", repr(e))
            records = []

    formatted = []
    for r in records:
        rec = dict(r)
        doc_name = rec.get("doctor_name")
        hosp_name = rec.get("hospital_name")
        rec_type = (rec.get("record_type") or "other").lower()

        if doc_name:
            if hosp_name:
                uploader = f"Dr. {doc_name} ({hosp_name})"
            else:
                uploader = f"Dr. {doc_name}"
        elif rec.get("doctor_id"):
            uploader = "Attending Physician"
        elif rec.get("uploaded_by") and str(rec.get("uploaded_by")).lower() == "doctor":
            uploader = "Doctor"
        else:
            uploader = "Patient"

        rec["uploader_label"] = uploader

        if not rec.get("file_url") and rec.get("id"):
            try:
                rec["file_url"] = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=rec["id"])
            except Exception:
                rec["file_url"] = f"/doctor/patient-record/{patient_id}/{rec['id']}"

        display_date = rec.get("document_date") or rec.get("uploaded_at") or rec.get("created_at") or "Recent"
        if display_date and len(str(display_date)) >= 10:
            rec["display_date"] = str(display_date)[:10]
        else:
            rec["display_date"] = display_date

        formatted.append(rec)

    return formatted


def compute_document_summary_counts(records):
    """Compute category counts from records list."""
    counts = {
        "consultations": 0,
        "prescriptions": 0,
        "lab_reports": 0,
        "imaging": 0,
        "other": 0,
        "total": len(records)
    }
    for r in records:
        t = (r.get("record_type") or "other").lower()
        if t == "consultation":
            counts["consultations"] += 1
        elif t == "prescription":
            counts["prescriptions"] += 1
        elif t in ["lab_report", "lab", "blood_test", "pathology"]:
            counts["lab_reports"] += 1
        elif t in ["scan_imaging", "imaging", "xray", "ct_scan", "mri", "ultrasound", "scan"]:
            counts["imaging"] += 1
        else:
            counts["other"] += 1
    return counts


@app.route("/doctor/consultations", endpoint="doctor_consultations")
@app.route("/doctor/consultations-prescriptions", endpoint="doctor_consultations_prescriptions")
def doctor_consultations():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")

    # 1. Fetch doctor profile
    doctor = {}
    try:
        doctor = get_doctor_profile(doctor_id, supabase_admin, session) or {}
    except Exception as e:
        print("[DoctorConsultations] Doctor profile fetch notice:", repr(e))

    if not doctor:
        doctor = {
            "id": doctor_id,
            "full_name": session.get("doctor_name", "Doctor"),
            "specialization": "Medical Specialist",
            "medical_registration_number": "REG-DOC",
            "hospital_name": "OmniCare Partner Hospital",
            "qualification": "MBBS, MD",
            "email": session.get("doctor_email", "")
        }

    # 2. Fetch authorized patients
    authorized_patients = get_authorized_patients_for_doctor(doctor_id)

    # 3. Check requested patient
    requested_pid = request.args.get("patient_id")
    selected_patient = None
    records = []
    doc_summary = {
        "consultations": 0,
        "prescriptions": 0,
        "lab_reports": 0,
        "imaging": 0,
        "other": 0,
        "total": 0
    }
    recent_prescriptions = []
    recent_consultations = []

    if requested_pid:
        for p in authorized_patients:
            if str(p.get("id")) == str(requested_pid) or str(p.get("patient_id")) == str(requested_pid):
                selected_patient = p
                break

        if not selected_patient:
            flash("Unauthorized access: You do not have active clinical authorization for this patient.", "error")
        else:
            pid = selected_patient.get("id") or selected_patient.get("patient_id")
            records = get_patient_document_history(pid)
            doc_summary = compute_document_summary_counts(records)
            recent_prescriptions = [r for r in records if (r.get("record_type") or "").lower() == "prescription"][:6]
            recent_consultations = [r for r in records if (r.get("record_type") or "").lower() == "consultation"][:6]
    elif authorized_patients:
        selected_patient = authorized_patients[0]
        pid = selected_patient.get("id") or selected_patient.get("patient_id")
        records = get_patient_document_history(pid)
        doc_summary = compute_document_summary_counts(records)
        recent_prescriptions = [r for r in records if (r.get("record_type") or "").lower() == "prescription"][:6]
        recent_consultations = [r for r in records if (r.get("record_type") or "").lower() == "consultation"][:6]

    today_date = datetime.now(timezone.utc).date().isoformat()
    current_time = datetime.now(timezone.utc).strftime("%H:%M")

    return render_template(
        "doctor/doctor_consultations.html",
        doctor=doctor,
        authorized_patients=authorized_patients,
        selected_patient=selected_patient,
        records=records,
        doc_summary=doc_summary,
        recent_prescriptions=recent_prescriptions,
        recent_consultations=recent_consultations,
        today_date=today_date,
        current_time=current_time
    )


@app.route("/doctor/consultations/api/patients", methods=["GET"])
def doctor_consultations_api_patients():
    """Returns JSON list of authorized patients for the logged-in doctor."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required."}), 401

    doctor_id = session.get("doctor_id")
    patients = get_authorized_patients_for_doctor(doctor_id)
    return jsonify({
        "success": True,
        "patients": patients,
        "count": len(patients)
    })


@app.route("/doctor/consultations/api/patient-summary/<patient_id>", methods=["GET"])
def doctor_consultations_api_patient_summary(patient_id):
    """Returns complete JSON summary of the selected patient including counts and records."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required."}), 401

    doctor_id = session.get("doctor_id")
    is_auth, patient = verify_doctor_patient_authorization(doctor_id, patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": "Unauthorized: No active clinical access to this patient."}), 403

    records = get_patient_document_history(patient_id)
    counts = compute_document_summary_counts(records)
    recent_prescriptions = [r for r in records if (r.get("record_type") or "").lower() == "prescription"][:6]
    recent_consultations = [r for r in records if (r.get("record_type") or "").lower() == "consultation"][:6]

    doctor = get_doctor_profile(doctor_id, supabase_admin, session) or {}

    return jsonify({
        "success": True,
        "patient": patient,
        "summary": counts,
        "records": records,
        "recent_prescriptions": recent_prescriptions,
        "recent_consultations": recent_consultations,
        "doctor": doctor
    })


@app.route("/doctor/consultations/<patient_id>/create-consultation", methods=["POST"])
def doctor_consultations_create_consultation(patient_id):
    """Create consultation note with vitals, clinical impression, and ReportLab PDF."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required."}), 401

    doctor_id = session.get("doctor_id")
    is_auth, patient_data = verify_doctor_patient_authorization(doctor_id, patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": "Unauthorized: No active clinical access to this patient."}), 403

    doctor_data = get_doctor_profile(doctor_id, supabase_admin, session) or {}

    data = request.get_json(silent=True) or request.form.to_dict()
    consultation_type = data.get("consultation_type", "General Consultation").strip()
    chief_complaint = data.get("chief_complaint", "").strip()
    hpi = data.get("hpi", "").strip()
    vitals = data.get("vitals") if isinstance(data.get("vitals"), dict) else {}
    if not vitals:
        vitals = {
            "bp": data.get("vital_bp", "").strip() or data.get("vitals_bp", "").strip(),
            "pulse": data.get("vital_pulse", "").strip() or data.get("vitals_pulse", "").strip(),
            "temperature": data.get("vital_temp", "").strip() or data.get("vitals_temperature", "").strip(),
            "respiratory_rate": data.get("vital_rr", "").strip() or data.get("vitals_rr", "").strip(),
            "oxygen_saturation": data.get("vital_spo2", "").strip() or data.get("vitals_spo2", "").strip(),
            "weight": data.get("vital_weight", "").strip() or data.get("vitals_weight", "").strip(),
            "height": data.get("vital_height", "").strip() or data.get("vitals_height", "").strip(),
            "bmi": data.get("vital_bmi", "").strip() or data.get("vitals_bmi", "").strip()
        }
    diagnosis_primary = data.get("diagnosis_primary", "").strip()
    diagnosis_secondary = data.get("diagnosis_secondary", "").strip()
    treatment_plan = data.get("treatment_plan", "").strip()
    clinical_notes = data.get("clinical_notes", "").strip()
    consultation_time = data.get("consultation_time", "").strip() or data.get("time", "").strip()
    findings = data.get("findings", "").strip()
    recommendations = data.get("recommendations", "").strip()
    follow_up = data.get("follow_up", "").strip()
    document_date = data.get("document_date", "").strip() or datetime.now(timezone.utc).date().isoformat()
    is_draft = str(data.get("is_draft", "")).lower() in ("true", "1")

    hospital_name = doctor_data.get("hospital_name") or "Medical Center"
    doctor_name = doctor_data.get("full_name") or "Doctor"

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
        "findings": findings,
        "clinical_examination_notes": findings,
        "diagnosis": diagnosis_primary,
        "diagnosis_primary": diagnosis_primary,
        "diagnosis_secondary": diagnosis_secondary,
        "treatment_plan": treatment_plan,
        "recommendations": recommendations,
        "general_advice": recommendations,
        "follow_up": follow_up,
        "clinical_notes": clinical_notes,
        "is_draft": is_draft
    }

    try:
        pdf_bytes = generate_consultation_pdf(doctor_data, patient_data, consultation_payload)
        filename = f"consultation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        title = data.get("title", "").strip() or f"Consultation ({consultation_type}) - {datetime.now().strftime('%d %b %Y')}"
        description = f"Chief complaint: {chief_complaint}. Diagnosis: {diagnosis_primary}" if diagnosis_primary else chief_complaint

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
            structured_data={
                "consultation": consultation_payload,
                "doctor_name": doctor_name,
                "hospital_name": hospital_name
            },
            is_draft=is_draft
        )

        try:
            log_audit_event(
                doctor_id=doctor_id,
                action="CONSULTATION_NOTE_CREATED",
                patient_ids=[patient_id],
                status="SUCCESS",
                metadata={"record_id": saved_rec.get("id"), "is_draft": is_draft, "diagnosis": diagnosis_primary},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        saved_rec["uploader_label"] = f"Dr. {doctor_name} ({hospital_name})" if hospital_name else f"Dr. {doctor_name}"
        saved_rec["document_date"] = document_date

        return jsonify({
            "success": True,
            "message": "Consultation note created successfully.",
            "record": saved_rec
        })
    except Exception as e:
        print("[DoctorConsultations] Error creating consultation:", repr(e))
        return jsonify({"success": False, "error": f"Failed to create consultation: {str(e)}"}), 500


@app.route("/doctor/consultations/<patient_id>/create-prescription", methods=["POST"])
def doctor_consultations_create_prescription(patient_id):
    """Create hospital-style digital prescription with ReportLab PDF and M/A/E/N timings."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required."}), 401

    doctor_id = session.get("doctor_id")
    is_auth, patient_data = verify_doctor_patient_authorization(doctor_id, patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": "Unauthorized: No active clinical access to this patient."}), 403

    doctor_data = get_doctor_profile(doctor_id, supabase_admin, session) or {}

    data = request.get_json(silent=True) or request.form.to_dict()
    diagnosis = data.get("diagnosis", "").strip()
    clinical_notes = data.get("clinical_notes", "").strip()
    general_advice = data.get("general_advice", "").strip()
    follow_up = data.get("follow_up", "").strip()
    prescription_time = data.get("prescription_time", "").strip() or data.get("time", "").strip()
    document_date = data.get("document_date", "").strip() or datetime.now(timezone.utc).date().isoformat()
    is_draft = str(data.get("is_draft", "")).lower() in ("true", "1")

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
    }

    hospital_name = doctor_data.get("hospital_name") or "Medical Center"
    doctor_name = doctor_data.get("full_name") or "Doctor"

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
            structured_data={
                "prescription": prescription_payload,
                "doctor_name": doctor_name,
                "hospital_name": hospital_name
            },
            is_draft=is_draft
        )

        try:
            log_audit_event(
                doctor_id=doctor_id,
                action="PRESCRIPTION_CREATED",
                patient_ids=[patient_id],
                status="SUCCESS",
                metadata={"record_id": saved_rec.get("id"), "medication_count": med_count, "diagnosis": diagnosis},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        saved_rec["uploader_label"] = f"Dr. {doctor_name} ({hospital_name})" if hospital_name else f"Dr. {doctor_name}"
        saved_rec["document_date"] = document_date

        return jsonify({
            "success": True,
            "message": "Prescription created successfully.",
            "record": saved_rec
        })
    except Exception as e:
        print("[DoctorConsultations] Error creating prescription:", repr(e))
        return jsonify({"success": False, "error": f"Failed to create prescription: {str(e)}"}), 500


@app.route("/doctor/consultations/<patient_id>/upload-document", methods=["POST"])
def doctor_consultations_upload_document(patient_id):
    """Upload external medical records, lab reports, imaging, or certificates."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required."}), 401

    doctor_id = session.get("doctor_id")
    is_auth, patient = verify_doctor_patient_authorization(doctor_id, patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": "Unauthorized: No active clinical access to this patient."}), 403

    if "document_file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files["document_file"]
    if not file or not file.filename:
        return jsonify({"success": False, "error": "Empty filename."}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ["pdf", "jpg", "jpeg", "png", "webp"]:
        return jsonify({"success": False, "error": f"Unsupported file type (.{ext}). Allowed: PDF, JPG, PNG, WEBP."}), 400

    file_bytes = file.read()
    if len(file_bytes) > 25 * 1024 * 1024:
        return jsonify({"success": False, "error": "File size exceeds 25 MB limit."}), 400

    title = request.form.get("title", "").strip() or filename
    record_type = request.form.get("category", "other").strip().lower()
    description = request.form.get("description", "").strip()
    document_date = request.form.get("document_date", "").strip() or datetime.now(timezone.utc).date().isoformat()

    doctor_data = get_doctor_profile(doctor_id, supabase_admin, session) or {}
    hospital_name = doctor_data.get("hospital_name") or "Medical Center"
    doctor_name = doctor_data.get("full_name") or "Doctor"

    content_type_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp"
    }
    content_type = content_type_map.get(ext, "application/octet-stream")

    try:
        saved_rec = save_patient_medical_record(
            supabase_client=supabase_admin,
            patient_id=patient_id,
            doctor_id=doctor_id,
            record_type=record_type,
            title=title,
            description=description,
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            document_date=document_date,
            structured_data={
                "uploaded_by_role": "doctor",
                "doctor_name": doctor_name,
                "hospital_name": hospital_name
            }
        )

        try:
            log_audit_event(
                doctor_id=doctor_id,
                action="MEDICAL_DOCUMENT_UPLOADED",
                patient_ids=[patient_id],
                status="SUCCESS",
                metadata={"record_id": saved_rec.get("id"), "record_type": record_type, "title": title},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        saved_rec["uploader_label"] = f"Dr. {doctor_name} ({hospital_name})" if hospital_name else f"Dr. {doctor_name}"
        saved_rec["document_date"] = document_date

        return jsonify({
            "success": True,
            "message": "Medical document uploaded successfully.",
            "record": saved_rec
        })
    except Exception as e:
        print("[DoctorConsultations] Error uploading document:", repr(e))
        return jsonify({"success": False, "error": f"Failed to upload document: {str(e)}"}), 500


@app.route("/doctor/consultations/<patient_id>/preview-pdf", methods=["POST"])
def doctor_consultations_preview_pdf(patient_id):
    """Generate in-memory PDF stream for live preview without saving."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required."}), 401

    doctor_id = session.get("doctor_id")
    is_auth, patient_data = verify_doctor_patient_authorization(doctor_id, patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": "Unauthorized: No active clinical access to this patient."}), 403

    doctor_data = get_doctor_profile(doctor_id, supabase_admin, session) or {}

    data = request.get_json(silent=True) or request.form.to_dict()
    template_type = data.get("template_type", "prescription").strip().lower()

    try:
        if template_type == "consultation":
            vitals = data.get("vitals") if isinstance(data.get("vitals"), dict) else {}
            payload = {
                "consultation_type": data.get("consultation_type", "General Consultation"),
                "date": data.get("document_date") or datetime.now(timezone.utc).date().isoformat(),
                "consultation_date": data.get("document_date") or datetime.now(timezone.utc).date().isoformat(),
                "consultation_time": data.get("consultation_time", ""),
                "chief_complaint": data.get("chief_complaint", "Clinical consultation."),
                "hpi": data.get("hpi", ""),
                "vitals": vitals,
                "findings": data.get("findings", ""),
                "diagnosis": data.get("diagnosis_primary", "Clinical Impression"),
                "treatment_plan": data.get("treatment_plan", ""),
                "recommendations": data.get("recommendations", ""),
                "follow_up": data.get("follow_up", ""),
                "clinical_notes": data.get("clinical_notes", "")
            }
            pdf_bytes = generate_consultation_pdf(doctor_data, patient_data, payload)
        else:
            medicines_raw = data.get("medicines", [])
            if isinstance(medicines_raw, str):
                try:
                    medicines = json.loads(medicines_raw)
                except Exception:
                    medicines = []
            else:
                medicines = medicines_raw or []

            payload = {
                "date": data.get("document_date") or datetime.now(timezone.utc).date().isoformat(),
                "prescription_date": data.get("document_date") or datetime.now(timezone.utc).date().isoformat(),
                "prescription_time": data.get("prescription_time", ""),
                "diagnosis": data.get("diagnosis", "Prescription"),
                "clinical_notes": data.get("clinical_notes", ""),
                "medicines": medicines,
                "general_advice": data.get("general_advice", ""),
                "follow_up": data.get("follow_up", "")
            }
            pdf_bytes = generate_prescription_pdf(doctor_data, patient_data, payload)

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=False,
            download_name="preview.pdf"
        )
    except Exception as e:
        print("[DoctorConsultations] Preview generation error:", repr(e))
        return jsonify({"success": False, "error": f"Preview generation failed: {str(e)}"}), 500


@app.route("/doctor/consultations/document/<patient_id>/<record_id>/download", methods=["GET"])
def doctor_consultations_download_document(patient_id, record_id):
    """Download medical document PDF with proper attachment header."""
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")
    is_auth, patient = verify_doctor_patient_authorization(doctor_id, patient_id)
    if not is_auth:
        flash("Unauthorized access to document.", "error")
        return redirect(url_for("doctor_consultations"))

    try:
        rec_res = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("id", record_id)
            .eq("patient_id", patient_id)
            .single()
            .execute()
        )
        record = rec_res.data
        if not record:
            flash("Record not found.", "error")
            return redirect(url_for("doctor_consultations", patient_id=patient_id))

        file_path = record.get("file_path")
        file_bytes = None
        if file_path:
            try:
                file_bytes = supabase_admin.storage.from_("medical-records").download(file_path)
            except Exception as dl_err:
                print("[DoctorConsultations] Storage download notice:", repr(dl_err))

        title = secure_filename(record.get("title") or "Medical_Document")
        if not title.endswith(".pdf"):
            title += ".pdf"

        if file_bytes:
            return send_file(
                io.BytesIO(file_bytes),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=title
            )

        # Fallback to redirecting to file_url
        if record.get("file_url"):
            return redirect(record["file_url"])

        flash("Document file not available.", "error")
        return redirect(url_for("doctor_consultations", patient_id=patient_id))
    except Exception as e:
        print("[DoctorConsultations] Download error:", repr(e))
        flash(f"Download failed: {str(e)}", "error")
        return redirect(url_for("doctor_consultations", patient_id=patient_id))


# ============================================================
# DOCTOR ACCESS & AUDIT LOG — PAGES & APIS
# ============================================================

@app.route("/doctor/access-audit")
def doctor_access_audit():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")

    # Fetch doctor details from database
    try:
        doctor_response = (
            supabase_admin
            .table("doctors")
            .select("*")
            .eq("id", doctor_id)
            .single()
            .execute()
        )
        doctor = doctor_response.data or {}
    except Exception as e:
        print("Error fetching doctor for access-audit:", repr(e))
        doctor = {}

    if not doctor:
        doctor = {
            "id": doctor_id,
            "full_name": session.get("doctor_name", "Doctor"),
            "specialization": "Medical Specialist",
            "medical_registration_number": "Registered",
            "email": session.get("doctor_email", "")
        }

    return render_template(
        "doctor/doctor_access_audit.html",
        doctor=doctor
    )


@app.route("/doctor/access-audit/api/summary", methods=["GET"])
def doctor_access_audit_summary():
    """Returns access overview counts derived from database."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    doctor_id = session.get("doctor_id")
    now = datetime.now(timezone.utc)

    try:
        access_res = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("doctor_id", doctor_id)
            .execute()
        )
        records = access_res.data or []
    except Exception as e:
        print("Error fetching access summary:", repr(e))
        return jsonify({
            "success": False,
            "error": "Failed to load access overview data.",
            "summary": {
                "total_requests": 0,
                "active_access": 0,
                "pending_requests": 0,
                "revoked_expired": 0
            }
        }), 500

    total_requests = len(records)
    active_count = 0
    pending_count = 0
    revoked_expired_count = 0

    for req in records:
        st = (req.get("status") or "").lower()
        expires_at = req.get("expires_at")

        if st == "active":
            if expires_at:
                try:
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                    if now >= exp_dt:
                        # Expire in database
                        try:
                            supabase_admin.table("access_requests").update({"status": "expired"}).eq("id", req["id"]).execute()
                        except Exception:
                            pass
                        st = "expired"
                except Exception:
                    pass

        if st == "active":
            active_count += 1
        elif st == "pending":
            pending_count += 1
        elif st in ("revoked", "expired", "rejected", "cancelled"):
            revoked_expired_count += 1

    return jsonify({
        "success": True,
        "summary": {
            "total_requests": total_requests,
            "active_access": active_count,
            "pending_requests": pending_count,
            "revoked_expired": revoked_expired_count
        }
    }), 200


@app.route("/doctor/access-audit/api/patients", methods=["GET"])
def doctor_access_audit_patients():
    """Returns authorized patients for the authenticated doctor."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    doctor_id = session.get("doctor_id")
    search_query = request.args.get("q", "").strip().lower()
    status_filter = request.args.get("status", "all").strip().lower()
    type_filter = request.args.get("type", "all").strip().lower()
    page = max(1, int(request.args.get("page", 1)))
    per_page = max(1, min(int(request.args.get("per_page", 10)), 50))

    now = datetime.now(timezone.utc)

    try:
        access_res = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("doctor_id", doctor_id)
            .order("requested_at", desc=True)
            .execute()
        )
        records = access_res.data or []
    except Exception as e:
        print("Error fetching patients list for access audit:", repr(e))
        return jsonify({"success": False, "error": "Database error while retrieving patients."}), 500

    patient_ids = list({r["patient_id"] for r in records if r.get("patient_id")})
    patients_map = {}
    if patient_ids:
        try:
            p_res = (
                supabase_admin
                .table("patients")
                .select("id, full_name, health_id, gender, date_of_birth")
                .in_("id", patient_ids)
                .execute()
            )
            for p in (p_res.data or []):
                patients_map[p["id"]] = p
        except Exception as e:
            print("Error retrieving patient records:", repr(e))

    patient_list = []
    seen_patients = set()

    for req in records:
        patient_id = req.get("patient_id")
        if not patient_id:
            continue

        p = patients_map.get(patient_id, {})
        full_name = p.get("full_name") or p.get("name") or "Unknown Patient"
        health_id = p.get("health_id") or "N/A"
        raw_status = (req.get("status") or "").lower()
        access_type = req.get("access_type") or "temporary"
        expires_at = req.get("expires_at")
        approved_at = req.get("approved_at") or req.get("requested_at")

        computed_status = raw_status
        if raw_status == "active":
            if expires_at:
                try:
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                    if now >= exp_dt:
                        computed_status = "expired"
                    elif (exp_dt - now) <= timedelta(hours=2):
                        computed_status = "expiring_soon"
                except Exception:
                    pass
        elif raw_status in ("rejected", "cancelled"):
            computed_status = "revoked"

        # Apply filters
        if status_filter != "all":
            if status_filter == "active" and computed_status not in ("active", "expiring_soon"):
                continue
            elif status_filter == "expiring_soon" and computed_status != "expiring_soon":
                continue
            elif status_filter == "expired" and computed_status != "expired":
                continue
            elif status_filter == "revoked" and computed_status != "revoked":
                continue

        if type_filter != "all" and access_type.lower() != type_filter:
            continue

        if search_query:
            if (search_query not in full_name.lower() and
                search_query not in health_id.lower() and
                search_query not in str(patient_id).lower()):
                continue

        # Prevent duplicate entries for same patient in the authorized list
        if patient_id in seen_patients:
            continue
        seen_patients.add(patient_id)

        granted_display = "—"
        if approved_at:
            try:
                g_dt = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
                granted_display = g_dt.strftime("%d %b %Y, %I:%M %p")
            except Exception:
                granted_display = str(approved_at)[:19]

        expires_display = "Permanent (No Expiry)" if access_type == "permanent" else "N/A"
        if expires_at:
            try:
                e_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                expires_display = e_dt.strftime("%d %b %Y, %I:%M %p")
            except Exception:
                expires_display = str(expires_at)[:19]

        patient_list.append({
            "patient_id": patient_id,
            "patient_name": full_name,
            "health_id": health_id,
            "gender": p.get("gender") or "Not specified",
            "access_type": access_type,
            "access_id": req.get("id"),
            "granted_at": approved_at,
            "granted_display": granted_display,
            "expires_at": expires_at,
            "expires_display": expires_display,
            "status": computed_status,
            "can_view_records": computed_status in ("active", "expiring_soon")
        })

    total = len(patient_list)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    paginated = patient_list[(page - 1) * per_page : page * per_page]

    return jsonify({
        "success": True,
        "patients": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }), 200


@app.route("/doctor/access-audit/api/requests", methods=["GET", "POST"])
def doctor_access_audit_requests():
    """GET access requests or POST a new access request."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    doctor_id = session.get("doctor_id")

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        patient_identifier = str(body.get("patient_id") or body.get("health_id") or "").strip()
        access_type = str(body.get("access_type") or "temporary").strip().lower()
        purpose = str(body.get("purpose") or "Clinical consultation and medical history review").strip()

        if not patient_identifier:
            return jsonify({"success": False, "error": "Patient Health ID or Patient ID is required."}), 400

        if access_type not in ("temporary", "permanent", "one_time"):
            access_type = "temporary"

        try:
            p_query = supabase_admin.table("patients").select("*")
            if "-" in patient_identifier and len(patient_identifier) == 36:
                p_res = p_query.eq("id", patient_identifier).execute()
            else:
                p_res = p_query.eq("health_id", patient_identifier).execute()

            if not p_res.data:
                return jsonify({"success": False, "error": f"No patient found matching '{patient_identifier}'."}), 404

            patient = p_res.data[0]
        except Exception as e:
            print("Error finding patient for access request:", repr(e))
            return jsonify({"success": False, "error": "Database error while looking up patient."}), 500

        patient_id = patient["id"]

        # Check existing pending request
        try:
            existing_res = (
                supabase_admin
                .table("access_requests")
                .select("*")
                .eq("doctor_id", doctor_id)
                .eq("patient_id", patient_id)
                .eq("status", "pending")
                .execute()
            )
            if existing_res.data:
                return jsonify({
                    "success": False,
                    "error": "An access request for this patient is already pending patient approval."
                }), 400
        except Exception as e:
            print("Error checking existing requests:", repr(e))

        now_iso = datetime.now(timezone.utc).isoformat()
        new_req_data = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "status": "pending",
            "access_type": access_type,
            "access_method": "approval",
            "purpose": purpose,
            "requested_at": now_iso
        }

        try:
            insert_res = (
                supabase_admin
                .table("access_requests")
                .insert(new_req_data)
                .execute()
            )
            created_record = insert_res.data[0] if insert_res.data else new_req_data

            # Log audit event
            log_audit_event(
                doctor_id=doctor_id,
                action="PATIENT_ACCESS_REQUESTED",
                patient_ids=[patient_id],
                status="SUCCESS",
                metadata={
                    "patient_id": patient_id,
                    "patient_name": patient.get("full_name"),
                    "health_id": patient.get("health_id"),
                    "access_type": access_type,
                    "purpose": purpose
                },
                client_ip=request.remote_addr
            )

            return jsonify({
                "success": True,
                "message": "Access request successfully submitted. Awaiting patient approval.",
                "request": created_record
            }), 201

        except Exception as e:
            print("Error inserting access request:", repr(e))
            return jsonify({"success": False, "error": "Failed to create access request in database."}), 500

    # GET requests
    search_query = request.args.get("q", "").strip().lower()
    status_filter = request.args.get("status", "all").strip().lower()
    page = max(1, int(request.args.get("page", 1)))
    per_page = max(1, min(int(request.args.get("per_page", 10)), 50))

    try:
        res = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("doctor_id", doctor_id)
            .order("requested_at", desc=True)
            .execute()
        )
        records = res.data or []
    except Exception as e:
        print("Error querying access requests:", repr(e))
        return jsonify({"success": False, "error": "Failed to load access requests."}), 500

    patient_ids = list({r["patient_id"] for r in records if r.get("patient_id")})
    patients_map = {}
    if patient_ids:
        try:
            p_res = (
                supabase_admin
                .table("patients")
                .select("id, full_name, health_id, gender")
                .in_("id", patient_ids)
                .execute()
            )
            for p in (p_res.data or []):
                patients_map[p["id"]] = p
        except Exception as e:
            print("Error fetching patients map:", repr(e))

    formatted_requests = []
    for req in records:
        p_id = req.get("patient_id")
        p = patients_map.get(p_id, {})
        p_name = p.get("full_name") or f"Patient {str(p_id)[:8]}"
        h_id = p.get("health_id") or "N/A"
        st = (req.get("status") or "pending").lower()

        if status_filter != "all" and st != status_filter:
            continue

        if search_query:
            if (search_query not in p_name.lower() and
                search_query not in h_id.lower() and
                search_query not in str(req.get("id")).lower() and
                search_query not in str(p_id).lower()):
                continue

        req_at = req.get("requested_at")
        req_display = req_at
        if req_at:
            try:
                r_dt = datetime.fromisoformat(req_at.replace("Z", "+00:00"))
                req_display = r_dt.strftime("%d %b %Y, %I:%M %p")
            except Exception:
                req_display = str(req_at)[:19]

        formatted_requests.append({
            "id": req.get("id"),
            "patient_id": p_id,
            "patient_name": p_name,
            "health_id": h_id,
            "access_type": req.get("access_type") or "temporary",
            "status": st,
            "requested_at": req_at,
            "requested_display": req_display or "—",
            "approved_at": req.get("approved_at"),
            "expires_at": req.get("expires_at"),
            "purpose": req.get("purpose") or "Clinical evaluation & treatment"
        })

    total = len(formatted_requests)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    paginated = formatted_requests[(page - 1) * per_page : page * per_page]

    return jsonify({
        "success": True,
        "requests": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }), 200


@app.route("/doctor/access-audit/api/requests/<request_id>/cancel", methods=["POST"])
def doctor_cancel_access_request(request_id):
    """Allows doctor to cancel a pending access request."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    doctor_id = session.get("doctor_id")

    try:
        res = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("id", request_id)
            .eq("doctor_id", doctor_id)
            .execute()
        )
        if not res.data:
            return jsonify({"success": False, "error": "Access request not found or not owned by you."}), 404

        req = res.data[0]
        if req.get("status") != "pending":
            return jsonify({
                "success": False,
                "error": f"Cannot cancel request with status '{req.get('status')}'. Only pending requests can be cancelled."
            }), 400

        supabase_admin.table("access_requests").update({"status": "cancelled"}).eq("id", request_id).execute()

        log_audit_event(
            doctor_id=doctor_id,
            action="PATIENT_ACCESS_CANCELLED",
            patient_ids=[req.get("patient_id")],
            status="SUCCESS",
            metadata={"request_id": request_id},
            client_ip=request.remote_addr
        )

        return jsonify({"success": True, "message": "Access request cancelled successfully."}), 200

    except Exception as e:
        print("Error cancelling request:", repr(e))
        return jsonify({"success": False, "error": "Failed to cancel access request."}), 500


@app.route("/doctor/access-audit/api/consent/<request_id>", methods=["GET"])
def doctor_access_consent_details(request_id):
    """Retrieve verified consent parameters and scope for an access authorization."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    doctor_id = session.get("doctor_id")

    try:
        res = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("id", request_id)
            .eq("doctor_id", doctor_id)
            .execute()
        )
        if not res.data:
            return jsonify({"success": False, "error": "Consent authorization record not found."}), 404

        req = res.data[0]
        patient_id = req.get("patient_id")
        patient = {}
        if patient_id:
            try:
                p_res = supabase_admin.table("patients").select("*").eq("id", patient_id).execute()
                if p_res.data:
                    patient = p_res.data[0]
            except Exception:
                pass

        now = datetime.now(timezone.utc)
        expires_at = req.get("expires_at")
        is_expired = False
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                is_expired = (now >= exp_dt)
            except Exception:
                pass

        consent = {
            "request_id": req.get("id"),
            "patient_id": patient_id,
            "patient_name": patient.get("full_name") or "Authorized Patient",
            "health_id": patient.get("health_id") or "N/A",
            "gender": patient.get("gender") or "Not specified",
            "blood_group": patient.get("blood_group") or "Not specified",
            "access_type": req.get("access_type") or "temporary",
            "status": "expired" if is_expired else req.get("status"),
            "requested_at": req.get("requested_at"),
            "approved_at": req.get("approved_at"),
            "expires_at": expires_at,
            "purpose": req.get("purpose") or "Clinical evaluation & longitudinal medical record review",
            "authorized_scopes": [
                {"name": "Medical History & Diagnoses", "status": "Granted"},
                {"name": "Prescription & Medication Records", "status": "Granted"},
                {"name": "Laboratory & Investigation Reports", "status": "Granted"},
                {"name": "Health Timeline & Vitals Trends", "status": "Granted"}
            ],
            "consent_standard": "HIPAA / HL7 FHIR Consent Directive (Permit)",
            "is_active": req.get("status") == "active" and not is_expired
        }

        return jsonify({"success": True, "consent": consent}), 200

    except Exception as e:
        print("Error retrieving consent details:", repr(e))
        return jsonify({"success": False, "error": "Failed to load consent details."}), 500


@app.route("/doctor/access-audit/api/logs", methods=["GET"])
def doctor_access_audit_logs_api():
    """Returns paginated, filterable audit log activities for the authenticated doctor."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    doctor_id = session.get("doctor_id")
    action = request.args.get("action")
    patient_id = request.args.get("patient_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    search = request.args.get("q")
    page = max(1, int(request.args.get("page", 1)))
    per_page = max(1, min(int(request.args.get("per_page", 15)), 50))

    try:
        data = query_doctor_audit_logs(
            doctor_id=doctor_id,
            action=action,
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            search=search,
            page=page,
            per_page=per_page
        )
        return jsonify({"success": True, **data}), 200
    except Exception as e:
        print("Error retrieving audit logs API:", repr(e))
        return jsonify({"success": False, "error": "Failed to retrieve audit log activities."}), 500


@app.route("/doctor/access-audit/api/logs/<log_id>", methods=["GET"])
def doctor_access_audit_log_detail(log_id):
    """Retrieve detailed view of a single audit activity record."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    doctor_id = session.get("doctor_id")
    log_entry = get_audit_log_by_id(log_id, doctor_id=doctor_id)
    if not log_entry:
        return jsonify({"success": False, "error": "Audit log entry not found or unauthorized."}), 404

    return jsonify({"success": True, "log": log_entry}), 200


@app.route("/doctor/access-audit/api/notifications", methods=["GET"])
def doctor_access_audit_notifications():
    """Retrieve access notifications for the authenticated doctor."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    doctor_id = session.get("doctor_id")
    limit = max(1, min(int(request.args.get("limit", 20)), 50))

    records = []
    patients_map = {}

    try:
        req_res = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("doctor_id", doctor_id)
            .order("requested_at", desc=True)
            .execute()
        )
        records = req_res.data or []

        patient_ids = list({r["patient_id"] for r in records if r.get("patient_id")})
        if patient_ids:
            try:
                p_res = (
                    supabase_admin
                    .table("patients")
                    .select("id, full_name, health_id")
                    .in_("id", patient_ids)
                    .execute()
                )
                for p in (p_res.data or []):
                    patients_map[p["id"]] = p
            except Exception:
                pass
    except Exception as e:
        print("Note: Supabase query in access-audit notifications (offline or fallback):", repr(e))

    try:
        notifications_data = get_doctor_notifications(
            doctor_id=doctor_id,
            access_requests=records,
            patients_map=patients_map,
            limit=limit
        )

        return jsonify({"success": True, **notifications_data}), 200

    except Exception as e:
        print("Error generating notifications:", repr(e))
        return jsonify({"success": False, "error": "Failed to load notifications."}), 500


@app.route("/doctor/access-audit/api/notifications/<notification_id>/read", methods=["POST"])
def doctor_access_audit_mark_notification_read(notification_id):
    """Mark a notification or all notifications as read."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    doctor_id = session.get("doctor_id")

    if notification_id == "all":
        body = request.get_json(silent=True) or {}
        ids = body.get("notification_ids", [])
        if not ids:
            try:
                req_res = (
                    supabase_admin
                    .table("access_requests")
                    .select("id, status")
                    .eq("doctor_id", doctor_id)
                    .execute()
                )
                records = req_res.data or []
                notifs = get_doctor_notifications(doctor_id=doctor_id, access_requests=records, limit=100)
                ids = [n["id"] for n in notifs.get("notifications", [])]
            except Exception:
                pass
        mark_all_notifications_as_read(doctor_id, ids)
    else:
        mark_notification_as_read(doctor_id, notification_id)

    return jsonify({"success": True, "message": "Notification read status updated."}), 200


@app.route("/doctor/access-audit/api/search-patient", methods=["GET"])
def doctor_access_search_patient():
    """Search patients by Health ID or Name for access requests."""
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Doctor authentication required"}), 401

    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify({"success": True, "patients": []}), 200

    try:
        query = supabase_admin.table("patients").select("id, full_name, health_id, gender, date_of_birth")
        if q.upper().startswith("OMC-"):
            res = query.ilike("health_id", f"%{q}%").limit(8).execute()
        else:
            res = query.ilike("full_name", f"%{q}%").limit(8).execute()

        patients = res.data or []
        return jsonify({"success": True, "patients": patients}), 200
    except Exception as e:
        print("Error searching patient:", repr(e))
        return jsonify({"success": False, "error": "Failed to search patient records."}), 500



# ============================================================
# DOCTOR PROFILE ROUTES & APIS
# ============================================================

@app.route("/doctor/profile")
def doctor_profile():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")
    profile = get_doctor_profile(doctor_id, supabase_admin, session)
    documents = list_doctor_documents(doctor_id, supabase_admin)
    preferences = get_working_preferences(doctor_id, supabase_admin)
    active_sessions = get_active_sessions_info(
        doctor_id,
        remote_addr=request.remote_addr,
        user_agent_str=request.headers.get("User-Agent")
    )
    two_factor = get_two_factor_status(doctor_id)

    return render_template(
        "doctor/doctor_profile.html",
        doctor=profile,
        documents=documents,
        preferences=preferences,
        active_sessions=active_sessions,
        two_factor=two_factor
    )


@app.route("/doctor/profile/api/details", methods=["GET"])
def doctor_profile_api_details():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    profile = get_doctor_profile(doctor_id, supabase_admin, session)
    if isinstance(profile, dict):
        profile = dict(profile)
        profile.pop("password", None)

    documents = list_doctor_documents(doctor_id, supabase_admin)
    preferences = get_working_preferences(doctor_id, supabase_admin)
    active_sessions = get_active_sessions_info(
        doctor_id,
        remote_addr=request.remote_addr,
        user_agent_str=request.headers.get("User-Agent")
    )
    two_factor = get_two_factor_status(doctor_id)

    return jsonify({
        "success": True,
        "profile": profile,
        "documents": documents,
        "preferences": preferences,
        "active_sessions": active_sessions,
        "two_factor": two_factor
    }), 200


@app.route("/doctor/profile/api/update", methods=["POST"])
def doctor_profile_api_update():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    data = request.get_json(silent=True) or request.form.to_dict()

    success, message, updated_profile = update_doctor_profile(doctor_id, data, supabase_admin)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    if "full_name" in data and data["full_name"]:
        session["doctor_name"] = data["full_name"]

    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="DOCTOR_PROFILE_UPDATED",
            status="SUCCESS",
            metadata={"updated_fields": list(data.keys())},
            client_ip=request.remote_addr
        )
    except Exception as e:
        print("[DoctorProfile] Audit log notice:", e)

    if isinstance(updated_profile, dict):
        updated_profile = dict(updated_profile)
        updated_profile.pop("password", None)

    return jsonify({"success": True, "message": message, "profile": updated_profile}), 200


@app.route("/doctor/profile/api/photo", methods=["POST"])
def doctor_profile_api_photo():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    if "photo" not in request.files:
        return jsonify({"success": False, "error": "No photograph file provided."}), 400

    file = request.files["photo"]
    if not file or not file.filename:
        return jsonify({"success": False, "error": "No file selected."}), 400

    file_bytes = file.read()
    filename = secure_filename(file.filename) or "photo.jpg"
    content_type = file.content_type or "image/jpeg"

    success, message, photo_url = upload_doctor_photo(
        doctor_id, file_bytes, filename, content_type, supabase_admin
    )
    if not success:
        return jsonify({"success": False, "error": message}), 400

    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="DOCTOR_PROFILE_PHOTO_UPDATED",
            status="SUCCESS",
            metadata={"filename": filename},
            client_ip=request.remote_addr
        )
    except Exception as e:
        print("[DoctorProfile] Photo audit log notice:", e)

    return jsonify({"success": True, "message": message, "photo_url": photo_url}), 200


@app.route("/doctor/profile/api/photo", methods=["DELETE"])
def doctor_profile_api_delete_photo():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    success, message = delete_doctor_photo(doctor_id, supabase_admin)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="DOCTOR_PROFILE_PHOTO_REMOVED",
            status="SUCCESS",
            client_ip=request.remote_addr
        )
    except Exception as e:
        print("[DoctorProfile] Photo remove audit log notice:", e)

    return jsonify({"success": True, "message": message, "default_avatar": True}), 200


@app.route("/doctor/profile/api/preferences", methods=["GET", "POST"])
def doctor_profile_api_preferences():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
        success, message, clean_prefs = update_working_preferences(doctor_id, data, supabase_admin)
        if not success:
            return jsonify({"success": False, "error": message}), 400

        try:
            log_audit_event(
                doctor_id=doctor_id,
                action="WORKING_PREFERENCES_UPDATED",
                status="SUCCESS",
                client_ip=request.remote_addr
            )
        except Exception as e:
            print("[DoctorProfile] Prefs audit log notice:", e)

        return jsonify({"success": True, "message": message, "preferences": clean_prefs}), 200

    prefs = get_working_preferences(doctor_id, supabase_admin)
    return jsonify({"success": True, "preferences": prefs}), 200


@app.route("/doctor/profile/api/documents", methods=["GET"])
def doctor_profile_api_documents():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    documents = list_doctor_documents(doctor_id, supabase_admin)
    return jsonify({"success": True, "documents": documents}), 200


@app.route("/doctor/profile/api/documents/upload", methods=["POST"])
def doctor_profile_api_documents_upload():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    file = request.files.get("document_file") or request.files.get("file")
    if not file or not file.filename:
        return jsonify({"success": False, "error": "Please select a document file to upload."}), 400

    document_name = request.form.get("document_name", "").strip()
    document_type = request.form.get("document_type", "other").strip()

    file_bytes = file.read()
    filename = secure_filename(file.filename) or "credential.pdf"
    content_type = file.content_type or "application/pdf"

    success, message, doc_record = upload_doctor_document(
        doctor_id, file_bytes, filename, content_type, document_name, document_type, supabase_admin
    )
    if not success:
        return jsonify({"success": False, "error": message}), 400

    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="CREDENTIAL_DOCUMENT_UPLOADED",
            status="SUCCESS",
            metadata={"document_name": doc_record.get("document_name"), "document_type": document_type},
            client_ip=request.remote_addr
        )
    except Exception as e:
        print("[DoctorProfile] Document upload audit notice:", e)

    return jsonify({"success": True, "message": message, "document": doc_record}), 201


@app.route("/doctor/profile/api/documents/<document_id>/view")
def doctor_profile_api_document_view(document_id):
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")
    doc = get_document_for_doctor(doctor_id, document_id, supabase_admin)
    if not doc:
        flash("Document not found or access denied.", "error")
        return redirect(url_for("doctor_profile"))

    file_path = doc.get("file_path", "")
    filename = os.path.basename(file_path)
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads", "doctors", str(doctor_id), "documents", filename)

    if os.path.exists(local_path):
        return send_file(local_path, mimetype=doc.get("mime_type", "application/pdf"))

    file_url = doc.get("file_url")
    if file_url:
        return redirect(file_url)

    flash("Unable to locate document file.", "error")
    return redirect(url_for("doctor_profile"))


@app.route("/doctor/profile/api/documents/<document_id>/download")
def doctor_profile_api_document_download(document_id):
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")
    doc = get_document_for_doctor(doctor_id, document_id, supabase_admin)
    if not doc:
        flash("Document not found or access denied.", "error")
        return redirect(url_for("doctor_profile"))

    file_path = doc.get("file_path", "")
    filename = os.path.basename(file_path)
    download_name = doc.get("file_name") or filename
    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads", "doctors", str(doctor_id), "documents", filename)

    if os.path.exists(local_path):
        return send_file(local_path, as_attachment=True, download_name=download_name)

    file_url = doc.get("file_url")
    if file_url:
        return redirect(file_url)

    flash("Unable to download document file.", "error")
    return redirect(url_for("doctor_profile"))


@app.route("/doctor/profile/api/documents/<document_id>", methods=["DELETE"])
def doctor_profile_api_document_delete(document_id):
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    success, message = delete_doctor_document(doctor_id, document_id, supabase_admin)
    if not success:
        return jsonify({"success": False, "error": message}), 404

    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="CREDENTIAL_DOCUMENT_DELETED",
            status="SUCCESS",
            metadata={"document_id": document_id},
            client_ip=request.remote_addr
        )
    except Exception as e:
        print("[DoctorProfile] Document delete audit notice:", e)

    return jsonify({"success": True, "message": message}), 200


@app.route("/doctor/profile/api/change-password", methods=["POST"])
def doctor_profile_api_change_password():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    data = request.get_json(silent=True) or request.form.to_dict()

    current_password = data.get("current_password", "").strip()
    new_password = data.get("new_password", "").strip()
    confirm_password = data.get("confirm_password", "").strip()

    success, message = change_doctor_password(
        doctor_id, current_password, new_password, confirm_password, supabase_admin
    )
    if not success:
        return jsonify({"success": False, "error": message}), 400

    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="DOCTOR_PASSWORD_CHANGED",
            status="SUCCESS",
            client_ip=request.remote_addr
        )
    except Exception as e:
        print("[DoctorProfile] Password change audit notice:", e)

    return jsonify({"success": True, "message": message}), 200


# ============================================================
# DOCTOR SETTINGS ROUTES & APIS
# ============================================================

@app.route("/doctor/settings")
def doctor_settings():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")
    profile = get_doctor_profile(doctor_id, supabase_admin, session)
    settings = get_doctor_settings(doctor_id, supabase_admin)
    preferences = get_working_preferences(doctor_id, supabase_admin)
    active_sessions = get_active_sessions_info(
        doctor_id,
        remote_addr=request.remote_addr,
        user_agent_str=request.headers.get("User-Agent")
    )
    services = check_connected_services_status(supabase_admin)
    two_factor = get_two_factor_status(doctor_id)

    return render_template(
        "doctor/doctor_settings.html",
        doctor=profile,
        settings=settings,
        preferences=preferences,
        active_sessions=active_sessions,
        services=services,
        two_factor=two_factor
    )


@app.route("/doctor/settings/api/preferences", methods=["GET", "POST"])
def doctor_settings_api_preferences():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
        success, message, clean_settings = update_doctor_settings(doctor_id, data, supabase_admin)
        if not success:
            return jsonify({"success": False, "error": message}), 400

        try:
            log_audit_event(
                doctor_id=doctor_id,
                action="DOCTOR_SETTINGS_UPDATED",
                status="SUCCESS",
                metadata={"updated_fields": list(data.keys())},
                client_ip=request.remote_addr
            )
        except Exception as e:
            print("[DoctorSettings] Settings update audit error:", e)

        return jsonify({"success": True, "message": message, "settings": clean_settings}), 200

    settings = get_doctor_settings(doctor_id, supabase_admin)
    return jsonify({"success": True, "settings": settings}), 200


@app.route("/doctor/settings/api/change-password", methods=["POST"])
def doctor_settings_api_change_password():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    data = request.get_json(silent=True) or request.form.to_dict()

    current_password = data.get("current_password", "").strip()
    new_password = data.get("new_password", "").strip()
    confirm_password = data.get("confirm_password", "").strip()

    success, message = change_doctor_password(
        doctor_id, current_password, new_password, confirm_password, supabase_admin
    )
    if not success:
        return jsonify({"success": False, "error": message}), 400

    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="DOCTOR_PASSWORD_CHANGED",
            status="SUCCESS",
            client_ip=request.remote_addr
        )
    except Exception as e:
        print("[DoctorSettings] Password change audit notice:", e)

    return jsonify({"success": True, "message": message}), 200


@app.route("/doctor/settings/api/sessions", methods=["GET"])
def doctor_settings_api_sessions():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    sessions_list = get_active_sessions_info(
        doctor_id,
        remote_addr=request.remote_addr,
        user_agent_str=request.headers.get("User-Agent")
    )
    return jsonify({"success": True, "sessions": sessions_list}), 200


@app.route("/doctor/settings/api/sessions/<session_id>/revoke", methods=["POST"])
def doctor_settings_api_session_revoke(session_id):
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="DOCTOR_SESSION_REVOKED",
            status="SUCCESS",
            metadata={"session_id": session_id},
            client_ip=request.remote_addr
        )
    except Exception as e:
        print("[DoctorSettings] Session revoke audit notice:", e)

    return jsonify({"success": True, "message": f"Session {session_id} has been revoked."}), 200


@app.route("/doctor/settings/api/services/status", methods=["GET"])
def doctor_settings_api_services_status():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    services_status = check_connected_services_status(supabase_admin)
    return jsonify({"success": True, "services": services_status}), 200


@app.route("/doctor/settings/api/export", methods=["GET"])
def doctor_settings_api_export():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session.get("doctor_id")
    export_data = export_doctor_data(doctor_id, supabase_admin, session)

    try:
        log_audit_event(
            doctor_id=doctor_id,
            action="DOCTOR_DATA_EXPORTED",
            status="SUCCESS",
            client_ip=request.remote_addr
        )
    except Exception as e:
        print("[DoctorSettings] Export audit notice:", e)

    response = jsonify(export_data)
    safe_doc_id = str(doctor_id).replace("-", "")[:8]
    response.headers["Content-Disposition"] = f"attachment; filename=omnicare_doctor_data_{safe_doc_id}.json"
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


@app.route("/doctor/settings/api/delete-account", methods=["POST"])
def doctor_settings_api_delete_account():
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    doctor_id = session.get("doctor_id")
    data = request.get_json(silent=True) or request.form.to_dict()
    password_confirm = data.get("password_confirm", "").strip()

    success, message = deactivate_doctor_account(doctor_id, password_confirm, supabase_admin)
    if not success:
        return jsonify({"success": False, "error": message}), 400

    session.clear()
    return jsonify({"success": True, "message": message}), 200
# ---------------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------------
# =========================================================
# WORKSPACE & RECORD ACCESS VERIFICATION HELPER
# =========================================================
def check_workspace_access(patient_id):
    """
    Validates if the caller is authorized to view this patient's records.
    Supports:
    1. Active External Consultation session (5-min OTP)
    2. Active Doctor OTP session (5-min OTP)
    3. Approved Doctor Access Request (active, non-expired)
    """
    pid = str(patient_id).strip()

    # 1. Check External Consultation (Session-based, non-logged in visitor)
    ext_sess = session.get("external_consultation")
    if ext_sess and str(ext_sess.get("patient_id")) == pid:
        verified = ExternalConsultationService.get_session(ext_sess.get("session_id"))
        if verified and verified.get("status") == "active":
            now_ts = int(datetime.now(timezone.utc).timestamp())
            rem = max(0, verified.get("expires_at_timestamp", 0) - now_ts)
            return True, {
                "is_external": True,
                "read_only": True,
                "remaining_seconds": rem,
                "session": verified,
                "doctor_id": "EXTERNAL_CONSULTATION"
            }, ""
        else:
            session.pop("external_consultation", None)
            return False, {}, "External consultation session has expired or was revoked."

    # 2. Check Doctor Login
    doctor_id = session.get("doctor_id")
    if not doctor_id:
        return False, {}, "Please login as a doctor or authenticate via patient QR OTP."

    # 3. Check Active Doctor OTP Session
    doc_otp = session.get("active_otp_access")
    if doc_otp and str(doc_otp.get("patient_id")) == pid:
        verified = ExternalConsultationService.get_session(doc_otp.get("session_id"))
        if verified and verified.get("status") == "active":
            now_ts = int(datetime.now(timezone.utc).timestamp())
            rem = max(0, verified.get("expires_at_timestamp", 0) - now_ts)
            return True, {
                "is_external": False,
                "read_only": True,
                "remaining_seconds": rem,
                "session": verified,
                "doctor_id": str(doctor_id)
            }, ""

    # 4. Check standard access_requests in database
    try:
        access_res = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", pid)
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .execute()
        )
        records = access_res.data or []
        if not records:
            return False, {}, "You do not have active access to this patient's medical records."

        acc = records[0]
        expires_at = acc.get("expires_at")
        if expires_at:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) >= exp_dt:
                try:
                    supabase_admin.table("access_requests").update({"status": "expired"}).eq("id", acc["id"]).execute()
                except Exception:
                    pass
                return False, {}, "This patient's temporary access has expired."

        return True, {
            "is_external": False,
            "read_only": False,
            "remaining_seconds": None,
            "access_record": acc,
            "doctor_id": str(doctor_id)
        }, ""
    except Exception as e:
        print("Database error checking access:", repr(e))
        return False, {}, "Failed to verify access permissions."


@app.route("/patient/qr-health-id", endpoint="patient_health_card")
def patient_health_card():

    if "patient_id" not in session:
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]

    try:

        # =================================================
        # GET PATIENT INFORMATION
        # =================================================

        response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )

        patient = response.data

        if not patient:
            flash(
                "Patient information not found.",
                "error"
            )

            return redirect(
                url_for("patient_dashboard")
            )

        # =================================================
        # CREATE SHORT PATIENT-FRIENDLY HEALTH ID
        # =================================================
        #
        # Example:
        # OMC-P1025
        #
        # If your database already has a health_id column,
        # use that value instead.
        #

        health_id = patient.get("health_id")

        if not health_id:

            # Create a short ID using patient database ID
            health_id = f"OMC-P{str(patient_id)[-4:].upper()}"
            (
              supabase_admin
              .table("patients")
              .update({
              "health_id": health_id
               })
              .eq("id", patient_id)
              .execute()
            )
        # =================================================
        # GENERATE REAL QR CODE
        # =================================================
        #
        # IMPORTANT:
        # The QR does NOT contain medical records.
        #
        # It only contains a secure OmniCare identifier.
        #

        # Universal Canonical QR Token (Non-guessable, does not leak database UUID)
        qr_token = ExternalConsultationService.get_or_create_qr_token(patient_id, health_id=health_id)
        canonical_domain = (os.getenv("CANONICAL_DOMAIN") or request.host_url.rstrip('/')).rstrip('/')
        qr_data = f"{canonical_domain}/qr/{qr_token}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4
        )

        qr.add_data(qr_data)
        qr.make(fit=True)

        qr_image = qr.make_image(
            fill_color="#24105f",
            back_color="white"
        )

        # =================================================
        # CONVERT QR IMAGE TO BASE64
        # =================================================

        qr_buffer = io.BytesIO()

        qr_image.save(
            qr_buffer,
            format="PNG"
        )

        qr_buffer.seek(0)

        qr_code = base64.b64encode(
            qr_buffer.getvalue()
        ).decode("utf-8")

        # =================================================
        # RENDER HEALTH CARD
        # =================================================

        return render_template(
            "patient/patient_health_card.html",

            # Patient information
            patient=patient,

            # Short patient-friendly ID
            health_id=health_id,

            # Real QR image
            qr_code=qr_code,
            qr_token=qr_token
        )

    except Exception as e:

        print("=" * 60)
        print("HEALTH CARD ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Error:", repr(e))
        print("=" * 60)

        flash(
            "Unable to load your Health Card.",
            "error"
        )

        return redirect(
            url_for("patient_dashboard")
        )


# =========================================================
# CANONICAL UNIVERSAL PATIENT QR LANDING PAGE
# =========================================================
@app.route("/qr/<qr_identifier>", endpoint="public_patient_qr_landing")
def public_patient_qr_landing(qr_identifier):
    patient = None
    health_id = None
    patient_id = None

    # 1. Resolve via ExternalConsultationService (token or health_id mapping)
    token_record = ExternalConsultationService.resolve_qr_token(qr_identifier)
    if token_record:
        patient_id = token_record.get("patient_id")

    if not patient_id:
        # Check direct lookup by health_id or id
        try:
            res = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("health_id", qr_identifier)
                .maybe_single()
                .execute()
            )
            if res.data:
                patient = res.data
                patient_id = patient.get("id")
        except Exception:
            pass

    if not patient and patient_id:
        try:
            res = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("id", patient_id)
                .single()
                .execute()
            )
            patient = res.data
        except Exception as e:
            print("QR Landing Patient Fetch Error:", repr(e))

    if not patient:
        # Final fallback: direct check if qr_identifier matches a database id
        try:
            res = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("id", qr_identifier)
                .maybe_single()
                .execute()
            )
            patient = res.data
        except Exception:
            pass

    if not patient:
        return render_template("patient/patient_not_found.html"), 404

    health_id = patient.get("health_id") or (f"OMC-P{str(patient['id'])[-4:].upper()}" if patient.get("id") else "OMC-PATIENT")

    # Calculate age safely
    age = patient.get("age")
    if not age and patient.get("date_of_birth"):
        try:
            from datetime import datetime, date
            dob_str = str(patient.get("date_of_birth"))
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            today = date.today()
            calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            age = f"{calculated_age} Years"
        except Exception:
            age = None
    elif age and str(age).isdigit():
        age = f"{age} Years"

    # Log external QR scan
    try:
        log_clinical_event(
            doctor_id="PUBLIC_VISITOR",
            action="INTERNAL_QR_SCAN" if "doctor_id" in session else "EXTERNAL_CONSULTATION_REQUESTED",
            patient_ids=[str(patient["id"])],
            status="SUCCESS",
            metadata={"qr_identifier": qr_identifier, "is_doctor_logged_in": "doctor_id" in session},
            client_ip=request.remote_addr
        )
    except Exception:
        pass

    return render_template(
        "patient/public_patient_info.html",
        patient=patient,
        health_id=health_id,
        qr_identifier=qr_identifier,
        calculated_age=age
    )


# Backward-compatible redirect for legacy URLs
@app.route("/patient-info/<patient_id>", endpoint="public_patient_info")
def public_patient_info(patient_id):
    qr_token = ExternalConsultationService.get_or_create_qr_token(patient_id)
    return public_patient_qr_landing(qr_identifier=qr_token)


# =========================================================
# EXTERNAL CONSULTATION — REQUEST PATIENT OTP
# =========================================================
@app.route("/qr/<qr_identifier>/request-consultation", methods=["POST"])
def external_consultation_request_otp(qr_identifier):
    try:
        data = request.get_json(silent=True) or request.form.to_dict()

        visitor_name = str(data.get("visitor_name") or "").strip()
        visitor_mobile = str(data.get("visitor_mobile") or "").strip()
        visitor_age = str(data.get("visitor_age") or "").strip()
        visitor_role = str(data.get("visitor_role") or "Doctor").strip()

        if not visitor_name:
            return jsonify({"success": False, "error": "Please enter your full name."}), 400

        digits_mobile = [c for c in visitor_mobile if c.isdigit()]
        if len(digits_mobile) < 10:
            return jsonify({"success": False, "error": "Please enter a valid 10-digit mobile number."}), 400

        if not visitor_age.isdigit() or int(visitor_age) < 18:
            return jsonify({"success": False, "error": "Please enter a valid adult age."}), 400

        # Resolve patient
        token_record = ExternalConsultationService.resolve_qr_token(qr_identifier)
        patient_id = token_record.get("patient_id") if token_record else None

        if not patient_id:
            try:
                res = supabase_admin.table("patients").select("id, phone, email, full_name").or_(f"health_id.eq.{qr_identifier},id.eq.{qr_identifier}").maybe_single().execute()
                if res.data:
                    patient = res.data
                    patient_id = patient.get("id")
                else:
                    return jsonify({"success": False, "error": "Patient not found for this QR identifier."}), 404
            except Exception:
                return jsonify({"success": False, "error": "Patient not found."}), 404
        else:
            try:
                res = supabase_admin.table("patients").select("id, phone, email, full_name").eq("id", patient_id).single().execute()
                patient = res.data or {}
            except Exception:
                patient = {"id": patient_id}

        # Request OTP strictly for the PATIENT (never the visitor)
        success, msg, challenge_meta = MSG91OTPService.request_otp(
            patient_id=str(patient_id),
            patient_phone=patient.get("phone"),
            patient_email=patient.get("email"),
            visitor_name=visitor_name,
            consultation_type="External Clinical Consultation"
        )

        if not success:
            return jsonify({"success": False, "error": msg}), 400

        # Cache visitor intake metadata in session for the verification step
        session[f"visitor_meta_{challenge_meta['challenge_id']}"] = {
            "full_name": visitor_name,
            "mobile": visitor_mobile,
            "age": visitor_age,
            "role": visitor_role,
            "hospital_name": data.get("hospital_name", ""),
            "location": data.get("location", ""),
            "email": data.get("visitor_email", ""),
            "qualification": data.get("qualification", ""),
            "medical_registration_number": data.get("medical_registration_number", "")
        }

        try:
            log_clinical_event(
                doctor_id=f"EXT_{digits_mobile[-4:]}",
                action="EXTERNAL_CONSULTATION_OTP_SENT",
                patient_ids=[str(patient_id)],
                status="SUCCESS",
                metadata={"visitor_name": visitor_name, "visitor_role": visitor_role, "masked_dest": challenge_meta["masked_destination"]},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": msg,
            "challenge_id": challenge_meta["challenge_id"],
            "masked_destination": challenge_meta["masked_destination"],
            "expires_in_seconds": challenge_meta["expires_in_seconds"],
            "otp_length": challenge_meta.get("otp_length", 4),
            "is_demo_mode": challenge_meta.get("is_demo_mode", False),
            "demo_otp_notice": challenge_meta.get("demo_otp_notice")
        }), 200

    except Exception as e:
        print("External Consultation Request Error:", repr(e))
        return jsonify({"success": False, "error": "An unexpected error occurred while requesting consultation."}), 500


# =========================================================
# EXTERNAL CONSULTATION — VERIFY OTP & CREATE 5-MIN SESSION
# =========================================================
@app.route("/qr/<qr_identifier>/verify-otp", methods=["POST"])
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
            return jsonify({"success": False, "error": msg}), 400

        # Retrieve visitor details
        visitor_details = session.pop(f"visitor_meta_{challenge_id}", {}) or {
            "full_name": verified_meta.get("visitor_name") or "External Doctor",
            "role": "Doctor"
        }

        # Create 5-minute active session
        session_record = ExternalConsultationService.create_session(
            patient_id=str(patient_id),
            visitor_details=visitor_details,
            is_internal_doctor=False
        )

        # Store in visitor Flask session
        session["external_consultation"] = session_record

        try:
            log_clinical_event(
                doctor_id="EXTERNAL_CONSULTATION",
                action="EXTERNAL_CONSULTATION_SESSION_STARTED",
                patient_ids=[str(patient_id)],
                status="SUCCESS",
                metadata={"session_id": session_record["session_id"], "visitor_name": session_record["visitor_name"]},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "Patient authorization verified successfully.",
            "redirect_url": url_for("doctor_patient_workspace", patient_id=str(patient_id))
        }), 200

    except Exception as e:
        print("External Consultation Verify Error:", repr(e))
        return jsonify({"success": False, "error": "Verification failed due to an internal error."}), 500


# =========================================================
# PATIENT PORTAL — REVOKE CONSULTATION SESSION EARLY
# =========================================================
@app.route("/patient/revoke-consultation/<session_id>", methods=["POST"])
def patient_revoke_consultation(session_id):
    if "patient_id" not in session:
        flash("Please login to manage your consultations.", "error")
        return redirect(url_for("patient_login"))

    patient_id = session["patient_id"]
    success, msg = ExternalConsultationService.revoke_session(session_id, patient_id)

    if success:
        try:
            log_clinical_event(
                doctor_id="PATIENT",
                action="EXTERNAL_CONSULTATION_SESSION_REVOKED",
                patient_ids=[str(patient_id)],
                status="SUCCESS",
                metadata={"session_id": session_id},
                client_ip=request.remote_addr
            )
        except Exception:
            pass
        flash("Consultation access has been revoked immediately.", "success")
    else:
        flash(msg, "error")

    return redirect(url_for("patient_doctor_access"))
@app.route("/doctor/request-access/<patient_id>", methods=["POST"])
def doctor_request_access(patient_id):

    # Check doctor login
    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    # Keep the Health ID after returning to Patient Access
    health_id = request.form.get("health_id", "").strip()

    try:

        # -----------------------------------------
        # CHECK EXISTING REQUEST
        # -----------------------------------------

        existing = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("patient_id", patient_id)
            .eq("doctor_id", doctor_id)
            .in_("status", ["pending", "active"])
            .execute()
        )

        if existing.data:

            existing_status = existing.data[0].get("status")

            if existing_status == "active":

                flash(
                    "You already have active access to this patient's medical records.",
                    "info"
                )

            else:

                flash(
                    "Access request is already waiting for patient approval.",
                    "info"
                )

            return redirect(
                url_for(
                    "doctor_patient_access",
                    health_id=health_id
                )
            )


        # -----------------------------------------
        # CREATE NEW ACCESS REQUEST
        # -----------------------------------------

        response = (
            supabase_admin
            .table("access_requests")
            .insert({
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "status": "pending",
                "access_method": "approval"
            })
            .execute()
        )


        # -----------------------------------------
        # SUCCESS
        # -----------------------------------------

        if response.data:

            flash(
                "✓ Access request sent successfully. Waiting for patient approval.",
                "success"
            )

        else:

            flash(
                "Unable to create access request.",
                "error"
            )


    except Exception as e:

        print("=" * 60)
        print("ACCESS REQUEST ERROR")
        print("=" * 60)
        print("Patient ID:", patient_id)
        print("Doctor ID:", doctor_id)
        print("Error:", repr(e))
        print("=" * 60)

        flash(
            "Something went wrong while requesting access.",
            "error"
        )


    # -----------------------------------------
    # RETURN TO PATIENT ACCESS
    # -----------------------------------------

    return redirect(
        url_for(
            "doctor_patient_access",
            health_id=health_id
        )
    )


@app.route("/doctor/patient-access", methods=["GET"])
def doctor_patient_access():

    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    identifier = request.args.get("identifier") or request.args.get("health_id", "").strip()

    patient = None
    error = None
    masked_phone = None

    if identifier:
        try:
            # 1. Try resolving via ExternalConsultationService (token / health_id)
            token_rec = ExternalConsultationService.resolve_qr_token(identifier)
            if token_rec and token_rec.get("patient_id"):
                res = supabase_admin.table("patients").select("*").eq("id", token_rec["patient_id"]).maybe_single().execute()
                patient = res.data

            # 2. Try health_id match
            if not patient:
                res = supabase_admin.table("patients").select("*").eq("health_id", identifier).maybe_single().execute()
                patient = res.data

            # 3. Try database ID match
            if not patient:
                res = supabase_admin.table("patients").select("*").eq("id", identifier).maybe_single().execute()
                patient = res.data

            if not patient:
                error = "No patient found with this Health ID or QR code."
            else:
                masked_phone = mask_phone_number(patient.get("phone"))

        except Exception as e:
            print("PATIENT ACCESS SEARCH ERROR:", repr(e))
            error = "Patient search failed. Please try again."

    return render_template(
        "doctor/patient_access.html",
        patient=patient,
        error=error,
        health_id=patient.get("health_id") if patient else identifier,
        identifier=identifier,
        masked_phone=masked_phone
    )


# =========================================================
# DOCTOR INTERNAL OTP ACCESS — SEND OTP
# =========================================================
@app.route("/doctor/patient-access/<patient_id>/send-otp", methods=["POST"])
def doctor_patient_send_otp(patient_id):
    if "doctor_id" not in session:
        return jsonify({"success": False, "error": "Please login as a doctor."}), 401

    doctor_id = session["doctor_id"]

    try:
        # Get doctor name
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
            "otp_length": challenge_meta.get("otp_length", 4),
            "is_demo_mode": challenge_meta.get("is_demo_mode", False),
            "demo_otp_notice": challenge_meta.get("demo_otp_notice")
        }), 200

    except Exception as e:
        print("Doctor Send OTP Error:", repr(e))
        return jsonify({"success": False, "error": f"Failed to send OTP to patient: {str(e)}"}), 500


# =========================================================
# DOCTOR INTERNAL OTP ACCESS — VERIFY OTP
# =========================================================
@app.route("/doctor/patient-access/<patient_id>/verify-otp", methods=["POST"])

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



        # Resolve doctor name for session audit
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





# ============================================================
# DOCTOR - PATIENT WORKSPACE
# ============================================================

import random
def generate_health_id():
    while True:

        number = random.randint(1000, 999999)

        health_id = f"OMC-P{number}"

        response = (
            supabase_admin
            .table("patients")
            .select("id")
            .eq("health_id", health_id)
            .execute()
        )

        if not response.data:
            return health_id

@app.route("/doctor/patient-records/<patient_id>")
def doctor_patient_records(patient_id):

    # Doctor must be logged in
    if "doctor_id" not in session:
        flash("Please login as a doctor.", "error")
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    try:
        # -----------------------------------------
        # CHECK ACTIVE ACCESS
        # -----------------------------------------

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
            flash(
                "You do not have active access to this patient's records.",
                "error"
            )
            return redirect(url_for(
                "doctor_patient_access"
            ))

        access = access_requests[0]

        # -----------------------------------------
        # CHECK EXPIRATION
        # -----------------------------------------

        expires_at = access.get("expires_at")

        if expires_at:
            expiry_time = datetime.fromisoformat(
                expires_at.replace("Z", "+00:00")
            )

            if datetime.now(timezone.utc) >= expiry_time:

                # Mark access as expired
                (
                    supabase_admin
                    .table("access_requests")
                    .update({
                        "status": "expired"
                    })
                    .eq("id", access["id"])
                    .execute()
                )

                flash(
                    "This temporary access has expired.",
                    "error"
                )

                return redirect(url_for(
                    "doctor_patient_access"
                ))

        # -----------------------------------------
        # GET PATIENT
        # -----------------------------------------

        patient_response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )

        patient = patient_response.data

        if not patient:
            flash("Patient not found.", "error")
            return redirect(url_for(
                "doctor_patient_access"
            ))

        # -----------------------------------------
        # GET MEDICAL RECORDS
        # -----------------------------------------

        records_response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("created_at", desc=True)
            .execute()
        )

        records = records_response.data or []

        return render_template(
            "doctor/patient_medical_records.html",
            patient=patient,
            records=records,
            access=access
        )

    except Exception as e:

        print("DOCTOR PATIENT RECORDS ERROR:", repr(e))

        flash(
            "Unable to load patient medical records.",
            "error"
        )

        return redirect(url_for(
            "doctor_patient_access"
        ))
    
# =========================================================
# DOCTOR - PATIENT WORKSPACE
# =========================================================
@app.route("/doctor/patient-workspace/<patient_id>")
def doctor_patient_workspace(patient_id):

    # Unified Access Verification (supports External Consultation, Doctor OTP, & Portal Consent)
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        flash(err_msg or "You do not have active access to this patient's medical records.", "error")
        if "external_consultation" in session:
            return redirect(url_for("public_patient_info", patient_id=patient_id))
        return redirect(url_for("doctor_my_patients"))

    is_external_consultation = access_info.get("is_external", False)
    read_only = access_info.get("read_only", False)
    remaining_seconds = access_info.get("remaining_seconds") or 300
    doctor_id = access_info.get("doctor_id", "EXTERNAL_CONSULTATION")
    access = access_info.get("access_record") or {
        "access_type": "temporary",
        "access_method": "otp" if is_external_consultation or read_only else "approval",
        "status": "active"
    }

    try:

        # -------------------------------------------------
        # 3. GET PATIENT
        # -------------------------------------------------

        patient_response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )

        patient = patient_response.data

        if not patient:

            flash(
                "Patient not found.",
                "error"
            )

            return redirect(
                url_for("doctor_my_patients")
            )

        try:
            log_audit_event(
                doctor_id=doctor_id,
                action="PATIENT_RECORD_VIEWED",
                patient_ids=[patient_id],
                status="SUCCESS",
                metadata={"patient_id": patient_id, "view": "workspace"},
                client_ip=request.remote_addr
            )
        except Exception:
            pass

        # -------------------------------------------------
        # 4. GET PATIENT MEDICAL RECORDS
        # -------------------------------------------------
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
        except Exception as rec_err:
            try:
                records_response = (
                    supabase_admin
                    .table("medical_records")
                    .select("*")
                    .eq("patient_id", patient_id)
                    .execute()
                )
                records = records_response.data or []
            except Exception as rec_err2:
                print("Notice: Medical records fetch:", repr(rec_err2))
                records = []

        for rec in records:
            if not rec.get("file_url") and rec.get("id"):
                try:
                    rec["file_url"] = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=rec["id"])
                except Exception:
                    pass

        # -------------------------------------------------
        # 5. GET AI HEALTH TIMELINE EVENTS
        # -------------------------------------------------
        try:
            timeline_response = (
                supabase_admin
                .table("health_timeline_events")
                .select("*")
                .eq("patient_id", patient_id)
                .order("event_date", desc=True)
                .execute()
            )
            timeline_events = timeline_response.data or []
        except Exception as time_err:
            print("Notice: Timeline events fetch:", repr(time_err))
            timeline_events = []

        # -------------------------------------------------
        # 6. DETECT MEDICAL CONFLICTS
        # -------------------------------------------------

        conflicts = detect_medical_conflicts(
            timeline_events
        )

        # -------------------------------------------------
        # 7. BUILD CONFLICT SUMMARY
        # -------------------------------------------------

        conflict_summary = {
            "total": len(conflicts),

            "high": sum(
                1
                for conflict in conflicts
                if conflict.get("severity") == "high"
            ),

            "medium": sum(
                1
                for conflict in conflicts
                if conflict.get("severity") == "medium"
            ),

            "low": sum(
                1
                for conflict in conflicts
                if conflict.get("severity") == "low"
            )
        }

        # -------------------------------------------------
        # 8. DEBUG INFORMATION
        # -------------------------------------------------

        print("=" * 70)
        print("DOCTOR PATIENT WORKSPACE")
        print("=" * 70)

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Doctor ID:",
            doctor_id
        )

        print(
            "Medical Records:",
            len(records)
        )

        print(
            "AI Timeline Events:",
            len(timeline_events)
        )

        print(
            "Medical Conflicts:",
            len(conflicts)
        )

        print(
            "High Conflicts:",
            conflict_summary["high"]
        )

        print(
            "Medium Conflicts:",
            conflict_summary["medium"]
        )

        print(
            "Low Conflicts:",
            conflict_summary["low"]
        )

        # -------------------------------------------------
        # 9. PRINT DETECTED CONFLICTS
        # -------------------------------------------------

        if conflicts:

            print("-" * 70)
            print("DETECTED MEDICAL CONFLICTS")
            print("-" * 70)

            for conflict in conflicts:

                print(
                    "Conflict Type:",
                    conflict.get("conflict_type")
                )

                print(
                    "Severity:",
                    conflict.get("severity")
                )

                print(
                    "Title:",
                    conflict.get("title")
                )

                print(
                    "Description:",
                    conflict.get("description")
                )

                print(
                    "Medication:",
                    conflict.get("medication_name")
                )

                # -----------------------------------------
                # PRINT SOURCE RECORDS
                # -----------------------------------------

                source_records = conflict.get("records") or []

                if source_records:

                    print("Source Records:")

                    for source in source_records:

                        print(
                            "  Date:",
                            source.get("event_date")
                        )

                        print(
                            "  Doctor:",
                            source.get("provider_name")
                        )

                        print(
                            "  Hospital:",
                            source.get("hospital_name")
                        )

                        print(
                            "  Record ID:",
                            source.get("medical_record_id")
                        )

                        print(
                            "  Dose:",
                            source.get("dose")
                        )

                        print(
                            "  Frequency:",
                            source.get("frequency")
                        )

                        print(
                            "  Duration:",
                            source.get("duration")
                        )

                        print(
                            "  Instructions:",
                            source.get("instructions")
                        )

                        print("-" * 40)

                print("-" * 70)

        else:

            print(
                "No medical conflicts detected."
            )

        print("=" * 70)

        # -------------------------------------------------
        # 9B. COMPUTE HEALTH TREND DATA
        # -------------------------------------------------
        patient_name = (
            patient.get("full_name")
            or patient.get("name")
            or "Patient"
        )

        trend_data = get_trend_analysis_data(
            timeline_events=timeline_events,
            medical_records=records,
            patient_name=patient_name
        )

        # -------------------------------------------------
        # 9C. LOAD DOCTOR PROFILE FOR DOCUMENT TEMPLATES
        # -------------------------------------------------
        doctor_profile = None
        if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
            try:
                doctor_profile = get_doctor_profile(doctor_id, supabase_admin, session)
            except Exception as dp_err:
                print("Notice: Doctor profile fetch notice:", repr(dp_err))
                doctor_profile = None

        if not doctor_profile:
            doctor_profile = {
                "full_name": session.get("doctor_name", "Doctor"),
                "email": session.get("doctor_email", ""),
                "hospital_name": session.get("doctor_hospital", "General Hospital"),
                "hospital_address": "",
                "phone": "",
                "specialization": "General Medicine",
                "registration_number": "",
                "qualification": "MBBS"
            }

        # -------------------------------------------------
        # 10. OPEN PATIENT WORKSPACE
        # -------------------------------------------------

        return render_template(
            "doctor/patient_workspace.html",

            patient=patient,

            records=records,

            timeline_events=timeline_events,

            conflicts=conflicts,

            conflict_summary=conflict_summary,

            access=access,

            trend_data=trend_data,

            doctor_profile=doctor_profile,

            is_external_consultation=is_external_consultation,
            read_only=read_only,
            remaining_seconds=remaining_seconds
        )

    except Exception as e:

        print("=" * 70)
        print("DOCTOR PATIENT WORKSPACE ERROR")
        print("=" * 70)

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Doctor ID:",
            doctor_id
        )

        print(
            "Error:",
            repr(e)
        )

        print("=" * 70)

        flash(
            "Unable to load patient workspace.",
            "error"
        )

        return redirect(
            url_for("doctor_my_patients")
        )
# ============================================================
# DOCTOR - VIEW ORIGINAL MEDICAL RECORD
# ============================================================

@app.route("/doctor/patient-record/<patient_id>/<record_id>")
def doctor_view_medical_record(patient_id, record_id):

    print("\n" + "=" * 80)
    print("DOCTOR VIEW ORIGINAL MEDICAL RECORD")
    print("=" * 80)

    # --------------------------------------------------------
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

    try:

        print("✅ Active access found")
        print("Access ID:", access.get("id"))
        print("Access Type:", access.get("access_type"))
        print("Expires At:", access.get("expires_at"))


        # ----------------------------------------------------
        # 3. CHECK EXPIRATION
        # ----------------------------------------------------

        expires_at = access.get("expires_at")

        if expires_at:

            print("\n[2] Checking access expiration...")

            expiry_time = datetime.fromisoformat(
                expires_at.replace("Z", "+00:00")
            )

            current_time = datetime.now(timezone.utc)

            print("Current UTC:", current_time)
            print("Expiry UTC :", expiry_time)

            if current_time >= expiry_time:

                print("❌ ACCESS EXPIRED")

                (
                    supabase_admin
                    .table("access_requests")
                    .update({
                        "status": "expired"
                    })
                    .eq("id", access["id"])
                    .execute()
                )

                flash(
                    "This patient's temporary access has expired.",
                    "error"
                )

                return redirect(
                    url_for("doctor_my_patients")
                )

            print("✅ Access is still valid")


        # ----------------------------------------------------
        # 4. GET MEDICAL RECORD
        # ----------------------------------------------------

        print("\n[3] Getting medical record...")

        record_response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("id", record_id)
            .eq("patient_id", patient_id)
            .execute()
        )

        records_found = record_response.data or []

        print(
            "Matching records:",
            len(records_found)
        )

        if not records_found:

            print("❌ MEDICAL RECORD NOT FOUND")

            print(
                "Record ID:",
                record_id
            )

            print(
                "Patient ID:",
                patient_id
            )

            flash(
                "Medical record not found.",
                "error"
            )

            return redirect(
                url_for(
                    "doctor_patient_workspace",
                    patient_id=patient_id
                )
            )

        record = records_found[0]

        print("✅ Medical record found")

        print(
            "Record title:",
            record.get("title")
        )

        print(
            "Record type:",
            record.get("record_type")
        )

        print(
            "Record ID:",
            record.get("id")
        )


        # ----------------------------------------------------
        # 5. GET FILE PATH
        # ----------------------------------------------------

        print("\n[4] Getting storage file path...")

        file_path = record.get("file_path")

        print(
            "Raw file_path:",
            repr(file_path)
        )

        if not file_path:

            print("❌ file_path IS EMPTY")

            flash(
                "Original medical file is not available.",
                "error"
            )

            return redirect(
                url_for(
                    "doctor_patient_workspace",
                    patient_id=patient_id
                )
            )


        # ----------------------------------------------------
        # 6. CLEAN STORAGE PATH
        #
        # If the database accidentally contains:
        #
        # medical-records/patient/file.pdf
        #
        # the storage API needs:
        #
        # patient/file.pdf
        # ----------------------------------------------------

        bucket_name = "medical-records"

        if file_path.startswith(
            bucket_name + "/"
        ):

            file_path = file_path[
                len(bucket_name) + 1:
            ]

        print(
            "Storage file path:",
            repr(file_path)
        )


        # ----------------------------------------------------
        # 7. CREATE SIGNED URL
        # ----------------------------------------------------

        print("\n[5] Creating Supabase signed URL...")

        signed_response = (
            supabase_admin
            .storage
            .from_(bucket_name)
            .create_signed_url(
                file_path,
                300
            )
        )

        print(
            "Signed URL response:",
            repr(signed_response)
        )


        # ----------------------------------------------------
        # 8. EXTRACT SIGNED URL
        # ----------------------------------------------------

        signed_url = None

        # Some supabase-py versions return a dictionary directly
        if isinstance(
            signed_response,
            dict
        ):

            signed_url = (
                signed_response.get("signedURL")
                or signed_response.get("signedUrl")
                or signed_response.get("signed_url")
            )

        # Some versions wrap the response
        elif hasattr(
            signed_response,
            "data"
        ):

            signed_data = signed_response.data

            print(
                "Signed response data:",
                repr(signed_data)
            )

            if isinstance(
                signed_data,
                dict
            ):

                signed_url = (
                    signed_data.get("signedURL")
                    or signed_data.get("signedUrl")
                    or signed_data.get("signed_url")
                )

            elif isinstance(
                signed_data,
                str
            ):

                signed_url = signed_data


        # ----------------------------------------------------
        # 9. VERIFY SIGNED URL
        # ----------------------------------------------------

        print(
            "\nExtracted signed URL:",
            repr(signed_url)
        )

        if not signed_url:

            print("\n❌ SIGNED URL WAS NOT GENERATED")

            print(
                "Bucket:",
                bucket_name
            )

            print(
                "File path:",
                file_path
            )

            flash(
                "Unable to generate a secure URL for the original medical record.",
                "error"
            )

            return redirect(
                url_for(
                    "doctor_patient_workspace",
                    patient_id=patient_id
                )
            )


        # ----------------------------------------------------
        # 10. SUCCESS
        # ----------------------------------------------------

        print("\n✅ SIGNED URL GENERATED SUCCESSFULLY")

        print(
            "Opening original medical record..."
        )

        print("=" * 80)

        return redirect(
            signed_url
        )


    except Exception as e:

        print("\n" + "=" * 80)
        print("❌ VIEW ORIGINAL MEDICAL RECORD ERROR")
        print("=" * 80)

        print(
            "Patient ID:",
            patient_id
        )

        print(
            "Doctor ID:",
            doctor_id
        )

        print(
            "Record ID:",
            record_id
        )

        print(
            "Error type:",
            type(e).__name__
        )

        print(
            "Error:",
            repr(e)
        )

        print("=" * 80)

        flash(
            "Unable to open the original medical record.",
            "error"
        )

        return redirect(
            url_for(
                "doctor_patient_workspace",
                patient_id=patient_id
            )
        )

# ============================================================
# DOCTOR - PATIENT WORKSPACE MEDICAL RECORD & TEMPLATE ROUTES
# ============================================================

@app.route("/doctor/patient-workspace/<patient_id>/upload-medical-record", methods=["POST"])
def doctor_upload_patient_medical_record(patient_id):
    """Option A: Upload existing medical file with metadata & Gemini extraction."""
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

    if access_info.get("read_only", False) or access_info.get("is_external", False):
        return jsonify({
            "success": False,
            "error": "Access is read-only. Medical record upload is prohibited during read-only sessions."
        }), 403

    doctor_id = access_info.get("doctor_id") or session.get("doctor_id") or "DOCTOR"
    doctor_data = {}
    if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
        try:
            doctor_data = get_doctor_profile(doctor_id, supabase_admin, session) or {}
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

        if not saved_rec.get("file_url") and saved_rec.get("id"):
            try:
                saved_rec["file_url"] = url_for("doctor_view_medical_record", patient_id=patient_id, record_id=saved_rec["id"])
            except Exception:
                pass

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
    """Option B: Create consultation note with vitals, diagnosis, and ReportLab PDF."""
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

    if access_info.get("read_only", False) or access_info.get("is_external", False):
        return jsonify({"success": False, "error": "Access is read-only. Record creation is prohibited."}), 403

    doctor_id = access_info.get("doctor_id") or session.get("doctor_id") or "DOCTOR"
    doctor_data = {}
    if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
        try:
            doctor_data = get_doctor_profile(doctor_id, supabase_admin, session) or {}
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
    """Option C: Create hospital-style prescription with M/A/E/N medicines and ReportLab PDF."""
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

    if access_info.get("read_only", False) or access_info.get("is_external", False):
        return jsonify({"success": False, "error": "Access is read-only. Prescription creation is prohibited."}), 403

    doctor_id = access_info.get("doctor_id") or session.get("doctor_id") or "DOCTOR"
    doctor_data = {}
    if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
        try:
            doctor_data = get_doctor_profile(doctor_id, supabase_admin, session) or {}
        except Exception:
            doctor_data = {}

    patient_res = supabase_admin.table("patients").select("*").eq("id", patient_id).single().execute()
    patient_data = patient_res.data or {}

    data = request.get_json(silent=True) or request.form.to_dict()
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
    """Option D: Create lab, scan, discharge summary, medical certificate, referral letter."""
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

    if access_info.get("read_only", False) or access_info.get("is_external", False):
        return jsonify({"success": False, "error": "Access is read-only. Document creation is prohibited."}), 403

    doctor_id = access_info.get("doctor_id") or session.get("doctor_id") or "DOCTOR"
    doctor_data = {}
    if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
        try:
            doctor_data = get_doctor_profile(doctor_id, supabase_admin, session) or {}
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
    """Generate in-memory PDF stream for live preview without saving."""
    is_auth, access_info, err_msg = check_workspace_access(patient_id)
    if not is_auth:
        return jsonify({"success": False, "error": err_msg or "Unauthorized workspace access."}), 403

    if access_info.get("read_only", False) or access_info.get("is_external", False):
        return jsonify({"success": False, "error": "Access is read-only."}), 403

    doctor_id = access_info.get("doctor_id") or session.get("doctor_id") or "DOCTOR"
    doctor_data = {}
    if doctor_id and doctor_id != "EXTERNAL_CONSULTATION":
        try:
            doctor_data = get_doctor_profile(doctor_id, supabase_admin, session) or {}
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
    """Return JSON list of current patient records with direct view links."""
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

# =========================================================
# DOCTOR - MY PATIENTS
# =========================================================

# =========================================================
# DOCTOR - MY PATIENTS
# =========================================================

@app.route("/doctor/my-patients")
def doctor_my_patients():

    # -----------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # -----------------------------------------------------

    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    patients = []

    try:

        print("\n" + "=" * 70)
        print("DOCTOR MY PATIENTS")
        print("=" * 70)

        print("Doctor ID:", doctor_id)

        # -------------------------------------------------
        # 2. GET ACTIVE ACCESS REQUESTS
        # -------------------------------------------------

        access_response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .order("approved_at", desc=True)
            .execute()
        )

        access_requests = access_response.data or []

        print("Active access requests:", len(access_requests))
        print("Access data:", access_requests)

        # -------------------------------------------------
        # 3. PROCESS EACH AUTHORIZED PATIENT
        # -------------------------------------------------

        for access in access_requests:

            patient_id = access.get("patient_id")

            print("\nPatient ID from access:", patient_id)

            if not patient_id:
                continue

            # -------------------------------------------------
            # 4. CHECK EXPIRATION
            # -------------------------------------------------

            expires_at = access.get("expires_at")
            access_type = access.get("access_type") or "temporary"

            if expires_at:

                try:

                    expiry_time = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )

                    current_time = datetime.now(timezone.utc)

                    if current_time >= expiry_time:

                        print(
                            "Access expired for patient:",
                            patient_id
                        )

                        (
                            supabase_admin
                            .table("access_requests")
                            .update({
                                "status": "expired"
                            })
                            .eq("id", access["id"])
                            .execute()
                        )

                        continue

                except Exception as expiry_error:

                    print(
                        "EXPIRY CHECK ERROR:",
                        repr(expiry_error)
                    )

            # -------------------------------------------------
            # 5. GET PATIENT
            # -------------------------------------------------

            patient_response = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("id", patient_id)
                .limit(1)
                .execute()
            )

            patient_data = patient_response.data or []

            print(
                "Patient returned:",
                patient_data
            )

            if not patient_data:
                print(
                    "Patient not found:",
                    patient_id
                )
                continue

            patient = patient_data[0]

            # -------------------------------------------------
            # 6. ADD ACCESS INFORMATION
            # -------------------------------------------------

            patient["patient_id"] = patient.get("id")

            patient["access_id"] = access.get("id")

            patient["access_type"] = access_type

            patient["access_status"] = "active"

            patient["approved_at"] = access.get(
                "approved_at"
            )

            patient["expires_at"] = expires_at

            patient["requested_at"] = access.get(
                "requested_at"
            )

            patients.append(patient)

        # -------------------------------------------------
        # 7. FINAL RESULT
        # -------------------------------------------------

        print("\nAuthorized patients:", len(patients))

        print("=" * 70)

        return render_template(
            "doctor/my_patients.html",
            patients=patients,
            error=None
        )

    except Exception as e:

        print("\n" + "=" * 70)
        print("❌ DOCTOR MY PATIENTS ERROR")
        print("=" * 70)

        print("Doctor ID:", doctor_id)

        print("Error type:", type(e).__name__)

        print("Error:", repr(e))

        print("=" * 70)

        return render_template(
            "doctor/my_patients.html",
            patients=[],
            error="Unable to load your authorized patients."
        )

# ============================================================
# DOCTOR - AI HEALTH ASSISTANT
# ============================================================

@app.route(
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


# ============================================================
# DOCTOR - PATIENT WORKSPACE TREND DATA API
# ============================================================

@app.route(
    "/doctor/patient-workspace/<patient_id>/trend-data",
    methods=["POST"]
)
def doctor_patient_trend_data(patient_id):
    """
    Secure server-side endpoint for retrieving filtered health trends.
    Supports authorized doctors and external consultations.
    """

    # --------------------------------------------------------
    # 1. VERIFY PATIENT WORKSPACE ACCESS
    # --------------------------------------------------------
    is_auth, access_info, err_msg = check_workspace_access(patient_id)

    if not is_auth:
        return {
            "success": False,
            "message": err_msg or "Unauthorized patient access."
        }, 403

    access_info = access_info or {}

    doctor_id = access_info.get(
        "doctor_id",
        "EXTERNAL_CONSULTATION"
    )

    try:

        # ----------------------------------------------------
        # 2. GET ACCESS RECORD FROM AUTHORIZATION RESPONSE
        # ----------------------------------------------------
        access = access_info.get("access_record") or {}

        # ----------------------------------------------------
        # 3. CHECK ACCESS EXPIRATION
        # ----------------------------------------------------
        expires_at = access.get("expires_at")

        if expires_at:

            try:
                expiry_time = datetime.fromisoformat(
                    expires_at.replace("Z", "+00:00")
                )

                if expiry_time.tzinfo is None:
                    expiry_time = expiry_time.replace(
                        tzinfo=timezone.utc
                    )

                current_time = datetime.now(timezone.utc)

                if current_time >= expiry_time:

                    if access.get("id"):
                        (
                            supabase_admin
                            .table("access_requests")
                            .update({"status": "expired"})
                            .eq("id", access["id"])
                            .eq("patient_id", patient_id)
                            .execute()
                        )

                    return {
                        "success": False,
                        "message": "This patient's temporary access has expired."
                    }, 403

            except (ValueError, TypeError, AttributeError) as expiry_error:

                print("TREND ACCESS EXPIRY ERROR:", repr(expiry_error))

                return {
                    "success": False,
                    "message": "Unable to verify access expiration."
                }, 403

        # ----------------------------------------------------
        # 4. GET PATIENT DETAILS
        # ----------------------------------------------------
        patient_response = (
            supabase_admin
            .table("patients")
            .select("*")
            .eq("id", patient_id)
            .single()
            .execute()
        )

        patient = patient_response.data or {}

        if not patient:
            return {
                "success": False,
                "message": "Patient not found."
            }, 404

        patient_name = (
            patient.get("full_name")
            or patient.get("name")
            or "Patient"
        )

        # ----------------------------------------------------
        # 5. GET PATIENT MEDICAL RECORDS
        # ----------------------------------------------------
        records_response = (
            supabase_admin
            .table("medical_records")
            .select("*")
            .eq("patient_id", patient_id)
            .order("uploaded_at", desc=True)
            .execute()
        )

        records = records_response.data or []

        # ----------------------------------------------------
        # 6. GET PATIENT HEALTH TIMELINE
        # ----------------------------------------------------
        timeline_response = (
            supabase_admin
            .table("health_timeline_events")
            .select("*")
            .eq("patient_id", patient_id)
            .order("event_date", desc=True)
            .execute()
        )

        timeline_events = timeline_response.data or []

        # ----------------------------------------------------
        # 7. GET FILTER PARAMETERS
        # ----------------------------------------------------
        req_data = request.get_json(silent=True) or {}

        time_period = req_data.get("time_period", "all")

        selected_params = req_data.get("parameters")

        # ----------------------------------------------------
        # 8. GENERATE HEALTH TREND ANALYSIS
        # ----------------------------------------------------
        trend_data = get_trend_analysis_data(
            timeline_events=timeline_events,
            medical_records=records,
            selected_params=selected_params,
            time_period=time_period,
            patient_name=patient_name
        )

        # ----------------------------------------------------
        # 9. RETURN SUCCESS RESPONSE
        # ----------------------------------------------------
        print("=" * 65)
        print("DOCTOR TREND ANALYSIS SUCCESS")
        print("=" * 65)
        print("Patient ID:", patient_id)
        print("Doctor ID:", doctor_id)
        print("Records:", len(records))
        print("Timeline Events:", len(timeline_events))
        print("Time Period:", time_period)
        print("Selected Parameters:", selected_params)
        print("=" * 65)

        return {
            "success": True,
            "trend_data": trend_data
        }, 200

    except Exception as e:

        print("=" * 65)
        print("DOCTOR TREND DATA API ERROR")
        print("=" * 65)
        print("Patient ID:", patient_id)
        print("Doctor ID:", doctor_id)
        print("Error:", repr(e))
        import traceback
        traceback.print_exc()
        print("=" * 65)

        return {
            "success": False,
            "message": "An error occurred while analyzing health trends."
        }, 500

@app.route("/doctor/shared-medical-records")
def doctor_shared_medical_records():

    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]
    patients = []

    try:
        response = (
            supabase_admin
            .table("access_requests")
            .select("*")
            .eq("doctor_id", doctor_id)
            .eq("status", "active")
            .eq("access_type", "permanent")
            .order("approved_at", desc=True)
            .execute()
        )

        now = datetime.now(timezone.utc)

        for access in response.data or []:
            patient_id = access.get("patient_id")

            if not patient_id:
                continue

            expires_at = access.get("expires_at")

            # Permanent access should not expire, but still
            # enforce an expiry timestamp if one exists.
            if expires_at:
                try:
                    expiry = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )

                    if expiry.tzinfo is None:
                        expiry = expiry.replace(tzinfo=timezone.utc)

                    if now >= expiry:
                        (
                            supabase_admin
                            .table("access_requests")
                            .update({"status": "expired"})
                            .eq("id", access["id"])
                            .execute()
                        )
                        continue

                except (ValueError, TypeError, AttributeError):
                    # Do not display a grant with an invalid expiry.
                    continue

            patient_response = (
                supabase_admin
                .table("patients")
                .select("*")
                .eq("id", patient_id)
                .limit(1)
                .execute()
            )

            patient_rows = patient_response.data or []

            if not patient_rows:
                continue

            patient = patient_rows[0]

            patient["patient_id"] = patient.get("id")
            patient["health_id_display"] = (
    patient.get("health_id")
    or patient.get("healthid")
    or "Not Available"
)
            patient["access_id"] = access.get("id")
            patient["access_type"] = "permanent"
            patient["access_status"] = "active"
            patient["approved_at"] = access.get("approved_at")

            approved_at = access.get("approved_at")
            patient["approved_at_display"] = None

            if approved_at:
                try:
                    approved_dt = datetime.fromisoformat(
                        approved_at.replace("Z", "+00:00")
                    )
                    patient["approved_at_display"] = (
                        approved_dt.strftime("%d %b %Y, %I:%M %p")
                    )
                except (ValueError, TypeError, AttributeError):
                    patient["approved_at_display"] = str(approved_at)

            # Compatibility with the existing patient-card template.
            patient["patient_name"] = (
                patient.get("full_name")
                or patient.get("name")
                or "Patient"
            )

            patients.append(patient)

        return render_template(
            "doctor/shared_medical_records.html",
            patients=patients,
            error=None
        )

    except Exception as e:
        print("SHARED MEDICAL RECORDS ERROR:", repr(e))

        return render_template(
            "doctor/shared_medical_records.html",
            patients=[],
            error="Unable to load shared medical records."
        )

@app.route("/doctor/guest-patient/create", methods=["POST"])
def create_guest_patient():
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = str(session["doctor_id"]).strip()
    full_name = request.form.get("full_name", "").strip()
    date_of_birth = request.form.get("date_of_birth", "").strip() or None
    gender = request.form.get("gender", "").strip() or None

    if not full_name:
        flash("Please enter the guest patient's name.", "error")
        return redirect(url_for("doctor_guest_patient"))

    guest_id = str(uuid.uuid4())
    guest_code = "GUEST-" + secrets.token_hex(4).upper()

    try:
        result = (
            supabase_admin.table("guest_patients")
            .insert({
                "id": guest_id,
                "guest_code": guest_code,
                "created_by_doctor_id": doctor_id,
                "full_name": full_name,
                "date_of_birth": date_of_birth,
                "gender": gender,
                "status": "active"
            })
            .execute()
        )

        if not result.data:
            raise RuntimeError("Guest patient creation failed.")

        supabase_admin.table("guest_patient_access").insert({
            "guest_patient_id": guest_id,
            "doctor_id": doctor_id,
            "status": "active"
        }).execute()

        flash(f"Guest patient created: {guest_code}", "success")

        # Redirect to the guest list for now.
        return redirect(url_for("doctor_guest_patient"))

    except Exception as e:
        print("CREATE GUEST PATIENT ERROR:", repr(e))
        flash("Unable to create guest patient. Check the Flask terminal.", "error")
        return redirect(url_for("doctor_guest_patient"))

# ============================================================
# OMNICARE AI — GUEST PATIENT WORKSPACE
# Add these imports at the top of app.py if not already present.
# ============================================================

import secrets
from werkzeug.utils import secure_filename
from flask import (
    request, redirect, url_for, flash, session, render_template
)

GUEST_ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp"}
GUEST_MAX_UPLOAD_BYTES = 12 * 1024 * 1024  # 12 MB


# ------------------------------------------------------------
# HELPER: GET A GUEST PATIENT OWNED BY THE LOGGED-IN DOCTOR
# ------------------------------------------------------------

def get_guest_patient_for_doctor(guest_patient_id, doctor_id):
    response = (
        supabase_admin
        .table("guest_patients")
        .select("*")
        .eq("id", guest_patient_id)
        .eq("created_by_doctor_id", doctor_id)
        .limit(1)
        .execute()
    )

    guests = response.data or []
    return guests[0] if guests else None


# ------------------------------------------------------------
# HELPER: CREATE A SHORT-LIVED URL FOR A PRIVATE FILE
# ------------------------------------------------------------

def get_guest_signed_url(file_path):
    if not file_path:
        return None

    try:
        result = (
            supabase_admin
            .storage
            .from_("medical-records")
            .create_signed_url(file_path, 900)
        )

        return (
            result.get("signedURL")
            or result.get("signedUrl")
        )

    except Exception as error:
        print("GUEST SIGNED URL ERROR:", repr(error))
        return None


# ============================================================
# DOCTOR — GUEST PATIENT WORKSPACE
# URL: /doctor/guest-patient/<guest_patient_id>/workspace
# ============================================================

@app.route(
    "/doctor/guest-patient/<guest_patient_id>/workspace",
    endpoint="doctor_guest_workspace"
)
def doctor_guest_workspace(guest_patient_id):

    # --------------------------------------------------------
    # 1. VERIFY DOCTOR LOGIN
    # --------------------------------------------------------
    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    try:
        # ----------------------------------------------------
        # 2. VERIFY GUEST OWNERSHIP
        # ----------------------------------------------------
        guest = get_guest_patient_for_doctor(
            guest_patient_id,
            doctor_id
        )

        if not guest:
            flash(
                "Guest patient not found or access denied.",
                "error"
            )
            return redirect(url_for("doctor_guest_patient"))

        # ----------------------------------------------------
        # 3. FETCH THIS GUEST'S MEDICAL RECORDS ONLY
        # ----------------------------------------------------
        records_response = (
            supabase_admin
            .table("guest_medical_records")
            .select("*")
            .eq("guest_patient_id", guest_patient_id)
            .eq("uploaded_by_doctor_id", doctor_id)
            .order("created_at", desc=True)
            .execute()
        )

        records = records_response.data or []

        # Generate temporary signed URLs for private documents.
        for record in records:
            record["secure_file_url"] = get_guest_signed_url(
                record.get("file_path")
            )
            record["file_url"] = record["secure_file_url"]
            if not record.get("uploaded_at") and record.get("created_at"):
                record["uploaded_at"] = record.get("created_at")

        # ----------------------------------------------------
        # 4. FETCH THIS GUEST'S HEALTH TIMELINE
        # ----------------------------------------------------
        timeline_response = (
            supabase_admin
            .table("guest_health_timeline_events")
            .select("*")
            .eq("guest_patient_id", guest_patient_id)
            .order("event_date", desc=True)
            .execute()
        )

        timeline_events = timeline_response.data or []

        for event in timeline_events:
            if not event.get("medical_record_id") and event.get("guest_medical_record_id"):
                event["medical_record_id"] = event["guest_medical_record_id"]

        # ----------------------------------------------------
        # 5. DETECT MEDICAL CONFLICTS USING EXISTING DETECTOR
        # ----------------------------------------------------
        conflicts = detect_medical_conflicts(
            timeline_events
        )

        conflict_summary = {
            "total": len(conflicts),
            "high": sum(
                1 for conflict in conflicts
                if conflict.get("severity") == "high"
            ),
            "medium": sum(
                1 for conflict in conflicts
                if conflict.get("severity") == "medium"
            ),
            "low": sum(
                1 for conflict in conflicts
                if conflict.get("severity") == "low"
            )
        }

        # ----------------------------------------------------
        # 6. BUILD GUEST-SPECIFIC AI TREND ANALYSIS
        # ----------------------------------------------------
        guest_name = (
            guest.get("full_name")
            or guest.get("name")
            or "Guest Patient"
        )

        trend_data = get_trend_analysis_data(
            timeline_events=timeline_events,
            medical_records=records,
            patient_name=guest_name
        )

        # ----------------------------------------------------
        # 7. RENDER GUEST WORKSPACE
        # ----------------------------------------------------
        return render_template(
            "doctor/guest_patient_workspace.html",
            guest=guest,
            records=records,
            timeline_events=timeline_events,
            conflicts=conflicts,
            conflict_summary=conflict_summary,
            trend_data=trend_data
        )

    except Exception as error:
        print("=" * 60)
        print("GUEST WORKSPACE LOAD ERROR")
        print("Guest Patient ID:", guest_patient_id)
        print("Doctor ID:", doctor_id)
        print("Error Type:", type(error).__name__)
        print("Error Details:", repr(error))
        print("=" * 60)

        flash(
            "Unable to load the guest workspace. "
            "Check the Flask terminal.",
            "error"
        )

        return redirect(url_for("doctor_guest_patient"))


# ============================================================
# DOCTOR — UPLOAD A GUEST MEDICAL RECORD
# ============================================================


@app.route(
    "/doctor/guest-patient/<guest_patient_id>/upload",
    methods=["POST"],
    endpoint="doctor_guest_upload_record"
)
def doctor_guest_upload_record(guest_patient_id):

    # --------------------------------------------------------
    # 1. AUTHENTICATION AND GUEST OWNERSHIP
    # --------------------------------------------------------

    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    guest = get_guest_patient_for_doctor(
        guest_patient_id,
        doctor_id
    )

    if not guest:
        flash(
            "Guest patient not found or access denied.",
            "error"
        )
        return redirect(url_for("doctor_guest_patient"))

    workspace_url = url_for(
        "doctor_guest_workspace",
        guest_patient_id=guest_patient_id
    )

    # --------------------------------------------------------
    # 2. VALIDATE FORM INPUTS
    # --------------------------------------------------------

    title = request.form.get("title", "").strip()
    record_type = request.form.get("record_type", "").strip()
    description = request.form.get("description", "").strip()
    uploaded_file = request.files.get("medical_file")

    if (
        not title
        or not record_type
        or not uploaded_file
        or not uploaded_file.filename
    ):
        flash(
            "Enter a title, select a record type, and choose a file.",
            "error"
        )
        return redirect(workspace_url)

    filename = secure_filename(uploaded_file.filename)

    extension = (
        filename.rsplit(".", 1)[-1].lower()
        if "." in filename else ""
    )

    if extension not in GUEST_ALLOWED_EXTENSIONS:
        flash(
            "Only PDF, PNG, JPG, JPEG, and WEBP files are allowed.",
            "error"
        )
        return redirect(workspace_url)

    # Derive the MIME type from the extension.
    mime_types = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp"
    }

    content_type = mime_types[extension]

    file_bytes = uploaded_file.read(
        GUEST_MAX_UPLOAD_BYTES + 1
    )

    if not file_bytes:
        flash("The selected file is empty.", "error")
        return redirect(workspace_url)

    if len(file_bytes) > GUEST_MAX_UPLOAD_BYTES:
        flash("Maximum upload size is 12 MB.", "error")
        return redirect(workspace_url)

    # --------------------------------------------------------
    # 3. UPLOAD ORIGINAL FILE TO GUEST-SPECIFIC STORAGE PATH
    # --------------------------------------------------------

    storage_path = (
        f"guests/{guest_patient_id}/"
        f"{secrets.token_hex(16)}.{extension}"
    )

    file_uploaded = False
    record_id = None

    try:
        (
            supabase_admin
            .storage
            .from_("medical-records")
            .upload(
                storage_path,
                file_bytes,
                {"content-type": content_type}
            )
        )

        file_uploaded = True

        # ----------------------------------------------------
        # 4. SAVE GUEST MEDICAL RECORD METADATA
        # ----------------------------------------------------

        insert_response = (
            supabase_admin
            .table("guest_medical_records")
            .insert({
                "guest_patient_id": guest_patient_id,
                "uploaded_by_doctor_id": doctor_id,
                "record_type": record_type,
                "title": title,
                "description": description or None,
                "file_name": filename,
                "file_path": storage_path
            })
            .execute()
        )

        if not insert_response.data:
            raise RuntimeError(
                "Supabase did not return the inserted guest record."
            )

        record = insert_response.data[0]
        record_id = record["id"]

        print("=" * 60)
        print("GUEST DOCUMENT UPLOADED")
        print("Guest ID:", guest_patient_id)
        print("Record ID:", record_id)
        print("Filename:", filename)
        print("=" * 60)

    except Exception as error:
        print("GUEST UPLOAD ERROR:", repr(error))

        # Remove the stored file if the metadata insertion failed.
        # Do not remove it when later AI processing fails.
        if file_uploaded and record_id is None:
            try:
                (
                    supabase_admin
                    .storage
                    .from_("medical-records")
                    .remove([storage_path])
                )
            except Exception as cleanup_error:
                print(
                    "GUEST FILE CLEANUP ERROR:",
                    repr(cleanup_error)
                )

        flash(
            "Unable to upload the report. Check the Flask terminal.",
            "error"
        )
        return redirect(workspace_url)

    # --------------------------------------------------------
    # 5. PROCESS DOCUMENT USING EXISTING GEMINI PROCESSOR
    # --------------------------------------------------------

    try:
        extracted_data = process_medical_document(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type
        )

        if not isinstance(extracted_data, dict):
            raise ValueError(
                "Medical processor did not return a dictionary."
            )

        print("GUEST DOCUMENT EXTRACTION COMPLETED")
        print("Extracted fields:", list(extracted_data.keys()))

        # ----------------------------------------------------
        # 6. NORMALIZE GEMINI'S EVENT DATE
        #
        # Examples:
        # 15-10-2026 -> 2026-10-15
        # 2026-10-15 -> 2026-10-15
        # 15/10/2026 -> 2026-10-15
        # ----------------------------------------------------

        raw_event_date = extracted_data.get("event_date")
        normalized_event_date = None

        if raw_event_date:
            raw_event_date = str(raw_event_date).strip()

            supported_formats = (
                "%d-%m-%Y",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%Y/%m/%d"
            )

            for date_format in supported_formats:
                try:
                    normalized_event_date = datetime.strptime(
                        raw_event_date,
                        date_format
                    ).date().isoformat()

                    break

                except ValueError:
                    continue

            if normalized_event_date is None:
                print(
                    "WARNING: Could not parse extracted event date:",
                    repr(raw_event_date)
                )

        print(
            "NORMALIZED EVENT DATE:",
            normalized_event_date
        )

        # ----------------------------------------------------
        # 7. BUILD GUEST-SPECIFIC TIMELINE EVENT
        # ----------------------------------------------------

        timeline_event = {
            "guest_patient_id": guest_patient_id,
            "guest_medical_record_id": record_id,

            "event_type": (
                extracted_data.get("event_type")
                or record_type
            ),

            "provider_name": extracted_data.get(
                "provider_name"
            ),

            "hospital_name": extracted_data.get(
                "hospital_name"
            ),

            "diagnosis": extracted_data.get("diagnosis"),

            "clinical_findings": extracted_data.get(
                "clinical_findings"
            ),

            "investigations": (
                extracted_data.get("investigations") or []
            ),

            "medications": (
                extracted_data.get("medications") or []
            ),

            "follow_up": extracted_data.get("follow_up"),

            "clinical_summary": extracted_data.get(
                "clinical_summary"
            ),

            "ai_processed": True
        }

        # Include a date only when successfully parsed.
        # Do not substitute today's date for a missing report date.
        if normalized_event_date:
            timeline_event["event_date"] = normalized_event_date

        # ----------------------------------------------------
        # 8. SAVE THE TIMELINE EVENT
        # ----------------------------------------------------

        timeline_response = (
            supabase_admin
            .table("guest_health_timeline_events")
            .insert(timeline_event)
            .execute()
        )

        if not timeline_response.data:
            raise RuntimeError(
                "The guest timeline event was not returned after insertion."
            )

        saved_event = timeline_response.data[0]

        print("=" * 60)
        print("GUEST TIMELINE EVENT SAVED SUCCESSFULLY")
        print("Guest ID:", guest_patient_id)
        print("Record ID:", record_id)
        print("Timeline Event ID:", saved_event.get("id"))
        print("Event Date:", normalized_event_date)
        print("Investigation Count:", len(
            timeline_event["investigations"]
        ))
        print("=" * 60)

        flash(
            "Report uploaded and AI processing completed successfully.",
            "success"
        )

    except Exception as ai_error:
        # The original report and its metadata remain available.
        print("=" * 60)
        print("GUEST AI PROCESSING / TIMELINE ERROR")
        print("Guest ID:", guest_patient_id)
        print("Record ID:", record_id)
        print("Error:", repr(ai_error))
        print("=" * 60)

        flash(
            "Report uploaded, but AI processing or timeline saving "
            "failed. The original report is preserved. Check the "
            "Flask terminal for the exact error.",
            "error"
        )

    return redirect(workspace_url)
# ============================================================
# DOCTOR — VIEW AN ORIGINAL GUEST MEDICAL RECORD
# ============================================================

@app.route(
    "/doctor/guest-record/<record_id>/view",
    endpoint="doctor_view_guest_medical_record"
)
def doctor_view_guest_medical_record(record_id):

    if "doctor_id" not in session:
        return redirect(url_for("doctor_login"))

    doctor_id = session["doctor_id"]

    try:
        response = (
            supabase_admin
            .table("guest_medical_records")
            .select("*")
            .eq("id", record_id)
            .eq("uploaded_by_doctor_id", doctor_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []

        if not rows:
            flash("Guest record not found or access denied.", "error")
            return redirect(url_for("doctor_guest_patient"))

        record = rows[0]

        # Verify that the guest profile also belongs to this doctor.
        guest = get_guest_patient_for_doctor(
            record.get("guest_patient_id"),
            doctor_id
        )

        if not guest:
            flash("Guest record access denied.", "error")
            return redirect(url_for("doctor_guest_patient"))

        file_url = get_guest_signed_url(
            record.get("file_path")
        )

        if not file_url:
            flash("Unable to securely open the original report.", "error")
            return redirect(
                url_for(
                    "doctor_guest_workspace",
                    guest_patient_id=record.get("guest_patient_id")
                )
            )

        return redirect(file_url)

    except Exception as error:
        print("GUEST RECORD VIEW ERROR:", repr(error))
        flash("Unable to open the guest report.", "error")
        return redirect(url_for("doctor_guest_patient"))


# ============================================================
# DOCTOR — GUEST PATIENT WORKSPACE TREND DATA API
# ============================================================

@app.route(
    "/doctor/guest-patient/<guest_patient_id>/trend-data",
    methods=["POST"]
)
def doctor_guest_trend_data(guest_patient_id):
    """
    Secure server-side endpoint for retrieving filtered health trend
    measurements, charts, summaries, and AI observations for guest patients.
    """
    if "doctor_id" not in session:
        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    doctor_id = session["doctor_id"]

    try:
        guest = get_guest_patient_for_doctor(
            guest_patient_id,
            doctor_id
        )

        if not guest:
            return {
                "success": False,
                "message": "Guest patient not found or access denied."
            }, 403

        records_response = (
            supabase_admin
            .table("guest_medical_records")
            .select("*")
            .eq("guest_patient_id", guest_patient_id)
            .eq("uploaded_by_doctor_id", doctor_id)
            .order("created_at", desc=True)
            .execute()
        )
        records = records_response.data or []

        for record in records:
            if not record.get("uploaded_at") and record.get("created_at"):
                record["uploaded_at"] = record.get("created_at")
            record["secure_file_url"] = get_guest_signed_url(
                record.get("file_path")
            )
            record["file_url"] = record["secure_file_url"]

        timeline_response = (
            supabase_admin
            .table("guest_health_timeline_events")
            .select("*")
            .eq("guest_patient_id", guest_patient_id)
            .order("event_date", desc=True)
            .execute()
        )
        timeline_events = timeline_response.data or []

        for event in timeline_events:
            if not event.get("medical_record_id") and event.get("guest_medical_record_id"):
                event["medical_record_id"] = event["guest_medical_record_id"]

        req_data = request.get_json(silent=True) or {}
        time_period = req_data.get("time_period", "all")
        selected_params = req_data.get("parameters")

        guest_name = (
            guest.get("full_name")
            or guest.get("name")
            or "Guest Patient"
        )

        trend_data = get_trend_analysis_data(
            timeline_events=timeline_events,
            medical_records=records,
            selected_params=selected_params,
            time_period=time_period,
            patient_name=guest_name
        )

        return {
            "success": True,
            "trend_data": trend_data
        }

    except Exception as e:
        print("=" * 70)
        print("DOCTOR GUEST TREND DATA API ERROR")
        print("Guest Patient ID:", guest_patient_id)
        print("Doctor ID       :", doctor_id)
        print("Error           :", repr(e))
        print("=" * 70)

        return {
            "success": False,
            "message": "An error occurred while analyzing health trends."
        }, 500


# ============================================================
# DOCTOR — GUEST PATIENT AI ASSISTANT
# ============================================================

@app.route(
    "/doctor/guest-patient/<guest_patient_id>/ai-assistant",
    methods=["POST"]
)
def doctor_guest_ai_assistant(guest_patient_id):
    """
    Secure server-side endpoint for questioning OmniCare AI about
    a guest patient's authorized clinical timeline.
    """
    if "doctor_id" not in session:
        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    doctor_id = session["doctor_id"]

    try:
        guest = get_guest_patient_for_doctor(
            guest_patient_id,
            doctor_id
        )

        if not guest:
            return {
                "success": False,
                "message": "Guest patient not found or access denied."
            }, 403

        timeline_response = (
            supabase_admin
            .table("guest_health_timeline_events")
            .select("*")
            .eq("guest_patient_id", guest_patient_id)
            .order("event_date", desc=True)
            .execute()
        )
        timeline_events = timeline_response.data or []

        for event in timeline_events:
            if not event.get("medical_record_id") and event.get("guest_medical_record_id"):
                event["medical_record_id"] = event["guest_medical_record_id"]

        data = request.get_json(silent=True) or {}
        question = data.get("question", "").strip()

        if not question:
            return {
                "success": False,
                "message": "Please enter a question."
            }, 400

        guest_records = []
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
        )

        return {
            "success": True,
            "answer": answer,
            "event_count": len(timeline_events)
        }

    except Exception as e:
        print("=" * 70)
        print("DOCTOR GUEST AI ASSISTANT ERROR")
        print("Guest Patient ID:", guest_patient_id)
        print("Doctor ID       :", doctor_id)
        print("Error           :", repr(e))
        print("=" * 70)

        return {
            "success": False,
            "message": "Unable to process the AI request."
        }, 500


# ============================================================
# DOCTOR — GUEST PATIENT AI SOURCE RECORDS
# ============================================================

@app.route(
    "/doctor/guest-patient/<guest_patient_id>/ai-sources",
    methods=["GET"]
)
def doctor_guest_ai_sources(guest_patient_id):
    """
    Secure server-side endpoint for retrieving source records
    associated with a guest patient's AI responses.
    """
    if "doctor_id" not in session:
        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    doctor_id = session["doctor_id"]

    try:
        guest = get_guest_patient_for_doctor(
            guest_patient_id,
            doctor_id
        )

        if not guest:
            return {
                "success": False,
                "message": "Guest patient access denied."
            }, 403

        timeline_response = (
            supabase_admin
            .table("guest_health_timeline_events")
            .select(
                """
                id,
                guest_medical_record_id,
                event_date,
                event_type,
                provider_name,
                hospital_name
                """
            )
            .eq("guest_patient_id", guest_patient_id)
            .order("event_date", desc=True)
            .execute()
        )
        timeline_events = timeline_response.data or []

        sources = []
        seen_records = set()

        for event in timeline_events:
            medical_record_id = (
                event.get("guest_medical_record_id")
                or event.get("medical_record_id")
            )

            if not medical_record_id:
                continue

            if medical_record_id in seen_records:
                continue

            seen_records.add(medical_record_id)

            try:
                view_url = url_for(
                    "doctor_view_guest_medical_record",
                    record_id=medical_record_id
                )
            except Exception:
                view_url = None

            sources.append({
                "medical_record_id": medical_record_id,
                "event_date": event.get("event_date"),
                "event_type": event.get("event_type"),
                "provider_name": event.get("provider_name"),
                "hospital_name": event.get("hospital_name"),
                "view_url": view_url
            })

        return {
            "success": True,
            "sources": sources
        }

    except Exception as e:
        print("=" * 70)
        print("DOCTOR GUEST AI SOURCES ERROR")
        print("Guest Patient ID:", guest_patient_id)
        print("Doctor ID       :", doctor_id)
        print("Error           :", repr(e))
        print("=" * 70)

        return {
            "success": False,
            "message": "Unable to load sources."
        }, 500

if __name__ == "__main__":

    app.run(
        debug=True
    )

