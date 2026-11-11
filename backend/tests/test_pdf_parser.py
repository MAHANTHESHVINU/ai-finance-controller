import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.pdf_parser import (
    _key_value_records,
    _table_records,
    _field_for_header,
    extract_pdf_to_csv,
)


class PdfParserTests(unittest.TestCase):
    def test_maps_common_table_headers_to_canonical_fields(self):
        self.assertEqual(_field_for_header("Invoice No.", "invoices"), "invoice_id")
        self.assertEqual(
            _field_for_header("Total Amount", "invoices"),
            "invoice_amount",
        )

    def test_extracts_labeled_invoice_fields(self):
        records = _key_value_records(
            "Invoice Number: INV-42\nTotal Amount: $1,250.00",
            "invoices",
            1,
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["invoice_id"], "INV-42")
        self.assertEqual(records[0]["invoice_amount"], "1250.00")

    def test_extracts_table_rows_with_unneeded_columns_omitted(self):
        records = _table_records(
            [
                ["Payment Ref", "Invoice Number", "Paid Amount"],
                ["PAY-1", "INV-1", "$100.00"],
            ],
            "payments",
            1,
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["payment_id"], "PAY-1")
        self.assertEqual(records[0]["payment_amount"], "100.00")

    def test_extracts_bank_statement_debit_and_generates_missing_transaction_id(self):
        records = _table_records(
            [
                ["Date", "Ref No.", "Debit", "Credit", "Description"],
                ["2026-04-10", "PAY-9", "25.00", "", "Payment"],
            ],
            "bank_transactions",
            2,
            1,
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["bank_txn_id"], "PDF-BANK-2-1-1")
        self.assertEqual(records[0]["reference_id"], "PAY-9")
        self.assertEqual(records[0]["bank_amount"], "25.00")

    def test_extracts_pdf_table_and_writes_valid_csv(self):
        class FakePage:
            def extract_tables(self):
                return [[
                    ["Invoice No.", "Total Amount"],
                    ["INV-7", "$80.00"],
                ]]

            def extract_text(self):
                return ""

        class FakePdf:
            pages = [FakePage()]

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "invoices.csv"
            with patch("pdfplumber.open", return_value=FakePdf()):
                result = extract_pdf_to_csv(
                    Path(directory) / "source.pdf",
                    output_path,
                    "invoices",
                )

            self.assertEqual(result["row_count"], 1)
            self.assertFalse(result["ocr_used"])
            self.assertIn("INV-7", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
