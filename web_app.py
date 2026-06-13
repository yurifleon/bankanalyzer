import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from uuid import uuid4

from flask import (Flask, abort, redirect, render_template, request,
                   send_from_directory, url_for)
from werkzeug.utils import secure_filename

import bank_csv_monthly_dual_profile_cardnum as analyzer

# Upload / analysis directory can be overridden by the UPLOAD_DIR environment variable.
_env_upload = os.environ.get("UPLOAD_DIR")
if _env_upload:
    UPLOAD_DIR = Path(_env_upload)
else:
    UPLOAD_DIR = Path(tempfile.gettempdir()) / "bankanalyzer_web"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
# Allow max upload size to be configured via env (default 50MB)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 50 * 1024 * 1024))


def parse_optional_int(value):
    if value is None:
        return None

    value = str(value).strip()
    if value == "":
        return None

    try:
        return int(value)
    except ValueError:
        return None


def compute_summary(transactions):
    total_debit = sum((tx["debit"] for tx in transactions), analyzer.Decimal("0"))
    total_credit = sum((tx["credit"] for tx in transactions), analyzer.Decimal("0"))
    dates = [tx["date"] for tx in transactions if tx["date"] is not None]

    return {
        "rows": len(transactions),
        "total_debit": total_debit,
        "total_credit": total_credit,
        "net": total_credit - total_debit,
        "first_date": min(dates).isoformat() if dates else None,
        "last_date": max(dates).isoformat() if dates else None,
    }


def compute_top_patterns(transactions, top_n=20, selected_month=None):
    counter = Counter()
    examples = defaultdict(list)

    for tx in transactions:
        if selected_month and tx["month"] != selected_month:
            continue

        vendor = tx["vendor"]
        if not vendor:
            continue

        counter[vendor] += 1
        if len(examples[vendor]) < 2 and tx["description"] not in examples[vendor]:
            examples[vendor].append(tx["description"])

    results = []
    for vendor, count in counter.most_common(top_n):
        results.append({
            "vendor": vendor,
            "count": count,
            "example": examples[vendor][0] if examples[vendor] else "",
        })

    return results


def build_analysis_directory():
    analysis_id = uuid4().hex
    analysis_dir = UPLOAD_DIR / analysis_id
    analysis_dir.mkdir(parents=True, exist_ok=True)
    return analysis_id, analysis_dir


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    csv_file = request.files.get("input_csv")

    if not csv_file or csv_file.filename == "":
        return render_template("index.html", error="Please upload a CSV file.")

    analysis_id, analysis_dir = build_analysis_directory()
    filename = secure_filename(csv_file.filename)
    input_path = analysis_dir / filename
    csv_file.save(str(input_path))

    profile = request.form.get("profile", "bank")
    search_text = request.form.get("search_text", "").strip() or None
    selected_month = request.form.get("month", "").strip() or None

    date_col = parse_optional_int(request.form.get("date_col"))
    text_col = parse_optional_int(request.form.get("text_col"))
    debit_col = parse_optional_int(request.form.get("debit_col"))
    credit_col = parse_optional_int(request.form.get("credit_col"))
    card_col = parse_optional_int(request.form.get("card_col"))

    if profile == "credit-card":
        default_date_col = 0
        default_text_col = 1
        default_debit_col = 4
        default_credit_col = -1
    else:
        default_date_col = 1
        default_text_col = 3
        default_debit_col = 4
        default_credit_col = 5

    date_col = default_date_col if date_col is None else date_col
    text_col = default_text_col if text_col is None else text_col
    debit_col = default_debit_col if debit_col is None else debit_col
    credit_col = default_credit_col if credit_col is None else credit_col

    try:
        transactions = analyzer.read_transactions(
            str(input_path),
            date_col,
            text_col,
            debit_col,
            credit_col,
            card_col,
        )
    except Exception as exc:
        return render_template("index.html", error=f"Failed to read CSV: {exc}")

    if not transactions:
        return render_template(
            "index.html",
            error=(
                "No valid transactions found. Check your file, column mapping, and date format. "
                "For credit-card profile, the expected layout is: date=A, description=B, amount=E."
            ),
        )

    input_stem = Path(filename).stem
    monthly_output = analysis_dir / f"{input_stem}_monthly_totals.xlsx"
    analyzer.write_workbook(transactions, str(monthly_output))

    filtered_output = None
    filtered_transactions = None
    if search_text or selected_month:
        filtered_transactions = analyzer.filter_transactions(
            transactions,
            search_text=search_text,
            selected_month=selected_month,
        )

        if filtered_transactions:
            filtered_output = analysis_dir / f"{input_stem}_filtered_analysis.xlsx"
            analyzer.write_workbook(filtered_transactions, str(filtered_output))

    monthly_totals = analyzer.summarize_month_totals(transactions)
    month_vendor_summary = analyzer.summarize_by_month_vendor(transactions)
    top_10_by_month = analyzer.top_10_per_month(month_vendor_summary)
    available_months = analyzer.get_available_months(transactions)
    pattern_summary = compute_top_patterns(transactions, top_n=20, selected_month=selected_month)
    full_summary = compute_summary(transactions)
    filtered_summary = compute_summary(filtered_transactions) if filtered_transactions else None

    return render_template(
        "results.html",
        analysis_id=analysis_id,
        monthly_output=monthly_output.name,
        filtered_output=filtered_output.name if filtered_output else None,
        profile=profile,
        date_col=date_col,
        text_col=text_col,
        debit_col=debit_col,
        credit_col=credit_col,
        card_col=card_col,
        search_text=search_text,
        selected_month=selected_month,
        available_months=available_months,
        monthly_totals=monthly_totals,
        top_10_by_month=top_10_by_month,
        pattern_summary=pattern_summary,
        full_summary=full_summary,
        filtered_summary=filtered_summary,
    )


@app.route("/download/<analysis_id>/<filename>")
def download_file(analysis_id, filename):
    analysis_path = UPLOAD_DIR / secure_filename(analysis_id)
    if not analysis_path.exists() or not analysis_path.is_dir():
        abort(404)

    safe_name = secure_filename(filename)
    return send_from_directory(str(analysis_path), safe_name, as_attachment=True)


if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug_env = os.environ.get("FLASK_DEBUG", None)
    # Default to False in containerized runs unless explicitly enabled.
    debug = False if debug_env is None else str(debug_env).lower() in ("1", "true", "yes")

    app.run(debug=debug, host=host, port=port)
