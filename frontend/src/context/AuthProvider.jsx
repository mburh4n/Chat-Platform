import { useCallback, useEffect, useMemo, useState } from "react";
import {
  TOKEN_STORAGE_KEY,
  clearStoredToken,
  getStoredToken,
  setUnauthorizedHandler,
  storeToken,
} from "../api/client";
import { login as loginRequest } from "../api/auth";
import { AuthContext } from "./auth-context";

const EXPIRED_NOTICE = "Your session has expired. Please log in again.";

// Read the "exp" claim from a JWT's payload, in milliseconds.
// The signature is NOT verified: only the backend can do that. We only need
// to know when the token stops working. Returns null for a damaged token.
function getTokenExpiry(token) {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      return null;
    }
    // JWTs use Base64URL ("-" and "_"); atob expects plain Base64 ("+" and "/")
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const payload = JSON.parse(atob(padded));

    if (typeof payload.exp !== "number" || !Number.isFinite(payload.exp)) {
      return null;
    }
    return payload.exp * 1000; // exp is in seconds
  } catch {
    return null;
  }
}

function isTokenUsable(token) {
  if (!token) {
    return false;
  }
  const expiry = getTokenExpiry(token);
  return expiry !== null && expiry > Date.now();
}

// On first load: keep a usable stored token, otherwise remove it
function readInitialToken() {
  const stored = getStoredToken();
  if (isTokenUsable(stored)) {
    return stored;
  }
  clearStoredToken();
  return null;
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(readInitialToken);
  const [notice, setNotice] = useState(null);

  const login = useCallback(async ({ email, password }) => {
    // Errors are not caught here: the login page shows them
    const data = await loginRequest({ email, password });
    storeToken(data.access_token);
    setToken(data.access_token);
    setNotice(null);
    return data;
  }, []);

  const logout = useCallback((reason) => {
    clearStoredToken();
    setToken(null);
    setNotice(reason === "expired" ? EXPIRED_NOTICE : null);
  }, []);

  const clearNotice = useCallback(() => {
    setNotice(null);
  }, []);

  // Log out automatically at the exact moment the token expires
  useEffect(() => {
    if (!token) {
      return;
    }
    const expiry = getTokenExpiry(token);
    if (expiry === null) {
      return;
    }
    const timerId = setTimeout(() => logout("expired"), Math.max(expiry - Date.now(), 0));
    return () => clearTimeout(timerId);
  }, [token, logout]);

  // A 401 on a request that carried our token means the backend rejected it
  useEffect(() => {
    setUnauthorizedHandler(() => logout("expired"));
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  // Keep several tabs in sync: login/logout in one tab updates the others
  useEffect(() => {
    function handleStorage(event) {
      if (event.key !== TOKEN_STORAGE_KEY) {
        return;
      }
      setToken(isTokenUsable(event.newValue) ? event.newValue : null);
    }
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: token !== null,
      notice,
      login,
      logout,
      clearNotice,
    }),
    [token, notice, login, logout, clearNotice],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
