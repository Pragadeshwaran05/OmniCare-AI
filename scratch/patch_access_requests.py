with open('templates/patient/access_requests.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = """    <!-- =====================================================
         ERROR
         ===================================================== -->

    {% if error %}

        <div class="error-message">
            {{ error }}
        </div>

    {% endif %}


    {% if access_requests %}"""

replacement = """    <!-- =====================================================
         ERROR
         ===================================================== -->

    {% if error %}

        <div class="error-message">
            {{ error }}
        </div>

    {% endif %}

    <!-- =====================================================
         ACTIVE EXTERNAL CONSULTATIONS & OTP SESSIONS
         ===================================================== -->
    {% if active_consultations %}
    <div class="external-consultations-section">
        <div class="section-badge-header">
            <span class="badge-icon">⚡</span>
            <h2>Active Instant & External Consultations</h2>
            <p>Temporary 5-minute sessions authorized via OTP. You can revoke any active consultation immediately.</p>
        </div>

        <div class="consultation-cards-list">
            {% for session in active_consultations %}
            <div class="consultation-card {% if session.status == 'active' %}active{% else %}inactive{% endif %}">
                <div class="consultation-card-top">
                    <div class="visitor-avatar">
                        {% if session.visitor_role == 'Doctor' %}👨‍⚕️{% else %}👤{% endif %}
                    </div>
                    <div class="visitor-info">
                        <h3>{{ session.visitor_name }}</h3>
                        <span class="visitor-role-badge">{{ session.visitor_role }}</span>
                        {% if session.hospital_name and session.hospital_name != 'Not provided' %}
                        <p class="visitor-hospital">🏥 {{ session.hospital_name }} ({{ session.location }})</p>
                        {% endif %}
                        {% if session.medical_registration_number %}
                        <p class="visitor-reg">Reg No: {{ session.medical_registration_number }} <span class="unverified-tag">(Unverified External Doctor)</span></p>
                        {% endif %}
                    </div>
                    <div class="consultation-status-badge {{ session.status }}">
                        {{ session.status|upper }}
                    </div>
                </div>

                <div class="consultation-timing-bar">
                    <span>Authorized: {{ session.created_at[:16].replace('T', ' ') }}</span>
                    {% if session.status == 'active' %}
                    <span class="remaining-highlight">⏱️ Remaining: {{ session.remaining_seconds // 60 }}m {{ session.remaining_seconds % 60 }}s</span>
                    {% elif session.status == 'revoked' %}
                    <span class="revoked-highlight">Revoked at: {{ session.revoked_at[:16].replace('T', ' ') if session.revoked_at else 'Prior' }}</span>
                    {% else %}
                    <span>Session Expired</span>
                    {% endif %}
                </div>

                {% if session.status == 'active' %}
                <div class="consultation-actions">
                    <form method="POST" action="{{ url_for('patient_revoke_consultation', session_id=session.session_id) }}" onsubmit="return confirm('Are you sure you want to immediately revoke this doctor\'s consultation access?');">
                        <button type="submit" class="btn-revoke-consultation">
                            🚫 Revoke Access Immediately
                        </button>
                    </form>
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}


    {% if access_requests %}"""

assert target in content, "target not found in access_requests.html"
content = content.replace(target, replacement, 1)

with open('templates/patient/access_requests.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated access_requests.html with active consultations!")
