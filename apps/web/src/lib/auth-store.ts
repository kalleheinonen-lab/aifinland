import { create } from "zustand";
import { refreshToken as refreshTokenApi, type LoginResponse } from "./api-client";

interface AuthUser {
  sub: string;
  org: string;
  roles: string[];
  displayName: string;
  orgName: string;
  mfaEnabled: boolean;
}

interface AuthState {
  accessToken: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setTokens: (response: LoginResponse) => void;
  clearAuth: () => void;
  refreshAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,
  isLoading: false,

  setTokens: (response: LoginResponse) => {
    set({
      accessToken: response.accessToken,
      user: response.user,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  clearAuth: () => {
    set({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  refreshAuth: async () => {
    set({ isLoading: true });
    try {
      const response = await refreshTokenApi();
      set({
        accessToken: response.accessToken,
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      set({
        accessToken: null,
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },
}));
