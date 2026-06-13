# Bank CSV Analyzer — User Manual

This repository provides two user-facing interfaces:

- `bank_csv_monthly_dual_profile_cardnum.py` — the command-line analyzer.
- `web_app.py` — a Flask-based browser interface for uploading CSVs and downloading generated workbooks.

The app can also run in a container, with a default upload directory of `/uploads` and configurable runtime settings.

---

## Architecture

The project is built from three layers:

### Core analyzer

The script `bank_csv_monthly_dual_profile_cardnum.py` contains the core processing pipeline.

- `open_csv_with_fallback()` opens the CSV file and tries several encodings until one succeeds.
- `parse_date()` supports common date formats such as `MM/DD/YYYY`, `YYYY-MM-DD`, and `MM-DD-YY`.
- `parse_amount()` cleans currency formatting, strips `$` and commas, and converts parenthesized values into negatives.
- `clean_vendor_name()` normalizes raw descriptions using regex to remove separators, dates, phone numbers, alphanumeric IDs, and state abbreviations, then filters noise words.
- `read_transactions()` loads rows into structured transaction dictionaries with date, vendor, debit, credit, net, and optional card number.
- `summarize_by_month_vendor()`, `summarize_month_totals()`, and `top_10_per_month()` aggregate data for sheet generation.
- `write_workbook()` produces an Excel workbook with three formatted sheets.

### Web interface

`web_app.py` exposes the analyzer as a browser app.

- Receives uploaded CSV files and optional search/month filters.
- Uses the same core analyzer functions as the CLI.
- Saves all files under `UPLOAD_DIR`, which can be configured via environment variables.
- Renders summary metrics, top vendor patterns, and workbook download links on the results page.
- Supports profile selection and column overrides from the upload form.

### Container support

Container packaging provides a production-ready deployment path.

- `Containerfile` builds the image from Python 3.11 slim.
- `entrypoint.sh` creates the upload directory before starting the app.
- The container runs `gunicorn` binding `0.0.0.0:5000`.
- A healthcheck verifies the app responds on `http://127.0.0.1:5000/`.

## Request flow

When a browser request is processed:

1. The user uploads a CSV and submits the form.
2. Flask saves the file to `UPLOAD_DIR`.
3. The app parses query parameters and resolves column mapping.
4. `read_transactions()` loads the CSV and normalizes vendors.
5. `write_workbook()` writes the Excel output file in the same upload directory.
6. The results page shows summary data and download links.

## Requirements

Python 3.7+ and the `openpyxl`, `Flask`, and `gunicorn` libraries.

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you prefer a system-installed library on Debian/Ubuntu:

```bash
sudo apt install python3-openpyxl
```

---

## Container usage

Build the container image from the repository root:

```bash
podman build --format docker -t bankanalyzer:web -f Containerfile .
```

Run the container and expose port 5000:

```bash
podman run --rm -p 5000:5000 --name bankanalyzer bankanalyzer:web
```

To persist uploads and generated workbooks on the host, mount a host directory:

```bash
mkdir -p /srv/bankanalyzer/uploads
podman run --rm -p 5000:5000 \
  -e UPLOAD_DIR=/uploads \
  -v /srv/bankanalyzer/uploads:/uploads:Z \
  --name bankanalyzer bankanalyzer:web
```

---

## Testing

Run the included unit tests:

```bash
source .venv/bin/activate
python -m unittest discover -s tests
```

If the virtual environment is not yet created:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Preparing your CSV

Export your transaction history as a CSV file. The analyzer supports headers, blank rows, and common encodings automatically (it tries `utf-8-sig`, `utf-16`, `cp1252`, and `latin-1`).

Each transaction row must include a parseable date and a numeric amount.

---

## CSV profiles

The analyzer supports two built-in layouts.

### Bank profile (default)

| Column | Index | Content |
|--------|-------|---------|
| B | 1 | Transaction date |
| D | 3 | Description |
| E | 4 | Debit / charge amount |
| F | 5 | Credit / payment amount |

### Credit-card profile (`--profile credit-card`)

| Column | Index | Content |
|--------|-------|---------|
| A | 0 | Transaction date |
| B | 1 | Description |
| E | 4 | Amount (positive = charge, negative = payment) |

Use `--profile credit-card` for card exports with sign-based amounts.

---

## Basic usage

### Generate a full-year workbook

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --profile credit-card
```

This generates a full-monthly workbook named `transactions_monthly_totals.xlsx` by default. Override the output filename with `--monthly-output`.

### Generate a vendor-filtered workbook

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "AMAZON" --profile credit-card
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "PANERA"
```

The search term matches both raw descriptions and normalized vendor names.

### Filter by month

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --month 2025-03
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "AMAZON" --month 2025-03
```

`--month` accepts `YYYY-MM`.

---

## Interactive modes

### Vendor menu (`--menu`)

Displays the top vendor patterns and prompts you to select one.

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --profile credit-card --menu
```

Use `--top N` to change how many patterns are shown.

### Month selection menu (`--month-menu`)

Choose a specific month or whole-year before filtering:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --month-menu
```

`--menu` and `--month-menu` can be combined.

---

## Output sheets

Every workbook includes the same three sheets.

### Monthly Totals

Reports each month with transaction count, total charges, payments, net value, and date range.

### Monthly Grouped

Groups by `vendor` (and `card_number` if provided) with counts, totals, net, and example descriptions.

### Top 10 Per Month

Lists the top vendors per month by total charges with a rank column.

All sheets include a frozen header row and auto-filters.

---

## Output file naming

Default full-year workbook:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv
```

Override with `--monthly-output`.

Filtered workbooks are generated automatically from the input name, filter terms, and month. Override with `--search-output`.

