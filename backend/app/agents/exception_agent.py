
import argparse
import csv
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:1b"

EXCEPTION_STATUSES = {
    "AMOUNT_MISMATCH",
    "DUPLICATE_BANK",
    "MISSING_BANK",
    "MISSING_INVOICE",
    "PAYMENT_INVOICE_MISMATCH",
    "INVALID_AMOUNT",
}


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def rule_based_analysis(record: dict) -> dict:
    """Safe fallback when the local LLM is unavailable."""
    status = record.get("status", "")
    difference = record.get("difference", "")
    payment_id = record.get("payment_id", "")

    explanations = {
        "AMOUNT_MISMATCH": (
            f"Payment {payment_id} does not agree with the bank amount. "
            f"The recorded difference is {difference}. Verify settlement "
            "fees, adjustments, and the original bank statement."
        ),
        "DUPLICATE_BANK": (
            f"Multiple bank entries reference payment {payment_id}. "
            "Check the original bank statement before treating any entry "
            "as a duplicate."
        ),
        "MISSING_BANK": (
            f"No bank transaction was found for payment {payment_id}. "
            "Check settlement timing, bank references, and the bank statement."
        ),
        "MISSING_INVOICE": (
            f"No corresponding invoice was found for payment {payment_id}. "
            "Verify the invoice identifier and source invoice records."
        ),
        "PAYMENT_INVOICE_MISMATCH": (
            f"The payment amount does not agree with the invoice amount "
            f"for {payment_id}. Verify both source records."
        ),
        "INVALID_AMOUNT": (
            f"At least one amount for {payment_id} is invalid. "
            "Check source data before reconciliation."
        ),
    }

    return {
        "payment_id": payment_id,
        "original_status": status,
        "analysis_method": "RULE_BASED",
        "explanation": explanations.get(
            status, "The exception needs further investigation."
        ),
        "recommended_action": record.get(
            "recommended_action", "Review source records."
        ),
        "priority": (
            "HIGH"
            if status in {"INVALID_AMOUNT", "DUPLICATE_BANK"}
            else "MEDIUM"
        ),
        "resolution_status": "HUMAN_REVIEW_REQUIRED",
    }


def ollama_analysis(record: dict, model: str) -> dict:
    """Ask a local Ollama model for a structured explanation."""
    evidence = {
        "payment_id": record.get("payment_id"),
        "invoice_id": record.get("invoice_id"),
        "invoice_amount": record.get("invoice_amount"),
        "payment_amount": record.get("payment_amount"),
        "bank_amount": record.get("bank_amount"),
        "difference": record.get("difference"),
        "status": record.get("status"),
        "reason_from_engine": record.get("reason"),
        "transaction_references": record.get("bank_transaction_ids"),
    }

    prompt = f"""
You are an assistant for finance exception investigation.

Explain the supplied reconciliation exception using only the evidence.
Do not invent transaction facts, claim money was recovered, or claim a
duplicate is confirmed unless the evidence proves it.
Do not change the reconciliation status.
Do not authorize payments, refunds, write-offs, or ledger adjustments.

Return JSON with exactly these string fields:
explanation, recommended_action, priority

priority must be LOW, MEDIUM, or HIGH.
Keep the explanation concise.
Recommend human verification for financial changes.

Evidence:
{json.dumps(evidence, ensure_ascii=False)}
"""

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8"))

    generated = json.loads(body["response"])

    explanation = generated.get("explanation")
    action = generated.get("recommended_action")
    priority = generated.get("priority")

    if not all(isinstance(value, str) and value.strip()
               for value in (explanation, action, priority)):
        raise ValueError("The model returned incomplete analysis.")

    priority = priority.strip().upper()
    if priority not in {"LOW", "MEDIUM", "HIGH"}:
        priority = "MEDIUM"

    return {
        "payment_id": record.get("payment_id", ""),
        # Always preserve the deterministic engine's status.
        "original_status": record.get("status", ""),
        "analysis_method": "OLLAMA",
        "explanation": explanation.strip(),
        "recommended_action": action.strip(),
        "priority": priority,
        # AI analysis never automatically changes financial records.
        "resolution_status": "HUMAN_REVIEW_REQUIRED",
    }


def analyze_exceptions(
    input_path: Path,
    output_path: Path,
    use_ollama: bool = True,
    model: str = DEFAULT_MODEL,
) -> list[dict]:
    records = read_csv(input_path)
    exceptions = [
        row for row in records
        if row.get("status") in EXCEPTION_STATUSES
    ]

    analyses = []

    for index, record in enumerate(exceptions, start=1):
        print(
            f"Analyzing exception {index}/{len(exceptions)}: "
            f"{record.get('payment_id')}"
        )

        analysis = None

        if use_ollama:
            try:
                analysis = ollama_analysis(record, model)
            except (
                urllib.error.URLError,
                TimeoutError,
                ValueError,
                KeyError,
                json.JSONDecodeError,
            ) as error:
                print(f"LLM unavailable or invalid response: {error}")

        if analysis is None:
            analysis = rule_based_analysis(record)

        analyses.append(analysis)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "payment_id",
        "original_status",
        "analysis_method",
        "explanation",
        "recommended_action",
        "priority",
        "resolution_status",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(analyses)

    method_counts = {}
    for item in analyses:
        method = item["analysis_method"]
        method_counts[method] = method_counts.get(method, 0) + 1

    print("\n=== EXCEPTION ANALYSIS SUMMARY ===")
    print(f"Exceptions analyzed: {len(analyses)}")
    print(f"Analysis methods: {method_counts}")
    print(f"Human review required: {len(analyses)}")
    print(f"Output: {output_path.resolve()}")

    return analyses


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Explain finance exceptions using Ollama or rule-based fallback."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("../../data/results/reconciliation_results.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../../data/results/exception_analysis.csv"),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OLLAMA_MODEL", DEFAULT_MODEL),
    )
    parser.add_argument(
        "--rules-only",
        action="store_true",
        help="Disable Ollama and use deterministic explanations.",
    )
    args = parser.parse_args()

    analyze_exceptions(
        input_path=args.input,
        output_path=args.output,
        use_ollama=not args.rules_only,
        model=args.model,
    )
