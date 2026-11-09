import re

with open("templates/doctor/patient_access.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add MSG91 SDK script tag
if "https://verify.msg91.com/otp-provider.js" not in content:
    content = content.replace(
        '<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>',
        '<script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>\n<script type="text/javascript" src="https://verify.msg91.com/otp-provider.js"></script>'
    )
    print("1. Added MSG91 SDK script tag.")

# 2. Update 6-digit text to 4-digit in Option B
content = content.replace(
    "<p>Sends a 6-digit verification code to the patient's mobile for immediate 5-minute read-only consultation.</p>",
    "<p>Sends a 4-digit verification code to the patient's mobile for immediate 5-minute read-only consultation.</p>"
)

# 3. Update modal texts and inputs
content = content.replace(
    "Ask the patient to share the 6-digit code received on their phone.",
    "Ask the patient to share the 4-digit code received on their phone."
)
content = content.replace(
    '<label for="doctor_entered_otp">Enter 6-Digit OTP</label>',
    '<label for="doctor_entered_otp">Enter 4-Digit OTP</label>'
)
content = content.replace(
    'maxlength="6"',
    'maxlength="4"'
)
content = content.replace(
    'pattern="[0-9]{6}"',
    'pattern="[0-9]{4}"'
)
content = content.replace(
    'placeholder="• • • • • •"',
    'placeholder="• • • •"'
)
content = content.replace(
    '<strong id="docOtpTimer">05:00</strong>',
    '<strong id="docOtpTimer">15:00</strong>'
)

# 4. Update JavaScript validation & timer defaults
content = content.replace(
    "let docSecondsRemaining = 300;",
    "let docSecondsRemaining = 900;"
)
content = content.replace(
    "startDoctorOtpTimer(data.expires_in_seconds || 300);",
    "startDoctorOtpTimer(data.expires_in_seconds || 900);"
)
content = content.replace(
    "function startDoctorOtpTimer(seconds) {\n    if (docOtpCountdown) clearInterval(docOtpCountdown);\n    docSecondsRemaining = seconds || 300;",
    "function startDoctorOtpTimer(seconds) {\n    if (docOtpCountdown) clearInterval(docOtpCountdown);\n    docSecondsRemaining = seconds || 900;"
)
content = content.replace(
    'if (enteredOtp.length !== 6) {\n        errBox.textContent = "Please enter a valid 6-digit OTP.";',
    'if (enteredOtp.length !== 4) {\n        errBox.textContent = "Please enter a valid 4-digit OTP.";'
)

# 5. Add MSG91 widget init & token handler function
widget_js_block = """
// ============================================================
// MSG91 OTP WIDGET INTEGRATION
// ============================================================
const msg91WidgetId = {{ msg91_widget_id|tojson if msg91_widget_id else '""' }};
const msg91TokenAuth = {{ msg91_token_auth|tojson if msg91_token_auth else '""' }};

if (typeof initSendOTP !== "undefined" && msg91WidgetId && msg91TokenAuth) {
    try {
        window.msg91Config = {
            widgetId: msg91WidgetId,
            tokenAuth: msg91TokenAuth,
            exposeMethods: true,
            success: async (tokenData) => {
                console.log("MSG91 Widget verification success:", tokenData);
                const token = typeof tokenData === "string" ? tokenData : ((tokenData && (tokenData["access-token"] || tokenData.message)) || "");
                if (token && currentPatientId) {
                    await verifyDoctorOtpWithToken(token);
                }
            },
            failure: (err) => {
                console.warn("MSG91 Widget failure:", err);
            }
        };
        initSendOTP(window.msg91Config);
    } catch (e) {
        console.warn("MSG91 initSendOTP notice:", e);
    }
}

async function verifyDoctorOtpWithToken(accessToken) {
    const successBox = document.getElementById("docOtpSuccess2");
    const errBox = document.getElementById("docOtpError2");
    errBox.style.display = "none";

    try {
        const response = await fetch(`/doctor/patient-access/${encodeURIComponent(currentPatientId)}/verify-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                access_token: accessToken
            })
        });
        const data = await response.json();
        if (data.success) {
            successBox.textContent = "✓ Verified via MSG91! Opening Patient Workspace in 5-minute read-only mode...";
            successBox.style.display = "block";
            if (docOtpCountdown) clearInterval(docOtpCountdown);
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 800);
        } else {
            errBox.textContent = data.error || "Token verification failed.";
            errBox.style.display = "block";
        }
    } catch (err) {
        errBox.textContent = "Network error during token verification.";
        errBox.style.display = "block";
    }
}
"""

if "verifyDoctorOtpWithToken" not in content:
    content = content.replace(
        "async function startQRScanner() {",
        widget_js_block + "\nasync function startQRScanner() {"
    )
    print("5. Added MSG91 widget init & verifyDoctorOtpWithToken.")

with open("templates/doctor/patient_access.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated templates/doctor/patient_access.html successfully.")
