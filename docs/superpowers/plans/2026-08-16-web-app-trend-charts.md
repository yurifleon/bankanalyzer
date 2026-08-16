# Web App Trend Charts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two client-side bar charts (monthly debit/credit/net trend, top-10-vendors-by-spend) to the web app's results page, using data already computed in `analyze()`.

**Architecture:** Two pure Python functions in `web_app.py` reshape existing summary data (`monthly_totals`, `month_vendor_summary`) into small JSON-serializable lists (`Decimal` → `float`). These are passed to `render_template`, and `templates/results.html` renders them into two Chart.js `bar` charts via an inline `<script>` block, next to their corresponding existing tables.

**Tech Stack:** Python 3 (Flask, existing `web_app.py`), Chart.js loaded via CDN (`cdn.jsdelivr.net`, matching the existing `modern-normalize` CDN reference), Jinja2 `tojson` filter. No new `requirements.txt` dependency.

## Global Constraints

- No new Python dependency — do not add anything to `requirements.txt`.
- Chart.js must load from `https://cdn.jsdelivr.net/npm/chart.js`, matching the existing CDN pattern already used for `modern-normalize` CSS in both `index.html` and `results.html`.
- Cast `Decimal` → `float` only in the new chart-data functions; the existing `Decimal`-based table rendering and `.xlsx` output must not change.
- Top-vendors chart ranks by `total_debit` (spend) and is scoped to `selected_month` when set, otherwise all months — matching how `compute_top_patterns` already scopes to `selected_month`.
- Per the approved spec (`docs/superpowers/specs/2026-08-16-web-app-trend-charts-design.md`), this feature keeps the existing test boundary: `tests/` covers only the core analyzer module. Verification here is manual (documented per-task below), not new `unittest` files — do not create files under `tests/` for this plan.
- Every task must end with `python -m unittest discover -s tests` passing (regression check — this must keep passing even though no new tests are added to that suite).

---

### Task 1: Chart data-shaping functions in `web_app.py`

**Files:**
- Modify: `web_app.py:79-81` (insert after `compute_top_patterns`, before `build_analysis_directory`)

**Interfaces:**
- Produces: `build_monthly_trend_data(monthly_totals: list[dict]) -> list[dict]`, each dict `{"month": str, "debit": float, "credit": float, "net": float}`.
- Produces: `build_top_vendor_data(month_vendor_summary: list[dict], selected_month: str | None = None, top_n: int = 10) -> list[dict]`, each dict `{"vendor": str, "total_debit": float}`, sorted descending by `total_debit`.
- Consumes: rows shaped like `analyzer.summarize_month_totals()` output (keys `month`, `count`, `total_debit`, `total_credit`, `first_date`, `last_date`, `Decimal` values) and `analyzer.summarize_by_month_vendor()` output (keys `month`, `vendor`, `card_number`, `count`, `total_debit`, `total_credit`, `first_date`, `last_date`, `examples`, `Decimal` values). Both already exist in the codebase — no changes to `bank_csv_monthly_dual_profile_cardnum.py` in this plan.

- [ ] **Step 1: Add the two functions**

Insert immediately after the `compute_top_patterns` function (currently ending at `web_app.py:79`, i.e. right before the blank lines leading into `def build_analysis_directory():`):

```python
def build_monthly_trend_data(monthly_totals):
    return [
        {
            "month": row["month"],
            "debit": float(row["total_debit"]),
            "credit": float(row["total_credit"]),
            "net": float(row["total_credit"] - row["total_debit"]),
        }
        for row in monthly_totals
    ]


def build_top_vendor_data(month_vendor_summary, selected_month=None, top_n=10):
    totals = defaultdict(lambda: analyzer.Decimal("0"))

    for row in month_vendor_summary:
        if selected_month and row["month"] != selected_month:
            continue
        if not row["vendor"]:
            continue
        totals[row["vendor"]] += row["total_debit"]

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:top_n]
    return [{"vendor": vendor, "total_debit": float(total)} for vendor, total in ranked]
```

