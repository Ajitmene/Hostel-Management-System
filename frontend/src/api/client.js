import axios from "axios";

// One centralized client. Tokens live in HttpOnly cookies the browser manages;
// JavaScript never sees them. Only the CSRF token is held in memory.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8001/api/v1",
  withCredentials: true,
});

let csrfToken = null;
export const setCsrfToken = (token) => {
  csrfToken = token || null;
};

let onSessionExpired = () => {};
export const setSessionExpiredHandler = (fn) => {
  onSessionExpired = fn;
};

const SAFE = ["get", "head", "options"];
api.interceptors.request.use((config) => {
  if (csrfToken && !SAFE.includes((config.method || "get").toLowerCase())) {
    config.headers["X-CSRF-Token"] = csrfToken;
  }
  return config;
});

let refreshing = null;
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response, config } = error;
    const isAuthCall = config?.url?.startsWith("/auth/");
    if (response?.status === 401 && config && !config._retried && !isAuthCall) {
      config._retried = true;
      try {
        refreshing = refreshing || api.post("/auth/refresh").finally(() => (refreshing = null));
        const res = await refreshing;
        setCsrfToken(res.data.csrf_token);
        return api(config); // retry once with the fresh cookies
      } catch {
        onSessionExpired();
      }
    }
    return Promise.reject(error);
  }
);
