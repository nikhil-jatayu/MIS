"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  type ReactNode,
} from "react";

import { apiFetch, isAuthError } from "@/lib/api";
import type { AuthResponse, User } from "@/lib/types";

const SESSION_KEY = ["auth", "me"] as const;

interface LoginInput {
  email: string;
  password: string;
}

interface ChangePasswordInput {
  current_password: string;
  new_password: string;
}

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (input: LoginInput) => Promise<User>;
  logout: () => Promise<void>;
  changePassword: (input: ChangePasswordInput) => Promise<User>;
  refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const session = useQuery({
    queryKey: SESSION_KEY,
    queryFn: async () => {
      try {
        return await apiFetch<User>("/auth/me");
      } catch (error) {
        if (isAuthError(error)) return null;
        throw error;
      }
    },
    retry: false,
    staleTime: Infinity,
  });

  const user = session.data ?? null;
  const isLoading = session.isPending;

  const refetchSession = session.refetch;

  const refreshUser = useCallback(async () => {
    const result = await refetchSession();
    return result.data ?? null;
  }, [refetchSession]);

  const login = useCallback(
    async (input: LoginInput) => {
      const response = await apiFetch<AuthResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(input),
      });
      queryClient.setQueryData(SESSION_KEY, response.user);
      return response.user;
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      queryClient.setQueryData(SESSION_KEY, null);
    }
  }, [queryClient]);

  const changePassword = useCallback(
    async (input: ChangePasswordInput) => {
      const updated = await apiFetch<User>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify(input),
      });
      queryClient.setQueryData(SESSION_KEY, updated);
      return updated;
    },
    [queryClient],
  );

  const value = useMemo(
    () => ({
      user,
      isLoading,
      login,
      logout,
      changePassword,
      refreshUser,
    }),
    [user, isLoading, login, logout, changePassword, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return context;
}
