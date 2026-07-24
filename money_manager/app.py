import os
import sqlite3
from pathlib import Path

import hashlib
import json
import mimetypes
import logging
import socket
import uuid
from datetime import date
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from flask import Flask, abort, g, jsonify, render_template, request, send_file
from core import build_rota_preview, default_sheets, payroll_weeks, wage_forecast_defaults

DB_PATH = Path(os.environ.get("MONEY_MANAGER_DB", "/config/money_manager.db"))
ICON_CACHE_DIR = Path(os.environ.get("MONEY_MANAGER_ICON_CACHE", "/config/icon_cache"))
ICON_FETCH_TIMEOUT = 10
ROTA_IMPORTER_TIMEOUT = 10
ROTA_ADDRESS_CACHE_SECONDS = 60
SUPERVISOR_ADDONS_URL = "http://supervisor/addons"
_rota_address_cache = None
VERSION_PATH = Path(__file__).resolve().parent / "VERSION"
NEXT_PAYDAY = "2026-07-23"

app = Flask(__name__)
logger = logging.getLogger(__name__)


class RotaImporterError(Exception):
    def __init__(self, category, message, attempted_url=None):
        super().__init__(message)
        self.category = category
        self.attempted_url = attempted_url


def configured_rota_importer_url():
    explicit = os.environ.get("ROTA_IMPORTER_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    try:
        options = json.loads(Path("/data/options.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return str(options.get("rota_importer_url", "")).strip().rstrip("/") or None


def clear_rota_address_cache():
    global _rota_address_cache
    _rota_address_cache = None


def discover_rota_importer(force=False):
    global _rota_address_cache
    explicit = configured_rota_importer_url()
    if explicit:
        parsed = urlparse(explicit)
        return {"url": explicit, "hostname": parsed.hostname, "port": parsed.port, "override": True}
    if not force and _rota_address_cache and monotonic() - _rota_address_cache[0] < ROTA_ADDRESS_CACHE_SECONDS:
        return _rota_address_cache[1]
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    if not token:
        raise RotaImporterError("discovery", "SUPERVISOR_TOKEN is unavailable")
    supervisor_request = Request(SUPERVISOR_ADDONS_URL, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    try:
        with urlopen(supervisor_request, timeout=ROTA_IMPORTER_TIMEOUT) as response:
            payload = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as error:
        logger.error("Rota Importer discovery failed at %s: %s: %s", SUPERVISOR_ADDONS_URL, type(error).__name__, error)
        raise RotaImporterError("discovery", f"{type(error).__name__}: {error}") from error
    addons = payload.get("data", {}).get("addons", payload.get("addons", [])) if isinstance(payload, dict) else []
    addon = next((item for item in addons if item.get("name") == "Rota PDF Importer" or item.get("slug", "") == "rota_importer" or item.get("slug", "").endswith("_rota_importer")), None)
    if not addon or not addon.get("hostname") or addon.get("ingress_port") is None:
        raise RotaImporterError("discovery", "Rota PDF Importer was not found in installed add-ons")
    address = {"url": f"http://{addon['hostname']}:{int(addon['ingress_port'])}", "hostname": addon["hostname"], "port": int(addon["ingress_port"]), "override": False}
    _rota_address_cache = (monotonic(), address)
    return address


def classify_upstream_error(error):
    if isinstance(error, HTTPError): return "http_error"
    if isinstance(error, (TimeoutError, socket.timeout)): return "timeout"
    reason = error.reason if isinstance(error, URLError) else error
    if isinstance(reason, socket.gaierror): return "dns_failure"
    if isinstance(reason, ConnectionRefusedError): return "connection_refused"
    return "connection_failure"


def request_rota_shifts(start_date, end_date):
    query = urlencode({"start_date": start_date, "end_date": end_date})
    for attempt in range(2):
        address = discover_rota_importer(force=attempt > 0)
        attempted_url = f"{address['url']}/api/my-wage-shifts?{query}"
        logger.info("Requesting Rota Importer URL: %s", attempted_url)
        try:
            with urlopen(Request(attempted_url, headers={"Accept": "application/json", "User-Agent": f"MoneyManager/{app_version()}"}), timeout=ROTA_IMPORTER_TIMEOUT) as response:
                return json.loads(response.read()), address, attempted_url
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            logger.error("Rota Importer invalid JSON at %s: %s: %s", attempted_url, type(error).__name__, error)
            raise RotaImporterError("invalid_json", f"{type(error).__name__}: {error}", attempted_url) from error
        except (HTTPError, URLError, TimeoutError, socket.timeout, ConnectionError) as error:
            category = classify_upstream_error(error)
            logger.error("Rota Importer %s at %s: %s: %s", category, attempted_url, type(error).__name__, error)
            if not address["override"] and attempt == 0:
                clear_rota_address_cache()
                continue
            raise RotaImporterError(category, f"{type(error).__name__}: {error}", attempted_url) from error

SCHEMA = """
CREATE TABLE IF NOT EXISTS cells (
    sheet TEXT NOT NULL,
    cell TEXT NOT NULL,
    value TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (sheet, cell)
);
CREATE TABLE IF NOT EXISTS app_data (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

DEFAULT_PAYMENT_ICONS = {
    "Rent": "🏠",
    "Council Tax": "🏛️",
    "Internet": "🌐",
    "Energy": "⚡",
    "Water": "💧",
    "Energy Credit": "⚡",
    "Car Tax": "🚗",
    "AA": "🛟",
    "Admiral": "🚘",
    "Petrol": "⛽",
    "Barclayloan": "🏦",
    "iCloud Drive": "☁️",
    "Vodafone": "📱",
    "Food": "🛒",
    "YouTube Premium": "▶️",
    "Google Drive": "△",
    "First Direct": "🏦",
    "Apple Care": "🍎",
    "Barclaycard": "💳",
    "PureGym": "🏋️",
    "ChatGPT": "✦",
    "PayPal": "P",
}

DEFAULT_PAYMENTS = [
    ["Rent",466.67,31],["Council Tax",94.91,1],["Internet",10,5],["Energy",139.97,6],
    ["Water",42.67,6],["Energy Credit",-93.91,6],["Car Tax",17.50,2],["AA",13.01,1],
    ["Admiral",49.55,12],["Petrol",105,1],["Barclayloan",92.83,31],["iCloud Drive",8.99,2],
    ["Vodafone",12,5],["Food",420,1],["YouTube Premium",12.99,25],["Google Drive",1.59,1],
    ["First Direct",7.29,2],["Apple Care",11.99,2],["Barclaycard",92.07,18],
    ["PureGym",21.99,1],["ChatGPT",17.97,1],["PayPal",24.91,1],
]


def default_budget_data():
    return {
        "settings": {"paydays": [NEXT_PAYDAY], "dailyFoodAmount": 15, "dailyPetrolAmount": 3.71},
        "recurringPayments": [
            {"id": str(uuid.uuid4()), "name": name, "icon": DEFAULT_PAYMENT_ICONS.get(name, ""), "amount": amount, "day": day, "active": True}
            for name, amount, day in DEFAULT_PAYMENTS
        ],
        "months": {},
        "wageForecast": wage_forecast_defaults(),
    }


def db():
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.executescript(SCHEMA)
    return g.db


@app.teardown_appcontext
def close_db(_error):
    if "db" in g:
        g.db.close()


def app_version():
    try:
        return VERSION_PATH.read_text().strip()
    except FileNotFoundError:
        return "0.0.0"


def load_sheets():
    sheets = default_sheets()
    rows = db().execute("SELECT sheet, cell, value FROM cells").fetchall()
    saved = {(row["sheet"], row["cell"]): row["value"] for row in rows}
    for sheet in sheets:
        for key, cell in sheet["cells"].items():
            if (sheet["slug"], key) in saved:
                cell["value"] = saved[(sheet["slug"], key)]
    return sheets


def cached_icon_path(icon_url):
    parsed = urlparse(icon_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        abort(400, description="Only HTTP and HTTPS icon URLs can be cached")

    extension = Path(parsed.path).suffix.lower()
    if extension not in {".avif", ".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"}:
        extension = ""

    cache_key = hashlib.sha256(icon_url.encode("utf-8")).hexdigest()
    matches = list(ICON_CACHE_DIR.glob(f"{cache_key}.*"))
    if matches:
        return matches[0]

    ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    request_headers = {"User-Agent": f"MoneyManager/{app_version()}"}
    icon_request = Request(icon_url, headers=request_headers)
    try:
        with urlopen(icon_request, timeout=ICON_FETCH_TIMEOUT) as response:
            content_type = response.headers.get_content_type()
            if not content_type.startswith("image/"):
                abort(415, description="Icon URL did not return an image")
            extension = extension or mimetypes.guess_extension(content_type) or ".img"
            cache_path = ICON_CACHE_DIR / f"{cache_key}{extension}"
            cache_path.write_bytes(response.read())
            return cache_path
    except HTTPError as error:
        abort(error.code, description="Could not fetch icon URL")
    except URLError:
        abort(502, description="Could not fetch icon URL")


@app.get("/api/icon")
def get_cached_icon():
    icon_url = request.args.get("url", "").strip()
    if not icon_url:
        abort(400, description="Missing icon URL")
    cache_path = cached_icon_path(icon_url)
    return send_file(cache_path, max_age=31536000, conditional=True)

@app.get("/")
def index():
    return render_template("index.html", sheets=load_sheets(), version=app_version())


@app.post("/api/cell")
def update_cell():
    payload = request.get_json(force=True)
    sheet = payload["sheet"]
    cell = payload["cell"]
    value = str(payload.get("value", ""))
    db().execute(
        "INSERT INTO cells (sheet, cell, value) VALUES (?, ?, ?) ON CONFLICT(sheet, cell) DO UPDATE SET value=excluded.value",
        (sheet, cell, value),
    )
    db().commit()
    return jsonify({"ok": True, "sheet": sheet, "cell": cell, "value": value})


def load_budget_data():
    row = db().execute("SELECT value FROM app_data WHERE key = ?", ("budget",)).fetchone()
    if not row:
        data = default_budget_data()
        save_budget_data(data)
        return data
    try:
        data = json.loads(row["value"])
    except json.JSONDecodeError:
        data = default_budget_data()
    settings = data.setdefault("settings", {})
    paydays = settings.setdefault("paydays", [])
    today_key = date.today().isoformat()
    if today_key <= NEXT_PAYDAY and NEXT_PAYDAY not in paydays and not any(day >= today_key for day in paydays):
        paydays.append(NEXT_PAYDAY)
        paydays.sort()

    settings.setdefault("dailyFoodAmount", 15)
    settings.setdefault("dailyPetrolAmount", 3.71)
    data.setdefault("recurringPayments", [])
    for payment in data["recurringPayments"]:
        payment.setdefault("icon", DEFAULT_PAYMENT_ICONS.get(payment.get("name", ""), ""))
    data.setdefault("months", {})
    wage_defaults = wage_forecast_defaults()
    wage_forecast = data.setdefault("wageForecast", wage_defaults)
    wage_settings = wage_forecast.setdefault("settings", {})
    for key, value in wage_defaults["settings"].items():
        wage_settings.setdefault(key, value)
    wage_forecast.setdefault("cycles", {})
    return data


def save_budget_data(data):
    db().execute(
        "INSERT INTO app_data (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        ("budget", json.dumps(data)),
    )
    db().commit()


@app.get("/api/budget")
def get_budget():
    return jsonify(load_budget_data())


@app.put("/api/budget")
def put_budget():
    data = request.get_json(force=True)
    save_budget_data(data)
    return jsonify({"ok": True, "data": data})


@app.post("/api/wages/import-rota-preview")
def import_rota_preview():
    payload = request.get_json(silent=True) or {}
    payday = payload.get("payday")
    try:
        weeks = payroll_weeks(payday)
    except (TypeError, ValueError):
        return jsonify({"error": "A valid payday in YYYY-MM-DD format is required."}), 400
    shifts = []
    attempted_urls = []
    try:
        # Query each week separately. The Rota Importer can cap a broad date
        # range to its newest results, which made the later weeks visible while
        # silently omitting weeks 40 and 41 from a four-week request.
        for week in weeks:
            upstream, _address, attempted_url = request_rota_shifts(week["start_date"], week["end_date"])
            attempted_urls.append(attempted_url)
            week_shifts = upstream.get("shifts") if isinstance(upstream, dict) else upstream
            if not isinstance(week_shifts, list):
                raise ValueError("Rota Importer response must contain a shifts list")
            shifts.extend(week_shifts)
    except RotaImporterError as error:
        labels = {"dns_failure": "DNS lookup failed", "connection_refused": "connection was refused", "timeout": "request timed out", "http_error": "returned an HTTP error", "invalid_json": "returned invalid JSON", "discovery": "could not be discovered"}
        return jsonify({"error": f"Rota Importer {labels.get(error.category, 'is unavailable')}. No wage data was changed.", "category": error.category}), 502
    except ValueError as error:
        logger.error("Rota Importer response from %s was invalid: %s", attempted_urls[-1] if attempted_urls else "unknown URL", error)
        return jsonify({"error": f"Rota Importer returned invalid data: {error}. No wage data was changed."}), 502
    try:
        preview = build_rota_preview(payday, shifts)
    except ValueError as error:
        logger.error("Rota Importer response from %s was invalid: %s: %s", ", ".join(attempted_urls), type(error).__name__, error)
        return jsonify({"error": f"Rota Importer returned invalid data: {error}. No wage data was changed."}), 502
    return jsonify(preview)


@app.get("/api/wages/rota-status")
def rota_status():
    try:
        today = date.today().isoformat()
        _payload, address, _attempted_url = request_rota_shifts(today, today)
        return jsonify({"available": True, "resolved_hostname": address["hostname"], "port": address["port"], "endpoint_reachable": True})
    except RotaImporterError as error:
        address = None
        try: address = discover_rota_importer()
        except RotaImporterError: pass
        return jsonify({"available": bool(address), "resolved_hostname": address.get("hostname") if address else None, "port": address.get("port") if address else None, "endpoint_reachable": False, "error": error.category}), 200


@app.post("/api/budget/reset")
def reset_budget():
    data = default_budget_data()
    save_budget_data(data)
    return jsonify({"ok": True, "data": data})


@app.post("/api/reset")
def reset():
    db().execute("DELETE FROM cells")
    db().execute("DELETE FROM app_data")
    db().commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099)
