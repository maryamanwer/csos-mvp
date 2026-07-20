import axios from "axios";

export const api = axios.create({
  baseURL: "/api/v1",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("csos_access_token");
  // NOTE: localStorage is fine here — this is a real deployed app, not a
  // Claude.ai artifact (artifacts must avoid browser storage; this file
  // ships in the user's own repo/build, not in an artifact sandbox).
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ---- Auth ----
export const login = (email: string, password: string) =>
  api.post("/auth/login", { email, password });

export const me = () => api.get("/auth/me");

// ---- Assets ----
export const listAssets = () => api.get("/assets");
export const getAsset = (id: string) => api.get(`/assets/${id}`);

// ---- Risk ----
export const topRisks = (limit = 5) => api.get(`/risk/top?limit=${limit}`);

// ---- Compliance ----
export const complianceCoverage = () => api.get("/compliance/coverage");

// ---- Chat ----
export const sendChatMessage = (message: string, conversation_id?: string) =>
  api.post("/chat", { message, conversation_id });

// ---- Reports ----
export const generateReport = (report_type: string, format: string = "pdf") =>
  api.post(`/reports/generate?report_type=${report_type}&format=${format}`);

// ---- Admin ----
export const listUsers = () => api.get("/admin/users");
export const auditLog = () => api.get("/admin/audit-log");
