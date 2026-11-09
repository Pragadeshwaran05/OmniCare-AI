with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    content = f.read()

target_top = """<div class="patient-workspace-page">

    <!-- BACK -->
    <a href="{{ url_for('doctor_my_patients') }}"
       class="back-to-patients">
        ← Back to My Patients
    </a>"""

replacement_top = """<div class="patient-workspace-page">

    {% if is_external_consultation or read_only %}
    <!-- EXTERNAL CONSULTATION / READ-ONLY BANNER -->
    <div class="external-consultation-banner">
        <div class="banner-content-left">
            <span class="banner-badge-icon">⏱️</span>
            <div>
                <h3 class="banner-title">EXTERNAL CONSULTATION – READ ONLY (SESSION EXPIRES IN <span id="consultationCountdownText">05:00</span>)</h3>
                <p class="banner-desc">
                    Authorized via Patient OTP. All medical records and diagnostic timelines are strictly in read-only consultation mode.
                </p>
            </div>
        </div>
        <div class="banner-timer-box">
            <span class="timer-label">Time Remaining</span>
            <span id="consultationCountdownLarge" class="timer-digits">05:00</span>
        </div>
    </div>
    {% endif %}

    <!-- BACK -->
    {% if is_external_consultation %}
    <a href="{{ url_for('public_patient_info', patient_id=patient.get('id')) }}"
       class="back-to-patients">
        ← End Consultation & Return to Patient Profile
    </a>
    {% else %}
    <a href="{{ url_for('doctor_my_patients') }}"
       class="back-to-patients">
        ← Back to My Patients
    </a>
    {% endif %}"""

assert target_top in content, "target_top not found"
content = content.replace(target_top, replacement_top, 1)

target_tail = """{% endblock %}"""

replacement_tail = """{% if is_external_consultation or read_only %}
<script>
(function() {
    let secondsLeft = {{ remaining_seconds or 300 }};
    const timerText = document.getElementById("consultationCountdownText");
    const timerLarge = document.getElementById("consultationCountdownLarge");

    function updateTimer() {
        if (secondsLeft <= 0) {
            if (timerText) timerText.textContent = "00:00 (EXPIRED)";
            if (timerLarge) timerLarge.textContent = "00:00";
            alert("Your 5-minute external consultation session has expired.");
            window.location.href = "{{ url_for('public_patient_info', patient_id=patient.get('id')) }}?session_expired=1";
            return;
        }
        const m = Math.floor(secondsLeft / 60);
        const s = secondsLeft % 60;
        const fmt = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
        if (timerText) timerText.textContent = fmt;
        if (timerLarge) timerLarge.textContent = fmt;
        secondsLeft--;
    }

    updateTimer();
    setInterval(updateTimer, 1000);
})();
</script>
{% endif %}

{% endblock %}"""

content = content.replace(target_tail, replacement_tail, 1)

with open('templates/doctor/patient_workspace.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched patient_workspace.html!")
