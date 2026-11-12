with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Normalize CRLF
c_norm = c.replace('\r\n', '\n')

old_code = '''        addDoctorAIMessage(

            "I could not process your request right now. Please try again."

        );'''

new_code = '''        const errorMsg = (error && error.message) ? error.message : "I could not process your request right now. Please try again.";
        addDoctorAIMessage(errorMsg);'''

assert old_code in c_norm, "old_code not found in patient_workspace.html"
c_norm = c_norm.replace(old_code, new_code)

with open('templates/doctor/patient_workspace.html', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(c_norm.replace('\n', '\r\n'))

print("SUCCESS: patient_workspace.html updated.")
