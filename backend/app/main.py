import os
import csv
import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from app.agents.exception_agent import analyze_exceptions
from app.reconciliation.engine import reconcile
from app.services.file_validator import validate_csv


# --------------------------------------------------
# Application configuration
# --------------------------------------------------

app = FastAPI(
    title="AI Finance Controller",
    description=(
        "AI-powered financial reconciliation, "
        "exception detection, and analysis."
    ),
    version="0.2.0",
)


# --------------------------------------------------
# CORS configuration
# --------------------------------------------------

# Set FRONTEND_ORIGINS on the hosting platform to your deployed frontend URL.
# Multiple origins may be comma-separated.
frontend_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

allowed_origins = list(
    dict.fromkeys(
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            *frontend_origins,
        ]
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Project paths
# main.py is located in backend/app/main.py.
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

RESULTS_DIR = DATA_DIR / "results"
UPLOADED_RESULTS_DIR = RESULTS_DIR / "uploaded"
CLEAN_TEST_DIR = DATA_DIR / "clean_test"
CLEAN_TEST_RESULTS_DIR = RESULTS_DIR / "clean_test"


# --------------------------------------------------
# CSV helper
# --------------------------------------------------

def read_csv(path: Path) -> list[dict]:
    """Read a CSV file and return its rows as dictionaries."""

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                f"{path.name} not found. "
                "Run the required operation first."
            ),
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        return list(csv.DictReader(file))


# --------------------------------------------------
# Basic endpoints
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "AI Finance Controller API",
        "status": "running",
        "version": "0.2.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


# --------------------------------------------------
# Reconciliation endpoint
# Supports original and uploaded datasets.
# Results are saved in separate directories.
# --------------------------------------------------

@app.post("/api/reconcile")
def run_reconciliation(source: str = "original"):

    if source not in {"original", "uploaded", "clean_test"}:
        raise HTTPException(
            status_code=400,
            detail="Source must be 'original', 'uploaded', or 'clean_test'.",
        )

    if source == "original":
        input_dir = DATA_DIR
        output_dir = RESULTS_DIR
    elif source == "uploaded":
        input_dir = UPLOAD_DIR
        output_dir = UPLOADED_RESULTS_DIR
    else:
        input_dir = CLEAN_TEST_DIR
        output_dir = CLEAN_TEST_RESULTS_DIR

    if source in {"uploaded", "clean_test"}:
        required_files = [
            "invoices.csv",
            "payments.csv",
            "bank_transactions.csv",
        ]

        missing_files = [
            filename
            for filename in required_files
            if not (input_dir / filename).is_file()
        ]

        if missing_files:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Required files are missing for '{source}'. "
                    "Missing: " + ", ".join(missing_files)
                ),
            )

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        metrics = reconcile(
            input_dir,
            output_dir,
        )

        return {
            "message": "Reconciliation completed successfully.",
            "source": source,
            "metrics": metrics,
        }

    except HTTPException:
        raise

    except (FileNotFoundError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Reconciliation failed: {exc}",
        ) from exc


# --------------------------------------------------
# Metrics endpoint
# Reads original or uploaded reconciliation metrics.
# --------------------------------------------------

@app.get("/api/metrics")
def get_metrics(source: str = "original"):

    if source == "original":
        metrics_file = RESULTS_DIR / "metrics.json"

    elif source == "uploaded":
        metrics_file = UPLOADED_RESULTS_DIR / "metrics.json"

    elif source == "clean_test":
        metrics_file = CLEAN_TEST_RESULTS_DIR / "metrics.json"

    else:
        raise HTTPException(
            status_code=400,
            detail="Source must be 'original', 'uploaded', or 'clean_test'.",
        )

    if not metrics_file.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "Metrics not found for this source. "
                "Run reconciliation first."
            ),
        )

    try:
        with metrics_file.open("r", encoding="utf-8") as file:
            return json.load(file)

    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read reconciliation metrics.",
        ) from exc


# --------------------------------------------------
# Reconciliation results endpoint
# --------------------------------------------------

