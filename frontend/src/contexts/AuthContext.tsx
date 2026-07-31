import React, { createContext, useContext, useState, ReactNode } from "react";
import { User } from "@/types";
import { login as apiLogin, me } from "@/services/api";

interface AuthContextValue {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);

  const login = async (email: string, password: string) => {
    const { data } = await apiLogin(email, password);
    localStorage.setItem("csos_access_token", data.access_token);
    const currentUser = await me();
    setUser(currentUser.data);
  };

  const logout = () => {
    localStorage.removeItem("csos_access_token");
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
