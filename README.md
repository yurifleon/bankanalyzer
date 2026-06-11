# Bank Analyzer

A simple Python script for analyzing bank and credit card CSV exports and writing monthly spending summaries to Excel.

## What it does

- Reads a CSV transaction export
- Normalizes vendor descriptions for grouping
- Generates an Excel workbook with:
  - Monthly totals
  - Monthly grouped vendor summaries
  - Top 10 vendors per month
- Optionally writes a filtered search workbook and subset CSV

## Requirements

- Python 3.7+
- `openpyxl`

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv
```

Credit-card profile example:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --profile credit-card
```

Search/filter examples:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "AMAZON"
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "NETFLIX" --month 2025-03
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --menu --profile credit-card
```

## CSV column mapping

Use explicit column overrides if your CSV layout differs:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv \
  --date-col 0 --text-col 2 --debit-col 3 --credit-col 4
```

For a single amount column profile, use `--credit-col -1`.

## Tests

Run the included unit tests after activating the virtual environment:

```bash
python -m unittest discover -s tests
```

## Notes

- The analyzer supports common encodings: `utf-8-sig`, `utf-16`, `cp1252`, `latin-1`
- The script now reports missing input files clearly instead of failing silently on encoding
