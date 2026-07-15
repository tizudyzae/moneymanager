import os
import sqlite3
from pathlib import Path

import json
import uuid
from datetime import date

from flask import Flask, g, jsonify, render_template, request
from core import default_sheets

DB_PATH = Path(os.environ.get("MONEY_MANAGER_DB", "/config/money_manager.db"))
VERSION_PATH = Path(__file__).resolve().parent / "VERSION"

app = Flask(__name__)

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

DEFAULT_PAYMENTS = [
    ["Rent",466.67,31],["Council Tax",94.91,1],["Internet",10,5],["Energy",139.97,6],
    ["Water",42.67,6],["Energy Credit",-93.91,6],["Car Tax",17.50,2],["AA",13.01,1],
    ["Admiral",49.55,12],["Petrol",105,1],["Barclayloan",92.83,31],["iCloud Drive",8.99,2],
    ["Vodafone",12,5],["Food",420,1],["YouTube Premium",12.99,25],["Google Drive",1.59,1],
    ["First Direct",7.29,2],["Apple Care",11.99,2],["Barclaycard",92.07,18],
    ["PureGym",21.99,1],["ChatGPT",17.97,1],["PayPal",24.91,1],
]


def default_budget_data():
    today = date.today()
    first = today.replace(day=1)
    return {
        "settings": {"paydays": [first.isoformat()]},
        "recurringPayments": [
            {"id": str(uuid.uuid4()), "name": name, "amount": amount, "day": day, "active": True}
            for name, amount, day in DEFAULT_PAYMENTS
        ],
        "months": {},
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
    data.setdefault("settings", {}).setdefault("paydays", [])
    data.setdefault("recurringPayments", [])
    data.setdefault("months", {})
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
