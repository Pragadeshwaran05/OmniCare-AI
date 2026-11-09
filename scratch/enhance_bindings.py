with open("templates/doctor/patient_access.html", "r", encoding="utf-8") as f:
    doc_html = f.read()

# Update openDoctorOtpModal and sendDoctorOtp
old_open_func = """function openDoctorOtpModal(patientId, patientName) {
    currentPatientId = patientId;
    document.getElementById("docOtpPatientName").textContent = patientName || "Patient";
    document.getElementById("docOtpStage1").style.display = "block";
    document.getElementById("docOtpStage2").style.display = "none";
    document.getElementById("docOtpError1").style.display = "none";
    document.getElementById("doctorOtpModal").style.display = "flex";
}"""

new_open_func = """function openDoctorOtpModal(patientId, patientName) {
    const btn = document.getElementById("btnStartDoctorOtp");
    currentPatientId = patientId || (btn && btn.dataset && btn.dataset.patientId) || currentPatientId;
    const name = patientName || (btn && btn.dataset && btn.dataset.patientName) || "Patient";
    const nameEl = document.getElementById("docOtpPatientName");
    if (nameEl) nameEl.textContent = name;
    const s1 = document.getElementById("docOtpStage1");
    if (s1) s1.style.display = "block";
    const s2 = document.getElementById("docOtpStage2");
    if (s2) s2.style.display = "none";
    const e1 = document.getElementById("docOtpError1");
    if (e1) e1.style.display = "none";
    const modal = document.getElementById("doctorOtpModal");
    if (modal) modal.style.display = "flex";
}"""

if old_open_func.replace("\r\n", "\n") in doc_html.replace("\r\n", "\n"):
    doc_html = doc_html.replace(old_open_func.replace("\n", "\r\n"), new_open_func.replace("\n", "\r\n"))
    print("Updated openDoctorOtpModal in patient_access.html")

old_send_start = """async function sendDoctorOtp() {
    const btn = document.getElementById("btnDocSendOtp");
    const errBox = document.getElementById("docOtpError1");
    const errBox2 = document.getElementById("docOtpError2");
    errBox.style.display = "none";
    errBox2.style.display = "none";

    btn.disabled = true;
    btn.textContent = "Sending OTP...";

    try {
        const response = await fetch(`/doctor/patient-access/${encodeURIComponent(currentPatientId)}/send-otp`,"""

new_send_start = """async function sendDoctorOtp() {
    const btn = document.getElementById("btnDocSendOtp");
    const errBox = document.getElementById("docOtpError1");
    const errBox2 = document.getElementById("docOtpError2");
    errBox.style.display = "none";
    errBox2.style.display = "none";

    if (!currentPatientId) {
        const triggerBtn = document.getElementById("btnStartDoctorOtp");
        currentPatientId = (triggerBtn && triggerBtn.dataset && triggerBtn.dataset.patientId) || null;
    }

    if (!currentPatientId) {
        errBox.textContent = "Patient identification missing. Please refresh and try again.";
        errBox.style.display = "block";
        return;
    }

    btn.disabled = true;
    btn.textContent = "Sending OTP...";

    try {
        const response = await fetch(`/doctor/patient-access/${encodeURIComponent(currentPatientId)}/send-otp`,"""

if old_send_start.replace("\r\n", "\n") in doc_html.replace("\r\n", "\n"):
    doc_html = doc_html.replace(old_send_start.replace("\n", "\r\n"), new_send_start.replace("\n", "\r\n"))
    print("Updated sendDoctorOtp in patient_access.html")

# Add DOMContentLoaded bindings
dom_bindings_doc = """
document.addEventListener("DOMContentLoaded", function() {
    const btn = document.getElementById("btnStartDoctorOtp");
    if (btn) {
        btn.addEventListener("click", function() {
            openDoctorOtpModal(this.dataset.patientId, this.dataset.patientName);
        });
    }

    const modal = document.getElementById("doctorOtpModal");
    if (modal) {
        modal.addEventListener("click", function(e) {
            if (e.target === this) closeDoctorOtpModal();
        });
    }

    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
            closeDoctorOtpModal();
        }
    });
});
"""

if "DOMContentLoaded" not in doc_html:
    doc_html = doc_html.replace("</script>", dom_bindings_doc + "\n</script>")
    print("Added DOMContentLoaded bindings to patient_access.html")

with open("templates/doctor/patient_access.html", "w", encoding="utf-8") as f:
    f.write(doc_html)


# Now update public_patient_info.html
with open("templates/patient/public_patient_info.html", "r", encoding="utf-8") as f:
    pub_html = f.read()

dom_bindings_pub = """
document.addEventListener("DOMContentLoaded", function() {
    const btn = document.getElementById("btnRequestConsultation");
    if (btn) {
        btn.addEventListener("click", openConsultationModal);
    }

    const modal = document.getElementById("consultationModal");
    if (modal) {
        modal.addEventListener("click", function(e) {
            if (e.target === this) closeConsultationModal();
        });
    }

    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
            closeConsultationModal();
        }
    });
});
"""

if "DOMContentLoaded" not in pub_html:
    pub_html = pub_html.replace("</script>", dom_bindings_pub + "\n</script>")
    print("Added DOMContentLoaded bindings to public_patient_info.html")

with open("templates/patient/public_patient_info.html", "w", encoding="utf-8") as f:
    f.write(pub_html)
