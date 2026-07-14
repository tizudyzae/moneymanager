# Nathan's Money Manager

A Home Assistant add-on that replaces a personal Google Sheets money tracker with a local web app.

## Features

- Track bank account balances and calculate money available for the month.
- Record monthly outgoings such as rent, council tax, internet, energy, food, subscriptions, cards, and loans.
- Show spreadsheet-style totals for monthly outgoings, total left to pay, and leftover money.
- Log daily food, petrol, fuel miles, and other spending without relying on the broken second sheet.
- Calculate wages from weekly basic hours, minutes, and `Time @ 3rd` entries.
- Store data locally in SQLite under the add-on configuration directory.

## Add-on layout

The add-on lives in `money_manager/` and is exposed through Home Assistant Ingress on port `8099`.

## Development

Run the unit tests with:

```bash
python -m pytest money_manager/tests/test_wages.py
```

Run the app locally after installing dependencies:

```bash
python -m pip install -r money_manager/requirements.txt
MONEY_MANAGER_DB=/tmp/money_manager.db python money_manager/app.py
```

## Versioning

The repository is configured with `.githooks/pre-commit` as its Git hooks path. Whenever Codex or another contributor commits staged code changes, the hook runs `scripts/bump_version.py` and automatically increments `money_manager/VERSION` in the same commit.
