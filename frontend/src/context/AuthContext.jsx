import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { auth } from "../api/endpoints.js";
import { setCsrfToken, setSessionExpiredHandler } from "../api/client.js";
import { useToast } from "./ToastContext.jsx";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  const accept = useCallback((data) => {
    setCsrfToken(data.csrf_token);
    setUser(data.user);
  }, []);

  // On page load/refresh: ask the server who we are; if the short-lived access
  // token has expired, rotate it with the refresh cookie and ask again.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await auth.me();
        if (!cancelled) accept(data);
      } catch (e) {
        if (e.response?.status === 401) {
          try {
            const { data } = await auth.refresh();
            if (!cancelled) accept(data);
          } catch {
            /* not signed in */
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [accept]);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setCsrfToken(null);
      setUser((current) => {
        if (current) toast?.info("Your session has ended. Please sign in again.");
        return null;
      });
    });
  }, [toast]);

  const login = useCallback(
    async (email, password) => {
      const { data } = await auth.login(email, password);
      accept(data);
      return data.user;
    },
    [accept]
  );

  const logout = useCallback(async () => {
    try {
      await auth.logout();
    } finally {
      setCsrfToken(null);
      setUser(null);
    }
  }, []);

  const can = useCallback((code) => !!user && (user.role === "admin" || user.permissions.includes(code)), [user]);

  const value = useMemo(
    () => ({ user, loading, login, logout, can, isAdmin: user?.role === "admin", accept }),
    [user, loading, login, logout, can, accept]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

// "/admin" or "/employee": where the signed-in user's pages live.
export const useBase = () => (useAuth().user?.role === "admin" ? "/admin" : "/employee");
