# Web App Trend Charts — Design

## Purpose

`web_app.py` / `templates/results.html` currently present every analysis result as HTML tables only (monthly totals, top vendors per month, recurring activity). The underlying data (`monthly_totals`, `month_vendor_summary`) already supports a "trend over time" and "top vendors" view, but a user has to read numbers across a table to see it. This adds two charts to the results page so spending trends and top vendors are visible at a glance, without replacing the existing tables or the downloadable `.xlsx` workbooks.

## Scope

In scope: two charts on `results.html`, rendered client-side, from data already computed in `analyze()`.
Out of scope: charts inside the generated `.xlsx` workbook, historical/multi-analysis comparison, category tagging, any new Python dependency.

## Charts

### 1. Monthly trend chart

Grouped bar chart, one group per month, three series per group: **Total Debit**, **Total Credit**, **Net** — mirroring the existing "Monthly totals" table columns exactly (same source: `monthly_totals`, from `analyzer.summarize_month_totals`). Placed directly above or below that table.

### 2. Top vendors chart

Vertical bar chart, one bar per vendor, top 10 by total debit (spend), same visual style as the monthly trend chart. Source: aggregate `month_vendor_summary` (already computed in `analyze()` for `top_10_per_month`) across all months by vendor, sum `total_debit`, sort descending, take top 10. If `selected_month` is set, aggregate only that month's entries instead — this matches how `compute_top_patterns` already scopes to `selected_month`. Placed near the existing "Top 10 vendors per month" table.

## Library

Chart.js, loaded via `<script src="https://cdn.jsdelivr.net/npm/chart.js">` in `results.html`. This follows the existing precedent of `modern-normalize` CSS already loaded from `cdn.jsdelivr.net` in both `index.html` and `results.html`. No new Python/`requirements.txt` dependency.

## Data flow / code changes

**`web_app.py`, in `analyze()`:**

- Build `monthly_trend`: list of `{"month": str, "debit": float, "credit": float, "net": float}`, derived from the existing `monthly_totals` list (cast `Decimal` → `float`; `.xlsx`/table values stay `Decimal` as today — this cast is only for the chart JSON).
- Build `top_vendors`: list of `{"vendor": str, "total_debit": float}`, top 10, computed by summing `month_vendor_summary` entries per vendor (scoped to `selected_month` if set) and sorting by `total_debit` descending.
- Pass both as new `render_template(...)` kwargs.

**`templates/results.html`:**

- Add the Chart.js `<script src>` tag in `<head>`.
- Add two `<canvas>` elements (one per chart), each inside a `.card`-style container matching the page's existing layout, near their corresponding tables.
- Add one inline `<script>` block near the end of `<body>` that reads `{{ monthly_trend | tojson }}` and `{{ top_vendors | tojson }}` and initializes two `Chart` instances (`type: 'bar'`), using default Chart.js colors (no new palette work needed for this internal tool).

## Edge cases

- No transactions after filtering (empty `monthly_trend` / `top_vendors`): skip chart initialization and render a "Not enough data to chart" note instead of an empty canvas, consistent with the existing empty-state row in the Recurring Activity table (`{% else %}` block).
- `net` can be negative (credit < debit in a month) — bar chart handles negative bars natively in Chart.js, no special casing needed.

## Testing

The existing `unittest` suite (`tests/test_bank_csv_monthly_dual_profile_cardnum.py`) covers only the core analyzer module, not `web_app.py` — this change keeps that boundary as-is. Verification is manual: run `python web_app.py`, upload a sample CSV under both profiles (`bank`, `credit-card`), confirm both charts render, confirm the empty-data note appears when a search/month filter yields zero rows, and confirm `python -m unittest discover -s tests` still passes (chart data-shaping code doesn't touch the analyzer module, so this is a regression check, not new coverage).
