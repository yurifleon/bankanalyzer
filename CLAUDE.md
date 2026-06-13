# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Repository: https://github.com/yurifleon/bankanalyzer

## Dependencies

Runtime deps are in `requirements.txt`: `openpyxl` (Excel output), `Flask` (web UI), `gunicorn` (container WSGI server). Install with:

```bash
pip install -r requirements.txt
# CLI-only minimum:
pip install openpyxl   # or: sudo apt install python3-openpyxl
```

## Running tests

`unittest`-based, no third-party test deps:

```bash
python -m unittest discover -s tests
# single test:
python -m unittest tests.test_bank_csv_monthly_dual_profile_cardnum.TestBankCSVMonthlyDualProfile.test_parse_amount
```

## Running the CLI

The core analyzer is `bank_csv_monthly_dual_profile_cardnum.py`.

```bash
# Generate full monthly analysis workbook (bank profile, default)
python3 bank_csv_monthly_dual_profile_cardnum.py input.csv

# Credit-card profile (single Amount column, positive=charge, negative=payment)
python3 bank_csv_monthly_dual_profile_cardnum.py input.csv --profile credit-card

# Generate monthly workbook + search-filtered workbook in one run
python3 bank_csv_monthly_dual_profile_cardnum.py input.csv "AMAZON"

# Interactive vendor menu
python3 bank_csv_monthly_dual_profile_cardnum.py input.csv --menu

# Filter to a specific month
python3 bank_csv_monthly_dual_profile_cardnum.py input.csv --month 2025-03

# Override column mapping (0-based indices)
python3 bank_csv_monthly_dual_profile_cardnum.py input.csv --date-col 0 --text-col 2 --debit-col 3 --credit-col 4

# Include card/account number column in grouping
python3 bank_csv_monthly_dual_profile_cardnum.py input.csv --card-col 6
```

## Running the web UI

`web_app.py` is a Flask front end that imports `bank_csv_monthly_dual_profile_cardnum` as a library (`analyzer`) — it does **not** shell out to the CLI. Upload a CSV, pick a profile / column overrides / search / month, and it renders summaries (`templates/results.html`) plus download links for the generated workbooks.

```bash
# Dev server (debug off by default)
python web_app.py            # serves on 0.0.0.0:5000

# Production-style (matches container CMD)
gunicorn web_app:app --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120
```

Env vars: `UPLOAD_DIR` (analysis output root; default `<tmp>/bankanalyzer_web`), `MAX_CONTENT_LENGTH` (upload cap, default 50MB), `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG`. Each upload gets a `uuid4` subdirectory under `UPLOAD_DIR`; downloads are served from there via `secure_filename`-guarded paths.

## Container

`Containerfile` (Podman/Docker) builds a `python:3.11-slim` image, runs as non-root `appuser`, and starts gunicorn. `entrypoint.sh` ensures `UPLOAD_DIR` exists and is owned by `appuser` before exec'ing the CMD. A `HEALTHCHECK` polls `/`.

```bash
podman build -t bankanalyzer -f Containerfile .
podman run -p 5000:5000 -v ./uploads:/uploads bankanalyzer
```

## Architecture

`bank_csv_monthly_dual_profile_cardnum.py` is a self-contained module usable both as a CLI (`main`) and as a library. `web_app.py` reuses its public functions (`read_transactions`, `filter_transactions`, `write_workbook`, `summarize_*`, `top_10_per_month`, `get_available_months`) — keep their signatures stable, since changing them breaks the web UI silently (no shared interface enforces it).

### Data flow

1. **`read_transactions`** — opens the CSV with multi-encoding fallback (`open_csv_with_fallback`: utf-8-sig → utf-16 → cp1252 → latin-1), parses dates and amounts, calls `clean_vendor_name` on each description, returns a list of transaction dicts.
2. **`clean_vendor_name`** — normalizes raw bank descriptions into a short vendor label. All regex patterns and data sets are pre-compiled at module level (`_RE_*`, `_VENDOR_REPLACEMENTS`, `_KEEP_SHORT`, `_LOCATION_WORDS`). Pipeline: strip separators → apply string replacements → remove phone numbers / dates / alphanumeric IDs / state abbreviations → tokenize → filter noise words → keep first 1–4 meaningful tokens → strip trailing location words.
3. **Summarization** — `summarize_month_totals`, `summarize_by_month_vendor`, `top_10_per_month` aggregate the transaction list. `write_workbook` calls `summarize_by_month_vendor` once and passes the result to both the *Monthly Grouped* sheet and `top_10_per_month` to avoid double computation.
4. **`write_workbook`** — produces an `.xlsx` with three sheets: *Monthly Totals*, *Monthly Grouped*, *Top 10 Per Month*, with frozen header row and auto-filter.
5. **`main`** — parses args, resolves column indices from profile defaults or overrides, runs the full pipeline, optionally generates a second filtered workbook and/or a subset CSV.

### CSV column profiles

| Profile | date | description | debit/amount | credit |
|---------|------|-------------|--------------|--------|
| `bank` (default) | col 1 (B) | col 3 (D) | col 4 (E) | col 5 (F) |
| `credit-card` | col 0 (A) | col 1 (B) | col 4 (E) | none (sign-based) |

All column indices can be overridden individually with `--date-col`, `--text-col`, `--debit-col`, `--credit-col`.

### Amount handling

- Bank profile: separate debit and credit columns, both always positive.
- Credit-card profile: single amount column; positive = charge (debit), negative = payment (credit).
- Parenthesized amounts like `(12.34)` are parsed as negative.
- `Decimal` is used throughout; values are cast to `float` only when writing to Excel.

### Vendor normalization notes

`NOISE_WORDS` includes payment processor prefixes (`GGLPAY`, `APLPAY`, `PYPL`, `VENMO`, `ZELLE`) so that e.g. Google Pay and Apple Pay transactions group with their underlying vendor rather than the processor. `_VENDOR_REPLACEMENTS` includes `BILINTERNET → INTERNET` to merge Amex's truncated `APPLE.COM/BILINTERNET` descriptions with direct `APPLE.COM/BILL INTERNET` charges.
