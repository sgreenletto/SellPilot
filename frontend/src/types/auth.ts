export interface LoginRequest {
  username: string
  password: string
}

export interface UserInfo {
  id: string
  username: string
  displayName: string
  avatar?: string
}

/** 后端 POST /api/v1/auth/login 响应 */
export interface LoginResponse {
  access_token: string
  token_type: string
}
