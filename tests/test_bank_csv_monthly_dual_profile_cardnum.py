import unittest
from decimal import Decimal
import bank_csv_monthly_dual_profile_cardnum as analyzer


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
