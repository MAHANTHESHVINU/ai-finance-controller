
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


# --------------------------------------------------
# CSV helpers
# --------------------------------------------------

def read_csv(path: Path) -> list[dict]:
    """Read CSV rows as dictionaries with normalized headers."""

    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(f"{path.name} has no header row.")

        rows = []

        for row in reader:
            normalized = {
                str(key).strip().lower(): (
                    value.strip() if isinstance(value, str) else value
                )
                for key, value in row.items()
                if key is not None
            }

            # Ignore completely empty lines.
            if any(value not in ("", None) for value in normalized.values()):
                rows.append(normalized)

        return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write dictionaries to CSV, including headers for empty results."""

    path.parent.mkdir(parents=True, exist_ok=True)

    default_columns = [
        "payment_id",
        "invoice_id",
        "invoice_amount",
        "payment_amount",
        "bank_amount",
        "invoice_date",
        "due_date",
        "payment_date",
        "bank_txn_id",
        "transaction_date",
        "status",
        "exception_reason",
        "amount_difference",
    ]

    columns = list(rows[0].keys()) if rows else default_columns

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


# --------------------------------------------------
# Monetary helpers
# --------------------------------------------------

CENT = Decimal("0.01")


def money(value) -> Decimal | None:
    """
    Convert a value to a two-decimal Decimal.
    Return None for missing or invalid amounts.
    """

    if value is None or str(value).strip() == "":
        return None

    try:
        amount = Decimal(str(value).strip())

        if not amount.is_finite():
            return None

        return amount.quantize(CENT, rounding=ROUND_HALF_UP)

    except (InvalidOperation, ValueError, TypeError):
        return None


def money_text(value: Decimal | None) -> str:
    """Format an amount for CSV output."""

    if value is None:
        return ""

    return f"{value:.2f}"


# --------------------------------------------------
# Reconciliation engine
# --------------------------------------------------

def reconcile(data_dir: Path, output_dir: Path) -> dict:
    """
    Reconcile invoices, payments and bank transactions.

    Matching rules:
    1. Link a payment to its invoice through invoice_id.
    2. Link bank transactions through reference_id == payment_id.
    3. Flag missing invoices and invalid amounts.
    4. Flag missing or duplicated bank transactions.
    5. Compare invoice, payment and bank amounts to two decimals.
    6. Calculate all metrics from actual results.
    """

    invoices = read_csv(data_dir / "invoices.csv")
    payments = read_csv(data_dir / "payments.csv")
    bank_transactions = read_csv(data_dir / "bank_transactions.csv")

    # --------------------------------------------------
    # Index invoices and payments
    # --------------------------------------------------

    invoice_by_id = {}

    for invoice in invoices:
        invoice_id = invoice.get("invoice_id", "").strip()

        if not invoice_id:
            continue

        if invoice_id in invoice_by_id:
            raise ValueError(
                f"Duplicate invoice_id found: {invoice_id}. "
                "Resolve duplicate invoice records before reconciliation."
            )

        invoice_by_id[invoice_id] = invoice

    payment_ids = [
        payment.get("payment_id", "").strip()
        for payment in payments
    ]

    nonempty_payment_ids = [value for value in payment_ids if value]

    if len(nonempty_payment_ids) != len(set(nonempty_payment_ids)):
        raise ValueError(
            "Duplicate payment_id found. "
            "Each payment must have a unique payment_id."
        )

    # --------------------------------------------------
    # Index bank transactions by payment reference
    # --------------------------------------------------

    bank_by_reference = defaultdict(list)

    for bank_row in bank_transactions:
        reference_id = bank_row.get("reference_id", "").strip()

        if reference_id:
            bank_by_reference[reference_id].append(bank_row)

    # Also track bank transaction IDs to detect malformed input.
    bank_ids = [
        row.get("bank_txn_id", "").strip()
        for row in bank_transactions
    ]

    nonempty_bank_ids = [value for value in bank_ids if value]

    if len(nonempty_bank_ids) != len(set(nonempty_bank_ids)):
        raise ValueError(
            "Duplicate bank_txn_id found. "
            "Each bank transaction must have a unique bank_txn_id."
        )

    # --------------------------------------------------
    # Reconcile each payment
    # --------------------------------------------------

    results = []

    for payment in payments:
        payment_id = payment.get("payment_id", "").strip()
        invoice_id = payment.get("invoice_id", "").strip()

        invoice = invoice_by_id.get(invoice_id)

        invoice_amount = (
            money(invoice.get("invoice_amount"))
            if invoice
            else None
        )

        payment_amount = money(payment.get("payment_amount"))

        bank_matches = bank_by_reference.get(payment_id, [])

        bank_row = bank_matches[0] if bank_matches else None

        bank_amount = (
            money(bank_row.get("bank_amount"))
            if bank_row
            else None
        )

        # Start with an explicit, auditable classification.
        status = ""
        reasons = []

        # 1. A payment without an invoice cannot be reconciled.
        if not invoice:
            status = "MISSING_INVOICE"
            reasons.append(f"No invoice found for invoice_id={invoice_id!r}")

        # 2. Missing or malformed payment/invoice amounts.
        elif payment_amount is None or invoice_amount is None:
            status = "INVALID_AMOUNT"
            reasons.append(
                "Invoice amount or payment amount is missing or invalid"
            )

        # 3. Identify multiple bank rows linked to one payment.
        elif len(bank_matches) > 1:
            status = "DUPLICATE_BANK"
            reasons.append(
                f"{len(bank_matches)} bank transactions reference "
                f"payment_id={payment_id!r}"
            )

        # 4. Check for a bank row explicitly marked as a duplicate.
        elif bank_row and bank_row.get("duplicate_of", "").strip():
            status = "DUPLICATE_BANK"
            reasons.append(
                "Bank transaction is marked as a duplicate "
                f"of {bank_row.get('duplicate_of', '').strip()!r}"
            )

        # 5. A bank transaction is required for a full match.
        elif not bank_row:
            status = "MISSING_BANK"
            reasons.append(
                f"No bank transaction references payment_id={payment_id!r}"
            )

        # 6. Validate bank amount.
        elif bank_amount is None:
            status = "INVALID_AMOUNT"
            reasons.append("Bank amount is missing or invalid")

        # 7. Compare the payment with its invoice.
        elif invoice_amount != payment_amount:
            status = "AMOUNT_MISMATCH"
            reasons.append(
                "Invoice amount differs from payment amount"
            )

        # 8. Compare the payment with the bank transaction.
        elif payment_amount != bank_amount:
            status = "AMOUNT_MISMATCH"
            reasons.append(
                "Payment amount differs from bank amount"
            )

        # 9. All required records and amounts agree.
        else:
            status = "MATCHED"
            reasons.append(
                "Invoice, payment and bank amounts agree"
            )

        # Calculate a useful amount difference for investigation.
        amount_difference = ""

        if payment_amount is not None and bank_amount is not None:
            amount_difference = money_text(bank_amount - payment_amount)
        elif invoice_amount is not None and payment_amount is not None:
            amount_difference = money_text(payment_amount - invoice_amount)

        results.append(
            {
                "payment_id": payment_id,
                "invoice_id": invoice_id,
                "invoice_amount": money_text(invoice_amount),
                "payment_amount": money_text(payment_amount),
                "bank_amount": money_text(bank_amount),
                "invoice_date": invoice.get("invoice_date", "") if invoice else "",
                "due_date": invoice.get("due_date", "") if invoice else "",
                "payment_date": payment.get("payment_date", ""),
                "bank_txn_id": bank_row.get("bank_txn_id", "") if bank_row else "",
                "transaction_date": (
                    bank_row.get("transaction_date", "")
                    if bank_row else ""
                ),
                "status": status,
                "exception_reason": "; ".join(reasons),
                "amount_difference": amount_difference,
            }
        )

    # --------------------------------------------------
    # Calculate metrics from actual reconciliation results
    # --------------------------------------------------

    status_counts = Counter(row["status"] for row in results)

    total_payments = len(results)
    matched = status_counts.get("MATCHED", 0)
    exceptions = total_payments - matched

    match_rate = (
        round(matched / total_payments * 100, 2)
        if total_payments
        else 0.0
    )

    exception_rate = (
        round(exceptions / total_payments * 100, 2)
        if total_payments
        else 0.0
    )

    metrics = {
        "total_invoices": len(invoices),
        "total_payments": total_payments,
        "bank_transaction_rows": len(bank_transactions),
        "matched": matched,
        "exceptions": exceptions,
        "match_rate_percent": match_rate,
        "exception_rate_percent": exception_rate,
        "status_counts": dict(status_counts),
    }

    # --------------------------------------------------
    # Save reconciliation results and metrics
    # --------------------------------------------------

    output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        output_dir / "reconciliation_results.csv",
        results,
    )

    with (output_dir / "metrics.json").open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(metrics, file, indent=4)

    return metrics


# --------------------------------------------------
# Optional command-line execution
# --------------------------------------------------

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[3]
    data_dir = project_root / "data"
    output_dir = data_dir / "results"

    result = reconcile(data_dir, output_dir)
    print(json.dumps(result, indent=4))
