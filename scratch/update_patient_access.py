import os

def main():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "doctor", "patient_access.html")
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Add demo banner in stage 2
    target1 = '''        <!-- STAGE 2: ENTER OTP -->
        <div id="docOtpStage2" class="doc-modal-body" style="display: none;">
            <div class="doc-otp-sent-banner">'''

    replacement1 = '''        <!-- STAGE 2: ENTER OTP -->
        <div id="docOtpStage2" class="doc-modal-body" style="display: none;">
            <div id="docOtpDemoBanner" class="doc-alert doc-alert-info" style="display: none; background: #e6fffa; border: 1px solid #319795; color: #234e52; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-weight: 600;"></div>

            <div class="doc-otp-sent-banner">'''

    # 2. Update sendDoctorOtp to display demo banner
    target2 = '''        if (data.success) {
            currentChallengeId = data.challenge_id;
            document.getElementById("docOtpMaskedDest").textContent = data.masked_destination;
            document.getElementById("docOtpStage1").style.display = "none";
            document.getElementById("docOtpStage2").style.display = "block";
            startDoctorOtpTimer(data.expires_in_seconds || 900);
            document.getElementById("doctor_entered_otp").focus();'''

    replacement2 = '''        if (data.success) {
            currentChallengeId = data.challenge_id;
            document.getElementById("docOtpMaskedDest").textContent = data.masked_destination;

            const demoBanner = document.getElementById("docOtpDemoBanner");
            if (data.is_demo_mode && data.demo_otp_notice) {
                demoBanner.textContent = data.demo_otp_notice;
                demoBanner.style.display = "block";
            } else if (demoBanner) {
                demoBanner.style.display = "none";
            }

            document.getElementById("docOtpStage1").style.display = "none";
            document.getElementById("docOtpStage2").style.display = "block";
            startDoctorOtpTimer(data.expires_in_seconds || 300);
            document.getElementById("doctor_entered_otp").focus();'''

    # 3. Update timer default in startDoctorOtpTimer
    target3 = '''    docSecondsRemaining = seconds || 900;'''
    replacement3 = '''    docSecondsRemaining = seconds || 300;'''

    code_norm = code.replace("\r\n", "\n")
    target1_norm = target1.replace("\r\n", "\n")
    replacement1_norm = replacement1.replace("\r\n", "\n")
    target2_norm = target2.replace("\r\n", "\n")
    replacement2_norm = replacement2.replace("\r\n", "\n")
    target3_norm = target3.replace("\r\n", "\n")
    replacement3_norm = replacement3.replace("\r\n", "\n")

    if target1_norm in code_norm and target2_norm in code_norm:
        code_norm = code_norm.replace(target1_norm, replacement1_norm, 1)
        code_norm = code_norm.replace(target2_norm, replacement2_norm, 1)
        code_norm = code_norm.replace(target3_norm, replacement3_norm, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(code_norm)
        print("SUCCESS: Updated templates/doctor/patient_access.html")
    else:
        print("FAILURE: Target snippets not found in patient_access.html")

if __name__ == "__main__":
    main()
