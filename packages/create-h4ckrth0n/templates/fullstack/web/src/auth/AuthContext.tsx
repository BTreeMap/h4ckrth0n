import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { decodeJwt } from "jose";
import { get, set, del } from "idb-keyval";

interface User {
  id: string;
  role: string;
  scopes: string[];
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (token: string, refreshToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = "h4ckrth0n_token";
const REFRESH_KEY = "h4ckrth0n_refresh";

function parseToken(token: string): User | null {
  try {
    const claims = decodeJwt(token);
    // 30-second buffer to account for clock skew
    if (claims.exp && claims.exp * 1000 < Date.now() + 30_000) return null;
    return {
      id: claims.sub as string,
      role: (claims.role as string) ?? "user",
      scopes: (claims.scopes as string[]) ?? [],
    };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    loading: true,
  });

  useEffect(() => {
    get<string>(TOKEN_KEY).then((token) => {
      if (token) {
        const user = parseToken(token);
        setState({ user, token: user ? token : null, loading: false });
      } else {
        setState((s) => ({ ...s, loading: false }));
      }
    });
  }, []);

  const login = useCallback(async (token: string, refreshToken: string) => {
    await Promise.all([set(TOKEN_KEY, token), set(REFRESH_KEY, refreshToken)]);
    const user = parseToken(token);
    setState({ user, token, loading: false });
  }, []);

  const logout = useCallback(async () => {
    setState({ user: null, token: null, loading: false });
    await del(TOKEN_KEY);
    await del(REFRESH_KEY);
  }, []);

  const refresh = useCallback(async () => {
    const refreshToken = await get<string>(REFRESH_KEY);
    if (!refreshToken) {
      await logout();
      return;
    }
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) throw new Error("refresh failed");
      const data = await res.json();
      await login(data.access_token, data.refresh_token);
    } catch {
      await logout();
    }
  }, [login, logout]);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
