with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_res = """        return jsonify({
            "success": True,
            "message": msg,
            "challenge_id": challenge_meta["challenge_id"],
            "masked_destination": challenge_meta["masked_destination"],
            "expires_in_seconds": challenge_meta["expires_in_seconds"]
        }), 200"""

new_res = """        return jsonify({
            "success": True,
            "message": msg,
            "challenge_id": challenge_meta["challenge_id"],
            "masked_destination": challenge_meta["masked_destination"],
            "expires_in_seconds": challenge_meta["expires_in_seconds"],
            "otp_length": challenge_meta.get("otp_length", 4)
        }), 200"""

norm_text = text.replace('\r\n', '\n')
norm_old = old_res.replace('\r\n', '\n')
norm_new = new_res.replace('\r\n', '\n')

if norm_old in norm_text:
    norm_text = norm_text.replace(norm_old, norm_new, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(norm_text.replace('\n', '\r\n'))
    print('Added otp_length to doctor_patient_send_otp response.')
else:
    print('Target not matched.')
