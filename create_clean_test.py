
import csv
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_ROOT / "data" / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "data" / "clean_test"

REQUIRED_FILES = [
    "invoices.csv",
    "payments.csv",
    "bank_transactions.csv",
]


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"No rows available to write: {path.name}")

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    for filename in REQUIRED_FILES:
        if not (SOURCE_DIR / filename).is_file():
            raise FileNotFoundError(
                f"Required uploaded file is missing: {SOURCE_DIR / filename}"
            )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Read copies from the current uploads.
    invoices = read_csv(SOURCE_DIR / "invoices.csv")
    payments = read_csv(SOURCE_DIR / "payments.csv")
    banks = read_csv(SOURCE_DIR / "bank_transactions.csv")

    payment_by_id = {
        row["payment_id"]: row
        for row in payments
        if row.get("payment_id")
    }

    # Make invoice amounts agree with their linked payments.
    payment_by_invoice = {
        row["invoice_id"]: row
        for row in payments
        if row.get("invoice_id")
    }

    for invoice in invoices:
        payment = payment_by_invoice.get(invoice.get("invoice_id"))
        if payment:
            invoice["invoice_amount"] = payment["payment_amount"]

    # Build one valid bank transaction for every payment.
    # This is synthetic test data, not a correction to real bank records.
    clean_banks = []
    seen_payments = set()

    for index, payment in enumerate(payments, start=1):
        payment_id = payment.get("payment_id", "").strip()

        if not payment_id or payment_id in seen_payments:
            raise ValueError(
                f"Missing or duplicate payment_id: {payment_id!r}"
            )

        seen_payments.add(payment_id)

        clean_banks.append({
            "bank_txn_id": f"CLEAN-BNK-{index:05d}",
            "reference_id": payment_id,
            "bank_amount": payment["payment_amount"],
            "transaction_date": payment.get("payment_date", ""),
            "transaction_type": "CREDIT",
            "duplicate_of": "",
        })

    write_csv(OUTPUT_DIR / "invoices.csv", invoices)
    write_csv(OUTPUT_DIR / "payments.csv", payments)
    write_csv(OUTPUT_DIR / "bank_transactions.csv", clean_banks)

    print("Clean synthetic test datasets created.")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Invoices: {len(invoices)}")
    print(f"Payments: {len(payments)}")
    print(f"Bank transactions: {len(clean_banks)}")
    print("Original uploaded files were not modified.")


if __name__ == "__main__":
    main()
