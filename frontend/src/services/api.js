/**
 * SO4 — Axios client.
 * Uses Vite proxy path /api when the app is served by Vite (dev :5173 or preview :4173).
 * Override with VITE_API_URL (e.g. http://127.0.0.1:5005) for static hosting without proxy.
 */
import axios from "axios";

function resolveBaseURL() {
  const env = import.meta.env.VITE_API_URL?.trim?.();
  if (env) return env.replace(/\/$/, "");

  // Vite dev server
  if (import.meta.env.DEV) {
    return "/api";
  }

  // vite preview (DEV is false but we still want /api + preview.proxy)
  if (typeof window !== "undefined") {
    const p = window.location.port;
    if (p === "4173" || p === "5173") {
      return "/api";
    }
  }

  return "http://127.0.0.1:5005";
}

const BASE_URL = resolveBaseURL();

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 28000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(
  (config) => {
    const full = `${config.baseURL || ""}${config.url || ""}`;
    console.info("[API] →", config.method?.toUpperCase(), full, config.params || "");
    return config;
  },
  (error) => {
    console.error("[API] request error", error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    console.info("[API] ←", response.status, response.config.url);
    return response;
  },
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data || error.message;
    console.error("[API] ← error", status, detail);
    return Promise.reject(error);
  }
);

export default api;
