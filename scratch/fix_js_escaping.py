# Fix Jinja escaping in templates/patient/public_patient_info.html
with open("templates/patient/public_patient_info.html", "r", encoding="utf-8") as f:
    pub_html = f.read()

pub_html = pub_html.replace(
    "const qrIdentifier = {{ qr_identifier|tojson if qr_identifier else (patient.get('id')|tojson) }};",
    'const qrIdentifier = {{ (qr_identifier or patient.get("id") or "")|tojson|safe }};'
)
pub_html = pub_html.replace(
    "const patientId = {{ patient.get('id')|tojson }};",
    'const patientId = {{ (patient.get("id") or "")|tojson|safe }};'
)
pub_html = pub_html.replace(
    "const msg91WidgetId = {{ msg91_widget_id|tojson if msg91_widget_id else '\"\"' }};",
    'const msg91WidgetId = {{ (msg91_widget_id or "")|tojson|safe }};'
)
pub_html = pub_html.replace(
    "const msg91TokenAuth = {{ msg91_token_auth|tojson if msg91_token_auth else '\"\"' }};",
    'const msg91TokenAuth = {{ (msg91_token_auth or "")|tojson|safe }};'
)

# Also ensure the button has an ID and event listener
pub_html = pub_html.replace(
    '<button type="button" class="btn-external-consultation" onclick="openConsultationModal()">',
    '<button type="button" id="btnRequestConsultation" class="btn-external-consultation" onclick="openConsultationModal()">'
)

with open("templates/patient/public_patient_info.html", "w", encoding="utf-8") as f:
    f.write(pub_html)
print("Updated templates/patient/public_patient_info.html")

# Fix Jinja escaping in templates/doctor/patient_access.html
with open("templates/doctor/patient_access.html", "r", encoding="utf-8") as f:
    doc_html = f.read()

doc_html = doc_html.replace(
    "const msg91WidgetId = {{ msg91_widget_id|tojson if msg91_widget_id else '\"\"' }};",
    'const msg91WidgetId = {{ (msg91_widget_id or "")|tojson|safe }};'
)
doc_html = doc_html.replace(
    "const msg91TokenAuth = {{ msg91_token_auth|tojson if msg91_token_auth else '\"\"' }};",
    'const msg91TokenAuth = {{ (msg91_token_auth or "")|tojson|safe }};'
)

# Ensure the doctor button uses data attributes and ID for robustness
old_btn = """                    <button type="button"
                            class="instant-otp-btn"
                            onclick="openDoctorOtpModal('{{ patient.get('id') }}', '{{ patient.get('full_name') or patient.get('name') or 'Patient' }}')">
                        ⚡ Start OTP Consultation
                    </button>"""

new_btn = """                    <button type="button"
                            id="btnStartDoctorOtp"
                            class="instant-otp-btn"
                            data-patient-id="{{ patient.get('id') }}"
                            data-patient-name="{{ patient.get('full_name') or patient.get('name') or 'Patient' }}"
                            onclick="openDoctorOtpModal(this.dataset.patientId, this.dataset.patientName)">
                        ⚡ Start OTP Consultation
                    </button>"""

if old_btn.replace("\r\n", "\n") in doc_html.replace("\r\n", "\n"):
    doc_html = doc_html.replace(old_btn.replace("\n", "\r\n"), new_btn.replace("\n", "\r\n"))
    print("Updated doctor instant OTP button.")
else:
    print("Warning: old_btn target not matched in doctor_patient_access.html")

with open("templates/doctor/patient_access.html", "w", encoding="utf-8") as f:
    f.write(doc_html)
print("Updated templates/doctor/patient_access.html")
