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


def test_wage_forecast_uses_four_weeks_and_night_premium_formula():
    weeks = [
        {"basicHours": 40, "basicMinutes": 0, "nightHours": 6, "nightMinutes": 0},
        {"basicHours": 38, "basicMinutes": 30, "nightHours": 3, "nightMinutes": 30},
        {"basicHours": 0, "basicMinutes": 0, "nightHours": 0, "nightMinutes": 0},
        {"basicHours": 20, "basicMinutes": 15, "nightHours": 1, "nightMinutes": 45},
    ]
    settings = {"hourlyRate": 15, "payePercent": 10, "niPercent": 8, "fixedDeductions": 25}

    result = money_core.calculate_wage_forecast(weeks, settings)

    expected_basic = (40 + 38.5 + 20.25) * 15
    expected_night = (6 + 3.5 + 1.75) * 15 / 3
    expected_gross = expected_basic + expected_night
    assert len(result["weeks"]) == 4
    assert round(result["gross"], 2) == round(expected_gross, 2)
    assert round(result["paye"], 2) == round(expected_gross * 0.10, 2)
    assert round(result["ni"], 2) == round(expected_gross * 0.08, 2)
    assert round(result["net"], 2) == round(expected_gross - expected_gross * 0.18 - 25, 2)


def test_wage_forecast_clamps_invalid_values():
    result = money_core.calculate_wage_forecast(
        [{"basicHours": -10, "basicMinutes": 99, "nightHours": -1, "nightMinutes": 75}],
        {"hourlyRate": -5, "payePercent": 120, "niPercent": -3, "fixedDeductions": -20},
    )

    assert len(result["weeks"]) == 4
    assert result["weeks"][0]["basicHours"] == 0
    assert result["weeks"][0]["basicMinutes"] == 59
    assert result["weeks"][0]["nightHours"] == 0
    assert result["weeks"][0]["nightMinutes"] == 59
    assert result["hourlyRate"] == 0
    assert result["payePercent"] == 100
    assert result["niPercent"] == 0
    assert result["fixedDeductions"] == 0


def test_empty_wage_weeks_default_to_39_basic_hours():
    weeks = money_core.empty_wage_weeks()

    assert len(weeks) == 4
    assert all(week["basicHours"] == 39 for week in weeks)
    assert all(week["basicMinutes"] == 0 for week in weeks)


def test_rota_preview_groups_all_four_payroll_weeks():
    shifts = [
        {"id": f"shift-{index}", "date": day, "start": "09:00", "finish": "17:00", "break_minutes": 30}
        for index, day in enumerate(["2026-06-14", "2026-06-21", "2026-06-28", "2026-07-05"])
    ]

    preview = money_core.build_rota_preview("2026-07-23", shifts)

    assert preview["requested_range"] == {"start_date": "2026-06-14", "end_date": "2026-07-11"}
    assert [week["basic_minutes"] for week in preview["weeks"]] == [450, 450, 450, 450]
    assert [week["night_minutes"] for week in preview["weeks"]] == [0, 0, 0, 0]


def test_rota_preview_handles_overnight_shift_and_additive_night_premium():
    preview = money_core.build_rota_preview("2026-07-23", [
        {"shift_id": 42, "shift_date": "2026-06-14", "start_time": "21:30", "finish_time": "06:30", "unpaid_break_minutes": 30}
    ])

    shift = preview["shifts"][0]
    assert shift["gross_minutes"] == 540
    assert shift["paid_minutes"] == 510
    assert shift["night_minutes"] == 480
    assert preview["weeks"][0]["basic_minutes"] == 510
    assert preview["weeks"][0]["night_minutes"] == 480
    assert shift["warning"]


def test_rota_preview_applies_standard_break_to_long_shift_when_break_is_missing():
    preview = money_core.build_rota_preview("2026-07-23", [
        {"id": "long", "date": "2026-06-14", "start": "09:00", "finish": "17:00"},
        {"id": "short", "date": "2026-06-15", "start": "09:00", "finish": "16:15"},
    ])

    assert preview["shifts"][0]["unpaid_break_minutes"] == 30
    assert preview["shifts"][0]["paid_minutes"] == 450
    assert preview["shifts"][1]["unpaid_break_minutes"] == 0
    assert preview["weeks"][0]["basic_minutes"] == 885


def test_rota_preview_preserves_explicit_break_for_long_shift():
    preview = money_core.build_rota_preview("2026-07-23", [
        {"id": "long", "date": "2026-06-14", "start": "09:00", "finish": "17:00", "break_minutes": 45},
    ])

    assert preview["shifts"][0]["unpaid_break_minutes"] == 45
    assert preview["shifts"][0]["paid_minutes"] == 435
