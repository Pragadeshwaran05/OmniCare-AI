import os

def main():
    test_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "test_universal_qr_consultation.py")
    with open(test_path, "r", encoding="utf-8") as f:
        content = f.read()

    target = '''        # Test API endpoint
        res = self.client.post("/api/msg91/verify-access-token", json={
            "access_token": "demo_token_xyz",
            "patient_id": self.patient_id,
            "context": "external"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn(f"/doctor/patient-workspace/{self.patient_id}", data["redirect_url"])'''

    new_test = '''        # Test API endpoint
        res = self.client.post("/api/msg91/verify-access-token", json={
            "access_token": "demo_token_xyz",
            "patient_id": self.patient_id,
            "context": "external"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn(f"/doctor/patient-workspace/{self.patient_id}", data["redirect_url"])

    # ---------------------------------------------------------
    # 10. DATABASE SCHEMA INTEGRITY & NO "doctors.name"
    # ---------------------------------------------------------
    @patch("app.supabase_admin")
    def test_14_doctor_send_otp_schema_integrity(self, mock_supabase):
        """Simulates strict PostgreSQL column enforcement: reject any query referencing non-existent 'name' column."""
        def strict_table_mock(tbl):
            m = MagicMock()
            def select_fn(cols):
                col_list = [c.strip() for c in cols.split(",")]
                # PostgreSQL 42703 strict check: table doctors only has full_name, not name
                if tbl == "doctors":
                    if "name" in col_list:
                        raise Exception("PostgreSQL error 42703: column doctors.name does not exist")
                    sel_mock = MagicMock()
                    sel_mock.eq.return_value.maybe_single.return_value.execute.return_value.data = {
                        "id": self.doctor_id,
                        "full_name": "Dr. Schema Verified"
                    }
                    return sel_mock
                elif tbl == "patients":
                    if "name" in col_list:
                        raise Exception("PostgreSQL error 42703: column patients.name does not exist")
                    sel_mock = MagicMock()
                    sel_mock.eq.return_value.maybe_single.return_value.execute.return_value.data = self.patient_data
                    sel_mock.eq.return_value.single.return_value.execute.return_value.data = self.patient_data
                    return sel_mock
                return MagicMock()

            m.select.side_effect = select_fn
            return m

        mock_supabase.table.side_effect = strict_table_mock

        with self.client.session_transaction() as sess:
            sess["doctor_id"] = self.doctor_id

        # Must succeed without PostgreSQL 42703
        send_res = self.client.post(f"/doctor/patient-access/{self.patient_id}/send-otp")
        self.assertEqual(send_res.status_code, 200)
        send_data = send_res.get_json()
        self.assertTrue(send_data["success"])
        self.assertIn("3210", send_data["masked_destination"])'''

    content_norm = content.replace("\r\n", "\n")
    target_norm = target.replace("\r\n", "\n")
    new_test_norm = new_test.replace("\r\n", "\n")

    if target_norm in content_norm:
        content_norm = content_norm.replace(target_norm, new_test_norm, 1)
        with open(test_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content_norm)
        print("SUCCESS: Added test_14 to test_universal_qr_consultation.py")
    else:
        print("FAILURE: Target not found")

if __name__ == "__main__":
    main()
