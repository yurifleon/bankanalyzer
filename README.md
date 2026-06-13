# Bank Analyzer

A Python-based bank and credit card CSV analyzer with both a CLI workflow and a browser-based web interface.

## Architecture

The repository is organized into three layers.

1. **Core analyzer logic** (`bank_csv_monthly_dual_profile_cardnum.py`)
   - **CSV reading:** `open_csv_with_fallback()` tries multiple encodings (`utf-8-sig`, `utf-16`, `cp1252`, `latin-1`).
   - **Parsing:** `parse_date()` and `parse_amount()` normalize dates and dollar values into Python objects.
   - **Vendor normalization:** `clean_vendor_name()` strips separators, phone numbers, dates, IDs, and state codes, then filters noise words.
   - **Transaction grouping:** `summarize_by_month_vendor()`, `summarize_month_totals()`, and `top_10_per_month()` aggregate transactions into the workbook rows.
   - **Output:** `write_workbook()` produces an Excel file with three sheets using `openpyxl`.

2. **Web interface** (`web_app.py`)
   - Accepts CSV uploads, optional search terms, and month filters.
   - Uses `read_transactions()` from the core analyzer.
   - Writes output workbooks to `UPLOAD_DIR` and exposes download links.
   - Supports overriding CSV column indices from the browser form.
   - Reads runtime configuration from environment variables.

3. **Container packaging** (`Containerfile`, `entrypoint.sh`)
   - Builds a minimal Python 3.11 image and installs runtime dependencies.
   - Uses `entrypoint.sh` to create the `UPLOAD_DIR` at container startup.
   - Runs the web app with `gunicorn` on `0.0.0.0:5000`.
   - Includes a `HEALTHCHECK` to verify the web endpoint is reachable.

## Detailed request flow

The web request flow is:

1. User uploads a CSV via the browser.
2. Flask saves the file to `UPLOAD_DIR`.
3. `web_app.py` parses form controls, resolves profile/column overrides, and calls `read_transactions()`.
4. The analyzer reads rows, normalizes vendors, and aggregates monthly totals.
5. `write_workbook()` creates the Excel output file in `UPLOAD_DIR`.
6. The browser results page renders summary data and download links.

## Requirements

- Python 3.7+
- `openpyxl`
- `Flask`
- `gunicorn`

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## CLI usage

Analyze a CSV and write the full monthly workbook:

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

## Web interface

Start the browser-based app:

```bash
python3 web_app.py
```

Open `http://127.0.0.1:5000` and upload your CSV. The web UI supports profile selection, optional search text, and month filtering.

## Container usage

Build the container image from the repository root:

```bash
podman build --format docker -t bankanalyzer:web -f Containerfile .
# or with Docker:
docker build -t bankanalyzer:web -f Containerfile .
```

Run the container and expose port 5000:

```bash
podman run --rm -p 5000:5000 --name bankanalyzer bankanalyzer:web
```

The container runs `gunicorn` with the Flask app and includes a healthcheck.

### Persistent uploads

To persist uploads and generated workbooks on the host, mount a host folder:

```bash
mkdir -p /srv/bankanalyzer/uploads
podman run --rm -p 5000:5000 \
  -e UPLOAD_DIR=/uploads \
  -v /srv/bankanalyzer/uploads:/uploads:Z \
  --name bankanalyzer bankanalyzer:web
```

### Supported environment variables

- `UPLOAD_DIR`: Container path for uploaded files and generated workbooks (default `/uploads`).
- `MAX_CONTENT_LENGTH`: Maximum upload size in bytes (default `52428800`, 50MB).
- `FLASK_HOST`, `FLASK_PORT`: Host and port for the Flask app inside the container (default `0.0.0.0:5000`).
- `FLASK_DEBUG`: Set to `1` or `true` to enable debug mode (default `false` in container).

## Tests

Run unit tests:

```bash
python -m unittest discover -s tests
```

## Notes

- The repository combines a CLI analyzer, a Flask web wrapper, and container packaging.
- The analyzer supports common CSV encodings: `utf-8-sig`, `utf-16`, `cp1252`, `latin-1`.
- The container runs the app with Gunicorn for a more production-ready runtime.

## Additional documentation

For a more detailed user guide, architecture description, and container usage examples, see `USER_MANUAL.md`.
