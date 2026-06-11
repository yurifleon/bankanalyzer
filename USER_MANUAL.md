# Bank CSV Analyzer — User Manual

`bank_csv_monthly_dual_profile_cardnum.py` reads a bank or credit-card CSV export and produces an Excel workbook with monthly spending summaries, vendor breakdowns, and an optional filtered workbook for a specific vendor or month.

---

## Requirements

Python 3.7+ and the `openpyxl` library.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you prefer a system package on Debian/Ubuntu:

```bash
sudo apt install python3-openpyxl
```

---

## Testing

A small test suite is included in the `tests/` folder.

```bash
source .venv/bin/activate
python -m unittest discover -s tests
```

If you have not created the virtual environment yet, first run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Preparing your CSV

Export your transaction history from your bank or card issuer as a CSV file. No manual editing is needed — the script handles headers, blank rows, and common encoding issues automatically (it tries utf-8-sig, utf-16, cp1252, and latin-1 in order).

The only requirement is that each data row contains a parseable date in one column and a dollar amount in another. See [Column mapping](#column-mapping) if your layout differs from the defaults.

---

## CSV profiles

The script has two built-in profiles that set default column positions.

### Bank profile (default)

Matches a typical checking/savings account export where debits and credits are in separate columns.

| Column | Index | Content |
|--------|-------|---------|
| B | 1 | Transaction date |
| D | 3 | Description |
| E | 4 | Debit / charge amount |
| F | 5 | Credit / payment amount |

### Credit-card profile (`--profile credit-card`)

Matches a typical credit-card export where a single amount column uses positive numbers for charges and negative numbers for payments.

| Column | Index | Content |
|--------|-------|---------|
| A | 0 | Transaction date |
| B | 1 | Description |
| E | 4 | Amount (positive = charge, negative = payment) |

Use `--profile credit-card` for Amex, Visa, Mastercard, and Discover card exports.

---

## Basic usage

### Generate a full-year workbook

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --profile credit-card
```

This always runs first regardless of other options. It writes `transactions_monthly_totals.xlsx` (or whatever name you specify with `--monthly-output`) containing three sheets described in [Output sheets](#output-sheets).

### Generate a workbook filtered to one vendor

Pass a search term as the second argument:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "AMAZON" --profile credit-card
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "PANERA"
```

The search matches against both the raw description and the normalized vendor name, case-insensitively. A second Excel file is written alongside the full-year file containing only the matching rows.

### Filter to a specific month

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --month 2025-03
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "AMAZON" --month 2025-03
```

`--month` accepts `YYYY-MM` format. When combined with a search term, both filters apply (rows must match the vendor AND fall in that month).

---

## Interactive modes

### Vendor menu (`--menu`)

Displays the top vendors ranked by transaction count and prompts you to pick one:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --profile credit-card --menu
```

```
Top 30 likely vendors/business patterns for whole year:

1. PANERA BREAD (85 rows)
   example: GglPay PANERA BREAD PENSACOLA  FL
2. AMAZON MARKEPLACE (76 rows)
   ...

Select a number (1-30) or type custom search text:
```

Type a number to use the corresponding vendor, or type any text to use that as a free-form search.

Use `--top N` to show more or fewer entries (default 30):

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --menu --top 50
```

### Month selection menu (`--month-menu`)

Prompts you to choose a specific month or the whole year:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --month-menu
```

```
Available months:

0. Whole year / all months
1. 2025-01
2. 2025-02
...

Select month number or press Enter for whole year:
```

`--menu` and `--month-menu` can be combined — the month selection runs first, then the vendor menu is shown filtered to that month.

---

## Output sheets

Every workbook (both the full-year file and any filtered file) contains the same three sheets.

### Monthly Totals

One row per calendar month. Columns:

| Column | Description |
|--------|-------------|
| Month | YYYY-MM |
| Transaction Count | Number of rows in that month |
| Total Debit / Charges | Sum of all charges |
| Total Credit / Payments | Sum of all payments/credits |
| Net Credit - Debit | Payments minus charges (positive = net credit) |
| First Date | Earliest transaction date in that month |
| Last Date | Latest transaction date in that month |

### Monthly Grouped

One row per vendor per month (and per card number if `--card-col` is used). Columns:

| Column | Description |
|--------|-------------|
| Month | YYYY-MM |
| Vendor / Group | Normalized vendor name |
| Card Number | Card/account identifier (only if `--card-col` was specified) |
| Transaction Count | Number of transactions for this vendor in this month |
| Total Debit / Charges | Sum of charges |
| Total Credit / Payments | Sum of payments |
| Net Credit - Debit | Net amount |
| First Date | First transaction date |
| Last Date | Last transaction date |
| Examples | Up to 3 raw description strings from the source CSV |

Sorted alphabetically by vendor within each month.

### Top 10 Per Month

The 10 highest-spending vendors for each month, ranked by total charges. Columns are the same as Monthly Grouped plus a **Rank** column (1–10). Ties in total charges are broken by transaction count.

All sheets have:
- Bold blue header row
- Frozen top row (header stays visible while scrolling)
- Auto-filter dropdowns on every column

---

## Output file naming

**Full-year workbook:** `INPUT_monthly_totals.xlsx` by default. Override with `--monthly-output`:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --monthly-output my_report.xlsx
```

**Search/filtered workbook:** Auto-generated from the input filename, the word `search`, the month (if any), and the search term. Examples:

```
transactions_search_AMAZON.xlsx
transactions_search_2025-03_PANERA BREAD.xlsx
transactions_search_2025-03_option_1.xlsx   ← when selected from menu
```

Override with `--search-output`:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "AMAZON" --search-output amazon_2025.xlsx
```

**Subset CSV:** Optionally write the raw matching rows back to a CSV file with `--subset-csv`:

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv "AMAZON" --subset-csv amazon_rows.csv
```

---

## Column mapping

If your CSV layout doesn't match either built-in profile, override individual columns with 0-based indices (column A = 0, B = 1, C = 2, …):

```bash
# Date in column A, description in column C, debit in column D, credit in column E
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv \
    --date-col 0 --text-col 2 --debit-col 3 --credit-col 4
```

Use `--credit-col -1` to indicate there is no separate credit column (sign-based single-amount layout like the credit-card profile):

```bash
python3 bank_csv_monthly_dual_profile_cardnum.py transactions.csv --debit-col 3 --credit-col -1
```

Any override takes precedence over the profile default for that column. You can mix profile defaults with individual overrides.

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