`defaultdict` is already imported at `web_app.py:3` (`from collections import Counter, defaultdict`) — no new import needed. `analyzer.Decimal` is available because `web_app.py:11` already does `import bank_csv_monthly_dual_profile_cardnum as analyzer`, and `compute_summary` (`web_app.py:41-42`) already uses `analyzer.Decimal("0")` the same way.

- [ ] **Step 2: Manually verify both functions**

Run from the repo root:

```bash
python3 -c "
from decimal import Decimal
from web_app import build_monthly_trend_data, build_top_vendor_data

monthly_totals = [
    {'month': '2025-01', 'count': 2, 'total_debit': Decimal('57.50'), 'total_credit': Decimal('0')},
    {'month': '2025-02', 'count': 3, 'total_debit': Decimal('43.00'), 'total_credit': Decimal('2000.00')},
]
print(build_monthly_trend_data(monthly_totals))

month_vendor_summary = [
    {'month': '2025-01', 'vendor': 'PANERA BREAD', 'total_debit': Decimal('12.50')},
    {'month': '2025-01', 'vendor': 'AMAZON', 'total_debit': Decimal('45.00')},
    {'month': '2025-02', 'vendor': 'PANERA BREAD', 'total_debit': Decimal('13.00')},
    {'month': '2025-02', 'vendor': 'AMAZON', 'total_debit': Decimal('30.00')},
]
print(build_top_vendor_data(month_vendor_summary))
print(build_top_vendor_data(month_vendor_summary, selected_month='2025-01'))
"
```

Expected output (three lines):

```
[{'month': '2025-01', 'debit': 57.5, 'credit': 0.0, 'net': -57.5}, {'month': '2025-02', 'debit': 43.0, 'credit': 2000.0, 'net': 1957.0}]
[{'vendor': 'AMAZON', 'total_debit': 75.0}, {'vendor': 'PANERA BREAD', 'total_debit': 25.5}]
[{'vendor': 'AMAZON', 'total_debit': 45.0}, {'vendor': 'PANERA BREAD', 'total_debit': 12.5}]
```

If the output doesn't match exactly, fix the function before proceeding — do not move to Step 3.

- [ ] **Step 3: Regression check**

```bash
python -m unittest discover -s tests
```

