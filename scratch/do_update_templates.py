import os
import re

def update_doctor_patient_access():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "doctor", "patient_access.html")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().replace("\r\n", "\n")

    # 1. Insert docOtpDemoBanner right after <div id="docOtpStage2"...>
    banner_html = '\n            <div id="docOtpDemoBanner" class="doc-alert doc-alert-info" style="display: none; background: #e6fffa; border: 1px solid #319795; color: #234e52; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-weight: 600;"></div>\n'
    
    stage2_pattern = re.compile(r'(<div\s+id="docOtpStage2"[^>]*>)', re.IGNORECASE)
    if not re.search(r'id="docOtpDemoBanner"', text):
        text = stage2_pattern.sub(r'\1' + banner_html, text, count=1)
        print("Inserted docOtpDemoBanner in patient_access.html")

    # 2. Update sendDoctorOtp to show demo banner and 300s timer
    old_success = re.compile(
        r'if\s*\(\s*data\.success\s*\)\s*\{[\s\n]*currentChallengeId\s*=\s*data\.challenge_id;[\s\n]*document\.getElementById\("docOtpMaskedDest"\)\.textContent\s*=\s*data\.masked_destination;[\s\n]*document\.getElementById\("docOtpStage1"\)\.style\.display\s*=\s*"none";[\s\n]*document\.getElementById\("docOtpStage2"\)\.style\.display\s*=\s*"block";[\s\n]*startDoctorOtpTimer\(data\.expires_in_seconds\s*\|\|\s*\d+\);',
        re.MULTILINE
    )

    new_success = '''if (data.success) {
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
            startDoctorOtpTimer(data.expires_in_seconds || 300);'''

    text, n_subs = old_success.subn(new_success, text, count=1)
    print(f"Substituted sendDoctorOtp success handling (count={n_subs})")

    # 3. Update timer default
    text = re.sub(r'docSecondsRemaining\s*=\s*seconds\s*\|\|\s*900;', 'docSecondsRemaining = seconds || 300;', text)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("Saved patient_access.html")


def update_public_patient_info():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "patient", "public_patient_info.html")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().replace("\r\n", "\n")

    # 1. Insert demoOtpBanner right after <div id="modalStep2"...>
    banner_html = '\n                <div id="demoOtpBanner" class="modal-alert modal-alert-info" style="display: none; background: #e6fffa; border: 1px solid #319795; color: #234e52; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-weight: 600;"></div>\n'
    
    step2_pattern = re.compile(r'(<div\s+id="modalStep2"[^>]*>)', re.IGNORECASE)
    if not re.search(r'id="demoOtpBanner"', text):
        text = step2_pattern.sub(r'\1' + banner_html, text, count=1)
        print("Inserted demoOtpBanner in public_patient_info.html")

    # 2. Update handleRequestConsultation to show demo banner and 300s timer
    old_success = re.compile(
        r'if\s*\(\s*data\.success\s*\)\s*\{[\s\n]*activeChallengeId\s*=\s*data\.challenge_id;[\s\n]*document\.getElementById\(\'challenge_id\'\)\.value\s*=\s*data\.challenge_id;[\s\n]*document\.getElementById\(\'maskedDestinationText\'\)\.textContent\s*=\s*data\.masked_destination;[\s\n]*document\.getElementById\(\'modalStep1\'\)\.style\.display\s*=\s*\'none\';[\s\n]*document\.getElementById\(\'modalStep2\'\)\.style\.display\s*=\s*\'block\';[\s\n]*startOtpTimer\(data\.expires_in_seconds\s*\|\|\s*\d+\);',
        re.MULTILINE
    )

    new_success = '''if (data.success) {
                    activeChallengeId = data.challenge_id;
                    document.getElementById('challenge_id').value = data.challenge_id;
                    document.getElementById('maskedDestinationText').textContent = data.masked_destination;

                    const demoBanner = document.getElementById('demoOtpBanner');
                    if (data.is_demo_mode && data.demo_otp_notice) {
                        demoBanner.textContent = data.demo_otp_notice;
                        demoBanner.style.display = 'block';
                    } else if (demoBanner) {
                        demoBanner.style.display = 'none';
                    }

                    document.getElementById('modalStep1').style.display = 'none';
                    document.getElementById('modalStep2').style.display = 'block';
                    startOtpTimer(data.expires_in_seconds || 300);'''

    text, n_subs = old_success.subn(new_success, text, count=1)
    print(f"Substituted handleRequestConsultation success handling (count={n_subs})")

    # 3. Update countdown timer default
    text = re.sub(r'countdownSeconds\s*=\s*durationSeconds\s*\|\|\s*900;', 'countdownSeconds = durationSeconds || 300;', text)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("Saved public_patient_info.html")


if __name__ == "__main__":
    update_doctor_patient_access()
    update_public_patient_info()
