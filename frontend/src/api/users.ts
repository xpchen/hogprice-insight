import request from './request'

export interface AdminRole {
  id: number
  code: string
  name: string
}

export interface AdminUser {
  id: number
  username: string
  display_name?: string
  is_active: boolean
  roles: string[]
  created_at: string
}

export interface CreateAdminUserPayload {
  username: string
  password: string
  display_name?: string
  role_codes: string[]
}

export interface UpdateAdminUserPayload {
  display_name?: string
  is_active?: boolean
  role_codes?: string[]
}

export const usersApi = {
  getRoles: () => request.get<AdminRole[]>('/admin/roles'),
  getUsers: () => request.get<AdminUser[]>('/admin/users'),
  createUser: (payload: CreateAdminUserPayload) => request.post<AdminUser>('/admin/users', payload),
  updateUser: (userId: number, payload: UpdateAdminUserPayload) =>
    request.patch<AdminUser>(`/admin/users/${userId}`, payload),
  resetPassword: (userId: number, newPassword: string) =>
    request.post<{ message: string }>(`/admin/users/${userId}/reset-password`, { new_password: newPassword })
}
