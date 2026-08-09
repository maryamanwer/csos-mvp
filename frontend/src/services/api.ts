import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const API_BASE_URL = "/api/v1";

export const api = axios.create({ baseURL: API_BASE_URL });
const refreshClient = axios.create({ baseURL: API_BASE_URL });

interface RetryableRequest extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("csos_access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetryableRequest | undefined;
    const refreshToken = localStorage.getItem("csos_refresh_token");
    const isRefreshable =
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      refreshToken &&
      !original.url?.includes("/auth/login") &&
      !original.url?.includes("/auth/refresh");

    if (!isRefreshable) return Promise.reject(error);
    original._retry = true;
    try {
      const { data } = await refreshClient.post("/auth/refresh", {
        refresh_token: refreshToken,
      });
      localStorage.setItem("csos_access_token", data.access_token);
      localStorage.setItem("csos_refresh_token", data.refresh_token);
      original.headers.Authorization = `Bearer ${data.access_token}`;
      return api(original);
    } catch (refreshError) {
      localStorage.removeItem("csos_access_token");
      localStorage.removeItem("csos_refresh_token");
      if (window.location.pathname !== "/login") window.location.assign("/login");
      return Promise.reject(refreshError);
    }
  },
);

// Auth
export const login = (email: string, password: string) =>
  api.post("/auth/login", { email, password });
export const me = () => api.get("/auth/me");
export const logout = (refreshToken: string) =>
  api.post("/auth/logout", { refresh_token: refreshToken });

// Dashboards
export const executiveDashboard = () => api.get("/dashboard/executive");
export const analystDashboard = (limit = 100) =>
  api.get("/dashboard/analyst", { params: { limit } });

// Assets
export const listAssets = (params?: Record<string, unknown>) =>
  api.get("/assets", { params });
export const getAsset = (id: string) => api.get(`/assets/${id}`);
export const createAsset = (payload: Record<string, unknown>) =>
  api.post("/assets", payload);
export const updateAsset = (id: string, payload: Record<string, unknown>) =>
  api.put(`/assets/${id}`, payload);
export const deleteAsset = (id: string) => api.delete(`/assets/${id}`);
export const importAssets = (file: File) => {
  const body = new FormData();
  body.append("file", file);
  return api.post("/assets/import", body);
};
export const createAssetRelationship = (
  sourceId: string,
  payload: Record<string, unknown>,
) => api.post(`/assets/${sourceId}/relationships`, payload);

// Vulnerabilities
export const listVulnerabilities = (params?: Record<string, unknown>) =>
  api.get("/vulnerabilities", { params });
export const createVulnerability = (payload: Record<string, unknown>) =>
  api.post("/vulnerabilities", payload);
export const updateVulnerability = (
  id: string,
  payload: Record<string, unknown>,
) => api.put(`/vulnerabilities/${id}`, payload);
export const deleteVulnerability = (id: string) =>
  api.delete(`/vulnerabilities/${id}`);
export const importVulnerabilities = (file: File) => {
  const body = new FormData();
  body.append("file", file);
  return api.post("/vulnerabilities/import", body);
};

// Correlated security findings
export const listSecurityFindings = (params?: Record<string, unknown>) =>
  api.get("/findings", { params });
export const getSecurityFinding = (findingId: string, assetId: string) =>
  api.get(`/findings/${findingId}`, { params: { asset_id: assetId } });
export const exportSecurityFindings = (params: Record<string, unknown>) =>
  api.get("/findings/export", { params, responseType: "blob" });

// Network Topology
export const getTopology = (focusAssetId?: string) =>
  api.get("/topology", {
    params: { focus_asset_id: focusAssetId, node_limit: 1500, relationship_limit: 1500 },
  });

// Risk and compliance
export const topRisks = (limit = 5) => api.get("/risk/top", { params: { limit } });
export const complianceCoverage = () => api.get("/compliance/coverage");

// Chat
export const sendChatMessage = (message: string, conversation_id?: string) =>
  api.post("/chat", { message, conversation_id });

// Reports
export const generateReport = (report_type: string, format: string = "pdf") =>
  api.post("/reports/generate", undefined, { params: { report_type, format } });

// Administration
export const listUsers = (search?: string) =>
  api.get("/admin/users", { params: search ? { search } : undefined });
export const createUser = (payload: object) =>
  api.post("/admin/users", payload);
export const updateUser = (id: string, payload: Record<string, unknown>) =>
  api.put(`/admin/users/${id}`, payload);
export const deactivateUser = (id: string) => api.delete(`/admin/users/${id}`);
export const listRoles = () => api.get("/admin/roles");
export const updateRole = (id: string, payload: Record<string, unknown>) =>
  api.put(`/admin/roles/${id}`, payload);
export const auditLog = () => api.get("/admin/audit-log");
