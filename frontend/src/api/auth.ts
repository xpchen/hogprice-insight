import request from './request'

export interface LoginForm {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface UserInfo {
  id: number
  username: string
  display_name?: string
  roles: string[]
}

export interface ChangePasswordForm {
  old_password: string
  new_password: string
}

export const authApi = {
  login: (username: string, password: string) => {
    const params = new URLSearchParams()
    params.append('username', username)
    params.append('password', password)
    return request.post<TokenResponse>('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })
  },
  
  getMe: () => {
    return request.get<UserInfo>('/auth/me')
  },

  changePassword: (payload: ChangePasswordForm) => {
    return request.post<{ message: string }>('/auth/change-password', payload)
  }
}
