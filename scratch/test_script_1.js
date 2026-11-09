
let html5QrCode = null;
let scannerRunning = false;
let currentPatientId = null;
let currentChallengeId = null;
let docOtpCountdown = null;
let docSecondsRemaining = 900;

function openDoctorOtpModal(patientId, patientName) {
    currentPatientId = patientId;
    document.getElementById("docOtpPatientName").textContent = patientName || "Patient";
    document.getElementById("docOtpStage1").style.display = "block";
    document.getElementById("docOtpStage2").style.display = "none";
    document.getElementById("docOtpError1").style.display = "none";
    document.getElementById("doctorOtpModal").style.display = "flex";
}

function closeDoctorOtpModal() {
    document.getElementById("doctorOtpModal").style.display = "none";
    if (docOtpCountdown) clearInterval(docOtpCountdown);
}

async function sendDoctorOtp() {
    const btn = document.getElementById("btnDocSendOtp");
    const errBox = document.getElementById("docOtpError1");
    const errBox2 = document.getElementById("docOtpError2");
    errBox.style.display = "none";
    errBox2.style.display = "none";

    btn.disabled = true;
    btn.textContent = "Sending OTP...";

    try {
        const response = await fetch(`/doctor/patient-access/${encodeURIComponent(currentPatientId)}/send-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        const data = await response.json();

        if (data.success) {
            currentChallengeId = data.challenge_id;
            document.getElementById("docOtpMaskedDest").textContent = data.masked_destination;
            document.getElementById("docOtpStage1").style.display = "none";
            document.getElementById("docOtpStage2").style.display = "block";
            startDoctorOtpTimer(data.expires_in_seconds || 900);
            document.getElementById("doctor_entered_otp").focus();
        } else {
            errBox.textContent = data.error || "Failed to dispatch OTP to patient.";
            errBox.style.display = "block";
        }
    } catch (err) {
        errBox.textContent = "Network error while requesting OTP.";
        errBox.style.display = "block";
    } finally {
        btn.disabled = false;
        btn.textContent = "📱 Send OTP to Patient";
    }
}

function startDoctorOtpTimer(seconds) {
    if (docOtpCountdown) clearInterval(docOtpCountdown);
    docSecondsRemaining = seconds || 900;
    const timerElem = document.getElementById("docOtpTimer");

    function tick() {
        const m = Math.floor(docSecondsRemaining / 60);
        const s = docSecondsRemaining % 60;
        timerElem.textContent = `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
        if (docSecondsRemaining <= 0) {
            clearInterval(docOtpCountdown);
            const err2 = document.getElementById("docOtpError2");
            err2.textContent = "OTP expired. Please click Resend OTP.";
            err2.style.display = "block";
        }
        docSecondsRemaining--;
    }

    tick();
    docOtpCountdown = setInterval(tick, 1000);
}

async function verifyDoctorOtp(event) {
    event.preventDefault();
    const btn = document.getElementById("btnDocVerifyOtp");
    const errBox = document.getElementById("docOtpError2");
    const successBox = document.getElementById("docOtpSuccess2");
    errBox.style.display = "none";
    successBox.style.display = "none";

    const enteredOtp = document.getElementById("doctor_entered_otp").value.trim();
    if (enteredOtp.length !== 4) {
        errBox.textContent = "Please enter a valid 4-digit OTP.";
        errBox.style.display = "block";
        return;
    }

    btn.disabled = true;
    btn.textContent = "Verifying...";

    try {
        const response = await fetch(`/doctor/patient-access/${encodeURIComponent(currentPatientId)}/verify-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                challenge_id: currentChallengeId,
                otp_code: enteredOtp
            })
        });
        const data = await response.json();

        if (data.success) {
            successBox.textContent = "✓ Verified! Opening Patient Workspace in 5-minute read-only mode...";
            successBox.style.display = "block";
            if (docOtpCountdown) clearInterval(docOtpCountdown);
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 800);
        } else {
            errBox.textContent = data.error || "Incorrect OTP. Please try again.";
            errBox.style.display = "block";
        }
    } catch (err) {
        errBox.textContent = "Network error during OTP verification.";
        errBox.style.display = "block";
    } finally {
        btn.disabled = false;
        btn.textContent = "✓ Verify & Open Workspace";
    }
}


// ============================================================
// MSG91 OTP WIDGET INTEGRATION
// ============================================================
const msg91WidgetId = "";
const msg91TokenAuth = "";

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

async function startQRScanner() {
    const container = document.getElementById("qrScannerContainer");
    container.style.display = "block";
    container.scrollIntoView({ behavior: "smooth" });

    if (typeof Html5Qrcode === "undefined") {
        alert("QR scanner library failed to load. Please refresh the page.");
        return;
    }

    if (scannerRunning) return;
    html5QrCode = new Html5Qrcode("qr-reader");

    try {
        await html5QrCode.start(
            { facingMode: "environment" },
            {
                fps: 10,
                qrbox: { width: 250, height: 250 }
            },
            async (decodedText) => {
                if (!scannerRunning && html5QrCode) return;
                scannerRunning = false;

                try {
                    await html5QrCode.stop();
                    await html5QrCode.clear();
                } catch (error) {
                    console.error("Scanner stop error:", error);
                }

                container.style.display = "none";

                let raw = decodedText.trim();
                let identifier = raw;

                // Support QR codes containing canonical URL https://domain/qr/<token>
                // or legacy URL https://domain/patient-info/<patient_id>
                try {
                    const url = new URL(raw);
                    const pathParts = url.pathname.split('/').filter(Boolean);
                    if (pathParts.length >= 2 && pathParts[0] === 'qr') {
                        identifier = pathParts[1];
                    } else if (pathParts.length >= 2 && pathParts[0] === 'patient-info') {
                        identifier = pathParts[1];
                    } else if (url.searchParams.get("identifier")) {
                        identifier = url.searchParams.get("identifier");
                    } else if (url.searchParams.get("health_id")) {
                        identifier = url.searchParams.get("health_id");
                    } else if (url.searchParams.get("qr_token")) {
                        identifier = url.searchParams.get("qr_token");
                    } else if (url.searchParams.get("patient_id")) {
                        identifier = url.searchParams.get("patient_id");
                    }
                } catch (error) {
                    // Raw string
                }

                window.location.href =
                    "/doctor/patient-access" +
                    "?identifier=" + encodeURIComponent(identifier);
            },
            (errorMessage) => {
                // Ignore normal scanning errors
            }
        );

        scannerRunning = true;

    } catch (error) {
        console.error("Camera error:", error);
        alert("Unable to access camera. Please allow camera permission and try again.");
        container.style.display = "none";
    }
}

async function closeQRScanner() {
    const container = document.getElementById("qrScannerContainer");
    if (html5QrCode && scannerRunning) {
        try {
            await html5QrCode.stop();
            await html5QrCode.clear();
        } catch (error) {
            console.error("Scanner close error:", error);
        }
    }
    scannerRunning = false;
    html5QrCode = null;
    container.style.display = "none";
}

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

