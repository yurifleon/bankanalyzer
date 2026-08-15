import unittest
from datetime import date
from decimal import Decimal
import bank_csv_monthly_dual_profile_cardnum as analyzer


def _make_tx(vendor, tx_date, debit=Decimal("0"), credit=Decimal("0"), description=None, card_number=""):
    return {
        "row_number": 1,
        "date": tx_date,
        "month": analyzer.month_key(tx_date),
        "description": description or vendor,
        "vendor": vendor,
        "card_number": card_number,
        "debit": debit,
        "credit": credit,
        "net": credit - debit,
        "row": [],
    }


class TestBankCSVMonthlyDualProfile(unittest.TestCase):
    def test_parse_amount(self):
        self.assertEqual(analyzer.parse_amount("$1,234.56"), Decimal("1234.56"))
        self.assertEqual(analyzer.parse_amount("(1,234.56)"), Decimal("-1234.56"))
        self.assertEqual(analyzer.parse_amount(""), Decimal("0"))
        self.assertEqual(analyzer.parse_amount(None), Decimal("0"))

    def test_parse_date(self):
        self.assertEqual(analyzer.parse_date("06/08/2026").isoformat(), "2026-06-08")
        self.assertEqual(analyzer.parse_date("2026-06-08").isoformat(), "2026-06-08")
        self.assertEqual(analyzer.parse_date("06-08-26").isoformat(), "2026-06-08")
        self.assertIsNone(analyzer.parse_date("2026.06.08"))

    def test_clean_vendor_name(self):
        self.assertEqual(
            analyzer.clean_vendor_name("GglPay PANERA BREAD PENSACOLA  FL"),
            "PANERA BREAD"
        )
        self.assertEqual(
            analyzer.clean_vendor_name("AMAZON.COM/BILL"),
            "AMAZON"
        )
        self.assertEqual(
            analyzer.clean_vendor_name("SHELL SERVICE STATIOSUNRISE FL"),
            "SHELL SERVICE STATIOSUNRISE"
        )

    def test_safe_filename(self):
        self.assertEqual(analyzer.safe_filename("AMAZON MARKETPLACE"), "AMAZON_MARKETPLACE")
        self.assertEqual(analyzer.safe_filename("///"), "search")

    def test_detect_recurring_activity_finds_fixed_monthly_charge(self):
        transactions = [
            _make_tx("NETFLIX", date(2025, 1, 5), debit=Decimal("15.99")),
            _make_tx("NETFLIX", date(2025, 2, 5), debit=Decimal("15.99")),
            _make_tx("NETFLIX", date(2025, 3, 6), debit=Decimal("15.99")),
            _make_tx("NETFLIX", date(2025, 4, 5), debit=Decimal("15.99")),
        ]

        results = analyzer.detect_recurring_activity(transactions)

        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertEqual(item["vendor"], "NETFLIX")
        self.assertTrue(item["is_recurring"])
        self.assertEqual(item["classification"], "Monthly Fixed Amount")
        self.assertEqual(item["direction"], "Expense / Charge")
        self.assertEqual(item["count"], 4)

    def test_detect_recurring_activity_ignores_infrequent_and_irregular(self):
        transactions = [
            # Only two occurrences: below the default min_occurrences threshold.
            _make_tx("RARE VENDOR", date(2025, 1, 1), debit=Decimal("50.00")),
            _make_tx("RARE VENDOR", date(2025, 6, 1), debit=Decimal("50.00")),
            # Irregular gaps and amounts: should not be classified as recurring.
            _make_tx("RANDOM SHOP", date(2025, 1, 3), debit=Decimal("12.00")),
            _make_tx("RANDOM SHOP", date(2025, 1, 20), debit=Decimal("87.00")),
            _make_tx("RANDOM SHOP", date(2025, 3, 15), debit=Decimal("5.00")),
        ]

        results = analyzer.detect_recurring_activity(transactions)

        by_vendor = {item["vendor"]: item for item in results}
        self.assertNotIn("RARE VENDOR", by_vendor)
        self.assertIn("RANDOM SHOP", by_vendor)
        self.assertFalse(by_vendor["RANDOM SHOP"]["is_recurring"])
        self.assertEqual(by_vendor["RANDOM SHOP"]["classification"], "Irregular")
