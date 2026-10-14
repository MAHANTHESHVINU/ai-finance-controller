
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def safe_divide(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def evaluate(data_dir: Path, results_dir: Path) -> dict:
    truth_rows = read_csv(data_dir / "ground_truth.csv")
    predicted_rows = read_csv(results_dir / "reconciliation_results.csv")

    truth = {row["payment_id"]: row["expected_status"] for row in truth_rows}
    predicted = {row["payment_id"]: row["status"] for row in predicted_rows}

    if len(truth) != len(truth_rows):
        raise ValueError("Duplicate payment IDs found in ground_truth.csv.")

    if len(predicted) != len(predicted_rows):
        raise ValueError("Duplicate payment IDs found in reconciliation_results.csv.")

    if set(truth) != set(predicted):
        missing_predictions = sorted(set(truth) - set(predicted))
        unexpected_predictions = sorted(set(predicted) - set(truth))
        raise ValueError(
            "Payment IDs do not match.\n"
            f"Missing predictions: {missing_predictions[:10]}\n"
            f"Unexpected predictions: {unexpected_predictions[:10]}"
        )

    labels = sorted(set(truth.values()) | set(predicted.values()))
    total = len(truth)

    correct = sum(truth[payment_id] == predicted[payment_id] for payment_id in truth)
    accuracy = safe_divide(correct, total)

    # Multiclass confusion matrix: rows are actual labels; columns are predictions.
    matrix = {
        actual: {
            prediction: sum(
                truth[payment_id] == actual
                and predicted[payment_id] == prediction
                for payment_id in truth
            )
            for prediction in labels
        }
        for actual in labels
    }

    per_class = {}

    for label in labels:
        true_positive = matrix[label][label]
        false_positive = sum(
            matrix[actual][label] for actual in labels if actual != label
        )
        false_negative = sum(
            matrix[label][prediction]
            for prediction in labels
            if prediction != label
        )

        precision = safe_divide(
            true_positive, true_positive + false_positive
        )
        recall = safe_divide(
            true_positive, true_positive + false_negative
        )
        f1 = safe_divide(
            2 * precision * recall, precision + recall
        )

        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "support": sum(matrix[label].values()),
        }

    # Binary evaluation: MATCHED versus any exception.
    actual_exception_ids = {
        payment_id for payment_id, status in truth.items()
        if status != "MATCHED"
    }
    predicted_exception_ids = {
        payment_id for payment_id, status in predicted.items()
        if status != "MATCHED"
    }

    tp = len(actual_exception_ids & predicted_exception_ids)
    fp = len(predicted_exception_ids - actual_exception_ids)
    fn = len(actual_exception_ids - predicted_exception_ids)
    tn = total - tp - fp - fn

    exception_metrics = {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": safe_divide(tp, tp + fp),
        "recall": safe_divide(tp, tp + fn),
        "f1_score": safe_divide(
            2 * safe_divide(tp, tp + fp) * safe_divide(tp, tp + fn),
            safe_divide(tp, tp + fp) + safe_divide(tp, tp + fn),
        ),
    }

    comparison_rows = [
        {
            "payment_id": payment_id,
            "expected_status": truth[payment_id],
            "predicted_status": predicted[payment_id],
            "correct": truth[payment_id] == predicted[payment_id],
        }
        for payment_id in sorted(truth)
    ]

    results_dir.mkdir(parents=True, exist_ok=True)

    with (results_dir / "evaluation_comparison.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=comparison_rows[0].keys())
        writer.writeheader()
        writer.writerows(comparison_rows)

    report = {
        "total_records": total,
        "correct_predictions": correct,
        "incorrect_predictions": total - correct,
        "classification_accuracy": accuracy,
        "classification_accuracy_percent": round(accuracy * 100, 2),
        "actual_status_counts": dict(Counter(truth.values())),
        "predicted_status_counts": dict(Counter(predicted.values())),
        "per_class_metrics": per_class,
        "exception_detection": exception_metrics,
        "confusion_matrix": matrix,
        "note": (
            "Results measure performance on this controlled synthetic dataset. "
            "They do not establish real-world production accuracy."
        ),
    }

    with (results_dir / "evaluation_report.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=2)

    print("\n=== EVALUATION REPORT ===")
    print(f"Records evaluated       : {total}")
    print(f"Correct predictions     : {correct}")
    print(f"Incorrect predictions   : {total - correct}")
    print(f"Classification accuracy : {accuracy * 100:.2f}%")
    print("\nException detection:")
    print(f"  Precision             : {exception_metrics['precision']:.2%}")
    print(f"  Recall                : {exception_metrics['recall']:.2%}")
    print(f"  F1 score              : {exception_metrics['f1_score']:.2%}")
    print("\nPer-class metrics:")

    for label, metrics in per_class.items():
        print(
            f"  {label}: "
            f"precision={metrics['precision']:.2%}, "
            f"recall={metrics['recall']:.2%}, "
            f"F1={metrics['f1_score']:.2%}, "
            f"support={metrics['support']}"
        )

    print(f"\nReport: {results_dir / 'evaluation_report.json'}")
    print(f"Comparison: {results_dir / 'evaluation_comparison.csv'}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate reconciliation predictions against ground truth."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("../../data"))
    parser.add_argument(
        "--results-dir", type=Path, default=Path("../../data/results")
    )
    args = parser.parse_args()

    evaluate(args.data_dir, args.results_dir)
