
import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def generate_dataset(records: int, output_dir: Path, seed: int = 42) -> None:
    if records < 20:
        raise ValueError("Use at least 20 records to generate a useful test dataset.")

    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    invoice_rows = []
    payment_rows = []
    bank_rows = []
    truth_rows = []

    payment_ids = [f"PAY-{i:05d}" for i in range(1, records + 1)]

    # Select separate groups so each payment has one primary test condition.
    shuffled_ids = payment_ids.copy()
    rng.shuffle(shuffled_ids)

    missing_count = max(1, round(records * 0.08))
    mismatch_count = max(1, round(records * 0.07))
    duplicate_count = max(1, round(records * 0.05))

    missing_ids = set(shuffled_ids[:missing_count])
    mismatch_ids = set(
        shuffled_ids[missing_count:missing_count + mismatch_count]
    )
    duplicate_ids = set(
        shuffled_ids[
            missing_count + mismatch_count:
            missing_count + mismatch_count + duplicate_count
        ]
    )

    start_date = date(2026, 1, 1)

    for i, payment_id in enumerate(payment_ids, start=1):
        invoice_id = f"INV-{i:05d}"
        customer_id = f"CUST-{rng.randint(1, max(10, records // 3)):04d}"

        invoice_date = start_date + timedelta(days=rng.randint(0, 180))
        payment_date = invoice_date + timedelta(days=rng.randint(1, 10))
        amount = rng.randrange(5000, 50001, 100)

        invoice_rows.append({
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "invoice_amount": f"{amount:.2f}",
            "invoice_date": invoice_date.isoformat(),
            "due_date": (invoice_date + timedelta(days=30)).isoformat(),
        })

        payment_rows.append({
            "payment_id": payment_id,
            "invoice_id": invoice_id,
            "payment_amount": f"{amount:.2f}",
            "payment_date": payment_date.isoformat(),
            "payment_status": "SUCCESS",
        })

        expected_status = "MATCHED"
        bank_amount = amount

        if payment_id in missing_ids:
            expected_status = "MISSING_BANK"

        elif payment_id in mismatch_ids:
            expected_status = "AMOUNT_MISMATCH"
            difference = rng.choice([-1, 1]) * rng.randrange(100, 2001, 100)
            bank_amount = amount + difference

        elif payment_id in duplicate_ids:
            expected_status = "DUPLICATE_BANK"

        truth_rows.append({
            "payment_id": payment_id,
            "invoice_id": invoice_id,
            "expected_amount": f"{amount:.2f}",
            "expected_status": expected_status,
        })

        # Missing payments deliberately have no corresponding bank entry.
        if payment_id not in missing_ids:
            bank_txn_id = f"BNK-{i:05d}"

            bank_rows.append({
                "bank_txn_id": bank_txn_id,
                "reference_id": payment_id,
                "bank_amount": f"{bank_amount:.2f}",
                "transaction_date": payment_date.isoformat(),
                "transaction_type": "CREDIT",
                "duplicate_of": "",
            })

            # Add a second bank entry for selected payments.
            if payment_id in duplicate_ids:
                bank_rows.append({
                    "bank_txn_id": f"BNK-DUP-{i:05d}",
                    "reference_id": payment_id,
                    "bank_amount": f"{bank_amount:.2f}",
                    "transaction_date": payment_date.isoformat(),
                    "transaction_type": "CREDIT",
                    "duplicate_of": bank_txn_id,
                })

    write_csv(output_dir / "invoices.csv", invoice_rows)
    write_csv(output_dir / "payments.csv", payment_rows)
    write_csv(output_dir / "bank_transactions.csv", bank_rows)
    write_csv(output_dir / "ground_truth.csv", truth_rows)

    print("Dataset generated successfully.")
    print(f"Output directory: {output_dir.resolve()}")
    print(f"Invoices: {len(invoice_rows)}")
    print(f"Payments: {len(payment_rows)}")
    print(f"Bank transactions: {len(bank_rows)}")
    print(f"Missing bank records: {len(missing_ids)}")
    print(f"Amount mismatches: {len(mismatch_ids)}")
    print(f"Duplicate cases: {len(duplicate_ids)}")
    print(f"Expected matched cases: {records - len(missing_ids) - len(mismatch_ids) - len(duplicate_ids)}")
    print("Ground truth saved separately for later evaluation.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate synthetic finance reconciliation data."
    )
    parser.add_argument("--records", type=int, default=100)
    parser.add_argument("--output-dir", type=Path, default=Path("../../data"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generate_dataset(args.records, args.output_dir, args.seed)
