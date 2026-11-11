import tempfile
import unittest
from pathlib import Path

from app.services.file_validator import validate_csv


class FileValidatorTests(unittest.TestCase):
    def test_rejects_non_finite_amounts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invoices.csv"
            path.write_text(
                "invoice_id,customer_id,invoice_amount,invoice_date,due_date\n"
                "INV-1,C-1,inf,2026-01-01,2026-02-01\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "non-finite"):
                validate_csv(path, "invoices")


if __name__ == "__main__":
    unittest.main()
