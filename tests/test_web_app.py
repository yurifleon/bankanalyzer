import unittest
from decimal import Decimal

import web_app


def _vendor_row(vendor, month, debit):
    return {"vendor": vendor, "month": month, "total_debit": Decimal(debit)}


class TestChartDataHelpers(unittest.TestCase):
    def test_monthly_trend_converts_decimals_and_preserves_months(self):
        rows = [
            {"month": "2025-01", "total_debit": Decimal("10.20"),
             "total_credit": Decimal("3.10")},
            {"month": "2025-02", "total_debit": Decimal("0"),
             "total_credit": Decimal("12.34")},
        ]

        result = web_app.build_monthly_trend_data(rows)

        self.assertEqual(result, [
            {"month": "2025-01", "debit": 10.20, "credit": 3.10, "net": -7.10},
            {"month": "2025-02", "debit": 0.0, "credit": 12.34, "net": 12.34},
        ])
        for row in result:
            for key in ("debit", "credit", "net"):
                self.assertIsInstance(row[key], float)

    def test_monthly_trend_empty_input(self):
        self.assertEqual(web_app.build_monthly_trend_data([]), [])

    def test_top_vendors_aggregates_months_and_converts_decimals(self):
        rows = [
            _vendor_row("SHOP", "2025-01", "10.10"),
            _vendor_row("CAFE", "2025-01", "20.25"),
            _vendor_row("SHOP", "2025-02", "15.20"),
        ]

        result = web_app.build_top_vendor_data(rows)

        self.assertEqual(result, [
            {"vendor": "SHOP", "total_debit": 25.30},
            {"vendor": "CAFE", "total_debit": 20.25},
        ])
        for row in result:
            self.assertIsInstance(row["total_debit"], float)

    def test_top_vendors_filters_month_before_ranking(self):
        rows = [
            _vendor_row("SHOP", "2025-01", "10.10"),
            _vendor_row("CAFE", "2025-01", "20.25"),
            _vendor_row("SHOP", "2025-02", "100.00"),
            _vendor_row("OTHER", "2025-02", "200.00"),
        ]

        self.assertEqual(
            web_app.build_top_vendor_data(rows, selected_month="2025-01", top_n=1),
            [{"vendor": "CAFE", "total_debit": 20.25}],
        )
        self.assertEqual(
            web_app.build_top_vendor_data(rows, selected_month="2025-03"), []
        )

    def test_top_vendors_orders_by_spend_and_limits_results(self):
        rows = [_vendor_row("VENDOR %s" % i, "2025-01", str(i))
                for i in (4, 11, 2, 8, 1, 12, 6, 3, 10, 5, 9, 7)]
        expected = [
            {"vendor": "VENDOR %s" % i, "total_debit": float(i)}
            for i in range(12, 2, -1)
        ]

        self.assertEqual(web_app.build_top_vendor_data(rows), expected)
        self.assertEqual(web_app.build_top_vendor_data(rows, top_n=3), expected[:3])

    def test_top_vendors_ignores_blank_vendors(self):
        rows = [
            _vendor_row("", "2025-01", "1000.00"),
            _vendor_row("SHOP", "2025-01", "1.25"),
        ]

        self.assertEqual(web_app.build_top_vendor_data(rows, top_n=1), [
            {"vendor": "SHOP", "total_debit": 1.25},
        ])
        self.assertEqual(web_app.build_top_vendor_data(rows[:1]), [])

    def test_top_vendors_empty_input(self):
        self.assertEqual(web_app.build_top_vendor_data([]), [])
