import { defineStore } from "pinia"

import { login as loginApi } from "@/api/auth"
import type { UserInfo } from "@/types/auth"

const TOKEN_KEY = "sellpilot_token"
const USER_KEY = "sellpilot_user"

function loadPersistedToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function loadPersistedUser(): UserInfo | null {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? (JSON.parse(raw) as UserInfo) : null
  } catch {
    return null
  }
}

function persistToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // 无痕模式等场景静默忽略
  }
}

function persistUser(user: UserInfo): void {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  } catch {
    // 无痕模式等场景静默忽略
  }
}

function clearPersistedAuth(): void {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  } catch {
    // 静默忽略
  }
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: loadPersistedToken(),
    user: loadPersistedUser(),
    loading: false,
  }),

  getters: {
    isAuthenticated: (state) => state.token !== null && state.user !== null,
    currentUser: (state) => state.user,
  },

  actions: {
    async login(username: string, password: string): Promise<void> {
      this.loading = true
      try {
        const res = await loginApi({ username, password })
        this.token = res.access_token
        this.user = { id: "", username, displayName: username }
        persistToken(res.access_token)
        persistUser(this.user)
      } finally {
        this.loading = false
      }
    },

    logout(): void {
      this.token = null
      this.user = null
      clearPersistedAuth()
    },
  },
})
