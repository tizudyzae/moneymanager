import importlib.util
import json
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


def test_budget_defaults_and_migrates_to_july_2026_payday(tmp_path, monkeypatch):
    money_app.DB_PATH = tmp_path / "money_manager.db"
    actual_date = money_app.date

    class BeforePayday:
        @staticmethod
        def today():
            return actual_date.fromisoformat("2026-07-22")

    monkeypatch.setattr(money_app, "date", BeforePayday)

    with money_app.app.test_client() as client:
        data = client.get("/api/budget").get_json()
        assert data["settings"]["paydays"] == ["2026-07-23"]

        data["settings"]["paydays"] = ["2026-07-01"]
        client.put("/api/budget", json=data)

        saved = client.get("/api/budget").get_json()
        assert saved["settings"]["paydays"] == ["2026-07-01", "2026-07-23"]


def test_budget_api_persists_wage_forecast_data(tmp_path):
    money_app.DB_PATH = tmp_path / "money_manager.db"

    with money_app.app.test_client() as client:
        data = client.get("/api/budget").get_json()
        data["wageForecast"]["settings"]["hourlyRate"] = 15.25
        data["wageForecast"]["cycles"]["2026-08-20"] = {
            "weeks": [
                {"basicHours": 40, "basicMinutes": 0, "nightHours": 5, "nightMinutes": 30},
                {"basicHours": 39, "basicMinutes": 15, "nightHours": 2, "nightMinutes": 0},
                {"basicHours": 38, "basicMinutes": 45, "nightHours": 0, "nightMinutes": 30},
                {"basicHours": 40, "basicMinutes": 0, "nightHours": 1, "nightMinutes": 0},
            ]
        }

        response = client.put("/api/budget", json=data)

        assert response.status_code == 200
        saved = client.get("/api/budget").get_json()
        assert saved["wageForecast"]["settings"]["hourlyRate"] == 15.25
        assert saved["wageForecast"]["cycles"]["2026-08-20"]["weeks"][0]["nightMinutes"] == 30


def test_icon_api_caches_remote_images(tmp_path, monkeypatch):
    money_app.ICON_CACHE_DIR = tmp_path / "icon_cache"
    calls = []

    class FakeHeaders:
        def get_content_type(self):
            return "image/png"

    class FakeResponse:
        headers = FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            calls.append("read")
            return b"fake-png"

    def fake_urlopen(_request, timeout):
        calls.append(timeout)
        return FakeResponse()

    monkeypatch.setattr(money_app, "urlopen", fake_urlopen)

    with money_app.app.test_client() as client:
        first = client.get("/api/icon?url=https%3A%2F%2Fexample.com%2Ficon.png")
        second = client.get("/api/icon?url=https%3A%2F%2Fexample.com%2Ficon.png")

    assert first.status_code == 200
    assert first.data == b"fake-png"
    assert second.status_code == 200
    assert second.data == b"fake-png"
    assert calls == [money_app.ICON_FETCH_TIMEOUT, "read"]
    assert len(list(money_app.ICON_CACHE_DIR.iterdir())) == 1


def test_icon_api_rejects_non_http_urls(tmp_path):
    money_app.ICON_CACHE_DIR = tmp_path / "icon_cache"

    with money_app.app.test_client() as client:
        response = client.get("/api/icon?url=file%3A%2F%2F%2Fetc%2Fpasswd")

    assert response.status_code == 400


def test_rota_preview_api_requests_exact_range_without_mutating_budget(tmp_path, monkeypatch):
    money_app.DB_PATH = tmp_path / "money_manager.db"
    monkeypatch.setenv("ROTA_IMPORTER_URL", "http://explicit-rota:8099")
    requested = []

    class FakeResponse:
        def __init__(self, shifts): self.shifts = shifts
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return json.dumps({"shifts": self.shifts}).encode()

    def fake_urlopen(request, timeout):
        requested.append(request.full_url)
        shifts = [{"id": "one", "date": "2026-06-14", "start": "22:00", "finish": "06:00", "break_minutes": 0}] if "start_date=2026-06-14" in request.full_url else []
        return FakeResponse(shifts)

    monkeypatch.setattr(money_app, "urlopen", fake_urlopen)
    with money_app.app.test_client() as client:
        before = client.get("/api/budget").get_json()
        response = client.post("/api/wages/import-rota-preview", json={"payday": "2026-07-23"})
        after = client.get("/api/budget").get_json()

    assert response.status_code == 200
    assert [url.split("?", 1)[1] for url in requested] == [
        "start_date=2026-06-14&end_date=2026-06-20",
        "start_date=2026-06-21&end_date=2026-06-27",
        "start_date=2026-06-28&end_date=2026-07-04",
        "start_date=2026-07-05&end_date=2026-07-11",
    ]
    assert response.get_json()["weeks"][0]["night_minutes"] == 480
    assert before == after


