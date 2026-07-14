import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("money_core", Path(__file__).parents[1] / "core.py")
money_core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(money_core)


def test_wage_calculation_matches_spreadsheet_example():
    weeks = [
        {"week_number": 36, "week_start": "2026-07-12", "basic_hours": 40, "basic_minutes": 0, "third_hours": 5, "third_minutes": 0},
        {"week_number": 37, "week_start": "2026-07-19", "basic_hours": 40, "basic_minutes": 0, "third_hours": 5, "third_minutes": 0},
        {"week_number": 38, "week_start": "2026-07-26", "basic_hours": 39, "basic_minutes": 0, "third_hours": 0, "third_minutes": 0},
        {"week_number": 39, "week_start": "2026-08-02", "basic_hours": 39, "basic_minutes": 30, "third_hours": 0, "third_minutes": 0},
    ]
    settings = {"basic_rate": 14.48, "third_rate": 4.8266666667, "paye_rate": 0.09731890562, "ni_rate": 0.06967692371, "student_loan": 10.4, "wage_stream": 5.0}

    result = money_core.calculate_wages(weeks, settings)

    assert result["total_time"] == "168 Hours and 30 Minutes"
    assert round(result["gross"], 2) == 2343.35
    assert round(result["net"], 2) == 1936.62


def test_minutes_to_label():
    assert money_core.minutes_to_label(2370) == "39 Hours and 30 Minutes"


def test_default_sheet_matches_visible_july_left_to_pay():
    sheet = money_core.build_sheet(money_core.DEFAULT_ACCOUNTS, money_core.DEFAULT_BILLS)

    assert round(sheet["totals_left"]["jul"], 2) == 1753.93
    assert round(sheet["pre_paid"]["jul"], 2) == 182.07