Use `--subset-csv` to export matching rows back to CSV.

---

## Column mapping

Override column indices using 0-based numbering:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv \
    --date-col 0 --text-col 2 --debit-col 3 --credit-col 4
```

Use `--credit-col -1` for layouts without a separate credit column.

---

## Web UI usage

Start the browser interface:

```bash
python3 web_app.py
```

Open `http://127.0.0.1:5000` and upload your CSV. Use profile selection, search filters, and month filters from the browser.

---

## Container usage

Build the container image:

```bash
podman build --format docker -t bankanalyzer:web -f Containerfile .
```

Run the container:

```bash
podman run --rm -p 5000:5000 --name bankanalyzer bankanalyzer:web
```

### Persistent upload directory

To store uploads and outputs on the host:

```bash
mkdir -p /srv/bankanalyzer/uploads
podman run --rm -p 5000:5000 \
  -e UPLOAD_DIR=/uploads \
  -v /srv/bankanalyzer/uploads:/uploads:Z \
  --name bankanalyzer bankanalyzer:web
```

### Environment variables

- `UPLOAD_DIR`: path inside the container for uploads and outputs.
- `MAX_CONTENT_LENGTH`: upload size limit in bytes.
- `FLASK_HOST`, `FLASK_PORT`: listening address and port.
- `FLASK_DEBUG`: enable debug mode when set to `1` or `true`.

---

## Notes

The system is designed for both CLI and browser usage, with container support for easier deployment.

---

## Multi-card accounts

If your CSV includes a card or account number column (common in business or household accounts with multiple cardholders), pass its 0-based column index with `--card-col`. The card number will appear in the Monthly Grouped and Top 10 sheets, and grouping will be by month + vendor + card number rather than just month + vendor:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --profile credit-card --card-col 6
```

---

## Console output

The script always prints a summary to the terminal:

```
Using profile: credit-card
Columns: date=0, description=1, debit/amount=4, credit=-1
Using file encoding: cp1252

Full Monthly Analysis
---------------------
Period: whole year / all months
Rows: 799
Total debit/charges/amount: 44369.70
Total credit/payments: 48013.19
Net credit minus debit: 3643.49
Transaction timeframe: 2025-01-01 to 2025-12-31
Full monthly workbook written to: transactions_monthly_totals.xlsx
```

If a search or month filter is applied, a second summary block follows for the filtered results.

To also print the top 10 vendors per month to the terminal (in addition to writing the sheet):

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --show-monthly-top10
```

---

## Vendor normalization

Raw bank descriptions like `GglPay PANERA BREAD PENSACOLA FL` are normalized to a short vendor label (`PANERA BREAD`) for grouping purposes. The normalization:

- Strips payment processor prefixes: Google Pay (`GGLPAY`), Apple Pay (`APLPAY`), PayPal (`PYPL`), Venmo, Zelle
- Removes phone numbers, transaction dates, alphanumeric reference codes, and US state abbreviations
- Removes common banking noise words (POS, PURCHASE, DEBIT, ACH, AUTOPAY, etc.)
- Strips trailing city/location names
- Keeps the first 1–4 meaningful words
- Applies known normalizations: `AMAZON.COM` → `AMAZON`, `WM SUPERCENTER` → `WAL MART`, etc.

The raw description is always preserved in the **Examples** column and in any subset CSV output.

---

## Troubleshooting

**"No valid transactions found"**
The script couldn't parse any dates in the date column. Check that `--profile` matches your file, or use `--date-col` to point to the correct column. The script accepts dates in `MM/DD/YYYY`, `MM/DD/YY`, `YYYY-MM-DD`, `MM-DD-YYYY`, and `MM-DD-YY` formats.

**Totals look wrong / charges and payments are swapped**
You may be using the wrong profile. Try adding or removing `--profile credit-card`. For the bank profile, charges go in the debit column and payments in the credit column (both positive). For the credit-card profile, charges are positive and payments are negative in a single amount column.

**Vendor grouping is too coarse / vendors are being merged incorrectly**
The normalization is heuristic. Use the search feature with the raw description text to locate specific transactions:
```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "APPLE.COM/BIL"
```

**Encoding error on open**
The script tries four encodings automatically. If all fail with a `RuntimeError`, the file may use an unusual encoding. Open it in a text editor, re-save as UTF-8, and try again.

**openpyxl not found**
```bash
pip install -r requirements.txt
```

If your Python environment is system-managed, use a virtual environment instead:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## All options reference

| Option | Default | Description |
|--------|---------|-------------|
| `input_csv` | *(required)* | Path to the input CSV file |
| `search_text` | *(optional)* | Vendor or text to filter on |
| `--profile` | `bank` | CSV layout: `bank` or `credit-card` |
| `--menu` | off | Show interactive vendor menu |
| `--month-menu` | off | Show interactive month selection |
| `--month YYYY-MM` | *(none)* | Filter to a specific month |
| `--top N` | 30 | Number of vendors shown in `--menu` |
| `--show-monthly-top10` | off | Print top 10 vendors per month to console |
| `--monthly-output FILE` | `INPUT_monthly_totals.xlsx` | Full-year workbook path |
| `--search-output FILE` | *(auto-generated)* | Filtered workbook path |
| `--subset-csv FILE` | *(none)* | Write matching raw rows to a CSV |
| `--date-col N` | profile default | 0-based date column index |
| `--text-col N` | profile default | 0-based description column index |
| `--debit-col N` | profile default | 0-based debit/amount column index |
| `--credit-col N` | profile default | 0-based credit column index (`-1` = none) |
| `--card-col N` | *(none)* | 0-based card/account number column index |
