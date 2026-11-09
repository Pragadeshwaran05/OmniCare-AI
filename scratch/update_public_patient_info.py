with open("templates/patient/public_patient_info.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add MSG91 SDK script tag in head
if "https://verify.msg91.com/otp-provider.js" not in content:
    content = content.replace(
        '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/public_patient_info.css\') }}">',
        '<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/public_patient_info.css\') }}">\n    <script type="text/javascript" src="https://verify.msg91.com/otp-provider.js"></script>'
    )
    print("1. Added MSG91 SDK script tag to public_patient_info.html.")

# 2. Update 6-digit text to 4-digit
content = content.replace(
    "Please ask the patient for the 6-digit OTP displayed on their device.",
    "Please ask the patient for the 4-digit OTP displayed on their device."
)
content = content.replace(
    '<label for="otp_code">Enter 6-Digit OTP</label>',
    '<label for="otp_code">Enter 4-Digit OTP</label>'
)
content = content.replace(
    '<input type="text" id="otp_code" name="otp_code" maxlength="6" pattern="[0-9]{6}" inputmode="numeric" placeholder="• • • • • •" required autocomplete="one-time-code">',
    '<input type="text" id="otp_code" name="otp_code" maxlength="4" pattern="[0-9]{4}" inputmode="numeric" placeholder="• • • •" required autocomplete="one-time-code">'
)
content = content.replace(
    '<strong id="otpCountdown">05:00</strong>',
    '<strong id="otpCountdown">15:00</strong>'
)

# 3. Update JavaScript logic
content = content.replace(
    "let countdownSeconds = 300;",
    "let countdownSeconds = 900;"
)
content = content.replace(
    "countdownSeconds = durationSeconds || 300;",
    "countdownSeconds = durationSeconds || 900;"
)
content = content.replace(
    "startOtpTimer(data.expires_in_seconds || 300);",
    "startOtpTimer(data.expires_in_seconds || 900);"
)
content = content.replace(
    "if (otpVal.length !== 6) {\n                errorBox.textContent = 'Please enter a valid 6-digit numeric OTP.';",
    "if (otpVal.length !== 4) {\n                errorBox.textContent = 'Please enter a valid 4-digit numeric OTP.';"
)

# 4. Add widget integration
widget_ext_block = """
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
                        if (token) {
                            await verifyExternalWithToken(token);
                        }
                    },
                    failure: (err) => {
                        console.warn("MSG91 Widget failure:", err);
                    }
                };
                initSendOTP(window.msg91Config);
            } catch(e) {
                console.warn("MSG91 initSendOTP notice:", e);
            }
        }

        async function verifyExternalWithToken(accessToken) {
            const successBox = document.getElementById('otpSuccessMessage');
            const errorBox = document.getElementById('otpErrorMessage');
            errorBox.style.display = 'none';

            try {
                const response = await fetch(`/qr/${encodeURIComponent(qrIdentifier)}/verify-otp`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        access_token: accessToken,
                        challenge_id: activeChallengeId || document.getElementById('challenge_id').value
                    })
                });
                const data = await response.json();
                if (data.success) {
                    successBox.textContent = '✓ Verified via MSG91! Redirecting to Clinical Workspace...';
                    successBox.style.display = 'block';
                    if (countdownTimer) clearInterval(countdownTimer);
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 800);
                } else {
                    errorBox.textContent = data.error || 'Token verification failed.';
                    errorBox.style.display = 'block';
                }
            } catch (err) {
                errorBox.textContent = 'Network error during token verification.';
                errorBox.style.display = 'block';
            }
        }
"""

if "verifyExternalWithToken" not in content:
    content = content.replace(
        "async function handleResendOTP() {",
        widget_ext_block + "\n        async function handleResendOTP() {"
    )
    print("4. Added MSG91 widget init & verifyExternalWithToken.")

with open("templates/patient/public_patient_info.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated templates/patient/public_patient_info.html successfully.")
