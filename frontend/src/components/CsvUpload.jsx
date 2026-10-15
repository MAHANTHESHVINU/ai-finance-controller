
import { useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

export default function CsvUpload() {
  const [datasetType, setDatasetType] = useState("invoices");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function handleUpload(event) {
    event.preventDefault();

    if (!file) {
      setError("Please select a CSV file.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("dataset_type", datasetType);
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE}/api/upload-csv`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setResult(data);
      setFile(null);
      event.target.reset();
      setDatasetType("invoices");
    } catch (err) {
      setError(err.message || "Unable to connect to the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="csv-upload-panel">
      <h2>Upload Financial Data</h2>
      <p>
        Upload a CSV file to validate its structure before reconciliation.
      </p>

      <form onSubmit={handleUpload} className="csv-upload-form">
        <label htmlFor="dataset-type">Dataset type</label>
        <select
          id="dataset-type"
          value={datasetType}
          onChange={(event) => setDatasetType(event.target.value)}
        >
          <option value="invoices">Invoices</option>
          <option value="payments">Payments</option>
          <option value="bank_transactions">Bank Transactions</option>
        </select>

        <label htmlFor="csv-file">CSV file</label>
        <input
          id="csv-file"
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => {
            setFile(event.target.files?.[0] || null);
            setResult(null);
            setError("");
          }}
        />

        <button type="submit" disabled={loading}>
          {loading ? "Validating..." : "Upload and Validate"}
        </button>
      </form>

      {error && (
        <div className="upload-error" role="alert">
          {error}
        </div>
      )}

      {result && (
        <div className="upload-success" role="status">
          <h3>CSV validated successfully</h3>
          <p>Dataset: {result.dataset_type}</p>
          <p>Rows: {result.row_count}</p>
          <p>Status: {result.valid ? "Valid" : "Invalid"}</p>
          <p>Columns: {result.columns?.join(", ")}</p>
        </div>
      )}
    </section>
  );
}
