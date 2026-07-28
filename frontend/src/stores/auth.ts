import { defineStore } from "pinia";

import {
  changePassword as changePasswordApi,
  login as loginApi,
  me as fetchMeApi,
} from "@/api/auth";
import type { AuthUser, ChangePasswordRequest } from "@/types/auth";

const TOKEN_KEY = "sellpilot_token";
const USER_KEY = "sellpilot_user";

function loadPersistedToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function loadPersistedUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

function persistAuth(token: string, user: AuthUser): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // Storage can be unavailable in private browsing.
  }
}

function persistToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Storage can be unavailable in private browsing.
  }
}

function clearPersistedAuth(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    // Storage can be unavailable in private browsing.
  }
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: loadPersistedToken() as string | null,
    user: loadPersistedUser() as AuthUser | null,
    loading: false,
    initialized: false,
    error: null as string | null,
  }),

  getters: {
    isAuthenticated: (state) => state.token !== null && state.user !== null,
    currentUser: (state) => state.user,
  },

  actions: {
    async login(username: string, password: string): Promise<void> {
      this.loading = true;
      this.error = null;
      try {
        const response = await loginApi({ username, password });
        this.token = response.access_token;
        persistToken(response.access_token);
        const user = await fetchMeApi();
        this.user = user;
        persistAuth(response.access_token, user);
        this.initialized = true;
      } catch (error: unknown) {
        this.logout();
        this.error = error instanceof Error ? error.message : "登录失败";
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchMe(): Promise<AuthUser> {
      const user = await fetchMeApi();
      this.user = user;
      if (this.token) persistAuth(this.token, user);
      return user;
    },

    async restoreSession(): Promise<void> {
      if (this.initialized) return;
      this.initialized = true;
      if (!this.token) {
        this.user = null;
        return;
      }
      this.loading = true;
      try {
        await this.fetchMe();
      } catch {
        this.logout();
      } finally {
        this.loading = false;
      }
    },

    async changePassword(payload: ChangePasswordRequest): Promise<void> {
      this.loading = true;
      this.error = null;
      try {
        this.user = await changePasswordApi(payload);
        if (this.token) persistAuth(this.token, this.user);
      } catch (error: unknown) {
        this.error = error instanceof Error ? error.message : "密码修改失败";
        throw error;
      } finally {
        this.loading = false;
      }
    },

    logout(): void {
      this.token = null;
      this.user = null;
      this.initialized = true;
      clearPersistedAuth();
    },
  },
});
