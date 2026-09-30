import axios from "axios";

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

export const TOKEN_STORAGE_KEY = "pdfchat_access_token";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function storeToken(token) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

// ---------------------------------------------------------------------------
// The one Axios instance used for every backend request
// ---------------------------------------------------------------------------

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 15000, // milliseconds
});

// Attach the JWT (if any) to every request automatically
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---------------------------------------------------------------------------
// Automatic logout when the backend rejects our token
// ---------------------------------------------------------------------------

// AuthProvider registers a function here; client.js knows nothing about React
let unauthorizedHandler = null;

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only a 401 on a request that carried a token means "your token is bad".
    // A wrong-password login is also 401 but sends no token: no logout then.
    const sentToken = Boolean(error.config?.headers?.Authorization);

    if (error.response?.status === 401 && sentToken && unauthorizedHandler) {
      unauthorizedHandler();
    }

    return Promise.reject(error);
  },
);
