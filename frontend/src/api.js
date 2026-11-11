const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();
const API_BASE = (configuredApiBase || (import.meta.env.DEV
  ? "http://127.0.0.1:8000"
  : "")).replace(/\/+$/, "");

export function apiUrl(path) {
  if (!API_BASE) {
    throw new Error(
      "VITE_API_BASE_URL is not configured. Set it to the deployed backend URL."
    );
  }

  return `${API_BASE}${path}`;
}
