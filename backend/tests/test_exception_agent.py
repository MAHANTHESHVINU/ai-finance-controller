import csv
import tempfile
import unittest
from pathlib import Path

from app.agents.exception_agent import read_csv, rule_based_analysis


class ExceptionAgentTests(unittest.TestCase):
    def test_rule_based_explanation_uses_engine_amount_difference(self):
        result = rule_based_analysis({
            "payment_id": "PAY-1",
            "status": "AMOUNT_MISMATCH",
            "amount_difference": "12.50",
        })

        self.assertIn("12.50", result["explanation"])

    def test_read_csv_rejects_missing_exception_status(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            with path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=["payment_id"])
                writer.writeheader()
                writer.writerow({"payment_id": "PAY-1"})

            with self.assertRaisesRegex(ValueError, "missing required columns"):
                read_csv(path)


if __name__ == "__main__":
    unittest.main()
