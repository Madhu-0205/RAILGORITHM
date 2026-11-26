import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, getToken, setToken } from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  initialising: boolean;
  login: (username: string, password: string, portal?: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initialising, setInitialising] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function restore() {
      if (!getToken()) {
        setInitialising(false);
        return;
      }
      try {
        const current = await api.me();
        if (!cancelled) setUser(current);
      } catch {
        setToken(null);
      } finally {
        if (!cancelled) setInitialising(false);
      }
    }
    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username: string, password: string, portal?: string) => {
    const response = await api.login(username, password, portal);
    setToken(response.access_token);
    setUser(response.user);
    return response.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Invalidate client session even if network fails
    } finally {
      setToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, initialising, login, logout }),
    [user, initialising, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
