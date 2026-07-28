import type { LoginRequest, LoginResponse } from "@/types/auth"

const MOCK_USER = {
  id: "u_001",
  username: "admin",
  displayName: "运营管理员",
}

const MOCK_TOKEN = "mock_token_sellpilot_2026"

/**
 * 模拟登录 API —— 后端未就绪时使用 mock 数据。
 * 接入真实后端时，替换为 `request<LoginResponse>("/v1/auth/login", { method: "POST", body: JSON.stringify(payload) })`。
 */
export async function login(payload: LoginRequest): Promise<LoginResponse> {
  // -- 模拟网络延迟 --
  await new Promise((resolve) => setTimeout(resolve, 600 + Math.random() * 400))

  console.log("[auth API] received:", JSON.stringify(payload))
  console.log("[auth API] expected: username=", MOCK_USER.username, "password=admin123")
  console.log("[auth API] match:", payload.username === MOCK_USER.username && payload.password === "admin123")

  if (payload.username !== MOCK_USER.username || payload.password !== "admin123") {
    throw new Error("用户名或密码错误")
  }

  return {
    token: MOCK_TOKEN,
    user: MOCK_USER,
  }
}
