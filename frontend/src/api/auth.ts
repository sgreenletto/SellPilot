import type { LoginRequest, LoginResponse } from "@/types/auth"

const MOCK_USER = {
  id: "u_001",
  username: "admin",
  displayName: "运营管理员",
}

/**
 * 生成结构完整的模拟 JWT。
 * 在 mock 模式下签名无效，但 header.payload 结构与真实 JWT 一致，
 * 方便前端解析用户信息（如过期时间、角色等）。
 */
function generateMockJWT(): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }))
  const now = Math.floor(Date.now() / 1000)
  const payload = btoa(
    JSON.stringify({
      sub: MOCK_USER.id,
      username: MOCK_USER.username,
      display_name: MOCK_USER.displayName,
      iat: now,
      exp: now + 86400, // 24 小时后过期
      mode: "mock",
    }),
  )
  // mock 签名为固定占位，真实后端会校验并拒绝此签名
  const signature = "mock_signature_sellpilot_2026"
  return `${header}.${payload}.${signature}`
}

/**
 * 模拟登录 API —— 后端未就绪时使用 mock 数据。
 * 接入真实后端时，替换为：
 *   import { request } from "@/api/http"
 *   export const login = (payload: LoginRequest) =>
 *     request<LoginResponse>("/v1/auth/login", { method: "POST", body: JSON.stringify(payload) })
 */
export async function login(payload: LoginRequest): Promise<LoginResponse> {
  await new Promise((resolve) => setTimeout(resolve, 600 + Math.random() * 400))

  if (payload.username !== MOCK_USER.username || payload.password !== "admin123") {
    throw new Error("用户名或密码错误")
  }

  return {
    token: generateMockJWT(),
    user: MOCK_USER,
  }
}
