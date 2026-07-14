import os
import sqlite3
from pathlib import Path

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
"""


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


@app.post("/api/reset")
def reset():
    db().execute("DELETE FROM cells")
    db().commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099)
