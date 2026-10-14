
from fastapi import FastAPI

app = FastAPI(
    title="AI Finance Controller",
    description="AI-powered financial reconciliation and exception resolution system",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "AI Finance Controller API",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
