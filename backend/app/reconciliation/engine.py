
import argparse
import csv
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


MATCHED = "MATCHED"
AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
MISSING_BANK = "MISSING_BANK"
DUPLICATE_BANK = "DUPLICATE_BANK"
MISSING_INVOICE = "MISSING_INVOICE"
PAYMENT_MISMATCH = "PAYMENT_INVOICE_MISMATCH"
INVALID_AMOUNT = "INVALID_AMOUNT"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def money(value: str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def reconcile(data_dir: Path, output_dir: Path) -> dict:
    invoices = read_csv(data_dir / "invoices.csv")
    payments = read_csv(data_dir / "payments.csv")
    bank_transactions = read_csv(data_dir / "bank_transactions.csv")

    invoice_by_id = {row["invoice_id"]: row for row in invoices}

    # Group bank records by payment reference.
    bank_by_reference = defaultdict(list)
    for row in bank_transactions:
        reference = row.get("reference_id", "").strip()
        if reference:
            bank_by_reference[reference].append(row)

    results = []

    for payment in payments:
        payment_id = payment["payment_id"]
        invoice_id = payment["invoice_id"]
        invoice = invoice_by_id.get(invoice_id)
        bank_rows = bank_by_reference.get(payment_id, [])

        result = {
            "payment_id": payment_id,
            "invoice_id": invoice_id,
            "invoice_amount": "",
            "payment_amount": payment.get("payment_amount", ""),
            "bank_amount": "",
            "bank_transaction_ids": ";".join(
                row["bank_txn_id"] for row in bank_rows
            ),
            "difference": "",
            "status": "",
            "reason": "",
            "auto_resolvable": "NO",
            "recommended_action": "REVIEW",
        }

        if invoice is None:
            result.update({
                "status": MISSING_INVOICE,
                "reason": "No invoice exists for this payment's invoice ID.",
                "recommended_action": "Locate or create the correct invoice.",
            })
            results.append(result)
            continue

        result["invoice_amount"] = invoice.get("invoice_amount", "")

        try:
            invoice_amount = money(invoice["invoice_amount"])
            payment_amount = money(payment["payment_amount"])

            if not invoice_amount.is_finite() or not payment_amount.is_finite():
                raise InvalidOperation

            if invoice_amount <= 0 or payment_amount <= 0:
                raise InvalidOperation

            bank_amounts = [money(row["bank_amount"]) for row in bank_rows]

            if any(not amount.is_finite() or amount <= 0 for amount in bank_amounts):
                raise InvalidOperation

        except (InvalidOperation, ValueError, TypeError):
            result.update({
                "status": INVALID_AMOUNT,
                "reason": "An invoice, payment, or bank amount is invalid.",
                "recommended_action": "Correct the source financial data.",
            })
            results.append(result)
            continue

        if payment_amount != invoice_amount:
            result.update({
                "status": PAYMENT_MISMATCH,
                "reason": (
                    f"Payment amount {payment_amount:.2f} differs from "
                    f"invoice amount {invoice_amount:.2f}."
                ),
                "recommended_action": "Review payment and invoice records.",
            })
            results.append(result)
            continue

        if not bank_rows:
            result.update({
                "status": MISSING_BANK,
                "reason": "No bank transaction references this payment.",
                "recommended_action": "Check bank statement and settlement timing.",
            })
            results.append(result)
            continue

        if len(bank_rows) > 1:
            result.update({
                "bank_amount": f"{sum(bank_amounts, Decimal('0.00')):.2f}",
                "difference": f"{sum(bank_amounts, Decimal('0.00')) - payment_amount:.2f}",
                "status": DUPLICATE_BANK,
                "reason": (
                    f"{len(bank_rows)} bank entries reference the same payment."
                ),
                "recommended_action": "Verify duplicate entries before adjustment.",
            })
            results.append(result)
            continue

        bank_amount = bank_amounts[0]
        result["bank_amount"] = f"{bank_amount:.2f}"
        difference = bank_amount - payment_amount
        result["difference"] = f"{difference:.2f}"

        if difference != Decimal("0.00"):
            result.update({
                "status": AMOUNT_MISMATCH,
                "reason": (
                    f"Bank amount differs from payment amount by "
                    f"{difference:.2f}."
                ),
                "recommended_action": "Investigate the amount discrepancy.",
            })
        else:
            result.update({
                "status": MATCHED,
                "reason": "Invoice, payment, and bank amounts agree.",
                "auto_resolvable": "YES",
                "recommended_action": "No action required.",
            })

        results.append(result)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "reconciliation_results.csv", results)

    total = len(results)
    counts = defaultdict(int)
    for result in results:
        counts[result["status"]] += 1

    matched = counts[MATCHED]
    exceptions = total - matched

    # These metrics are based on payment records, not raw bank-row counts.
    metrics = {
        "total_payments": total,
        "matched": matched,
        "exceptions": exceptions,
        "match_rate_percent": round(matched / total * 100, 2) if total else 0,
        "exception_rate_percent": round(exceptions / total * 100, 2) if total else 0,
        "status_counts": dict(sorted(counts.items())),
        "bank_transaction_rows": len(bank_transactions),
    }

    with (output_dir / "metrics.json").open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    print("\n=== RECONCILIATION SUMMARY ===")
    print(f"Payments processed : {total}")
    print(f"Matched            : {matched}")
    print(f"Exceptions         : {exceptions}")
    print(f"Match rate         : {metrics['match_rate_percent']}%")
    print(f"Exception rate     : {metrics['exception_rate_percent']}%")

    print("\nStatus breakdown:")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

    print(f"\nResults: {output_dir / 'reconciliation_results.csv'}")
    print(f"Metrics: {output_dir / 'metrics.json'}")

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reconcile invoices, payments, and bank transactions."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("../../data"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("../../data/results")
    )
    args = parser.parse_args()

    reconcile(args.data_dir, args.output_dir)
