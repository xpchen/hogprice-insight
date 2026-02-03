/**
 * 调试工具
 * 在开发环境中启用，帮助调试API请求
 */

export const debugLog = (message: string, data?: any) => {
  if (import.meta.env.DEV) {
    console.log(`[DEBUG] ${message}`, data || '')
  }
}

export const debugError = (message: string, error: any) => {
  if (import.meta.env.DEV) {
    console.error(`[ERROR] ${message}`, error)
    if (error.response) {
      console.error('Response:', error.response.data)
      console.error('Status:', error.response.status)
      console.error('Headers:', error.response.headers)
    }
  }
}
