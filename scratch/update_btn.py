with open("templates/doctor/patient_access.html", "r", encoding="utf-8") as f:
    text = f.read()

target = """                    <button type="button"
                            class="instant-otp-btn"
                            onclick="openDoctorOtpModal('{{ patient.get('id') }}', '{{ patient.get('full_name') or patient.get('name') or 'Patient' }}')">
                        ⚡ Start OTP Consultation
                    </button>"""

replacement = """                    <button type="button"
                            id="btnStartDoctorOtp"
                            class="instant-otp-btn"
                            data-patient-id="{{ patient.get('id') }}"
                            data-patient-name="{{ patient.get('full_name') or patient.get('name') or 'Patient' }}"
                            onclick="openDoctorOtpModal(this.dataset.patientId, this.dataset.patientName)">
                        ⚡ Start OTP Consultation
                    </button>"""

# Normalize
norm_text = text.replace("\r\n", "\n")
norm_target = target.replace("\r\n", "\n")
norm_repl = replacement.replace("\r\n", "\n")

if norm_target in norm_text:
    norm_text = norm_text.replace(norm_target, norm_repl)
    with open("templates/doctor/patient_access.html", "w", encoding="utf-8") as f:
        f.write(norm_text.replace("\n", "\r\n"))
    print("Successfully added id and data attributes to btnStartDoctorOtp")
else:
    print("Error: target still not matched!")
