
import csv
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.agents.exception_agent import analyze_exceptions
from app.reconciliation.engine import reconcile

app = FastAPI(
    title="AI Finance Controller",
    description="Financial reconciliation and AI-powered exception analysis",
    version="0.2.0",
)

# Resolve paths from this file, not from the terminal's working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = DATA_DIR / "results"

RECONCILIATION_FILE = RESULTS_DIR / "reconciliation_results.csv"
METRICS_FILE = RESULTS_DIR / "metrics.json"
EXCEPTIONS_FILE = RESULTS_DIR / "exception_analysis.csv"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Results not found: {path.name}. Run reconciliation first.",
        )

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


@app.get("/")
def root():
    return {
        "message": "AI Finance Controller API",
        "status": "running",
        "version": "0.2.0",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/reconcile")
def run_reconciliation():
    try:
        metrics = reconcile(DATA_DIR, RESULTS_DIR)
        return {
            "message": "Reconciliation completed",
            "metrics": metrics,
        }
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/metrics")
def get_metrics():
    if not METRICS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Metrics not found. Run reconciliation first.",
        )

    with METRICS_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


@app.get("/api/reconciliation")
def get_reconciliation_results():
    return read_csv(RECONCILIATION_FILE)


@app.post("/api/analyze-exceptions")
def run_exception_analysis():
    if not RECONCILIATION_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Run reconciliation before analyzing exceptions.",
        )

    try:
        analyses = analyze_exceptions(
            input_path=RECONCILIATION_FILE,
            output_path=EXCEPTIONS_FILE,
            use_ollama=True,
        )
        return {
            "message": "Exception analysis completed",
            "total_analyzed": len(analyses),
            "results": analyses,
        }
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/exceptions")
def get_exceptions():
    return read_csv(EXCEPTIONS_FILE)
