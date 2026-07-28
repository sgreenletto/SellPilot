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

export interface LoginResponse {
  token: string
  user: UserInfo
}
