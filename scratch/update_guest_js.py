with open('static/js/guest_patient_workspace.js', 'r', encoding='utf-8') as f:
    c = f.read()

c_norm = c.replace('\r\n', '\n')

old_code = '''        addDoctorAIMessage(
            "I could not process your request right now. Please try again."
        );'''

new_code = '''        const errorMsg = (error && error.message) ? error.message : "I could not process your request right now. Please try again.";
        addDoctorAIMessage(errorMsg);'''

assert old_code in c_norm, "old_code not found in guest_patient_workspace.js"
c_norm = c_norm.replace(old_code, new_code)

with open('static/js/guest_patient_workspace.js', 'w', encoding='utf-8') as f:
    f.write(c_norm)

print("SUCCESS: guest_patient_workspace.js updated.")
