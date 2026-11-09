from unittest.mock import MagicMock

mock_sup = MagicMock()
mock_sup.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {"name": "test"}

res1 = mock_sup.table("patients").select("*").eq("id", "123").maybe_single().execute()
print("res1:", res1.data)

res2 = mock_sup.table("patients").select("*").eq("health_id", "456").maybe_single().execute()
print("res2:", res2.data)
