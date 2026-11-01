// Baked in at BUILD time (Vite). Empty = same origin (dev proxy). A trailing slash is tolerated.
const BASE = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");
// Generous because a sleeping free-tier backend can take ~1 min to wake up; AI calls may retry server-side.
const TIMEOUT_MS = 60000;
const AI_TIMEOUT_MS = 100000;

export class ApiError extends Error {
  constructor(code, message, status) { super(message); this.code = code; this.status = status; }
}

async function request(path, { method = "GET", body, params, timeout = TIMEOUT_MS } = {}) {
  const qs = params
    ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")).toString()
    : "";
  let res;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    res = await fetch(BASE + path + qs, {
      method, headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
  } catch (e) {
    if (e?.name === "AbortError") throw new ApiError("TIMEOUT", "The server took too long to respond. It may be waking up; please retry in a moment.", 0);
    throw new ApiError("SERVER_UNREACHABLE", "KrishiMitra server is not reachable. Check that the backend is running and retry.", 0);
  } finally {
    clearTimeout(timer);
  }
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON body */ }
  if (!res.ok) throw new ApiError(data?.error?.code || `HTTP_${res.status}`, data?.error?.message || "Request failed.", res.status);
  return data;
}

export const api = {
  health: () => request("/api/health"),
  crops: () => request("/api/crops"),
  weather: (params) => request("/api/weather", { params }),
  mandi: (params) => request("/api/mandi/prices", { params }),
  soil: (body) => request("/api/soil/analyze", { method: "POST", body }),
  advisory: (body) => request("/api/advisory", { method: "POST", body, timeout: AI_TIMEOUT_MS }),
  demo: () => request("/api/demo"),
};
