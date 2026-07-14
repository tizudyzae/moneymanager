import os
import sqlite3
from datetime import date
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for
from core import calculate_wages, money

DB_PATH = Path(os.environ.get("MONEY_MANAGER_DB", "/config/money_manager.db"))

app = Flask(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    balance REAL NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    day_due INTEGER,
    category TEXT NOT NULL DEFAULT 'Outgoing',
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spent_on TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS wage_weeks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number INTEGER NOT NULL,
    week_start TEXT NOT NULL,
    basic_hours INTEGER NOT NULL DEFAULT 0,
    basic_minutes INTEGER NOT NULL DEFAULT 0,
    third_hours INTEGER NOT NULL DEFAULT 0,
    third_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS wage_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    basic_rate REAL NOT NULL DEFAULT 14.48,
    third_rate REAL NOT NULL DEFAULT 4.8266666667,
    paye_rate REAL NOT NULL DEFAULT 0.09731890562,
    ni_rate REAL NOT NULL DEFAULT 0.06967692371,
    student_loan REAL NOT NULL DEFAULT 10.40,
    wage_stream REAL NOT NULL DEFAULT 5.00
);
INSERT OR IGNORE INTO wage_settings (id) VALUES (1);
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



@app.template_filter("money")
def money_filter(value):
    return money(float(value or 0))


@app.route("/")
def index():
    conn = db()
    accounts = conn.execute("SELECT * FROM accounts ORDER BY sort_order, id").fetchall()
    bills = conn.execute("SELECT * FROM bills ORDER BY sort_order, id").fetchall()
    monthly_income = sum(account["balance"] for account in accounts)
    outgoing = sum(bill["amount"] for bill in bills)
    expenses = conn.execute("SELECT * FROM expenses ORDER BY spent_on DESC, id DESC LIMIT 20").fetchall()
    expense_total = conn.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expenses").fetchone()["total"]
    weeks = conn.execute("SELECT * FROM wage_weeks ORDER BY week_start, id").fetchall()
    settings = conn.execute("SELECT * FROM wage_settings WHERE id = 1").fetchone()
    wages = calculate_wages(weeks, settings)
    return render_template("index.html", accounts=accounts, bills=bills, monthly_income=monthly_income, outgoing=outgoing, left_to_pay=outgoing, leftover=monthly_income - outgoing, expenses=expenses, expense_total=expense_total, settings=settings, wages=wages, today=date.today().isoformat())


@app.post("/accounts")
def add_account():
    db().execute("INSERT INTO accounts (name, balance) VALUES (?, ?)", (request.form["name"], float(request.form["balance"] or 0)))
    db().commit()
    return redirect(url_for("index"))


@app.post("/bills")
def add_bill():
    day_due = request.form.get("day_due") or None
    db().execute("INSERT INTO bills (name, amount, day_due, category) VALUES (?, ?, ?, ?)", (request.form["name"], float(request.form["amount"] or 0), day_due, request.form.get("category") or "Outgoing"))
    db().commit()
    return redirect(url_for("index"))


@app.post("/expenses")
def add_expense():
    db().execute("INSERT INTO expenses (spent_on, category, amount, notes) VALUES (?, ?, ?, ?)", (request.form.get("spent_on") or date.today().isoformat(), request.form["category"], float(request.form["amount"] or 0), request.form.get("notes", "")))
    db().commit()
    return redirect(url_for("index"))


@app.post("/wages/settings")
def update_wage_settings():
    fields = ["basic_rate", "third_rate", "paye_rate", "ni_rate", "student_loan", "wage_stream"]
    values = [float(request.form[field] or 0) for field in fields]
    db().execute("UPDATE wage_settings SET basic_rate=?, third_rate=?, paye_rate=?, ni_rate=?, student_loan=?, wage_stream=? WHERE id=1", values)
    db().commit()
    return redirect(url_for("index"))


@app.post("/wages/weeks")
def add_wage_week():
    db().execute(
        "INSERT INTO wage_weeks (week_number, week_start, basic_hours, basic_minutes, third_hours, third_minutes) VALUES (?, ?, ?, ?, ?, ?)",
        (int(request.form["week_number"]), request.form["week_start"], int(request.form.get("basic_hours") or 0), int(request.form.get("basic_minutes") or 0), int(request.form.get("third_hours") or 0), int(request.form.get("third_minutes") or 0)),
    )
    db().commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099)
