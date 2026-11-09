with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = "qr_data = request.host_url.rstrip('/') + url_for(\"public_patient_info\", patient_id=patient_id)"
print("Is target in text?", target in text)
