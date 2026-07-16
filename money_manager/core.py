from __future__ import annotations

from copy import deepcopy
from typing import Any


COLUMNS = [chr(code) for code in range(ord("A"), ord("Z") + 1)]


def money(value: float) -> str:
    prefix = "-£" if value < 0 else "£"
    return f"{prefix}{abs(value):,.2f}"


def col_to_index(col: str) -> int:
    total = 0
    for char in col.upper():
        total = total * 26 + (ord(char) - 64)
    return total - 1


def index_to_col(index: int) -> str:
    index += 1
    out = ""
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


def cell_key(row: int, col: int) -> str:
    return f"{index_to_col(col)}{row}"


def parse_number(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace("£", "").replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return float(text)
    except ValueError:
        return 0.0


class SheetDefinition:
    def __init__(self, slug: str, title: str, rows: int, cols: int, col_widths: dict[str, int], cells: dict[str, dict[str, Any]]):
        self.slug = slug
        self.title = title
        self.rows = rows
        self.cols = cols
        self.col_widths = col_widths
        self.cells = cells


def c(value: Any = "", cls: str = "", formula: str | None = None, editable: bool = True) -> dict[str, Any]:
    data = {"value": value, "class": cls, "editable": editable}
    if formula:
        data["formula"] = formula
    return data


def make_budget_sheet() -> SheetDefinition:
    cells: dict[str, dict[str, Any]] = {}
    for key, value in {
        "M1": "5>Feb", "N1": "5>Mar", "O1": "2>Apr", "P1": "28>May", "Q1": "25>Jun", "R1": "23>Jul",
        "M2": "First Direct", "N2": "732.00", "O2": "283.53", "P2": "163.43", "Q2": "2,017.00", "R2": "1,936.00",
        "Q3": "71.68", "M3": "Lloyds", "M4": "78.73",
    }.items():
        cells[key] = c(value, "header-dark" if key[1:] in {"2", "3"} else "date-head", editable=not key.endswith("2"))
    bills = [
        ("Rent (31)", "466.67"), ("Council Tax", "94.91"), ("Internet", "10.00"), ("Energy", "139.97"), ("Water", "42.67"),
        ("Energy credit", "-93.91"), ("Car Tax (2)", "17.50"), ("AA", "13.01"), ("Admiral (12)", "49.55"),
        ("Petrol", "105.00"), ("Barclayloan (31)", "92.83"), ("icloud drive (2)", "8.99"), ("Vodafone (5)", "12.00"),
        ("Food", "420.00"), ("Youtube Premium (25)", "12.99"), ("lloyds direct", "183.94"), ("Google Drive", "1.59"),
        ("First Direct (02)", "7.29"), ("Apple Care (2)", "11.99"), ("Barclaycard (18)", "92.07"), ("Puregym", "21.99"),
        ("Chatgpt", "17.97"), ("Paypal", "24.91"),
    ]
    for i, (name, amount) in enumerate(bills, start=5):
        cells[f"L{i}"] = c(name, "bill-name")
        cells[f"Q{i}"] = c(amount, "expense")
        cells[f"R{i}"] = c(amount, "expense")
    cells["N15"] = c("33.39", "expense")
    cells["N20"] = c("135.00", "expense")
    cells["L30"] = c("Total Left To Pay", "total-label", editable=False)
    cells["Q30"] = c("246.85", "total-purple", formula="=SUM(Q5:Q29)-Q2")
    cells["R30"] = c("1,753.93", "total-purple", formula="=SUM(R5:R29)-R2")
    cells["L31"] = c("Total Leftover (Pre Paid)", "total-label", editable=False)
    cells["N31"] = c("0.00", "total-green")
    cells["O31"] = c("732.00", "total-green")
    cells["P31"] = c("283.53", "total-green")
    cells["Q31"] = c("66.99", "total-green", formula="=Q2-Q30")
    cells["R31"] = c("182.07", "total-green", formula="=R2-R30")
    return SheetDefinition("budget", "Copy of 2023", 31, 19, {"A": 38, "L": 220, "M": 78, "N": 78, "O": 78, "P": 78, "Q": 78, "R": 78}, cells)


def make_food_sheet() -> SheetDefinition:
    cells: dict[str, dict[str, Any]] = {}
    days = ["Thu", "Fri", "Sat", "sun", "Mon", "Tue", "Wed"]
    dates = ["25/06/2025", "26/6", "27/6", "28/6", "29/6", "30/6", "1/7"]
    for idx, (day, dt) in enumerate(zip(days, dates), start=2):
        cells[f"{index_to_col(idx-1)}1"] = c(day, "day-head", editable=False)
        cells[f"{index_to_col(idx-1)}2"] = c(dt, "date-head")
    for row in [4, 8, 12]:
        cells[f"A{row}"] = c("Fuel Miles", "fuel-label", editable=False)
    for row in [3,4,7,8,11,12,15,16]:
        for col in range(1, 8):
            cells[cell_key(row, col)] = c(cells.get(cell_key(row, col), {}).get("value", ""), "fuel-input")
    for col, val in zip(range(1, 8), ["2/7", "3/7", "4/7", "5/7", "6/7", "7/7", "8/7"]): cells[cell_key(6, col)] = c(val, "date-head")
    for col, val in zip(range(1, 8), ["9/7", "10/7", "11/7", "12/7", "13/7", "14/7", "15/7"]): cells[cell_key(10, col)] = c(val, "date-head")
    for col, val in zip(range(1, 8), ["16/7", "17/7", "18/7", "19/7", "20/7", "21/7", "22/7"]): cells[cell_key(14, col)] = c(val, "date-head")
    for key in ["I4", "I8", "I12"]: cells[key] = c("0.00", "blue-block", formula="=SUM(B3:H3)")
    cells["I16"] = c("3.00", "blue-block", formula="=SUM(F16:H16)")
    cells["J16"] = c("1", "blue-block")
    cells["D23"] = c("0.25", "plain")
    cells["E23"] = c("per mile", "plain")
    for key, val in {"C25":"Daily Miles", "D25":"Dail Cost", "E25":"Weekly Cost", "F25":"Monthly Cost", "C26":"20.00", "D26":"5.00", "E26":"£35.00", "F26":"£140.00"}.items(): cells[key] = c(val, "plain")
    return SheetDefinition("food", "Copy of Food/Fuel Calc", 83, 11, {"A": 115, "B": 86, "C": 86, "D": 86, "E": 86, "F": 86, "G": 86, "H": 86, "I": 96, "J": 96}, cells)


def make_wage_sheet() -> SheetDefinition:
    cells: dict[str, dict[str, Any]] = {}
    headers = {"A1":"Wk", "B1":"07/12/2026", "C1":"Hours", "D1":"Minutes", "F1":"Total", "G1":"Pay", "I1":"Rate"}
    for k,v in headers.items(): cells[k] = c(v, "wage-head")
    weeks = [(36,"Basic Time",40,0,2400,"40 Hours and 0 Minutes","£579.20"),(36,"Time @ 3rd",5,0,300,"5 Hours and 0 Minutes","£24.13"),(37,"Basic Time",40,0,2400,"40 Hours and 0 Minutes","£579.20"),(37,"Time @ 3rd",5,0,300,"5 Hours and 0 Minutes","£24.13"),(38,"Basic Time",39,0,2340,"39 Hours and 0 Minutes","£564.72"),(38,"Time @ 3rd",0,0,0,"0 Hours and 0 Minutes","£0.00"),(39,"Basic Time",39,30,2370,"39 Hours and 30 Minutes","£571.96"),(39,"Time @ 3rd",0,0,0,"0 Hours and 0 Minutes","£0.00")]
    colors = ["wk-blue","wk-blue","wk-green","wk-green","wk-yellow","wk-yellow","wk-red","wk-red"]
    for r, row in enumerate(weeks, start=2):
        for col, val in zip(["A","B","C","D","E","F","G"], row): cells[f"{col}{r}"] = c(val, colors[r-2])
    for k,v in {"F13":"158 Hours and 30 Minute", "F14":"GROSS PAY", "G14":"£2,343.35", "F15":"paye", "G15":"£228.05", "F16":"ni", "G16":"£163.28", "F17":"usdaw", "G17":"10.4", "F18":"wage stream", "G18":"5", "F21":"th", "G21":"£1,936.62", "I2":"14.48", "I3":"13.99"}.items(): cells[k] = c(v, "plain")
    return SheetDefinition("wages", "30>Apr", 21, 12, {"A": 34, "B": 125, "C": 86, "D": 86, "E": 95, "F": 170, "G": 95}, cells)


DEFAULT_SHEETS = [make_budget_sheet(), make_food_sheet(), make_wage_sheet()]


def serialise_sheet(sheet: SheetDefinition) -> dict[str, Any]:
    return {"slug": sheet.slug, "title": sheet.title, "rows": sheet.rows, "cols": sheet.cols, "col_widths": sheet.col_widths, "cells": deepcopy(sheet.cells)}


def default_sheets() -> list[dict[str, Any]]:
    return [serialise_sheet(sheet) for sheet in DEFAULT_SHEETS]

# Compatibility helpers kept for the existing unit tests and for anyone importing the
# earlier calculation API. The web UI now renders spreadsheet-like editable cells, but
# these pure functions remain useful for validating the numbers shown in the template.
MONTH_COLUMNS = [
    {"key": "feb", "label": "5>Feb", "income": 0.0},
    {"key": "mar", "label": "5>Mar", "income": 732.00},
    {"key": "apr", "label": "2>Apr", "income": 283.53},
    {"key": "may", "label": "28>May", "income": 163.43},
    {"key": "jun", "label": "25>Jun", "income": 2017.00},
    {"key": "jul", "label": "23>Jul", "income": 1936.00},
]
DEFAULT_ACCOUNTS = [{"name": "First Direct", "balance": 732.00, "months": {"apr": 283.53, "may": 163.43, "jun": 2017.00, "jul": 1936.00}}, {"name": "Lloyds", "balance": 71.68, "months": {}}, {"name": "", "balance": 78.73, "months": {}}]
DEFAULT_BILLS = [{"name": name, "amount": parse_number(amount), "paid_months": ["jun"]} for name, amount in [("Rent (31)", "466.67"), ("Council Tax", "94.91"), ("Internet", "10.00"), ("Energy", "139.97"), ("Water", "42.67"), ("Energy credit", "-93.91"), ("Car Tax (2)", "17.50"), ("AA", "13.01"), ("Admiral (12)", "49.55"), ("Petrol", "105.00"), ("Barclayloan (31)", "92.83"), ("icloud drive (2)", "8.99"), ("Vodafone (5)", "12.00"), ("Food", "420.00"), ("Youtube Premium (25)", "12.99"), ("lloyds direct", "183.94"), ("Google Drive", "1.59"), ("First Direct (02)", "7.29"), ("Apple Care (2)", "11.99"), ("Barclaycard (18)", "92.07"), ("Puregym", "21.99"), ("Chatgpt", "17.97"), ("Paypal", "24.91")]]
for bill in DEFAULT_BILLS:
    if bill["name"] in {"Vodafone (5)", "Google Drive", "Puregym", "Chatgpt", "Paypal"}:
        bill["paid_months"].append("feb")


def build_sheet(accounts, bills, months=MONTH_COLUMNS):
    bill_rows = []
    for bill in bills:
        values = {month["key"]: bill["amount"] if month["key"] in bill.get("paid_months", []) else 0.0 for month in months}
        bill_rows.append({**bill, "values": values})
    totals_left = {month["key"]: sum(row["amount"] - row["values"][month["key"]] for row in bill_rows) for month in months}
    pre_paid = {month["key"]: month["income"] - totals_left[month["key"]] for month in months}
    return {"months": months, "account_rows": accounts, "bill_rows": bill_rows, "totals_left": totals_left, "pre_paid": pre_paid}



def clamp_number(value: Any, minimum: float = 0.0, maximum: float | None = None) -> float:
    number = parse_number(value)
    if number < minimum:
        return minimum
    if maximum is not None and number > maximum:
        return maximum
    return number


def clamp_minutes(value: Any) -> int:
    return int(clamp_number(value, 0, 59))


def wage_forecast_defaults() -> dict[str, Any]:
    return {
        "settings": {
            "hourlyRate": 14.48,
            "payePercent": 10,
            "niPercent": 8,
            "fixedDeductions": 15.4,
        },
        "cycles": {},
    }


def normalise_wage_week(week: dict[str, Any] | None, index: int = 0) -> dict[str, Any]:
    week = week or {}
    return {
        "label": week.get("label") or f"Week {index + 1}",
        "basicHours": clamp_number(week.get("basicHours", week.get("basic_hours", 0))),
        "basicMinutes": clamp_minutes(week.get("basicMinutes", week.get("basic_minutes", 0))),
        "nightHours": clamp_number(week.get("nightHours", week.get("third_hours", 0))),
        "nightMinutes": clamp_minutes(week.get("nightMinutes", week.get("third_minutes", 0))),
    }


def empty_wage_weeks() -> list[dict[str, Any]]:
    return [normalise_wage_week(None, index) for index in range(4)]


def calculate_wage_forecast(weeks: list[dict[str, Any]], settings: dict[str, Any]) -> dict[str, Any]:
    normalised_weeks = [normalise_wage_week(weeks[index] if index < len(weeks) else None, index) for index in range(4)]
    hourly_rate = clamp_number(settings.get("hourlyRate", settings.get("hourly_rate", 0)))
    paye_percent = clamp_number(settings.get("payePercent", settings.get("paye_percent", 0)), 0, 100)
    ni_percent = clamp_number(settings.get("niPercent", settings.get("ni_percent", 0)), 0, 100)
    fixed_deductions = clamp_number(settings.get("fixedDeductions", settings.get("fixed_deductions", 0)))

    rows = []
    gross = 0.0
    total_basic_minutes = 0
    total_night_minutes = 0
    for week in normalised_weeks:
        basic_minutes = int(week["basicHours"] * 60 + week["basicMinutes"])
        night_minutes = int(week["nightHours"] * 60 + week["nightMinutes"])
        basic_hours = basic_minutes / 60
        premium_hours = night_minutes / 60
        basic_pay = basic_hours * hourly_rate
        night_premium = premium_hours * hourly_rate / 3
        week_gross = basic_pay + night_premium
        gross += week_gross
        total_basic_minutes += basic_minutes
        total_night_minutes += night_minutes
        rows.append({
            **week,
            "basicPay": basic_pay,
            "nightPremium": night_premium,
            "gross": week_gross,
        })

    paye = gross * (paye_percent / 100)
    ni = gross * (ni_percent / 100)
    deductions = paye + ni + fixed_deductions
    return {
        "weeks": rows,
        "hourlyRate": hourly_rate,
        "payePercent": paye_percent,
        "niPercent": ni_percent,
        "fixedDeductions": fixed_deductions,
        "gross": gross,
        "paye": paye,
        "ni": ni,
        "deductions": deductions,
        "net": gross - deductions,
        "totalBasicTime": minutes_to_label(total_basic_minutes),
        "totalNightPremiumTime": minutes_to_label(total_night_minutes),
    }

def minutes_to_label(total_minutes):
    hours, minutes = divmod(int(total_minutes), 60)
    return f"{hours} Hours and {minutes} Minutes"


def wage_row_pay(hours, minutes, rate):
    return ((hours * 60) + minutes) / 60 * rate


def calculate_wages(weeks, settings):
    rows = []
    gross = 0.0
    total_minutes = 0
    for week in weeks:
        basic_minutes = week["basic_hours"] * 60 + week["basic_minutes"]
        third_minutes = week["third_hours"] * 60 + week["third_minutes"]
        basic_pay = wage_row_pay(week["basic_hours"], week["basic_minutes"], settings["basic_rate"])
        third_pay = wage_row_pay(week["third_hours"], week["third_minutes"], settings["third_rate"])
        gross += basic_pay + third_pay
        total_minutes += basic_minutes + third_minutes
        rows.append({"week": week, "basic_total": minutes_to_label(basic_minutes), "third_total": minutes_to_label(third_minutes), "basic_pay": basic_pay, "third_pay": third_pay})
    paye = gross * settings["paye_rate"]
    ni = gross * settings["ni_rate"]
    deductions = paye + ni + settings["student_loan"] + settings["wage_stream"]
    return {"rows": rows, "gross": gross, "paye": paye, "ni": ni, "deductions": deductions, "net": gross - deductions, "total_time": minutes_to_label(total_minutes)}
