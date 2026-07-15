import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
spec = importlib.util.spec_from_file_location("money_app", Path(__file__).parents[1] / "app.py")
money_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(money_app)


def test_budget_api_persists_payday_data_and_recurring_payments(tmp_path):
    money_app.DB_PATH = tmp_path / "money_manager.db"

    with money_app.app.test_client() as client:
        data = client.get("/api/budget").get_json()
        data["settings"]["paydays"] = ["2026-07-23", "2026-08-28"]
        data["recurringPayments"].append({
            "id": "test-recurring",
            "name": "Test Subscription",
            "amount": 12.34,
            "day": 15,
            "active": True,
        })

        response = client.put("/api/budget", json=data)

        assert response.status_code == 200
        saved = client.get("/api/budget").get_json()
        assert saved["settings"]["paydays"] == ["2026-07-23", "2026-08-28"]
        assert any(payment["id"] == "test-recurring" for payment in saved["recurringPayments"])


def test_budget_defaults_and_migrates_to_july_2026_payday(tmp_path):
    money_app.DB_PATH = tmp_path / "money_manager.db"

    with money_app.app.test_client() as client:
        data = client.get("/api/budget").get_json()
        assert data["settings"]["paydays"] == ["2026-07-23"]

        data["settings"]["paydays"] = ["2026-07-01"]
        client.put("/api/budget", json=data)

        saved = client.get("/api/budget").get_json()
        assert saved["settings"]["paydays"] == ["2026-07-01", "2026-07-23"]
