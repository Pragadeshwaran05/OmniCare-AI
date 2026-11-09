with open("app.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
    "from services.msg91_otp_service import MSG91OTPService, mask_phone_number, mask_email_address",
    "from services.msg91_otp_service import MSG91OTPService, mask_phone_number, mask_email_address, is_dev_mode"
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Added is_dev_mode import to app.py")
