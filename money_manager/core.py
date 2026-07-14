def money(value):
    return f"£{value:,.2f}"


MONTH_COLUMNS = [
    {"key": "feb", "label": "5>Feb", "income": 0.0},
    {"key": "mar", "label": "5>Mar", "income": 732.00},
    {"key": "apr", "label": "2>Apr", "income": 283.53},
    {"key": "may", "label": "28>May", "income": 163.43},
    {"key": "jun", "label": "25>Jun", "income": 2017.00},
    {"key": "jul", "label": "23>Jul", "income": 1936.00},
]


DEFAULT_ACCOUNTS = [
    {"name": "First Direct", "balance": 732.00, "months": {"apr": 283.53, "may": 163.43, "jun": 2017.00, "jul": 1936.00}},
    {"name": "Lloyds", "balance": 71.68, "months": {}},
    {"name": "", "balance": 78.73, "months": {}},
]


DEFAULT_BILLS = [
    {"name": "Rent (31)", "amount": 466.67, "day_due": 31, "category": "Home", "paid_months": ["jun"]},
    {"name": "Council Tax", "amount": 94.91, "day_due": None, "category": "Home", "paid_months": ["jun"]},
    {"name": "Internet", "amount": 10.00, "day_due": None, "category": "Home", "paid_months": ["jun"]},
    {"name": "Energy", "amount": 139.97, "day_due": None, "category": "Home", "paid_months": ["jun"]},
    {"name": "Water", "amount": 42.67, "day_due": None, "category": "Home", "paid_months": ["jun"]},
    {"name": "Energy credit", "amount": -93.91, "day_due": None, "category": "Credit", "paid_months": ["jun"]},
    {"name": "Car Tax (2)", "amount": 17.50, "day_due": 2, "category": "Car", "paid_months": ["jun"]},
    {"name": "AA", "amount": 13.01, "day_due": None, "category": "Car", "paid_months": ["jun"]},
    {"name": "Admiral (12)", "amount": 49.55, "day_due": 12, "category": "Car", "paid_months": ["jun"]},
    {"name": "Petrol", "amount": 105.00, "day_due": None, "category": "Car", "paid_months": ["jun"], "actual": 33.39},
    {"name": "Barclayloan (31)", "amount": 92.83, "day_due": 31, "category": "Debt", "paid_months": ["jun"]},
    {"name": "icloud drive (2)", "amount": 8.99, "day_due": 2, "category": "Subscriptions", "paid_months": ["jun"]},
    {"name": "Vodafone (5)", "amount": 12.00, "day_due": 5, "category": "Phone", "paid_months": ["feb", "jun"]},
    {"name": "Food", "amount": 420.00, "day_due": None, "category": "Food", "paid_months": ["jun"], "actual": 135.00},
    {"name": "Youtube Premium (25)", "amount": 12.99, "day_due": 25, "category": "Subscriptions", "paid_months": ["jun"]},
    {"name": "lloyds direct", "amount": 183.94, "day_due": None, "category": "Debt", "paid_months": ["jun"]},
    {"name": "Google Drive", "amount": 1.59, "day_due": None, "category": "Subscriptions", "paid_months": ["feb", "jun"]},
    {"name": "First Direct (02)", "amount": 7.29, "day_due": 2, "category": "Banking", "paid_months": ["jun"]},
    {"name": "Apple Care (2)", "amount": 11.99, "day_due": 2, "category": "Subscriptions", "paid_months": ["jun"]},
    {"name": "Barclaycard (18)", "amount": 92.07, "day_due": 18, "category": "Debt", "paid_months": ["jun"]},
    {"name": "Puregym", "amount": 21.99, "day_due": None, "category": "Health", "paid_months": ["feb", "jun"]},
    {"name": "Chatgpt", "amount": 17.97, "day_due": None, "category": "Subscriptions", "paid_months": ["feb", "jun"]},
    {"name": "Paypal", "amount": 24.91, "day_due": None, "category": "Debt", "paid_months": ["feb", "jun"]},
]


def bill_cell_amount(bill, month_key):
    return bill["amount"] if month_key in bill.get("paid_months", []) else 0.0


def build_sheet(accounts, bills, months=MONTH_COLUMNS):
    account_rows = []
    for account in accounts:
        account_rows.append({"name": account["name"], "balance": account["balance"], "months": account.get("months", {})})
    bill_rows = []
    for bill in bills:
        values = {month["key"]: bill_cell_amount(bill, month["key"]) for month in months}
        bill_rows.append({**bill, "values": values})
    totals_left = {month["key"]: sum(row["amount"] - row["values"][month["key"]] for row in bill_rows) for month in months}
    pre_paid = {month["key"]: month["income"] - totals_left[month["key"]] for month in months}
    return {"months": months, "account_rows": account_rows, "bill_rows": bill_rows, "totals_left": totals_left, "pre_paid": pre_paid}


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
