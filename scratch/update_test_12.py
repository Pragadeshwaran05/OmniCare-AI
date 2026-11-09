with open("tests/test_universal_qr_consultation.py", "r", encoding="utf-8") as f:
    t = f.read()

old_test_12 = """    @patch("app.supabase_admin")
    def test_12_doctor_instant_otp_flow(self, mock_supabase):
        \"\"\"Doctor can dispatch 4-digit OTP to patient and verify demo OTP '1234' for instant 5-minute access.\"\"\"
        mock_supabase.table().select().eq().single().execute.return_value.data = self.patient_data
        mock_supabase.table().select().eq().maybe_single().execute.return_value.data = {
            "id": self.doctor_id,
            "full_name": "Dr. Internal Hospital",
        }"""

new_test_12 = """    @patch("app.supabase_admin")
    def test_12_doctor_instant_otp_flow(self, mock_supabase):
        \"\"\"Doctor can dispatch 4-digit OTP to patient and verify demo OTP '1234' for instant 5-minute access.\"\"\"
        def table_mock(tbl):
            m = MagicMock()
            if tbl == "doctors":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                    "id": self.doctor_id,
                    "full_name": "Dr. Internal Hospital"
                }
            elif tbl == "patients":
                m.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data
                m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = self.patient_data
            return m
        mock_supabase.table.side_effect = table_mock"""

if old_test_12 in t:
    t = t.replace(old_test_12, new_test_12, 1)
    with open("tests/test_universal_qr_consultation.py", "w", encoding="utf-8") as f:
        f.write(t)
    print("Updated test_12_doctor_instant_otp_flow mock.")
else:
    print("Could not match old_test_12")