def test_rota_preview_api_collects_early_and_late_weeks_without_range_truncation(tmp_path, monkeypatch):
    money_app.DB_PATH = tmp_path / "money_manager.db"
    monkeypatch.setenv("ROTA_IMPORTER_URL", "http://explicit-rota:8099")
    shifts_by_start = {
        "2026-07-12": [{"id": "week-40", "date": "2026-07-12", "start": "09:00", "finish": "17:00"}],
        "2026-07-19": [{"id": "week-41", "date": "2026-07-19", "start": "09:00", "finish": "17:00"}],
        "2026-07-26": [{"id": "week-42", "date": "2026-07-26", "start": "09:00", "finish": "17:00"}],
        "2026-08-02": [{"id": "week-43", "date": "2026-08-02", "start": "09:00", "finish": "17:00"}],
    }

    def fake_request(start_date, end_date):
        return {"shifts": shifts_by_start[start_date]}, {"hostname": "rota", "port": 8099}, f"http://rota/shifts?start_date={start_date}&end_date={end_date}"

    monkeypatch.setattr(money_app, "request_rota_shifts", fake_request)
    money_app._rota_debug_entries.clear()
    with money_app.app.test_client() as client:
        response = client.post("/api/wages/import-rota-preview", json={"payday": "2026-08-20"})
        debug = client.get("/api/wages/rota-debug").get_json()["entries"]

    assert response.status_code == 200
    assert [week["shift_count"] for week in response.get_json()["weeks"]] == [1, 1, 1, 1]
    assert response.get_json()["source_shift_ids"] == ["week-40", "week-41", "week-42", "week-43"]
    assert [entry["shift_count"] for entry in debug if entry["event"] == "week_response"] == [1, 1, 1, 1]
    assert debug[-1]["weekly_shift_counts"] == [1, 1, 1, 1]
    assert all("attempted_url" not in entry for entry in debug)


def test_rota_debug_api_clears_entries():
    money_app._rota_debug_entries[:] = [{"event": "test"}]

    with money_app.app.test_client() as client:
        response = client.delete("/api/wages/rota-debug")
        saved = client.get("/api/wages/rota-debug").get_json()

    assert response.status_code == 200
    assert saved == {"entries": []}


def test_rota_preview_api_failure_does_not_modify_wage_cycle(tmp_path, monkeypatch):
    money_app.DB_PATH = tmp_path / "money_manager.db"
    monkeypatch.setenv("ROTA_IMPORTER_URL", "http://explicit-rota:8099")

    def invalid_response(*_args, **_kwargs):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self): return b'{not json'
        return FakeResponse()

    monkeypatch.setattr(money_app, "urlopen", invalid_response)
    with money_app.app.test_client() as client:
        data = client.get("/api/budget").get_json()
        data["wageForecast"]["cycles"]["2026-07-23"] = {"weeks": [{"basicHours": 12}]}
        client.put("/api/budget", json=data)
        response = client.post("/api/wages/import-rota-preview", json={"payday": "2026-07-23"})
        saved = client.get("/api/budget").get_json()

    assert response.status_code == 502
    assert response.get_json()["category"] == "invalid_json"
    assert saved["wageForecast"]["cycles"]["2026-07-23"]["weeks"][0]["basicHours"] == 12


def test_supervisor_discovers_repository_prefixed_slug_hostname_and_port(monkeypatch):
    monkeypatch.delenv("ROTA_IMPORTER_URL", raising=False)
    monkeypatch.setenv("SUPERVISOR_TOKEN", "secret-token")
    money_app.clear_rota_address_cache()
    seen = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self):
            return json.dumps({"data": {"addons": [{"name": "Something Else", "slug": "other"}, {"name": "Renamed", "slug": "local_ab12_rota_importer", "hostname": "local-ab12-rota-importer", "ingress_port": 8099}]}}).encode()

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["authorization"] = request.get_header("Authorization")
        return Response()

    monkeypatch.setattr(money_app, "urlopen", fake_urlopen)
    address = money_app.discover_rota_importer()
    assert seen == {"url": "http://supervisor/addons", "authorization": "Bearer secret-token"}
    assert address == {"url": "http://local-ab12-rota-importer:8099", "hostname": "local-ab12-rota-importer", "port": 8099, "override": False}


def test_supervisor_discovery_matches_addon_name(monkeypatch):
    monkeypatch.delenv("ROTA_IMPORTER_URL", raising=False)
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")
    money_app.clear_rota_address_cache()

    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return json.dumps({"data": {"addons": [{"name": "Rota PDF Importer", "slug": "unexpected", "hostname": "actual-host", "ingress_port": 8123}]}}).encode()

    monkeypatch.setattr(money_app, "urlopen", lambda *_args, **_kwargs: Response())
    assert money_app.discover_rota_importer()["url"] == "http://actual-host:8123"


def test_explicit_rota_url_override_skips_supervisor(monkeypatch):
    monkeypatch.setenv("ROTA_IMPORTER_URL", "http://debug-host:9000/")
    monkeypatch.setattr(money_app, "urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Supervisor must not be called")))
    assert money_app.discover_rota_importer() == {"url": "http://debug-host:9000", "hostname": "debug-host", "port": 9000, "override": True}


def test_unreachable_rota_importer_reports_connection_refused(monkeypatch):
    monkeypatch.setenv("ROTA_IMPORTER_URL", "http://debug-host:8099")

    def refused(*_args, **_kwargs):
        from urllib.error import URLError
        raise URLError(ConnectionRefusedError(111, "Connection refused"))

    monkeypatch.setattr(money_app, "urlopen", refused)
    with money_app.app.test_client() as client:
        response = client.post("/api/wages/import-rota-preview", json={"payday": "2026-07-23"})
    assert response.status_code == 502
    assert response.get_json()["category"] == "connection_refused"


def test_rota_status_reports_safe_discovered_address(monkeypatch):
    monkeypatch.setattr(money_app, "request_rota_shifts", lambda *_args: ({"shifts": []}, {"hostname": "repo-rota", "port": 8099}, "http://repo-rota:8099/api/my-wage-shifts"))
    with money_app.app.test_client() as client:
        response = client.get("/api/wages/rota-status")
    assert response.get_json() == {"available": True, "resolved_hostname": "repo-rota", "port": 8099, "endpoint_reachable": True}
