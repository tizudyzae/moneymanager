# Nathan's Money Manager

A Home Assistant add-on that replaces a personal Google Sheets money tracker with a local web app.

## Features

- Track bank account balances and calculate money available for the month.
- Record monthly outgoings such as rent, council tax, internet, energy, food, subscriptions, cards, and loans.
- Show spreadsheet-style totals for monthly outgoings, total left to pay, and leftover money.
- Log daily food, petrol, fuel miles, and other spending without relying on the broken second sheet.
- Forecast wages for four-week pay cycles with basic time, Time@3rd, PAYE, NI, and fixed deduction estimates.
- Store data locally in SQLite under the add-on configuration directory.

## Add-on layout

The add-on lives in `money_manager/` and is exposed through Home Assistant Ingress on port `8099`.

## Wage Forecast

The Wage Forecast tab uses the same local SQLite-backed app data as the expense tracker. Each forecast cycle is keyed by payday and contains exactly four consecutive payroll weeks. Rota Importer hours and shifts are synchronised automatically; each expanded week shows the imported basic and Time@3rd hours, with a Details view containing shift-level calculations and daily totals. Hours can also be overridden manually. The estimate uses:

- Basic pay = total basic hours × hourly rate.
- Time@3rd pay = Time@3rd hours × hourly rate ÷ 3.
- Gross pay = basic pay + Time@3rd pay.
- Estimated net pay = gross pay - estimated PAYE - estimated NI - fixed deductions.

PAYE percentage, NI percentage, fixed deductions, hourly rate, and weekly hours are editable in the Wage Forecast tab. Values are validated to prevent negative amounts, out-of-range minutes, and percentages outside 0-100.

## Development

Run the unit tests with:

```bash
python -m pytest money_manager/tests/test_wages.py money_manager/tests/test_app_storage.py
```

Run the app locally after installing dependencies:

```bash
python -m pip install -r money_manager/requirements.txt
MONEY_MANAGER_DB=/tmp/money_manager.db python money_manager/app.py
```

## Versioning

The repository is configured with `.githooks/pre-commit` as its Git hooks path. Whenever Codex or another contributor commits staged code changes, the hook runs `scripts/bump_version.py` and automatically increments `money_manager/VERSION` in the same commit.
