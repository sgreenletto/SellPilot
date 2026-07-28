export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface AuthUser {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}