Expected: all existing tests still pass (this plan hasn't touched the analyzer module, so this confirms nothing broke on import).

- [ ] **Step 4: Commit**

```bash
git add web_app.py
git commit -m "$(cat <<'EOF'
Add chart data-shaping helpers for web app results page

build_monthly_trend_data() and build_top_vendor_data() reshape
already-computed summary data into JSON-serializable lists for the
upcoming Chart.js charts on the results page.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Wire chart data into the `analyze()` view

**Files:**
- Modify: `web_app.py:170-201` (inside `analyze()`, after `month_vendor_summary` is computed, and in the `render_template` call)

**Interfaces:**
- Consumes: `build_monthly_trend_data`, `build_top_vendor_data` from Task 1 (exact signatures above).
- Produces: `monthly_trend` and `top_vendors` template variables, available to `templates/results.html` in Task 3.

- [ ] **Step 1: Compute the chart data and pass it to the template**

In `analyze()`, current code at `web_app.py:170-179`:

```python
    monthly_totals = analyzer.summarize_month_totals(transactions)
    month_vendor_summary = analyzer.summarize_by_month_vendor(transactions)
    top_10_by_month = analyzer.top_10_per_month(month_vendor_summary)
    available_months = analyzer.get_available_months(transactions)
    pattern_summary = compute_top_patterns(transactions, top_n=20, selected_month=selected_month)
    recurring_activity = [
        item for item in analyzer.detect_recurring_activity(transactions) if item["is_recurring"]
    ]
    full_summary = compute_summary(transactions)
    filtered_summary = compute_summary(filtered_transactions) if filtered_transactions else None
```

Add two lines after `month_vendor_summary` is computed:

```python
    monthly_totals = analyzer.summarize_month_totals(transactions)
    month_vendor_summary = analyzer.summarize_by_month_vendor(transactions)
    monthly_trend = build_monthly_trend_data(monthly_totals)
    top_vendors = build_top_vendor_data(month_vendor_summary, selected_month=selected_month)
    top_10_by_month = analyzer.top_10_per_month(month_vendor_summary)
    available_months = analyzer.get_available_months(transactions)
    pattern_summary = compute_top_patterns(transactions, top_n=20, selected_month=selected_month)
    recurring_activity = [
        item for item in analyzer.detect_recurring_activity(transactions) if item["is_recurring"]
    ]
    full_summary = compute_summary(transactions)
    filtered_summary = compute_summary(filtered_transactions) if filtered_transactions else None
```

Then in the `render_template("results.html", ...)` call (current code at `web_app.py:181-201`), add two new kwargs alongside the existing ones (e.g. next to `top_10_by_month=top_10_by_month,`):

```python
        monthly_trend=monthly_trend,
        top_vendors=top_vendors,
```

- [ ] **Step 2: Manually verify the route still responds correctly**

`templates/results.html` doesn't reference `monthly_trend`/`top_vendors` yet (that's Task 3), so Jinja will simply ignore the two new kwargs — this step confirms that's true and nothing else broke.

Create a sample CSV for manual testing (bank profile: date=col1, description=col3, debit=col4, credit=col5):

```bash
cat > /tmp/sample_bank.csv <<'EOF'
id,date,ref,description,debit,credit
1,01/05/2025,,PANERA BREAD PENSACOLA FL,12.50,
2,01/12/2025,,AMAZON.COM/BILL,45.00,
3,02/03/2025,,PANERA BREAD PENSACOLA FL,13.00,
4,02/10/2025,,PAYCHECK DEPOSIT,,2000.00
5,02/15/2025,,AMAZON.COM/BILL,30.00,
EOF
```

Start the dev server in one terminal:

```bash
python web_app.py
```

In another terminal, POST the sample CSV and check the response status and that no traceback appears:

```bash
curl -s -o /tmp/results.html -w "%{http_code}\n" \
  -F "input_csv=@/tmp/sample_bank.csv" \
  -F "profile=bank" \
  http://127.0.0.1:5000/analyze
grep -c "Traceback" /tmp/results.html
```

Expected: first command prints `200`, second command prints `0` (no traceback in the response body). Stop the dev server (`Ctrl+C`) when done.

- [ ] **Step 3: Regression check**

```bash
python -m unittest discover -s tests
```

Expected: all existing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add web_app.py
git commit -m "$(cat <<'EOF'
Pass chart data from analyze() to the results template

Computes monthly_trend and top_vendors alongside the existing
summary data and passes them to results.html, ready for the
Chart.js rendering added in the next commit.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Render the charts in `templates/results.html`

**Files:**
- Modify: `templates/results.html:6` (add Chart.js CDN script tag)
- Modify: `templates/results.html:91-119` (Monthly totals section — add trend chart)
- Modify: `templates/results.html:121-149` (Top 10 vendors per month section — add top-vendors chart)
- Modify: `templates/results.html:185-187` (end of `<body>` — add inline chart-init script)

**Interfaces:**
- Consumes: `monthly_trend` and `top_vendors` template variables from Task 2 (exact shapes: `monthly_trend` = list of `{month, debit, credit, net}`; `top_vendors` = list of `{vendor, total_debit}`).

- [ ] **Step 1: Add the Chart.js CDN script tag**

At `templates/results.html:6`, current line:

```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/modern-normalize/modern-normalize.css">
```

Add immediately after it:

```html
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/modern-normalize/modern-normalize.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

- [ ] **Step 2: Add the monthly trend chart to the "Monthly totals" section**

Current code at `templates/results.html:91-92`:

```html
  <h2>Monthly totals</h2>
  <div class="table-wrapper">
```

Change to:

```html
  <h2>Monthly totals</h2>
  {% if monthly_trend %}
    <div class="card">
      <canvas id="monthlyTrendChart" height="100"></canvas>
    </div>
  {% else %}
    <p>Not enough data to chart.</p>
  {% endif %}
  <div class="table-wrapper">
```

(The rest of that table block, `templates/results.html:93-119`, is unchanged.)

- [ ] **Step 3: Add the top-vendors chart to the "Top 10 vendors per month" section**

Current code at `templates/results.html:121-122`:

```html
  <h2>Top 10 vendors per month</h2>
  <div class="table-wrapper">
```

Change to:

```html
  <h2>Top 10 vendors per month</h2>
  {% if top_vendors %}
    <div class="card">
      <canvas id="topVendorsChart" height="100"></canvas>
    </div>
  {% else %}
    <p>Not enough data to chart.</p>
  {% endif %}
  <div class="table-wrapper">
```

(The rest of that table block, `templates/results.html:123-149`, is unchanged.)

- [ ] **Step 4: Add the chart-init script before `</body>`**

Current code at `templates/results.html:185-187`:

```html
  </div>
</body>
</html>
```

Change to:

```html
  </div>

  <script>
    const monthlyTrend = {{ monthly_trend | tojson }};
    const topVendors = {{ top_vendors | tojson }};

    if (monthlyTrend.length > 0) {
      new Chart(document.getElementById('monthlyTrendChart'), {
        type: 'bar',
        data: {
          labels: monthlyTrend.map(function (row) { return row.month; }),
          datasets: [
            { label: 'Total Debit', data: monthlyTrend.map(function (row) { return row.debit; }) },
            { label: 'Total Credit', data: monthlyTrend.map(function (row) { return row.credit; }) },
            { label: 'Net', data: monthlyTrend.map(function (row) { return row.net; }) },
          ],
        },
        options: { responsive: true },
      });
    }

    if (topVendors.length > 0) {
      new Chart(document.getElementById('topVendorsChart'), {
        type: 'bar',
        data: {
          labels: topVendors.map(function (row) { return row.vendor; }),
          datasets: [
            { label: 'Total Debit', data: topVendors.map(function (row) { return row.total_debit; }) },
          ],
        },
        options: { responsive: true },
      });
    }
  </script>
</body>
</html>
```

Note: the `{% if monthly_trend %}` / `{% if top_vendors %}` guards in Steps 2–3 mean the `<canvas>` elements only exist in the DOM when there's data, which is exactly when `monthlyTrend.length > 0` / `topVendors.length > 0` are true — so `document.getElementById(...)` is never called against a missing canvas.

- [ ] **Step 5: Manually verify charts render in the browser**

Reuse the sample CSV from Task 2 (`/tmp/sample_bank.csv`; recreate it if it no longer exists using the heredoc from Task 2, Step 2).

```bash
python web_app.py
```

Open `http://127.0.0.1:5000` in a browser, upload `/tmp/sample_bank.csv` with profile `bank`, submit. On the results page, confirm:
- A "Monthly totals" bar chart appears above the Monthly totals table, with 2 month groups (2025-01, 2025-02) and 3 bars per group (Total Debit, Total Credit, Net).
- A "Top 10 vendors per month" bar chart appears above that table, with 3 bars (AMAZON, PANERA BREAD, and the vendor `clean_vendor_name` produces for "PAYCHECK DEPOSIT" — check `analyzer.clean_vendor_name` if the label looks unexpected, no code change needed either way).
- No JavaScript errors in the browser devtools console.

Then test the empty-data path: submit the same file with `month` set to `2099-01` (a month with no transactions) and confirm both chart sections show "Not enough data to chart." instead of an empty canvas, and there's still no JavaScript console error.

Stop the dev server (`Ctrl+C`) when done.

- [ ] **Step 6: Regression check**

```bash
python -m unittest discover -s tests
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add templates/results.html
git commit -m "$(cat <<'EOF'
Render monthly trend and top-vendors charts on results page

Adds Chart.js (via CDN, matching the existing modern-normalize
pattern) and two bar charts next to their corresponding tables,
using the monthly_trend/top_vendors data wired in the previous
commit. Falls back to a "not enough data" note when either
dataset is empty.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