@app.get("/api/reconciliation")
def get_reconciliation_results(source: str = "original"):

    if source == "original":
        results_file = RESULTS_DIR / "reconciliation_results.csv"

    elif source == "uploaded":
        results_file = (
            UPLOADED_RESULTS_DIR / "reconciliation_results.csv"
        )

    elif source == "clean_test":
        results_file = CLEAN_TEST_RESULTS_DIR / "reconciliation_results.csv"

    else:
        raise HTTPException(
            status_code=400,
            detail="Source must be 'original', 'uploaded', or 'clean_test'.",
        )

    return read_csv(results_file)


# --------------------------------------------------
# AI exception analysis endpoint
# Analyzes the selected reconciliation results.
# --------------------------------------------------

@app.post("/api/analyze-exceptions")
def run_exception_analysis(source: str = "original"):

    if source == "original":
        results_file = RESULTS_DIR / "reconciliation_results.csv"
        output_file = RESULTS_DIR / "exception_analysis.csv"

    elif source == "uploaded":
        results_file = (
            UPLOADED_RESULTS_DIR / "reconciliation_results.csv"
        )
        output_file = (
            UPLOADED_RESULTS_DIR / "exception_analysis.csv"
        )

    elif source == "clean_test":
        results_file = CLEAN_TEST_RESULTS_DIR / "reconciliation_results.csv"
        output_file = CLEAN_TEST_RESULTS_DIR / "exception_analysis.csv"

    else:
        raise HTTPException(
            status_code=400,
            detail="Source must be 'original', 'uploaded', or 'clean_test'.",
        )

    if not results_file.is_file():
        raise HTTPException(
            status_code=404,
            detail="Run reconciliation before analyzing exceptions.",
        )

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)

        analyses = analyze_exceptions(
            input_path=results_file,
            output_path=output_file,
            use_ollama=True,
        )

        return {
            "message": "Exception analysis completed.",
            "source": source,
            "total_analyzed": len(analyses),
            "results": analyses,
        }

    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Exception analysis failed: {exc}",
        ) from exc
    except Exception as exc:
        # Keep provider/network details in server logs, not in the API response.
        print(f"Exception analysis provider error: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=502,
            detail=(
                "Exception analysis provider failed. "
                "Check backend logs and AI service availability."
            ),
        ) from exc


# --------------------------------------------------
# AI exception results endpoint
# --------------------------------------------------

@app.get("/api/exceptions")
def get_exceptions(source: str = "original"):

    if source == "original":
        exceptions_file = RESULTS_DIR / "exception_analysis.csv"

    elif source == "uploaded":
        exceptions_file = (
            UPLOADED_RESULTS_DIR / "exception_analysis.csv"
        )

    elif source == "clean_test":
        exceptions_file = CLEAN_TEST_RESULTS_DIR / "exception_analysis.csv"

    else:
        raise HTTPException(
            status_code=400,
            detail="Source must be 'original', 'uploaded', or 'clean_test'.",
        )

    return read_csv(exceptions_file)


# --------------------------------------------------
# CSV upload endpoint
# Validates and saves the three required datasets.
# --------------------------------------------------

@app.post("/api/upload-csv")
async def upload_csv(
    dataset_type: str = Form(...),
    file: UploadFile = File(...),
):

    allowed_types = {
        "invoices",
        "payments",
        "bank_transactions",
    }

    if dataset_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid dataset type. Choose invoices, "
                "payments, or bank_transactions."
            ),
        )

    if (
        not file.filename
        or not file.filename.lower().endswith(".csv")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = UPLOAD_DIR / f"{dataset_type}.csv"

    temporary = UPLOAD_DIR / (
        f".{dataset_type}_{uuid4().hex}.tmp"
    )

    try:
        # Save to a temporary file before validation.
        with temporary.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Validate required columns and amount values.
        validation_result = validate_csv(
            temporary,
            dataset_type,
        )

        # Replace the previous upload only after validation succeeds.
        temporary.replace(destination)

        return {
            "message": "CSV validated and saved successfully.",
            "filename": file.filename,
            "saved_as": destination.name,
            **validation_result,
        }

    except ValueError as exc:
        temporary.unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        temporary.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Could not process the uploaded CSV.",
        ) from exc

    finally:
        await file.close()
