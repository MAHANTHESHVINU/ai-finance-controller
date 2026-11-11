import csv
import tempfile
import unittest
from pathlib import Path

from app.reconciliation.engine import reconcile


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.data_dir = self.root / "input"
        self.output_dir = self.root / "output"
        self.data_dir.mkdir()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_csv(self, filename, fieldnames, rows):
        with (self.data_dir / filename).open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def write_dataset(self, payments=None, invoices=None, bank_rows=None):
        self.write_csv(
            "invoices.csv",
            ["invoice_id", "invoice_amount"],
            invoices if invoices is not None else [
                {"invoice_id": "INV-1", "invoice_amount": "100.00"}
            ],
        )
        self.write_csv(
            "payments.csv",
            ["payment_id", "invoice_id", "payment_amount"],
            payments if payments is not None else [
                {"payment_id": "PAY-1", "invoice_id": "INV-1",
                 "payment_amount": "100.00"}
            ],
        )
        self.write_csv(
            "bank_transactions.csv",
            ["bank_txn_id", "reference_id", "bank_amount"],
            bank_rows if bank_rows is not None else [
                {"bank_txn_id": "BNK-1", "reference_id": "PAY-1",
                 "bank_amount": "100.00"}
            ],
        )

    def test_matched_payment_and_metrics(self):
        self.write_dataset()

        metrics = reconcile(self.data_dir, self.output_dir)

        self.assertEqual(metrics["matched"], 1)
        self.assertEqual(metrics["match_rate_percent"], 100.0)
        with (self.output_dir / "reconciliation_results.csv").open(
            newline="",
            encoding="utf-8",
        ) as file:
            result = next(csv.DictReader(file))
        self.assertEqual(result["status"], "MATCHED")

    def test_classifies_amount_mismatch_and_duplicate_bank(self):
        payments = [
            {"payment_id": "PAY-1", "invoice_id": "INV-1",
             "payment_amount": "100.00"},
            {"payment_id": "PAY-2", "invoice_id": "INV-2",
             "payment_amount": "80.00"},
        ]
        invoices = [
            {"invoice_id": "INV-1", "invoice_amount": "100.00"},
            {"invoice_id": "INV-2", "invoice_amount": "80.00"},
        ]
        bank_rows = [
            {"bank_txn_id": "BNK-1", "reference_id": "PAY-1",
             "bank_amount": "101.00"},
            {"bank_txn_id": "BNK-2", "reference_id": "PAY-2",
             "bank_amount": "80.00"},
            {"bank_txn_id": "BNK-3", "reference_id": "PAY-2",
             "bank_amount": "80.00"},
        ]
        self.write_dataset(payments, invoices, bank_rows)

        metrics = reconcile(self.data_dir, self.output_dir)

        self.assertEqual(
            metrics["status_counts"],
            {"AMOUNT_MISMATCH": 1, "DUPLICATE_BANK": 1},
        )

    def test_classifies_missing_invoice_missing_bank_and_invalid_amount(self):
        payments = [
            {"payment_id": "PAY-1", "invoice_id": "INV-MISSING",
             "payment_amount": "50.00"},
            {"payment_id": "PAY-2", "invoice_id": "INV-2",
             "payment_amount": "75.00"},
            {"payment_id": "PAY-3", "invoice_id": "INV-3",
             "payment_amount": "not-a-number"},
        ]
        invoices = [
            {"invoice_id": "INV-2", "invoice_amount": "75.00"},
            {"invoice_id": "INV-3", "invoice_amount": "75.00"},
        ]
        bank_rows = [
            {"bank_txn_id": "BNK-3", "reference_id": "PAY-3",
             "bank_amount": "75.00"},
        ]
        self.write_dataset(payments, invoices, bank_rows)

        metrics = reconcile(self.data_dir, self.output_dir)

        self.assertEqual(
            metrics["status_counts"],
            {
                "MISSING_INVOICE": 1,
                "MISSING_BANK": 1,
                "INVALID_AMOUNT": 1,
            },
        )

    def test_rejects_missing_required_header(self):
        self.write_csv(
            "invoices.csv",
            ["invoice_id"],
            [{"invoice_id": "INV-1"}],
        )
        self.write_csv(
            "payments.csv",
            ["payment_id", "invoice_id", "payment_amount"],
            [{"payment_id": "PAY-1", "invoice_id": "INV-1",
              "payment_amount": "10"}],
        )
        self.write_csv(
            "bank_transactions.csv",
            ["bank_txn_id", "reference_id", "bank_amount"],
            [],
        )

        with self.assertRaisesRegex(ValueError, "missing required columns"):
            reconcile(self.data_dir, self.output_dir)

    def test_rejects_duplicate_normalized_headers(self):
        (self.data_dir / "invoices.csv").write_text(
            "invoice_id, Invoice_ID, invoice_amount\nINV-1,INV-1,10\n",
            encoding="utf-8",
        )
        self.write_csv(
            "payments.csv",
            ["payment_id", "invoice_id", "payment_amount"],
            [],
        )
        self.write_csv(
            "bank_transactions.csv",
            ["bank_txn_id", "reference_id", "bank_amount"],
            [],
        )

        with self.assertRaisesRegex(ValueError, "duplicate column names"):
            reconcile(self.data_dir, self.output_dir)

    def test_rejects_rows_with_extra_columns(self):
        self.write_csv(
            "invoices.csv",
            ["invoice_id", "invoice_amount"],
            [{"invoice_id": "INV-1", "invoice_amount": "100"}],
        )
        (self.data_dir / "payments.csv").write_text(
            "payment_id,invoice_id,payment_amount\nPAY-1,INV-1,100,EXTRA\n",
            encoding="utf-8",
        )
        self.write_csv(
            "bank_transactions.csv",
            ["bank_txn_id", "reference_id", "bank_amount"],
            [],
        )

        with self.assertRaisesRegex(ValueError, "more values than"):
            reconcile(self.data_dir, self.output_dir)

    def test_rejects_empty_payment_identifier(self):
        self.write_dataset(
            payments=[{"payment_id": "", "invoice_id": "INV-1",
                       "payment_amount": "100.00"}],
        )

        with self.assertRaisesRegex(ValueError, "non-empty payment_id"):
            reconcile(self.data_dir, self.output_dir)


if __name__ == "__main__":
    unittest.main()
