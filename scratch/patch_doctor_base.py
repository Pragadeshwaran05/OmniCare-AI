with open('templates/doctor_base.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Topbar actions
target_topbar_actions = """        <div class="common-topbar-actions">

        <span
            class="common-topbar-action"
            title="Notifications"
            aria-label="Notifications"
        >
            🔔
        </span>

        <a
            href="{{ url_for('doctor_profile') }}"
            class="common-topbar-action"
            title="Doctor Profile"
            aria-label="Doctor Profile"
        >
            👤
        </a>

    </div>"""

replacement_topbar_actions = """        <div class="common-topbar-actions">
        {% if is_external_consultation %}
            <span style="background: #f0fdfa; color: #0f766e; border: 1px solid #99f6e4; padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; gap: 5px;">
                🔒 External Read-Only Session
            </span>
        {% else %}
        <span
            class="common-topbar-action"
            title="Notifications"
            aria-label="Notifications"
        >
            🔔
        </span>

        <a
            href="{{ url_for('doctor_profile') }}"
            class="common-topbar-action"
            title="Doctor Profile"
            aria-label="Doctor Profile"
        >
            👤
        </a>
        {% endif %}
    </div>"""

assert target_topbar_actions in content, "target_topbar_actions not found"
content = content.replace(target_topbar_actions, replacement_topbar_actions, 1)

# 2. Sidebar wrap
target_aside_start = """        <!-- =================================================
            SIDEBAR OVERLAY
            ================================================= -->"""
replacement_aside_start = """        {% if not is_external_consultation %}
        <!-- =================================================
            SIDEBAR OVERLAY
            ================================================= -->"""

assert target_aside_start in content, "target_aside_start not found"
content = content.replace(target_aside_start, replacement_aside_start, 1)

target_aside_end = """        </aside>


        <!-- =================================================
            MAIN CONTENT
            ================================================= -->

        <main class="doctor-main">"""

replacement_aside_end = """        </aside>
        {% endif %}


        <!-- =================================================
            MAIN CONTENT
            ================================================= -->

        <main class="doctor-main" {% if is_external_consultation %}style="margin-left: 0 !important; width: 100% !important; max-width: 100% !important;"{% endif %}>"""

assert target_aside_end in content, "target_aside_end not found"
content = content.replace(target_aside_end, replacement_aside_end, 1)

# 3. Bottom bar wrap
target_bottom_start = """        <!-- =================================================
            COMMON BOTTOM NAVIGATION
            ================================================= -->

        <nav class="common-bottom-bar">"""

replacement_bottom_start = """        {% if not is_external_consultation %}
        <!-- =================================================
            COMMON BOTTOM NAVIGATION
            ================================================= -->

        <nav class="common-bottom-bar">"""

assert target_bottom_start in content, "target_bottom_start not found"
content = content.replace(target_bottom_start, replacement_bottom_start, 1)

target_bottom_end = """        </nav>


        <!-- =================================================
            JAVASCRIPT
            ================================================= -->"""

replacement_bottom_end = """        </nav>
        {% endif %}


        <!-- =================================================
            JAVASCRIPT
            ================================================= -->"""

assert target_bottom_end in content, "target_bottom_end not found"
content = content.replace(target_bottom_end, replacement_bottom_end, 1)

with open('templates/doctor_base.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated doctor_base.html for external consultations!")
