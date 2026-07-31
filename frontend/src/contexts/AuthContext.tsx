import React, { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { User } from "@/types";
import { login as apiLogin, logout as apiLogout, me } from "@/services/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const clearTokens = () => {
  localStorage.removeItem("csos_access_token");
  localStorage.removeItem("csos_refresh_token");
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const restoreSession = async () => {
      if (!localStorage.getItem("csos_access_token")) {
        setLoading(false);
        return;
      }
      try {
        const response = await me();
        setUser(response.data);
      } catch {
        clearTokens();
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    void restoreSession();
  }, []);

  const login = async (email: string, password: string) => {
    const { data } = await apiLogin(email, password);
    localStorage.setItem("csos_access_token", data.access_token);
    localStorage.setItem("csos_refresh_token", data.refresh_token);
    const currentUser = await me();
    setUser(currentUser.data);
    return currentUser.data;
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem("csos_refresh_token");
    try {
      if (refreshToken) await apiLogout(refreshToken);
    } finally {
      clearTokens();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
