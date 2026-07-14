def money(value):
    return f"£{value:,.2f}"


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
