
import { useCallback, useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

const DATASETS = [
  {
    value: "invoices",
    label: "Invoices",
    description: "Invoice records and due dates",
  },
  {
    value: "payments",
    label: "Payments",
    description: "Customer payment records",
  },
  {
    value: "bank_transactions",
    label: "Bank Transactions",
    description: "Bank statement transactions",
  },
];

const styles = {
  app: {
    minHeight: "100vh",
    background: "#f4f7fb",
    color: "#172033",
    fontFamily: "Inter, Arial, sans-serif",
  },
  header: {
    background: "#111c35",
    color: "#ffffff",
    padding: "24px 5%",
  },
  brand: {
    margin: 0,
    fontSize: "26px",
    fontWeight: 800,
  },
  subtitle: {
    color: "#bdc9df",
    margin: "8px 0 0",
    fontSize: "14px",
  },
  main: {
    maxWidth: "1400px",
    margin: "0 auto",
    padding: "28px 5%",
  },
  toolbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "16px",
    flexWrap: "wrap",
    marginBottom: "24px",
  },
  heading: {
    margin: "0 0 6px",
    fontSize: "25px",
  },
  muted: {
    color: "#65718a",
    fontSize: "14px",
    margin: 0,
  },
  panel: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "14px",
    padding: "22px",
    marginBottom: "24px",
    boxShadow: "0 3px 12px rgba(25, 40, 70, 0.04)",
    minWidth: 0,
  },
  panelTitle: {
    fontSize: "18px",
    margin: "0 0 8px",
  },
  label: {
    display: "block",
    fontSize: "13px",
    fontWeight: 700,
    marginBottom: "8px",
    color: "#46536b",
  },
  input: {
    width: "100%",
    boxSizing: "border-box",
    padding: "11px 12px",
    border: "1px solid #ccd5e3",
    borderRadius: "8px",
    background: "#ffffff",
    color: "#172033",
    fontSize: "14px",
  },
  button: {
    border: 0,
    borderRadius: "8px",
    padding: "12px 16px",
    background: "#2459d3",
    color: "#ffffff",
    fontWeight: 700,
    fontSize: "14px",
    cursor: "pointer",
  },
  secondaryButton: {
    border: "1px solid #ccd5e3",
    borderRadius: "8px",
    padding: "11px 14px",
    background: "#ffffff",
    color: "#26344d",
    fontWeight: 700,
    fontSize: "13px",
    cursor: "pointer",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
    gap: "16px",
    marginBottom: "24px",
  },
  metricLabel: {
    fontSize: "13px",
    color: "#65718a",
    margin: "0 0 12px",
  },
  metricValue: {
    fontSize: "29px",
    fontWeight: 800,
    margin: 0,
    overflowWrap: "anywhere",
  },
  metricNote: {
    color: "#8290a7",
    fontSize: "12px",
    margin: "9px 0 0",
  },
  twoColumns: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 400px), 1fr))",
    gap: "20px",
  },
  tableWrap: {
    overflowX: "auto",
    width: "100%",
  },
  table: {
    borderCollapse: "collapse",
    width: "100%",
    fontSize: "13px",
    whiteSpace: "nowrap",
  },
  th: {
    textAlign: "left",
    background: "#f6f8fc",
    padding: "12px",
    borderBottom: "1px solid #e3e8f0",
    color: "#536078",
  },
  td: {
    padding: "12px",
    borderBottom: "1px solid #edf0f5",
  },
  status: {
    padding: "12px 14px",
    borderRadius: "8px",
    fontSize: "14px",
    marginBottom: "20px",
    overflowWrap: "anywhere",
  },
};

function formatValue(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (typeof value === "number") {
    return value.toLocaleString("en-IN", {
      maximumFractionDigits: 2,
    });
  }

  return String(value);
}

