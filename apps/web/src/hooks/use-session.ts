"use client";

import { useEffect, useRef, useCallback } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { logout as logoutApi } from "@/lib/api-client";

const TOKEN_LIFETIME_MS = 24 * 60 * 60 * 1000; // 24 hours
const REFRESH_BEFORE_EXPIRY_MS = 1 * 60 * 60 * 1000; // Refresh at 23h mark (1h before expiry)

export function useSession() {
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const refreshAuth = useAuthStore((s) => s.refreshAuth);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasAttemptedRefresh = useRef(false);

  const scheduleRefresh = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
    const refreshDelay = TOKEN_LIFETIME_MS - REFRESH_BEFORE_EXPIRY_MS;
    refreshTimerRef.current = setTimeout(() => {
      refreshAuth();
    }, refreshDelay);
  }, [refreshAuth]);

  // On mount: attempt silent token refresh
  useEffect(() => {
    if (!hasAttemptedRefresh.current) {
      hasAttemptedRefresh.current = true;
      refreshAuth();
    }
  }, [refreshAuth]);

  // Schedule automatic refresh when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      scheduleRefresh();
    }
    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, [isAuthenticated, scheduleRefresh]);

  const logout = useCallback(async () => {
    try {
      await logoutApi();
    } catch {
      // Logout API failure should not block client-side cleanup
    }
    clearAuth();
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current);
    }
  }, [clearAuth]);

  return {
    user,
    isLoading,
    isAuthenticated,
    logout,
  };
}
