import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi, type UserInfo } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref<UserInfo | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))
  
  const setToken = (newToken: string) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }
  
  const clearToken = () => {
    token.value = null
    localStorage.removeItem('token')
    user.value = null
  }
  
  const fetchUserInfo = async () => {
    try {
      const userInfo = await authApi.getMe()
      user.value = userInfo
      return userInfo
    } catch (error) {
      clearToken()
      throw error
    }
  }
  
  return {
    user,
    token,
    setToken,
    clearToken,
    fetchUserInfo
  }
})
