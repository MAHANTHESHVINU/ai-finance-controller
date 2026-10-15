
from pathlib import Path
import pandas as pd


REQUIRED_COLUMNS = {
    "invoices": {
        "invoice_id",
        "customer_id",
        "invoice_amount",
        "invoice_date",
        "due_date",
    },
    "payments": {
        "payment_id",
        "invoice_id",
        "payment_amount",
        "payment_date",
        "payment_status",
    },
    "bank_transactions": {
        "bank_txn_id",
        "reference_id",
        "bank_amount",
        "transaction_date",
        "transaction_type",
        "duplicate_of",
    },
}


AMOUNT_COLUMNS = {
    "invoices": "invoice_amount",
    "payments": "payment_amount",
    "bank_transactions": "bank_amount",
}


def validate_csv(file_path: Path, dataset_type: str) -> dict:
    """Validate an uploaded CSV against the project's data schema."""

    if dataset_type not in REQUIRED_COLUMNS:
        raise ValueError(
            "Unsupported dataset type. Use invoices, payments, "
            "or bank_transactions."
        )

    try:
        df = pd.read_csv(file_path)
    except Exception as exc:
        raise ValueError(f"Could not read CSV: {exc}") from exc

    if df.empty:
        raise ValueError("The CSV file is empty.")

    df.columns = df.columns.str.strip().str.lower()

    if df.columns.duplicated().any():
        raise ValueError("Duplicate column names were found.")

    missing = REQUIRED_COLUMNS[dataset_type] - set(df.columns)

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    amount_column = AMOUNT_COLUMNS[dataset_type]
    amounts = pd.to_numeric(df[amount_column], errors="coerce")

    if amounts.isna().any():
        raise ValueError(
            f"Column '{amount_column}' contains invalid or empty amounts."
        )

    if (amounts < 0).any():
        raise ValueError(
            f"Column '{amount_column}' cannot contain negative values."
        )

    return {
        "dataset_type": dataset_type,
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "valid": True,
    }