function getStatusColor(status) {
  const normalized = String(status || "").toUpperCase();

  if (normalized === "MATCHED") {
    return { background: "#dcfce7", color: "#166534" };
  }

  if (
    normalized.includes("MISMATCH") ||
    normalized.includes("MISSING") ||
    normalized.includes("DUPLICATE") ||
    normalized.includes("INVALID")
  ) {
    return { background: "#fee2e2", color: "#991b1b" };
  }

  return { background: "#fef3c7", color: "#92400e" };
}

function StatusBadge({ value }) {
  const colors = getStatusColor(value);

  return (
    <span
      style={{
        ...colors,
        display: "inline-block",
        borderRadius: "6px",
        padding: "5px 8px",
        fontSize: "11px",
        fontWeight: 800,
      }}
    >
      {formatValue(value)}
    </span>
  );
}

function DataTable({ rows, emptyMessage, maxRows = 100 }) {
  if (!rows || rows.length === 0) {
    return (
      <p style={{ ...styles.muted, padding: "18px 0" }}>
        {emptyMessage}
      </p>
    );
  }

  const columns = Object.keys(rows[0]);

  return (
    <div style={styles.tableWrap}>
      <table style={styles.table}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} style={styles.th}>
                {column.replaceAll("_", " ")}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.slice(0, maxRows).map((row, index) => (
            <tr key={row.payment_id || row.id || index}>
              {columns.map((column) => (
                <td key={column} style={styles.td}>
                  {column.toLowerCase() === "status" ||
                  column.toLowerCase() === "reconciliation_status" ? (
                    <StatusBadge value={row[column]} />
                  ) : (
                    formatValue(row[column])
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {rows.length > maxRows && (
        <p style={styles.muted}>
          Showing {maxRows} of {rows.length} records.
        </p>
      )}
    </div>
  );
}

function App() {
  const [dataSource, setDataSource] = useState("original");
  const [datasetType, setDatasetType] = useState("invoices");
  const [selectedFile, setSelectedFile] = useState(null);

  const [metrics, setMetrics] = useState(null);
  const [reconciliation, setReconciliation] = useState([]);
  const [exceptions, setExceptions] = useState([]);

  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");
  const [apiOnline, setApiOnline] = useState(null);

  const showMessage = (text, type = "info") => {
    setMessage(text);
    setMessageType(type);
  };

  const requestJson = async (url, options = {}) => {
    const response = await fetch(`${API_BASE}${url}`, options);

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail || `Request failed with status ${response.status}.`
      );
    }

    return data;
  };

  const refreshDashboard = useCallback(async () => {
    setLoading(true);

    try {
      const health = await requestJson("/health");
      setApiOnline(health.status === "healthy");

      const source = dataSource;

      const [metricsResult, recordsResult] = await Promise.allSettled([
        requestJson(`/api/metrics?source=${source}`),
        requestJson(`/api/reconciliation?source=${source}`),
      ]);

      if (metricsResult.status === "fulfilled") {
        setMetrics(metricsResult.value);
      } else {
        setMetrics(null);
      }

      if (recordsResult.status === "fulfilled") {
        setReconciliation(
          Array.isArray(recordsResult.value) ? recordsResult.value : []
        );
      } else {
        setReconciliation([]);
      }

      try {
        const exceptionResult = await requestJson(
          `/api/exceptions?source=${source}`
        );

        setExceptions(
          Array.isArray(exceptionResult) ? exceptionResult : []
        );
      } catch {
        setExceptions([]);
      }

      if (
        metricsResult.status === "rejected" &&
        recordsResult.status === "rejected"
      ) {
        showMessage(
          "The API is running, but no reconciliation results were found for this dataset. Run reconciliation first.",
          "info"
        );
      } else {
        showMessage("Dashboard data refreshed.", "success");
      }
    } catch (error) {
      setApiOnline(false);
      setMetrics(null);
      setReconciliation([]);
      setExceptions([]);

      showMessage(
        `Cannot connect to the backend. Start FastAPI and try again. ${error.message}`,
        "error"
      );
    } finally {
      setLoading(false);
    }
  }, [dataSource]);

  useEffect(() => {
    refreshDashboard();
  }, [refreshDashboard]);

  async function handleUpload(event) {
    event.preventDefault();

    if (!selectedFile) {
      showMessage("Please select a CSV file first.", "error");
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".csv")) {
      showMessage("Only CSV files are supported.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("dataset_type", datasetType);
    formData.append("file", selectedFile);

    setUploading(true);
    showMessage("Uploading and validating CSV...", "info");

    try {
      const result = await requestJson("/api/upload-csv", {
        method: "POST",
        body: formData,
      });

      setSelectedFile(null);
      event.target.reset();

      showMessage(
        `${result.message} ${result.saved_as} — ${result.row_count} rows validated.`,
        "success"
      );
    } catch (error) {
      showMessage(`Upload failed: ${error.message}`, "error");
    } finally {
      setUploading(false);
    }
  }

  async function runReconciliation() {
    setLoading(true);
    showMessage("Reconciling financial records...", "info");

    try {
      const result = await requestJson(
        `/api/reconcile?source=${dataSource}`,
        { method: "POST" }
      );

      setMetrics(result.metrics || null);

      showMessage(
        `${result.message} Dataset: ${dataSource}.`,
        "success"
      );

      // Refresh tables and metrics after reconciliation.
      const [metricsResult, recordsResult] = await Promise.allSettled([
        requestJson(`/api/metrics?source=${dataSource}`),
        requestJson(`/api/reconciliation?source=${dataSource}`),
      ]);

      if (metricsResult.status === "fulfilled") {
        setMetrics(metricsResult.value);
      }

      if (recordsResult.status === "fulfilled") {
        setReconciliation(
          Array.isArray(recordsResult.value) ? recordsResult.value : []
        );
      }

      setExceptions([]);
    } catch (error) {
      showMessage(`Reconciliation failed: ${error.message}`, "error");
    } finally {
      setLoading(false);
    }
  }

  async function runExceptionAnalysis() {
    setAnalyzing(true);
    showMessage("Analyzing exceptions with the AI agent...", "info");

    try {
      const result = await requestJson(
        `/api/analyze-exceptions?source=${dataSource}`,
        { method: "POST" }
      );

      setExceptions(
        Array.isArray(result.results) ? result.results : []
      );

      showMessage(
        `${result.message} ${result.total_analyzed} exceptions analyzed.`,
        "success"
      );
    } catch (error) {
      showMessage(`AI analysis failed: ${error.message}`, "error");
    } finally {
      setAnalyzing(false);
    }
  }

  const totalPayments = Number(metrics?.total_payments ?? 0);
  const matched = Number(metrics?.matched ?? 0);
  const exceptionCount = Number(
    metrics?.exceptions ?? Math.max(totalPayments - matched, 0)
  );

  const matchRate = Number(metrics?.match_rate_percent ?? 0);
  const exceptionRate = Number(metrics?.exception_rate_percent ?? 0);

  const statusCounts = metrics?.status_counts || {};

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <div style={{ maxWidth: "1400px", margin: "0 auto" }}>
          <p style={{ margin: "0 0 6px", color: "#91b6ff", fontSize: "12px" }}>
            INTELLIGENT FINANCIAL OPERATIONS
          </p>

          <h1 style={styles.brand}>AI Finance Controller</h1>

          <p style={styles.subtitle}>
            Automated reconciliation, exception detection and AI-powered
            financial analysis.
          </p>
        </div>
      </header>

      <main style={styles.main}>
        <div style={styles.toolbar}>
          <div>
            <h2 style={styles.heading}>Finance Overview</h2>
            <p style={styles.muted}>
              Upload data, reconcile transactions and investigate exceptions.
            </p>
          </div>

          <div style={{ minWidth: "220px" }}>
            <label htmlFor="data-source" style={styles.label}>
              Active dataset
            </label>

            <select
              id="data-source"
              value={dataSource}
              onChange={(event) => setDataSource(event.target.value)}
              style={styles.input}
            >
              <option value="original">Original datasets</option>
              <option value="uploaded">Uploaded CSV datasets</option>
              <option value="clean_test">Clean Test Dataset (100% match)</option>
            </select>
          </div>
        </div>

        <div
          style={{
            ...styles.status,
            background:
              messageType === "error"
                ? "#fee2e2"
                : messageType === "success"
                  ? "#dcfce7"
                  : "#eaf1ff",
            color:
              messageType === "error"
                ? "#991b1b"
                : messageType === "success"
                  ? "#166534"
                  : "#244a91",
          }}
          role="status"
          aria-live="polite"
        >
          <strong>
            {apiOnline === false
              ? "Backend connection issue: "
              : messageType === "error"
                ? "Error: "
                : ""}
          </strong>
          {message || "Ready."}
        </div>

        {/* CSV upload */}
        <section style={styles.panel}>
          <h3 style={styles.panelTitle}>Upload Financial Data</h3>

          <p style={{ ...styles.muted, marginBottom: "20px" }}>
            Upload each CSV separately. Files are validated before they replace
            the corresponding uploaded dataset.
          </p>

          <form onSubmit={handleUpload}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
                gap: "16px",
                alignItems: "end",
              }}
            >
              <div>
                <label htmlFor="dataset-type" style={styles.label}>
                  Dataset type
                </label>

                <select
                  id="dataset-type"
                  value={datasetType}
                  onChange={(event) => setDatasetType(event.target.value)}
                  style={styles.input}
                >
                  {DATASETS.map((dataset) => (
                    <option key={dataset.value} value={dataset.value}>
                      {dataset.label}
                    </option>
                  ))}
                </select>

                <p style={{ ...styles.muted, marginTop: "6px" }}>
                  {DATASETS.find((item) => item.value === datasetType)?.description}
                </p>
              </div>

              <div>
                <label htmlFor="csv-file" style={styles.label}>
                  Select CSV file
                </label>

                <input
                  id="csv-file"
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(event) =>
                    setSelectedFile(event.target.files?.[0] || null)
                  }
                  style={styles.input}
                />
              </div>

              <button
                type="submit"
                disabled={uploading}
                style={{
                  ...styles.button,
                  opacity: uploading ? 0.65 : 1,
                }}
              >
                {uploading ? "Uploading..." : "Upload and Validate"}
              </button>
            </div>
          </form>
        </section>

        {/* Reconciliation controls */}
        <section style={styles.panel}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "16px",
            }}
          >
            <div>
              <h3 style={styles.panelTitle}>Reconciliation Engine</h3>
              <p style={styles.muted}>
                Current source:{" "}
                <strong>
                  {dataSource === "original"
                    ? "Original data"
                    : dataSource === "uploaded"
                      ? "Uploaded data"
                      : "Clean test data"}
                </strong>
              </p>
            </div>

            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={refreshDashboard}
                disabled={loading}
                style={styles.secondaryButton}
              >
                {loading ? "Loading..." : "Refresh Dashboard"}
              </button>

              <button
                type="button"
                onClick={runReconciliation}
                disabled={loading || uploading}
                style={styles.button}
              >
                {loading ? "Processing..." : "Run Reconciliation"}
              </button>
            </div>
          </div>
        </section>

        {/* Financial metrics */}
        <section>
          <h3 style={{ ...styles.panelTitle, marginBottom: "16px" }}>
            Reconciliation Metrics
          </h3>

          <div style={styles.grid}>
            {[
              {
                label: "Total Payments",
                value: formatValue(metrics?.total_payments),
                note: "Payment records evaluated",
              },
              {
                label: "Matched Transactions",
                value: formatValue(metrics?.matched),
                note: "Successfully reconciled",
              },
              {
                label: "Exceptions",
                value: formatValue(metrics?.exceptions),
                note: "Records requiring investigation",
              },
              {
                label: "Match Rate",
                value:
                  metrics?.match_rate_percent !== undefined
                    ? `${formatValue(metrics.match_rate_percent)}%`
                    : "—",
                note: "Percentage of matched payments",
              },
            ].map((item) => (
              <div key={item.label} style={styles.panel}>
                <p style={styles.metricLabel}>{item.label}</p>
                <p style={styles.metricValue}>{item.value}</p>
                <p style={styles.metricNote}>{item.note}</p>
              </div>
            ))}
          </div>
        </section>

        <div style={styles.twoColumns}>
          <section style={styles.panel}>
            <h3 style={styles.panelTitle}>Match Rate</h3>

            <p style={{ ...styles.metricValue, marginTop: "16px" }}>
              {metrics ? `${formatValue(matchRate)}%` : "—"}
            </p>

            <div
              style={{
                height: "12px",
                background: "#e8edf5",
                borderRadius: "20px",
                overflow: "hidden",
                margin: "18px 0 10px",
              }}
            >
              <div
                style={{
                  width: `${Math.max(0, Math.min(100, matchRate))}%`,
                  height: "100%",
                  background: "#16a36a",
                  borderRadius: "20px",
                  transition: "width 0.3s ease",
                }}
              />
            </div>

            <p style={styles.muted}>
              Exception rate:{" "}
              {metrics ? `${formatValue(exceptionRate)}%` : "—"}
            </p>
          </section>

          <section style={styles.panel}>
            <h3 style={styles.panelTitle}>Exception Breakdown</h3>

            {Object.keys(statusCounts).length === 0 ? (
              <p style={{ ...styles.muted, marginTop: "18px" }}>
                No status breakdown available. Run reconciliation to generate
                metrics.
              </p>
            ) : (
              <div style={{ marginTop: "14px" }}>
                {Object.entries(statusCounts).map(([status, count]) => (
                  <div
                    key={status}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: "12px",
                      padding: "12px 0",
                      borderBottom: "1px solid #edf0f5",
                    }}
                  >
                    <span style={{ fontSize: "13px" }}>
                      {status.replaceAll("_", " ")}
                    </span>
                    <StatusBadge value={count} />
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* Reconciliation records */}
        <section style={styles.panel}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "12px",
              flexWrap: "wrap",
              marginBottom: "16px",
            }}
          >
            <div>
              <h3 style={styles.panelTitle}>Reconciliation Records</h3>
              <p style={styles.muted}>
                {reconciliation.length} records loaded for the selected source.
              </p>
            </div>
          </div>

          <DataTable
            rows={reconciliation}
            emptyMessage="No reconciliation records found. Upload all three datasets and run reconciliation."
          />
        </section>

        {/* AI exception analysis */}
        <section style={styles.panel}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "16px",
              marginBottom: "16px",
            }}
          >
            <div>
              <h3 style={styles.panelTitle}>AI Exception Analysis</h3>
              <p style={styles.muted}>
                Use the exception agent to analyze reconciliation results.
              </p>
            </div>

            <button
              type="button"
              onClick={runExceptionAnalysis}
              disabled={analyzing || loading}
              style={{
                ...styles.button,
                background: "#6d43c0",
                opacity: analyzing ? 0.65 : 1,
              }}
            >
              {analyzing ? "Analyzing..." : "Analyze Exceptions with AI"}
            </button>
          </div>

          <p style={{ ...styles.muted, marginBottom: "16px" }}>
            {exceptions.length} exception analysis records loaded.
          </p>

          <DataTable
            rows={exceptions}
            emptyMessage="No AI exception analysis results yet. Run reconciliation first, then click Analyze Exceptions with AI."
          />
        </section>

        <footer
          style={{
            textAlign: "center",
            color: "#7b879c",
            fontSize: "12px",
            padding: "10px 0 24px",
          }}
        >
          AI Finance Controller · Financial reconciliation and exception
          management
        </footer>
      </main>
    </div>
  );
}

export default App;
