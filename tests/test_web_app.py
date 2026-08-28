import os
import tempfile
import unittest
from decimal import Decimal

# Keep the module's import-time mkdir out of the real upload location.
os.environ.setdefault("UPLOAD_DIR", os.path.join(tempfile.gettempdir(), "bankanalyzer_web_tests"))

try:
    import web_app
except ImportError as exc:  # pragma: no cover - depends on install profile
    # CLAUDE.md documents a CLI-only install (openpyxl alone). Skip rather than
    # failing the whole discovery run when Flask is not present.
    raise unittest.SkipTest("web_app requires Flask: %s" % exc)


def _row(month, category, debit="0", credit="0", count=1):
    return {
        "month": month,
        "category": category,
        "count": count,
        "total_debit": Decimal(debit),
        "total_credit": Decimal(credit),
    }


class TestBuildCategoryData(unittest.TestCase):
    def test_ranks_spend_categories_and_converts_to_float(self):
        summary = [
            _row("2026-03", "Groceries", debit="75.50"),
            _row("2026-03", "Dining", debit="120.25"),
        ]

        data = web_app.build_category_data(summary)

        self.assertEqual(
            data["categories"],
            [
                {"category": "Dining", "total_debit": 120.25},
                {"category": "Groceries", "total_debit": 75.50},
            ],
        )
        self.assertIsInstance(data["categories"][0]["total_debit"], float)

    def test_excludes_income_and_transfers_from_the_chart(self):
        summary = [
            _row("2026-03", "Groceries", debit="75.50"),
            _row("2026-03", "Income", credit="2000.00"),
            _row("2026-03", "Transfers", debit="500.00"),
        ]

        data = web_app.build_category_data(summary)

        self.assertEqual([c["category"] for c in data["categories"]], ["Groceries"])

    def test_honors_selected_month(self):
        summary = [
            _row("2026-03", "Groceries", debit="75.50"),
            _row("2026-04", "Groceries", debit="10.00"),
        ]

        data = web_app.build_category_data(summary, selected_month="2026-04")

        self.assertEqual(data["categories"], [{"category": "Groceries", "total_debit": 10.0}])

    def test_reports_uncategorized_share_of_spend(self):
        summary = [
            _row("2026-03", "Groceries", debit="75.00"),
            _row("2026-03", web_app.analyzer.UNCATEGORIZED, debit="25.00"),
        ]

        data = web_app.build_category_data(summary)

        self.assertEqual(data["uncategorized_pct"], 25.0)

    def test_uncategorized_share_is_zero_when_there_is_no_spend(self):
        data = web_app.build_category_data([_row("2026-03", "Income", credit="2000.00")])

        self.assertEqual(data["categories"], [])
        self.assertEqual(data["uncategorized_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
